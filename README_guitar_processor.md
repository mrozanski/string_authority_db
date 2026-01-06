# String Authority Database Processor - Complete Documentation

This document describes the complete String Authority database processor system including JSON input structure, image processing workflow, and usage examples. This documentation is designed to be comprehensive enough for both human developers and LLM agents to prepare JSON data for ingestion.

## Complete Submission Structure

A complete submission requires these top-level properties:

```json
{
  "manufacturer": { ... },
  "model": { ... },
  "individual_guitar": { ... }
}
```

**Note:** All fields are case-sensitive. Use exact field names as shown.

## 1. Manufacturer

**Required fields:**
- `name` (string, 1-100 chars): The official company name as it appears in catalogs or legal documents

**Optional fields:**
- `display_name` (string, max 50 chars): Short display name for UI (e.g., "Gibson" instead of "Gibson Guitar Corporation")
- `country` (string, max 50 chars): Country where the company is headquartered
- `founded_year` (integer, 1800-2030): Year the company was established
- `website` (string, URI format): Current company website URL
- `status` (string, enum: "active", "defunct", "acquired", default: "active")
- `notes` (string): Additional historical or contextual information
- `logo_source` (string, file path or URL): Path to company logo image file

### Manufacturer Example

```json
{
  "manufacturer": {
    "name": "Fender Musical Instruments Corporation",
    "display_name": "Fender",
    "country": "USA",
    "founded_year": 1946,
    "website": "https://www.fender.com",
    "status": "active",
    "notes": "Founded by Leo Fender in Fullerton, California",
    "logo_source": "images/fender_logo.png"
  }
}
```

## 2. Model

**Required fields:**
- `manufacturer_name` (string): Will be matched case-insensitively against existing manufacturers. **IMPORTANT:** The manufacturer must already exist in the database or be included in the same submission.
- `name` (string, 1-150 chars): Model name as it appears in catalogs
- `year` (integer, 1900-2030): Year the model was introduced

**Optional fields:**
- `product_line_name` (string): Product series or line name (e.g., "Stratocaster", "Les Paul")
- `production_type` (string, enum: "mass", "limited", "custom", "prototype", "one-off", default: "mass")
- `production_start_date` (string, date format: YYYY-MM-DD)
- `production_end_date` (string, date format: YYYY-MM-DD)
- `estimated_production_quantity` (integer, min 1): Total units produced
- `msrp_original` (number, min 0): Original retail price
- `currency` (string, max 3 chars, default: "USD"): ISO currency code
- `description` (string): Detailed description of the model
- `specifications` (object): Technical specifications (see Section 5)

### Model Example

```json
{
  "model": {
    "manufacturer_name": "Fender Musical Instruments Corporation",
    "product_line_name": "Stratocaster",
    "name": "Stratocaster",
    "year": 1954,
    "production_type": "mass",
    "production_start_date": "1954-01-01",
    "production_end_date": null,
    "estimated_production_quantity": 1000000,
    "msrp_original": 249.50,
    "currency": "USD",
    "description": "The original electric guitar that defined rock music",
    "specifications": {
      "body_wood": "Alder",
      "neck_wood": "Maple",
      "fingerboard_wood": "Maple",
      "scale_length_inches": 25.5,
      "num_frets": 21,
      "pickup_configuration": "SSS"
    }
  }
}
```

## 3. Individual Guitar

**CRITICAL: You must provide exactly ONE of these three identification methods (they are mutually exclusive):**

**Option A - Complete Model Reference (Recommended for complete data):**
- `model_reference` (object, required)
  - `manufacturer_name` (string, required): Will be matched case-insensitively against existing manufacturers
  - `model_name` (string, required): Will be matched case-insensitively against existing models  
  - `year` (integer, required): Must match exactly (no case conversion)
  - **All three sub-fields are required when using this option**

**Option B - Fallback Manufacturer + Model:**
- `manufacturer_name_fallback` (string, max 100 chars, required): Use when exact manufacturer match not found
- `model_name_fallback` (string, max 150 chars, required): Use when exact model match not found

**Option C - Fallback Manufacturer + Description:**
- `manufacturer_name_fallback` (string, max 100 chars, required): Use when exact manufacturer match not found
- `description` (string, required): Detailed description when model information is incomplete

