"""
Guitar Registry Image Processing Module
Handles image ingestion, validation, and storage management
"""

import os
import hashlib
import mimetypes
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import json
import requests
from PIL import Image
import io
import uuid
from pathlib import Path

# You would install these with: uv add cloudinary pillow colormath
import cloudinary
import cloudinary.uploader
from colormath.color_objects import sRGBColor, HSVColor
from colormath.color_conversions import convert_color

@dataclass
class ImageMetadata:
    """Metadata extracted from processed images"""
    width: int
    height: int
    aspect_ratio: float
    dominant_color: str
    file_size: int
    mime_type: str
    
@dataclass
class ProcessedImage:
    """Result of image processing"""
    storage_key: str
    original_url: str
    variants: Dict[str, str]
    metadata: ImageMetadata
    hash: str

class GuitarImageProcessor:
    """Handles image processing for the guitar registry"""
    
    # Image size variants for responsive loading
    VARIANTS = {
        'thumbnail': 150,
        'small': 400,
        'medium': 800,
        'large': 1600,
        'xlarge': 2400
    }
    
    # Valid image types for different contexts
    IMAGE_TYPES = {
        'manufacturer': ['logo', 'primary', 'gallery'],
        'product_line': ['primary', 'gallery', 'catalog'],
        'model': ['primary', 'gallery', 'headstock', 'body_front', 'body_back', 
                  'neck', 'hardware', 'detail', 'catalog'],
        'individual_guitar': ['primary', 'gallery', 'headstock', 'serial_number',
                             'body_front', 'body_back', 'neck', 'hardware', 
                             'detail', 'certificate', 'documentation', 'historical']
    }
    
    def __init__(self, config: Dict):
        """Initialize with storage configuration"""
        self.config = config
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=config['cloudinary_cloud_name'],
            api_key=config['cloudinary_api_key'],
            api_secret=config['cloudinary_api_secret']
        )
        
    def process_image(self, 
                     image_source: str, 
                     entity_type: str,
                     entity_id: str,
                     image_type: str,
                     source_info: Optional[Dict] = None,
                     working_dir: Optional[Path] = None) -> ProcessedImage:
        """
        Process an image from URL or file path
        
        Args:
            image_source: URL or file path to image
            entity_type: Type of entity (manufacturer, model, etc)
            entity_id: UUID of the entity
            image_type: Type of image (primary, gallery, etc)
            source_info: Attribution and source information
            
        Returns:
            ProcessedImage with all variants and metadata
        """
        # Validate image type for entity
        if image_type not in self.IMAGE_TYPES.get(entity_type, []):
            raise ValueError(f"Invalid image type '{image_type}' for entity type '{entity_type}'")
        
        # Load image
        image_data, original_filename = self._load_image(image_source, working_dir)
        
        # Extract metadata
        metadata = self._extract_metadata(image_data)
        
        # Generate hash for deduplication
        image_hash = self._generate_hash(image_data)
        
        # Create storage path
        storage_path = f"guitars/{entity_type}/{entity_id}/{image_type}/{image_hash}"
        
        # Upload to Cloudinary with transformations
        upload_result = self._upload_with_variants(image_data, storage_path)
        
        return ProcessedImage(
            storage_key=upload_result['public_id'],
            original_url=upload_result['secure_url'],
            variants=self._extract_variant_urls(upload_result['public_id']),
            metadata=metadata,
            hash=image_hash
        )
    
    def _load_image(self, source: str, working_dir: Optional[Path] = None) -> Tuple[bytes, str]:
        """Load image from URL or file path (absolute/relative)"""
        if source.startswith(('http://', 'https://')):
            # Existing URL handling
            response = requests.get(source, timeout=30)
            response.raise_for_status()
            filename = source.split('/')[-1]
            return response.content, filename
        else:
            # File path handling (absolute or relative)
            file_path = Path(source)
            if not file_path.is_absolute():
                # Resolve relative paths from the working directory (JSON file location)
                base_dir = working_dir or Path.cwd()
                # Remove the leading ./ if present
                source_path = source
                if source_path.startswith('./'):
                    source_path = source_path[2:]
                file_path = base_dir / source_path
            
            if not file_path.exists():
                raise FileNotFoundError(f"Image file not found: {file_path}")
            
            with open(file_path, 'rb') as f:
                return f.read(), file_path.name
    
    def _extract_metadata(self, image_data: bytes) -> ImageMetadata:
        """Extract metadata from image"""
        img = Image.open(io.BytesIO(image_data))
        
        # Basic dimensions
        width, height = img.size
        aspect_ratio = round(width / height, 3)
        
        # Dominant color (simplified - you'd want more sophisticated analysis)
        dominant_color = self._get_dominant_color(img)
        
        # File info
        file_size = len(image_data)
        mime_type = Image.MIME.get(img.format, 'image/jpeg')
        
        return ImageMetadata(
            width=width,
            height=height,
            aspect_ratio=aspect_ratio,
            dominant_color=dominant_color,
            file_size=file_size,
            mime_type=mime_type
        )
    
    def _get_dominant_color(self, img: Image.Image) -> str:
        """Extract dominant color as hex"""
        # Resize for faster processing
        img_small = img.resize((150, 150))
        
        # Convert to RGB if necessary
        if img_small.mode != 'RGB':
            img_small = img_small.convert('RGB')
        
        # Get colors
        colors = img_small.getcolors(150 * 150)
        if not colors:
            return '#000000'
        
        # Find most common color
        most_common = max(colors, key=lambda x: x[0])
        rgb = most_common[1]
        
        # Convert to hex
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
    
    def _generate_hash(self, image_data: bytes) -> str:
        """Generate SHA-256 hash of image for deduplication"""
        return hashlib.sha256(image_data).hexdigest()[:16]
    
    def _upload_with_variants(self, image_data: bytes, storage_path: str) -> Dict:
        """Upload image to Cloudinary with eager transformations"""
        eager_transformations = [
            {'width': size, 'crop': 'limit', 'quality': 'auto', 'fetch_format': 'auto'}
            for size in self.VARIANTS.values()
        ]
        
        result = cloudinary.uploader.upload(
            image_data,
            public_id=storage_path,
            eager=eager_transformations,
            eager_async=True,
            overwrite=False,
            resource_type='image',
            tags=['string_authority'],
            context={
                'uploaded_at': datetime.utcnow().isoformat(),
                'processor_version': '1.0'
            }
        )
        
        return result
    
    def _extract_variant_urls(self, public_id: str) -> Dict[str, str]:
        """Generate URLs for all variants"""
        base_url = f"https://res.cloudinary.com/{self.config['cloudinary_cloud_name']}/image/upload"
        
        variants = {}
        for name, width in self.VARIANTS.items():
            transformation = f"w_{width},c_limit,q_auto,f_auto"
            variants[name] = f"{base_url}/{transformation}/{public_id}"
        
        return variants

