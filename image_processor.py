#!/usr/bin/env python3
"""
Simple Image Processor for Guitar Registry
Uploads images to Cloudinary and saves metadata to database
"""

import os
import sys
import argparse
import json
import psycopg2
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from pathlib import Path

# Image processing
from PIL import Image
import io

# Cloudinary
import cloudinary
import cloudinary.uploader

@dataclass
class ImageConfig:
    """Configuration for image processing"""
    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str
    db_host: str
    db_port: str
    db_name: str
    db_user: str
    db_password: str

@dataclass
class ImageUploadResult:
    """Result of image upload and processing"""
    image_id: str
    storage_key: str
    original_url: str
    thumbnail_url: str
    small_url: str
    medium_url: str
    large_url: str
    xlarge_url: str
    width: int
    height: int
    aspect_ratio: float
    dominant_color: str
    file_size: int
    mime_type: str

class SimpleImageProcessor:
    """Simplified image processor for guitar registry"""
    
    # Image size variants
    VARIANTS = {
        'thumbnail': 150,
        'small': 400,
        'medium': 800,
        'large': 1600,
        'xlarge': 2400
    }
    
    def __init__(self, config: ImageConfig):
        self.config = config
        
        # Configure Cloudinary
        cloudinary.config(
            cloud_name=config.cloudinary_cloud_name,
            api_key=config.cloudinary_api_key,
            api_secret=config.cloudinary_api_secret
        )
        
        # Database connection
        self.db_conn = psycopg2.connect(
            host=config.db_host,
            port=config.db_port,
            database=config.db_name,
            user=config.db_user,
            password=config.db_password
        )
    
    def upload_image(self, 
                    image_path: str,
                    entity_type: str,
                    entity_id: str,
                    image_type: str = 'primary',
                    is_primary: bool = False,
                    caption: Optional[str] = None,
                    uploaded_by: Optional[str] = None) -> ImageUploadResult:
        """
        Upload an image and save to database
        
        Args:
            image_path: Path to image file
            entity_type: Type of entity (manufacturer, model, individual_guitar, etc)
            entity_id: UUID of the entity
            image_type: Type of image (primary, logo, gallery, etc)
            is_primary: Whether this is the primary image for the entity
            caption: Optional caption for the image
            uploaded_by: UUID of user who uploaded (optional)
            
        Returns:
            ImageUploadResult with all URLs and metadata
        """
        print(f"Processing image: {image_path}")
        
        # Validate file exists
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load and process image
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Extract metadata
        metadata = self._extract_metadata(image_data, image_path)
        
        # Generate storage path
        image_hash = hashlib.sha256(image_data).hexdigest()[:16]
        storage_path = f"guitars/{entity_type}/{entity_id}/{image_type}/{image_hash}"
        
        print(f"Uploading to Cloudinary: {storage_path}")
        
        # Upload to Cloudinary with variants
        upload_result = self._upload_to_cloudinary(image_data, storage_path)
        
        # Save to database
        image_id = self._save_to_database(
            entity_type, entity_id, image_type, is_primary, caption,
            metadata, upload_result, uploaded_by
        )
        
        # Ensure eager transformations exist
        eager_urls = upload_result.get('eager', [])
        if len(eager_urls) < 5:
            raise ValueError("Cloudinary upload failed to generate all required variants")
        
        return ImageUploadResult(
            image_id=image_id,
            storage_key=upload_result['public_id'],
            original_url=upload_result['secure_url'],
            thumbnail_url=eager_urls[0]['secure_url'],
            small_url=eager_urls[1]['secure_url'],
            medium_url=eager_urls[2]['secure_url'],
            large_url=eager_urls[3]['secure_url'],
            xlarge_url=eager_urls[4]['secure_url'],
            width=metadata['width'],
            height=metadata['height'],
            aspect_ratio=metadata['aspect_ratio'],
            dominant_color=metadata['dominant_color'],
            file_size=metadata['file_size'],
            mime_type=metadata['mime_type']
        )
    
    def _extract_metadata(self, image_data: bytes, image_path: str) -> Dict:
        """Extract metadata from image"""
        img = Image.open(io.BytesIO(image_data))
        
        # Basic dimensions
        width, height = img.size
        aspect_ratio = round(width / height, 3)
        
        # Dominant color
        dominant_color = self._get_dominant_color(img)
        
        # File info
        file_size = len(image_data)
        mime_type = Image.MIME.get(img.format, 'image/jpeg')
        
        return {
            'width': width,
            'height': height,
            'aspect_ratio': aspect_ratio,
            'dominant_color': dominant_color,
            'file_size': file_size,
            'mime_type': mime_type,
            'original_filename': os.path.basename(image_path)
        }
    
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
    
    def _upload_to_cloudinary(self, image_data: bytes, storage_path: str) -> Dict:
        """Upload image to Cloudinary with eager transformations"""
        eager_transformations = [
            {'width': size, 'crop': 'limit', 'quality': 'auto', 'fetch_format': 'auto'}
            for size in self.VARIANTS.values()
        ]
        
        result = cloudinary.uploader.upload(
            image_data,
            public_id=storage_path,
            eager=eager_transformations,
            eager_async=False,  # Wait for transformations to complete
            overwrite=False,
            resource_type='image',
            tags=['string_authority'],
            context={
                'uploaded_at': datetime.now(timezone.utc).isoformat(),
                'processor_version': '2.0'
            }
        )
        
        return result
    
    def _save_to_database(self, entity_type: str, entity_id: str, image_type: str,
                         is_primary: bool, caption: Optional[str], metadata: Dict,
                         upload_result: Dict, uploaded_by: Optional[str]) -> str:
        """Save image metadata to database"""
        
        # If setting as primary, unset any existing primary
        if is_primary:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE images 
                    SET is_primary = FALSE 
                    WHERE entity_type = %s AND entity_id = %s AND is_primary = TRUE
                """, (entity_type, entity_id))
        
        # Get next display order
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(MAX(display_order), 0) + 1 
                FROM images 
                WHERE entity_type = %s AND entity_id = %s
            """, (entity_type, entity_id))
            display_order = cursor.fetchone()[0]
        
        # Get eager URLs from upload result
        eager_urls = upload_result.get('eager', [])
        if len(eager_urls) < 5:
            raise ValueError("Cloudinary upload failed to generate all required variants")
        
        # Insert image record
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO images (
                    entity_type, entity_id, image_type, is_primary, display_order, caption,
                    storage_provider, storage_key, original_url,
                    thumbnail_url, small_url, medium_url, large_url, xlarge_url,
                    original_filename, mime_type, file_size_bytes, width, height,
                    aspect_ratio, dominant_color, uploaded_by, validation_status,
                    tags, description
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    'cloudinary', %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, 'approved',
                    %s, %s
                ) RETURNING id
            """, (
                entity_type, entity_id, image_type, is_primary, display_order, caption,
                upload_result['public_id'], upload_result['secure_url'],
                eager_urls[0]['secure_url'],
                eager_urls[1]['secure_url'],
                eager_urls[2]['secure_url'],
                eager_urls[3]['secure_url'],
                eager_urls[4]['secure_url'],
                metadata['original_filename'], metadata['mime_type'], metadata['file_size'],
                metadata['width'], metadata['height'],
                metadata['aspect_ratio'], metadata['dominant_color'], uploaded_by,
                ['string_authority', entity_type, image_type],
                f"Uploaded via SimpleImageProcessor at {datetime.now(timezone.utc).isoformat()}"
            ))
            
            image_id = cursor.fetchone()[0]
            self.db_conn.commit()
            
            return image_id
    
    def create_duplicate(self, original_image_id: str, target_entity_type: str,
                        target_entity_id: str, image_type: str = 'gallery',
                        is_primary: bool = False, caption: Optional[str] = None,
                        duplicate_reason: Optional[str] = None) -> str:
        """Create a duplicate image for another entity"""
        
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT create_image_duplicate(%s, %s, %s, %s, %s, %s, %s)
            """, (original_image_id, target_entity_type, target_entity_id, 
                  image_type, is_primary, caption, duplicate_reason))
            
            duplicate_id = cursor.fetchone()[0]
            self.db_conn.commit()
            
            return duplicate_id
    
    def list_entity_images(self, entity_type: str, entity_id: str) -> list:
        """List all images for an entity"""
        with self.db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM get_entity_images(%s, %s)
            """, (entity_type, entity_id))
            
            return cursor.fetchall()
    
    def close(self):
        """Close database connection"""
        if self.db_conn:
            self.db_conn.close()

def load_config(cloudinary_config_path: str = "cloudinary_config.json", db_config_path: str = "db_config.json") -> ImageConfig:
    """Load configuration from files"""
    
    # Load Cloudinary config
    if os.path.exists(cloudinary_config_path):
        with open(cloudinary_config_path, 'r') as f:
            cloudinary_config = json.load(f)
    else:
        # Create template Cloudinary config file
        template_config = {
            "cloudinary_cloud_name": "your_cloud_name",
            "cloudinary_api_key": "your_api_key", 
            "cloudinary_api_secret": "your_api_secret"
        }
        
        with open(cloudinary_config_path, 'w') as f:
            json.dump(template_config, f, indent=2)
        
        print(f"Created template Cloudinary config file: {cloudinary_config_path}")
        print("Please edit it with your Cloudinary credentials and run again.")
        sys.exit(1)
    
    # Load database config
    if os.path.exists(db_config_path):
        with open(db_config_path, 'r') as f:
            db_config = json.load(f)
    else:
        print(f"Database config file not found: {db_config_path}")
        sys.exit(1)
    
    # Combine configs
    config_data = {
        "cloudinary_cloud_name": cloudinary_config["cloudinary_cloud_name"],
        "cloudinary_api_key": cloudinary_config["cloudinary_api_key"],
        "cloudinary_api_secret": cloudinary_config["cloudinary_api_secret"],
        "db_host": db_config["host"],
        "db_port": db_config["port"],
        "db_name": db_config["database"],
        "db_user": db_config["user"],
        "db_password": db_config["password"]
    }
    
    return ImageConfig(**config_data)

def main():
    parser = argparse.ArgumentParser(description="Upload images to Guitar Registry")
    parser.add_argument("image_path", help="Path to image file")
    parser.add_argument("entity_type", help="Entity type (manufacturer, model, individual_guitar)")
    parser.add_argument("entity_id", help="UUID of the entity")
    parser.add_argument("--image-type", default="primary", help="Image type (primary, logo, gallery, etc)")
    parser.add_argument("--is-primary", action="store_true", help="Set as primary image")
    parser.add_argument("--caption", help="Image caption")
    parser.add_argument("--cloudinary-config", default="cloudinary_config.json", help="Cloudinary config file path")
    parser.add_argument("--db-config", default="db_config.json", help="Database config file path")
    parser.add_argument("--create-duplicate", help="Create duplicate for another entity (format: entity_type:entity_id)")
    parser.add_argument("--duplicate-reason", help="Reason for duplicate")
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.cloudinary_config, args.db_config)
    
    # Initialize processor
    processor = SimpleImageProcessor(config)
    
    try:
        # Upload image
        result = processor.upload_image(
            image_path=args.image_path,
            entity_type=args.entity_type,
            entity_id=args.entity_id,
            image_type=args.image_type,
            is_primary=args.is_primary,
            caption=args.caption
        )
        
        print(f"\n✅ Image uploaded successfully!")
        print(f"Image ID: {result.image_id}")
        print(f"Storage Key: {result.storage_key}")
        print(f"Original URL: {result.original_url}")
        print(f"Medium URL: {result.medium_url}")
        print(f"Dimensions: {result.width}x{result.height}")
        print(f"File size: {result.file_size:,} bytes")
        
        # Create duplicate if requested
        if args.create_duplicate:
            duplicate_parts = args.create_duplicate.split(':')
            if len(duplicate_parts) == 2:
                target_entity_type, target_entity_id = duplicate_parts
                duplicate_id = processor.create_duplicate(
                    result.image_id,
                    target_entity_type,
                    target_entity_id,
                    image_type="gallery",
                    is_primary=False,
                    caption=f"Duplicate of {args.caption or 'original image'}",
                    duplicate_reason=args.duplicate_reason or "Manual duplicate"
                )
                print(f"\n✅ Duplicate created: {duplicate_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        processor.close()

if __name__ == "__main__":
    main() 