**Optional fields:**
- `nickname` (string, max 50 chars): Guitar's nickname (e.g., "Pearly Gates", "Lucille")
- `year_estimate` (string, max 50 chars): Use format like "circa 1959", "late 1950s", "early 1960s"
- `serial_number` (string, max 50 chars): Guitar's unique serial number
- `production_date` (string, date format: YYYY-MM-DD): Specific production date if known
- `production_number` (integer): Production sequence number if known
- `significance_level` (string, enum: "historic", "notable", "rare", "custom", default: "notable")
- `significance_notes` (string): Explanation of why this guitar is significant
- `current_estimated_value` (number): Current market value estimate
- `last_valuation_date` (string, date format: YYYY-MM-DD): Date of last valuation
- `condition_rating` (string, enum: "mint", "excellent", "very_good", "good", "fair", "poor", "relic")
- `modifications` (string): Description of any modifications made to the guitar
- `provenance_notes` (string): History of ownership and usage
- `specifications` (object): Individual-specific specifications (see Section 5)
- `photos` (array): Array of photo objects (see Section 7)

### Individual Guitar Examples

#### Option A - Complete Model Reference (All three sub-fields required)
```json
{
  "individual_guitar": {
    "model_reference": {
      "manufacturer_name": "Fender Musical Instruments Corporation",
      "model_name": "Stratocaster",
      "year": 1954
    },
    "nickname": "The First",
    "serial_number": "01234",
    "production_date": "1954-06-15",
    "significance_level": "historic",
    "significance_notes": "One of the first 100 Stratocasters ever produced",
    "current_estimated_value": 50000.00,
    "condition_rating": "excellent",
    "provenance_notes": "Original owner, never modified"
  }
}
```

#### Option B - Fallback Manufacturer + Model
```json
{
  "individual_guitar": {
    "manufacturer_name_fallback": "Fender",
    "model_name_fallback": "Stratocaster",
    "nickname": "Old Reliable",
    "year_estimate": "circa 1959",
    "serial_number": "12345",
    "significance_level": "notable",
    "current_estimated_value": 25000.00,
    "condition_rating": "very_good"
  }
}
```

#### Option C - Fallback Manufacturer + Description
```json
{
  "individual_guitar": {
    "manufacturer_name_fallback": "Unknown Manufacturer",
    "description": "Vintage electric guitar with single coil pickups, likely from the 1950s",
    "nickname": "Mystery Guitar",
    "year_estimate": "1950s",
    "significance_level": "notable",
    "current_estimated_value": 15000.00
  }
}
```

## 4. Source Attribution

**Required fields:**
- `source_name` (string, 1-100 chars): Name of the source (e.g., "Fender 1954 Catalog", "Guitar World Magazine")

**Optional fields:**
- `source_type` (string, enum: "manufacturer_catalog", "auction_record", "museum", "book", "website", "manual_entry", "price_guide"): Type of source
- `url` (string, URI format, max 500 chars): URL to the source if available online
- `isbn` (string, max 20 chars): ISBN for books
- `publication_date` (string, date format: YYYY-MM-DD): Date the source was published
- `reliability_score` (integer, 1-10): 1=least reliable, 10=most reliable
- `notes` (string): Additional information about the source

## 5. Specifications Object

**All fields optional:** Include only the specifications that are known and verified.

- `body_wood` (string, max 50 chars): Primary wood used for guitar body
- `neck_wood` (string, max 50 chars): Primary wood used for neck
- `fingerboard_wood` (string, max 50 chars): Wood used for fingerboard
- `scale_length_inches` (number, 20-30): Scale length in inches
- `num_frets` (integer, 12-36): Number of frets
- `nut_width_inches` (number, 1.0-2.5): Width of nut in inches
- `neck_profile` (string, max 50 chars): Neck shape profile
- `bridge_type` (string, max 50 chars): Type of bridge
- `pickup_configuration` (string, max 150 chars): Pickup styles, brand, and arrangement (e.g., "2 x single coils (SS)", "2 x PAF humbuckers", "Seymour Duncan JB TB-4 humbucker in the bridge and two Seymour Duncan SSL-6 single coils in the middle and neck positions")
- `electronics_description` (string): Description of electronics and controls
- `hardware_finish` (string, max 50 chars): Finish of hardware (e.g., "Chrome", "Gold", "Black")
- `body_finish` (long text): Finish of guitar body (e.g., "Nitrocellulose Cherry Sunburst", "Olympic White, Lake placid Blue, ", "Sandblasted satin urethane, multiple colors")
- `weight_lbs` (number, 1-20): Weight in pounds
- `case_included` (boolean): Whether case was included
- `case_type` (string, max 50 chars): Type of case if included