class ImageAssociationManager:
    """Manages associations between images and entities"""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def associate_image(self,
                       entity_type: str,
                       entity_id: str,
                       image_id: str,
                       image_type: str,
                       is_primary: bool = False,
                       caption: Optional[str] = None,
                       user_id: Optional[str] = None) -> str:
        """Create association between image and entity"""
        
        # If setting as primary, unset any existing primary
        if is_primary:
            self._unset_primary(entity_type, entity_id)
        
        # Get next display order
        display_order = self._get_next_display_order(entity_type, entity_id)
        
        # Insert association
        query = """
            INSERT INTO image_associations 
            (entity_type, entity_id, image_id, image_type, 
             display_order, is_primary, caption, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        cursor = self.db.cursor()
        cursor.execute(query, (
            entity_type, entity_id, image_id, image_type,
            display_order, is_primary, caption, user_id
        ))
        
        association_id = cursor.fetchone()[0]
        self.db.commit()
        
        return association_id
    
    def _unset_primary(self, entity_type: str, entity_id: str):
        """Remove primary flag from existing images"""
        query = """
            UPDATE image_associations 
            SET is_primary = FALSE
            WHERE entity_type = %s AND entity_id = %s AND is_primary = TRUE
        """
        cursor = self.db.cursor()
        cursor.execute(query, (entity_type, entity_id))
    
    def _get_next_display_order(self, entity_type: str, entity_id: str) -> int:
        """Get next display order for entity"""
        query = """
            SELECT COALESCE(MAX(display_order), -1) + 1
            FROM image_associations
            WHERE entity_type = %s AND entity_id = %s
        """
        cursor = self.db.cursor()
        cursor.execute(query, (entity_type, entity_id))
        return cursor.fetchone()[0]

class ImageSourceValidator:
    """Validates and categorizes image sources"""
    
    @staticmethod
    def categorize_source(source: str) -> str:
        """Determine source type: url, absolute_path, or relative_path"""
        if source.startswith(('http://', 'https://')):
            return 'url'
        elif Path(source).is_absolute():
            return 'absolute_path'
        else:
            return 'relative_path'
    
    @staticmethod
    def validate_source(source: str, base_dir: Optional[Path] = None) -> bool:
        """Validate that source is accessible"""
        source_type = ImageSourceValidator.categorize_source(source)
        
        if source_type == 'url':
            try:
                response = requests.head(source, timeout=10)
                return response.status_code == 200
            except:
                return False
        else:
            file_path = Path(source)
            if not file_path.is_absolute():
                base = base_dir or Path.cwd()
                file_path = base / file_path
            return file_path.exists() and file_path.is_file()

# Example usage in your CLI tool
def process_guitar_images(guitar_data: Dict, processor: GuitarImageProcessor, db_connection):
    """Process images for guitar entities"""
    
    association_manager = ImageAssociationManager(db_connection)
    
    # Process manufacturer logo if provided
    if 'manufacturer' in guitar_data and 'logo_url' in guitar_data['manufacturer']:
        try:
            processed = processor.process_image(
                guitar_data['manufacturer']['logo_url'],
                'manufacturer',
                guitar_data['manufacturer']['id'],
                'logo',
                source_info={'source_type': 'web_scrape'}
            )
            
            # Save to database
            image_id = save_processed_image(processed, db_connection, 'manufacturer', guitar_data['manufacturer']['id'], 'logo')
            
            # Create association
            association_manager.associate_image(
                'manufacturer',
                guitar_data['manufacturer']['id'],
                image_id,
                'logo',
                is_primary=True
            )
            
        except Exception as e:
            print(f"Error processing manufacturer logo: {e}")
    
    # Process model images
    if 'model' in guitar_data and 'images' in guitar_data['model']:
        for idx, image_info in enumerate(guitar_data['model']['images']):
            try:
                processed = processor.process_image(
                    image_info['url'],
                    'model',
                    guitar_data['model']['id'],
                    image_info.get('type', 'gallery'),
                    source_info=image_info.get('source')
                )
                
                image_id = save_processed_image(processed, db_connection, 'model', guitar_data['model']['id'], image_info.get('type', 'gallery'))
                
                association_manager.associate_image(
                    'model',
                    guitar_data['model']['id'],
                    image_id,
                    image_info.get('type', 'gallery'),
                    is_primary=(idx == 0),  # First image is primary
                    caption=image_info.get('caption')
                )
                
            except Exception as e:
                print(f"Error processing model image: {e}")

def save_processed_image(processed: ProcessedImage, db_connection, entity_type: str, entity_id: str, image_type: str) -> str:
    """Save processed image to database"""
    query = """
        INSERT INTO images (
            entity_type, entity_id, image_type, storage_provider, storage_key, original_url,
            thumbnail_url, small_url, medium_url, large_url, xlarge_url,
            width, height, aspect_ratio, dominant_color,
            file_size_bytes, mime_type
        ) VALUES (
            %s, %s, %s, 'cloudinary', %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s
        ) RETURNING id
    """
    
    cursor = db_connection.cursor()
    cursor.execute(query, (
        entity_type,
        entity_id,
        image_type,
        processed.storage_key,
        processed.original_url,
        processed.variants.get('thumbnail'),
        processed.variants.get('small'),
        processed.variants.get('medium'),
        processed.variants.get('large'),
        processed.variants.get('xlarge'),
        processed.metadata.width,
        processed.metadata.height,
        processed.metadata.aspect_ratio,
        processed.metadata.dominant_color,
        processed.metadata.file_size,
        processed.metadata.mime_type
    ))
    
    image_id = cursor.fetchone()[0]
    db_connection.commit()
    
    return image_id

def process_guitar_with_photos(guitar_data, working_dir=None, db_connection=None, processor=None, cloudinary_config=None):
    """Process guitar data with support for URL and local file images"""
    
    if db_connection is None:
        raise ValueError("Database connection is required")
    
    if processor is None:
        raise ValueError("Guitar data processor is required")
    
    # Phase 1: Create entities (unchanged)
    entity_ids = processor.process_submission(guitar_data)
    
    if not entity_ids.get('success'):
        print(f"✗ Entity creation failed: {entity_ids.get('conflicts', [])}")
        return entity_ids
    
    # Phase 2: Process mixed image sources
    if cloudinary_config is None:
        # Fallback to environment variables
        cloudinary_config = {
            'cloudinary_cloud_name': os.getenv('CLOUDINARY_CLOUD_NAME'),
            'cloudinary_api_key': os.getenv('CLOUDINARY_API_KEY'),
            'cloudinary_api_secret': os.getenv('CLOUDINARY_API_SECRET')
        }
    
    image_processor = GuitarImageProcessor(cloudinary_config)
    
    processed_images = []
    
    # Get all entity IDs (both created and updated)
    all_entity_ids = {}
    
    # Add created entities
    if 'ids_created' in entity_ids:
        all_entity_ids.update(entity_ids['ids_created'])
    
    # Add updated entities (we need to get these from the database)
    if 'actions_taken' in entity_ids:
        for action in entity_ids['actions_taken']:
            if 'update' in action.lower():
                # For now, let's process individual_guitar photos regardless of whether it was created or updated
                if 'individual_guitar' in guitar_data:
                    # Get the guitar ID from the database
                    cursor = db_connection.cursor()
                    cursor.execute(
                        "SELECT id FROM individual_guitars WHERE serial_number = %s",
                        (guitar_data['individual_guitar'].get('serial_number'),)
                    )
                    result = cursor.fetchone()
                    if result:
                        all_entity_ids['individual_guitar'] = result[0]
    
    for entity_type in ['manufacturer', 'product_line', 'model', 'individual_guitar']:
        if entity_type in all_entity_ids and all_entity_ids[entity_type]:
            photos = extract_photos_for_entity(guitar_data, entity_type)
            
            for photo_spec in photos:
                try:
                    # Validate source accessibility
                    # The working_dir is the JSON file's parent directory
                    # The source paths are relative to the JSON file location
                    base_dir = Path(working_dir) if working_dir else Path.cwd()
                    # Remove the leading ./ if present
                    source_path = photo_spec['source']
                    if source_path.startswith('./'):
                        source_path = source_path[2:]
                    resolved_path = base_dir / source_path
                    
                    if not resolved_path.exists():
                        print(f"⚠ Skipping inaccessible image: {photo_spec['source']}")
                        continue
                    
                    # Process image (handles URLs and files uniformly)
                    processed_image = image_processor.process_image(
                        photo_spec['source'],
                        entity_type,
                        all_entity_ids[entity_type],
                        photo_spec.get('type', 'gallery'),
                        source_info={
                            'source_type': ImageSourceValidator.categorize_source(photo_spec['source']),
                            'original_path': photo_spec['source']
                        },
                        working_dir=Path(working_dir) if working_dir else None
                    )
                    
                    # Save to database with enhanced metadata
                    image_id = save_processed_image(processed_image, db_connection, entity_type, all_entity_ids[entity_type], photo_spec.get('type', 'gallery'))
                    
                    # Update image with additional metadata (is_primary, caption, etc.)
                    if photo_spec.get('is_primary', False):
                        cursor = db_connection.cursor()
                        cursor.execute("""
                            UPDATE images 
                            SET is_primary = TRUE, caption = %s
                            WHERE id = %s
                        """, (photo_spec.get('caption'), image_id))
                        db_connection.commit()
                    
                    processed_images.append({
                        'entity_type': entity_type,
                        'entity_id': all_entity_ids[entity_type],
                        'image_id': image_id,
                        'source': photo_spec['source'],
                        'type': photo_spec.get('type', 'gallery')
                    })
                    
                except Exception as e:
                    print(f"✗ Error processing image {photo_spec['source']}: {e}")
                    # Continue with other images rather than failing entire batch
    
    # Add image processing results to the entity creation results
    entity_ids['processed_images'] = processed_images
    entity_ids['image_count'] = len(processed_images)
    
    return entity_ids

def extract_photos_for_entity(guitar_data, entity_type):
    """Extract photo specifications for a given entity type"""
    photos = []
    
    if entity_type == 'manufacturer' and 'manufacturer' in guitar_data:
        if 'logo_source' in guitar_data['manufacturer']:
            photos.append({
                'source': guitar_data['manufacturer']['logo_source'],
                'type': 'logo',
                'is_primary': True
            })
    
    elif entity_type == 'individual_guitar' and 'individual_guitar' in guitar_data:
        if 'photos' in guitar_data['individual_guitar']:
            photos.extend(guitar_data['individual_guitar']['photos'])
    
    return photos