# Image Integration for String Authority database processor

This document describes the enhanced image processing capabilities that have been integrated into the String Authority database processor system.

## Overview

The String Authority database processor now supports processing images from multiple sources:
- **Remote URLs** (HTTP/HTTPS)
- **Local file paths** (absolute and relative)
- **Mixed sources** within the same submission

## Enhanced JSON Schema

### Manufacturer Logos

```json
{
  "manufacturer": {
    "name": "Gibson Guitar Corporation",
    "logo_source": "./logos/gibson-logo.png"  // Can be URL or file path
  }
}
```

### Individual Guitar Photos

```json
{
  "individual_guitar": {
    "photos": [
      {
        "source": "https://example.com/guitar-front.jpg",  // URL
        "type": "body_front",
        "caption": "Front view of Jessica", 
        "is_primary": true
      },
      {
        "source": "./images/serial-number.jpg",  // Relative path
        "type": "serial_number",
        "caption": "Serial number close-up"
      },
      {
        "source": "/absolute/path/headstock.png",  // Absolute path
        "type": "headstock"
      }
    ]
  }
}
```

## Supported Image Types

- `primary` - Main image for the entity
- `logo` - Manufacturer or brand logo
- `gallery` - General gallery image
- `headstock` - Headstock detail
- `serial_number` - Serial number close-up
- `body_front` - Front view of guitar body
- `body_back` - Back view of guitar body
- `neck` - Neck detail
- `hardware` - Hardware components
- `detail` - Other detail shots
- `certificate` - Documentation/certificates
- `documentation` - Other documentation
- `historical` - Historical photos

## Processing Workflow

### Two-Phase Processing

1. **Phase 1: Entity Creation**
   - Process guitar data through existing `GuitarDataProcessor`
   - Create/resolve manufacturer → product_line → model → individual_guitar entities
   - Return entity IDs for use in Phase 2

2. **Phase 2: Image Processing**
   - Extract photo URLs/paths from input JSON
   - Validate source accessibility
   - Process images using enhanced `GuitarImageProcessor`
   - Create associations using direct schema approach

### Source Validation

The system automatically validates image sources before processing:

- **URLs**: Checks HTTP status code (200 OK)
- **File paths**: Verifies file exists and is accessible
- **Relative paths**: Resolved from input file location

### Error Handling

- Individual image failures don't break the entire batch
- Inaccessible sources are skipped with warnings
- Processing continues with remaining images

## Usage Examples

### Command Line

```bash
# Process a file with mixed image sources
python guitar_processor_cli.py --file example_guitar_with_images.json --verbose

# Process a batch of files
python guitar_processor_cli.py --file batch_guitars.json --verbose
```

### Working Directory Context

Relative paths are resolved from the location of the input JSON file:

```bash
# If example_guitar_with_images.json is in /data/guitars/
# And it contains "./images/serial.jpg"
# The system will look for /data/guitars/images/serial.jpg
python guitar_processor_cli.py --file /data/guitars/example_guitar_with_images.json
```

### Environment Variables

Required for Cloudinary integration:

```bash
export CLOUDINARY_CLOUD_NAME="your_cloud_name"
export CLOUDINARY_API_KEY="your_api_key"
export CLOUDINARY_API_SECRET="your_api_secret"
```

## Database Integration

Images are stored in the `images` table with:

- **Entity associations**: Direct links to manufacturers, models, individual guitars
- **Storage metadata**: Cloudinary URLs, file sizes, dimensions
- **Processing metadata**: Upload timestamps, validation status
- **Source attribution**: Original URLs/paths, source types

## Key Features

1. **Unified Processing**: Single method handles URLs and files
2. **Path Resolution**: Automatic resolution of relative paths
3. **Source Tracking**: Full attribution of image origins
4. **Validation**: Pre-processing validation of accessibility
5. **Graceful Degradation**: Individual failures don't break batches
6. **Working Directory Context**: Relative paths resolved from input location
7. **Non-breaking**: Existing guitar processing works unchanged
8. **Entity-first**: Guarantees valid UUIDs before image processing
9. **Transactional**: All-or-nothing processing prevents orphaned records
10. **Flexible**: Supports photos on any entity type

## Sample Files

- `example_guitar_with_images.json` - Demonstrates mixed image sources
- `example_guitar_models.json` - Basic guitar data without images
- `vintage_guitars_sample.json` - Sample vintage guitar data

## Troubleshooting

### Common Issues

1. **File not found**: Check relative path resolution from JSON file location
2. **URL inaccessible**: Verify URL is publicly accessible
3. **Cloudinary errors**: Check environment variables and API credentials
4. **Database connection**: Ensure database is running and accessible

### Debug Mode

Use `--verbose` flag for detailed processing information:

```bash
python guitar_processor_cli.py --file data.json --verbose
```

This will show:
- Image source validation results
- Processing progress for each image
- Detailed error messages
- Processing statistics 