### One model can have multiple specification objects

You can choose to combine options in one specification object or to use multiple specification objects if the differences are significant.

For guitar models the specifications property can be either:

- An array of specification objects
- A single specification object
- Not present

For individual guitars the specifications property can be either:

- A single specification object
- Not present

## Decision Framework

**Create separate specification records when physical construction or functionality differs:**

1. **Different materials** (wood types, finish chemistry)
2. **Different electronics** (pickup types, wiring configurations)
3. **Different hardware** (bridge types, tuner types)
4. **Different physical dimensions** (scale length, fret count, nut width)

**Combine variations in single record when only cosmetic differences exist:**

1. **Color variations** of same finish type
2. **Hardware color** variations (chrome vs gold vs black)
3. **Minor aesthetic differences** that don't affect construction

## Examples

### ✅ Good: Combine Color Variations
```json
{
  "body_finish": "Polyurethane gloss - Olympic White, Lake Placid Blue, Ivory, Silver",
  "hardware_finish": "Chrome, Gold, Black nickel",
  "body_wood": "Alder",
  "pickup_configuration": "3 x single coils (SSS) - Fender V-Mod II"
}
```

### ✅ Good: Separate Records for Different Woods
```json
[
  {
    "body_finish": "Polyurethane gloss - 3-Color Sunburst, Natural",
    "body_wood": "Ash",
    "neck_wood": "Maple",
    "pickup_configuration": "3 x single coils (SSS) - Fender V-Mod II"
  },
  {
    "body_finish": "Polyurethane gloss - Olympic White, Black",
    "body_wood": "Alder", 
    "neck_wood": "Maple",
    "pickup_configuration": "3 x single coils (SSS) - Fender V-Mod II"
  }
]
```

### ✅ Good: Separate Records for Different Electronics
```json
[
  {
    "body_finish": "Nitrocellulose lacquer - Heritage Cherry Sunburst, Tobacco Burst",
    "pickup_configuration": "2 x PAF humbuckers - Gibson BurstBucker Pro",
    "electronics_description": "2 volume, 2 tone, 3-way toggle"
  },
  {
    "body_finish": "Nitrocellulose lacquer - Heritage Cherry Sunburst, Tobacco Burst", 
    "pickup_configuration": "2 x PAF humbuckers - Gibson BurstBucker Pro with coil tap",
    "electronics_description": "2 volume (push-pull coil tap), 2 tone, 3-way toggle"
  }
]
```

### ✅ Good: Separate Records for Different Bridge Types
```json
[
  {
    "body_finish": "Polyurethane - Vintage White, Shell Pink",
    "bridge_type": "Vintage-style tremolo",
    "pickup_configuration": "HSS - Humbucker bridge, 2 single coils"
  },
  {
    "body_finish": "Polyurethane - Vintage White, Shell Pink",
    "bridge_type": "Floyd Rose locking tremolo", 
    "pickup_configuration": "HSS - Humbucker bridge, 2 single coils"
  }
]
```

### ✅ Good: Separate Records for Scale Length Variations
```json
[
  {
    "scale_length_inches": 25.5,
    "num_frets": 22,
    "nut_width_inches": 1.625,
    "neck_profile": "Modern C",
    "fingerboard_wood": "Rosewood, Maple"
  },
  {
    "scale_length_inches": 24.75,
    "num_frets": 22, 
    "nut_width_inches": 1.687,
    "neck_profile": "Vintage 50s",
    "fingerboard_wood": "Rosewood"
  }
]
```

### ✅ Good: Complex Real-World Example - PRS SE Custom 24
```json
[
  {
    "body_finish": "Polyurethane gloss - Turquoise, Black Cherry, Blood Orange, Vintage Sunburst",
    "body_wood": "Mahogany with maple cap",
    "neck_wood": "Maple", 
    "fingerboard_wood": "Rosewood",
    "scale_length_inches": 25.0,
    "num_frets": 24,
    "pickup_configuration": "2 x humbuckers - PRS 85/15 S with coil tap",
    "bridge_type": "PRS patented tremolo",
    "hardware_finish": "Nickel"
  },
  {
    "body_finish": "Polyurethane gloss - Black Gold Burst, Violet", 
    "body_wood": "Mahogany with quilted maple cap",
    "neck_wood": "Maple",
    "fingerboard_wood": "Ebony",
    "scale_length_inches": 25.0,
    "num_frets": 24,
    "pickup_configuration": "2 x humbuckers - PRS 85/15 S with coil tap",
    "bridge_type": "PRS patented tremolo", 
    "hardware_finish": "Nickel"
  }
]
```

### ❌ Avoid: Over-separation for Minor Variations
```json
// Don't create separate records for each color:
[
  {"body_finish": "Polyurethane gloss - Olympic White", "body_wood": "Alder"},
  {"body_finish": "Polyurethane gloss - Lake Placid Blue", "body_wood": "Alder"},
  {"body_finish": "Polyurethane gloss - Ivory", "body_wood": "Alder"}
]

// Instead combine:
{"body_finish": "Polyurethane gloss - Olympic White, Lake Placid Blue, Ivory", "body_wood": "Alder"}
```

### ❌ Avoid: Under-separation for Functional Differences  
```json
// Don't combine different pickup configurations:
{"pickup_configuration": "SSS Fender V-Mod II or HSS with Double Tap humbucker"}

// Instead separate:
[
  {"pickup_configuration": "3 x single coils (SSS) - Fender V-Mod II"},
  {"pickup_configuration": "HSS - Double Tap humbucker bridge, 2 V-Mod II single coils"}
]
```

## Quick Reference

**Combine when:** Colors, hardware finishes, minor aesthetic variations
**Separate when:** Woods, pickups, electronics, bridges, dimensions, finish chemistry

This approach ensures your data is both UI-friendly and accurately represents the real variations that matter to players and collectors.

## 6. Photo Object

**Required fields:**
- `source` (string, file path or URL): Path to image file or URL

**Optional fields:**
- `type` (string, enum: "body_front", "body_back", "headstock", "serial_number", "detail", "gallery", "logo", "catalog", "primary", "historical", default: "gallery")
- `caption` (string): Description of what the photo shows
- `is_primary` (boolean, default: false): Whether this is the main photo

### Photo Example

```json
{
  "photos": [
    {
      "source": "images/stratocaster_front.jpg",
      "type": "body_front",
      "caption": "Front view of 1954 Stratocaster",
      "is_primary": true
    },
    {
      "source": "images/stratocaster_serial.jpg",
      "type": "serial_number",
      "caption": "Serial number detail"
    }
  ]
}
```

## 7. Complete Submission Example

Here's a complete example showing all components together:

```json
{
  "manufacturer": {
    "name": "Fender Musical Instruments Corporation",
    "display_name": "Fender",
    "country": "USA",
    "founded_year": 1946,
    "website": "https://www.fender.com",
    "status": "active",
    "notes": "Founded by Leo Fender in Fullerton, California"
  },
  "model": {
    "manufacturer_name": "Fender Musical Instruments Corporation",
    "product_line_name": "Stratocaster",
    "name": "Stratocaster",
    "year": 1954,
    "production_type": "mass",
    "msrp_original": 249.50,
    "currency": "USD",
    "description": "The original electric guitar that defined rock music"
  },
  "individual_guitar": {
    "model_reference": {
      "manufacturer_name": "Fender Musical Instruments Corporation",
      "model_name": "Stratocaster",
      "year": 1954
    },
    "nickname": "The First",
    "serial_number": "01234",
    "production_date": "1954-06-15",
    "significance_level": "historic",
    "significance_notes": "One of the first 100 Stratocasters ever produced",
    "current_estimated_value": 50000.00,
    "condition_rating": "excellent"
  }
}
```

## 8. Image Processing Workflow

The String Authority database processor includes a comprehensive image processing system that automatically handles image uploads, metadata extraction, and database integration.

### Quick Reference

```bash
# Basic upload
uv run python image_processor.py <image_file> <entity_type> <entity_id> [options]

# Examples
uv run python image_processor.py logo.png manufacturer 0197bdb2-23c1-72ad-b5b1-c77f67d4896c --image-type logo --is-primary
uv run python image_processor.py guitar.jpg model 0197bda6-49cb-7642-b812-b7b1c2af7824 --image-type primary --is-primary --caption "1954 Stratocaster"
uv run python image_processor.py serial.jpg individual_guitar 0197bda6-49cb-7642-b812-b7b1c2af7824 --image-type serial_number
```

### Setup

#### 1. Install Dependencies

```bash
# Install required packages
pip install -r requirements-image.txt

# Or using uv
uv pip install -r requirements-image.txt
```

#### 2. Set up Cloudinary

1. Sign up for a free Cloudinary account at https://cloudinary.com
2. Get your credentials from the Dashboard:
   - Cloud Name
   - API Key
   - API Secret

#### 3. Create Configuration File

The script will automatically create a `cloudinary_config.json` template file on first run. Edit it with your credentials:

```json
{
  "cloudinary_cloud_name": "your_cloud_name",
  "cloudinary_api_key": "your_api_key",
  "cloudinary_api_secret": "your_api_secret"
}
```

### Usage

#### Basic Image Upload

```bash
# Upload a manufacturer logo
uv run python image_processor.py fender-logo.png manufacturer 01982004-3a25-75cf-832c-552b20e8975f --image-type logo --is-primary --caption "Fender Logo"

# Upload a model image
uv run python image_processor.py stratocaster.jpg model 0197bda6-49cb-7642-b812-b7b1c2af7824 --image-type primary --is-primary --caption "1954 Stratocaster"

# Upload an individual guitar image
uv run python image_processor.py guitar-serial.jpg individual_guitar 0197bda6-49cb-7642-b812-b7b1c2af7824 --image-type serial_number --caption "Serial Number Detail"
```

#### Create Duplicates

```bash
# Upload image and create duplicate for manufacturer
uv run python image_processor.py stratocaster.jpg model 0197bda6-49cb-7642-b812-b7b1c2af7824 \
  --image-type primary --is-primary --caption "1954 Stratocaster" \
  --create-duplicate "manufacturer:0197bdb2-23c1-72ad-b5b1-c77f67d4896c" \
  --duplicate-reason "Represents manufacturer as flagship example"
```

#### Custom Configuration Files

```bash
# Use custom config files
uv run python image_processor.py image.jpg manufacturer 0197bdb2-23c1-72ad-b5b1-c77f67d4896c \
  --cloudinary-config my-cloudinary.json \
  --db-config my-database.json
```

### Command Line Options

**Required Arguments:**
- `image_path`: Path to the image file
- `entity_type`: Type of entity (manufacturer, model, individual_guitar, product_line, specification, finish)
- `entity_id`: UUID of the entity

**Optional Arguments:**
- `--image-type`: Type of image (primary, logo, gallery, headstock, serial_number, body_front, body_back, neck, hardware, detail, certificate, documentation, historical)
- `--is-primary`: Set as primary image for the entity
- `--caption`: Image caption
- `--cloudinary-config`: Path to Cloudinary config file (default: cloudinary_config.json)
- `--db-config`: Path to database config file (default: db_config.json)
- `--create-duplicate`: Create duplicate for another entity (format: entity_type:entity_id)
- `--duplicate-reason`: Reason for creating duplicate

### Image Processing Examples

#### Upload Fender Logo

```bash
# Get Fender manufacturer ID
psql -d string_authority -c "SELECT id, name FROM manufacturers WHERE name LIKE '%Fender%';"

# Upload logo
uv run python image_processor.py fender-logo.png manufacturer 0197bdb2-23c1-72ad-b5b1-c77f67d4896c \
  --image-type logo --is-primary --caption "Fender Musical Instruments Corporation Logo"
```

#### Upload Stratocaster Image

```bash
# Get Stratocaster model ID
psql -d string_authority -c "SELECT id, name, year FROM models WHERE name = 'Stratocaster' AND year = 1954;"

# Upload image
uv run python image_processor.py 1954-stratocaster.jpg model 0197bda6-49cb-7642-b812-b7b1c2af7824 \
  --image-type primary --is-primary --caption "1954 Fender Stratocaster - The Original"
```

#### Upload Individual Guitar Image

```bash
# Get individual guitar ID
psql -d string_authority -c "SELECT id, serial_number FROM individual_guitars WHERE serial_number = '12345';"

# Upload serial number image
uv run python image_processor.py serial-12345.jpg individual_guitar 0197bda6-49cb-7642-b812-b7b1c2af7824 \
  --image-type serial_number --caption "Serial Number: 12345"
```

#### Create Duplicate for Manufacturer

```bash
# Upload model image and create duplicate for manufacturer
uv run python image_processor.py stratocaster.jpg model 0197bda6-49cb-7642-b812-b7b1c2af7824 \
  --image-type primary --is-primary --caption "1954 Stratocaster" \
  --create-duplicate "manufacturer:0197bdb2-23c1-72ad-b5b1-c77f67d4896c" \
  --duplicate-reason "Represents manufacturer as flagship example"
```

### Image Processing Features

- ✅ **Automatic image variants**: Creates thumbnail, small, medium, large, and xlarge versions
- ✅ **Metadata extraction**: Extracts dimensions, aspect ratio, dominant color, file size
- ✅ **Database integration**: Saves all metadata to PostgreSQL
- ✅ **Duplicate support**: Create duplicates for multiple entities (many-to-many)
- ✅ **Validation**: Ensures only one primary image per entity
- ✅ **Cloudinary integration**: Automatic upload with transformations
- ✅ **Error handling**: Comprehensive error checking and reporting

## 10. Batch Processing Support

The CLI supports both single submissions and batch processing with arrays of submissions:

### Single Submission
```json
{
  "manufacturer": { ... },
  "model": { ... },
  "individual_guitar": { ... }
}
```

### Batch Submission
```json
[
  {
    "manufacturer": { ... },
    "model": { ... }
  },
  {
    "model": { ... }
  },
  {
    "manufacturer": { ... },
    "model": { ... },
    "individual_guitar": { ... }
  }
]
```

**Note:** Each item in a batch can have different combinations of entities. The system processes them independently and provides a summary of results.

## 11. Smart Matching & Flexibility

The String Authority database processor system includes intelligent matching capabilities to make data ingestion more flexible while maintaining data integrity:

### **Case-Insensitive Name Matching**
- **Manufacturer names**: "Fender", "fender", "FENDER" all resolve to the same manufacturer
- **Model names**: "Stratocaster", "stratocaster", "STRATOCASTER" all resolve to the same model
- **Product line names**: Also matched case-insensitively

### **Fuzzy Matching for Similar Models**
- The system can detect similar models and suggest potential matches
- Confidence scores help determine whether to auto-merge or require manual review
- Prevents duplicate entries while allowing for minor variations in naming

### **Hybrid Data Approach**
- **Option A**: Complete model reference with exact matching (recommended)
- **Option B**: Fallback text fields when exact matches aren't available
- **Option C**: Minimal fallback with description when model info is incomplete

### **Benefits of This Approach**
- **Easier data ingestion** from various sources with different naming conventions
- **Reduced manual intervention** for common variations
- **Maintains data quality** through intelligent conflict resolution
- **Supports both structured and unstructured data** sources

## 12. Validation Rules

### Data Validation
- **String fields**: Have maximum length limits, must be quoted
- **Numeric fields**: Have minimum/maximum value constraints, no quotes
- **Date fields**: Must be in YYYY-MM-DD format as quoted strings
- **URI fields**: Must be valid URLs or file paths as quoted strings
- **Enum fields**: Must match exactly one of the specified values, case-sensitive
- **Required fields**: Cannot be null, missing, or empty strings
- **Optional fields**: Can be null, omitted entirely, or contain valid data
- **Field names**: Must be exactly as specified, case-sensitive

### **Critical Validation Rules**

#### Individual Guitar Identification
- **Exactly one identification method required**: You must provide either `model_reference` OR fallback fields, not both
- **Model reference validation**: If using `model_reference`, all three sub-fields (`manufacturer_name`, `model_name`, `year`) are required
- **Fallback validation**: If using fallback approach, you must provide `manufacturer_name_fallback` AND either `model_name_fallback` OR `description`

#### Field Dependencies
- **Manufacturer dependency**: `model.manufacturer_name` must reference an existing manufacturer in the database (or be included in the same submission)
- **Model dependency**: `individual_guitar.model_reference` must reference an existing model in the database (or be included in the same submission)
- **Serial number uniqueness**: Serial numbers must be unique across all individual guitars

#### Image Validation
- Only one primary image per entity
- Valid entity types: manufacturer, model, individual_guitar, product_line, specification, finish
- Valid image types: primary, logo, gallery, headstock, serial_number, body_front, body_back, neck, hardware, detail, certificate, documentation, historical
- Maximum file size: 10MB
- Supported formats: JPEG, PNG, WebP, AVIF

### **Critical Validation Notes**
- **Manufacturer names are matched case-insensitively** between manufacturer and model/individual_guitar objects (e.g., "Fender", "fender", "FENDER" all match)
- **Model names are matched case-insensitively** between model and individual_guitar objects (e.g., "Stratocaster", "stratocaster", "STRATOCASTER" all match)
- **Years must match exactly** between model and individual_guitar objects (e.g., 1954 must match 1954, not "1954")
- **Serial numbers must be unique** across all individual guitars
- **Date formats must be YYYY-MM-DD** (e.g., "1954-06-15", not "06/15/1954" or "June 15, 1954")

## 13. Database Schema

The system works with an enhanced database schema that includes:

### Core Tables
- `manufacturers`: Company information
- `models`: Guitar model specifications
- `individual_guitars`: Specific guitar instances with hybrid FK + fallback approach
- `specifications`: Technical details
- `data_sources`: Source attribution

### Image Management Tables
- `images`: Image metadata with direct entity associations
- `image_sources`: Image attribution and licensing
- Support for duplicates with `is_duplicate` and `original_image_id` fields
- Automatic primary image management
- Responsive image variants

### Hybrid Individual Guitar Schema
The `individual_guitars` table supports both approaches:
- **Foreign key reference**: `model_id` links to existing models (for complete data)
- **Fallback text fields**: `manufacturer_name_fallback`, `model_name_fallback`, `year_estimate`, `description` (for incomplete data)
- **Constraint**: Ensures either `model_id` OR fallback fields are provided

## 14. Troubleshooting

### Common Issues

1. **"Cloudinary upload failed"**: Check your Cloudinary credentials
2. **"Image file not found"**: Verify the image path is correct
3. **"Entity not found"**: Check the entity_type and entity_id are valid
4. **"Database connection failed"**: Verify database is running and credentials are correct
5. **"Validation failed"**: Check required fields and data format compliance
6. **"Year mismatch"**: Ensure year values match exactly between model and individual guitar (e.g., both must be 1954, not "1954")
7. **"Invalid date format"**: Use YYYY-MM-DD format for all dates
8. **"Missing dependency"**: Ensure referenced manufacturers and models exist in the database
9. **"Invalid individual guitar identification"**: Provide exactly one identification method (model_reference OR fallback fields)

### Debug Mode

For more verbose output, you can modify the scripts to add debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 15. Next Steps

After setting up your data and images, you can:

1. **Query images**: Use the database functions to retrieve images
2. **Create more duplicates**: Use the `create_duplicate` function
3. **Add image sources**: Add attribution information to `image_sources` table
4. **Build UI**: Use the image URLs to display images in your application
5. **Extend functionality**: Add custom validation rules or processing workflows

## 16. Example Queries

### Find if a model has a primary image

```sql
SELECT i.id, i.entity_type, i.entity_id, i.image_type, i.is_primary, i.caption, i.original_url
FROM images i
WHERE i.entity_type = 'model'
AND i.entity_id = '019820af-3caf-73d0-90ce-700d3f4a1f70'
```

### Get all images for an entity

```sql
SELECT * FROM get_entity_images('model', '019820af-3caf-73d0-90ce-700d3f4a1f70');
```

## 17. LLM Agent Guidelines

When preparing JSON data for ingestion, follow these guidelines:

1. **Use exact field names** as specified in this documentation
2. **Manufacturer names are case-insensitive** - "Fender", "fender", and "FENDER" will all match
3. **Model names are case-insensitive** - "Stratocaster", "stratocaster", and "STRATOCASTER" will all match
4. **Years must match exactly** - Use the same data type (both integer or both string)
5. **Include all required fields** for each object type
6. **Validate enum values** against the specified options
7. **Check field length limits** for string fields
8. **Verify numeric ranges** for numeric fields
9. **Use the complete examples** as templates for your data
10. **Test your JSON** with a JSON validator before submission
11. **Provide exactly one identification method** for individual guitars (model_reference OR fallback fields)
12. **Ensure field dependencies** are satisfied (manufacturers must exist before referencing them)
13. **Use batch processing** for multiple submissions to improve efficiency