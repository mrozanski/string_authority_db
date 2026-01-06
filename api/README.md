# String Authority Database Search API

A Flask-based REST API for searching guitar models and individual instruments in the String Authority database.

## Features

- **Model Search**: Search for guitar models by name, manufacturer, and year with fuzzy matching
- **Individual Guitar Search**: Search for specific guitars by serial number or model characteristics
- **Fuzzy Search**: Supports partial matches, case-insensitive search, and typo tolerance
- **Pagination**: Configurable page sizes with metadata
- **Year Extraction**: Automatically extracts years from model names
- **Multi-field Search**: Searches across model names, product lines, and manufacturer names

## Quick Start

### Installation

```bash
# Install dependencies
uv add flask flask-cors psycopg2

# Or using pip
pip install flask flask-cors psycopg2
```

### Configuration

The API uses the existing `db_config.json` file or environment variables for database connection:

Environment variables:
- `DB_HOST`: Database host
- `DB_NAME`: Database name  
- `DB_USER`: Database user
- `DB_PASSWORD`: Database password
- `DB_PORT`: Database port (default: 5432)
- `MAX_PAGE_SIZE`: Maximum results per page (default: 10)

### Running the API

```bash
# Start the development server
uv run python api/app.py

# Or using python directly
python api/app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Health Check

```
GET /api/health
```

Returns the API health status and database connection status.

### Model Search

```
GET /api/search/models
```

Search for guitar models with fuzzy matching.

**Required Parameters:**
- `model_name` (string): Model name to search for

**Optional Parameters:**
- `manufacturer_name` (string): Filter by manufacturer name
- `year` (integer): Filter by production year (1900-2030)
- `page` (integer): Page number, defaults to 1
- `page_size` (integer): Results per page, defaults to 10, max configurable

**Example Requests:**
```bash
# Basic search
curl "http://localhost:5000/api/search/models?model_name=Les Paul"

# With manufacturer filter
curl "http://localhost:5000/api/search/models?model_name=Stratocaster&manufacturer_name=Fender"

# With year and pagination
curl "http://localhost:5000/api/search/models?model_name=Les Paul Standard&year=1959&page=1&page_size=5"
```

**Response Format:**
```json
{
  "models": [
    {
      "id": "019820ad-be5e-7e78-af44-bec1e789f601",
      "model_name": "Les Paul Standard",
      "manufacturer_name": "Gibson",
      "year": 1959,
      "product_line_name": "Les Paul",
      "description": "The Gibson Les Paul Standard..."
    }
  ],
  "total_records": 25,
  "current_page": 1,
  "page_size": 10,
  "total_pages": 3
}
```

### Individual Guitar Search

```
GET /api/search/instruments
```

Search for individual guitars/instruments.

**Search Types:**

1. **Serial Number Search:**
   - `serial_number` (string): Serial number to search for

2. **Unknown Serial Search:**
   - `unknown_serial` (boolean): Set to `true`
   - `model_name` (string, optional): Model name
   - `manufacturer_name` (string, optional): Manufacturer name
   - `year_estimate` (integer, optional): Estimated year (1900-2030)

**Optional Parameters:**
- `page` (integer): Page number, defaults to 1
- `page_size` (integer): Results per page, defaults to 10, max configurable

**Example Requests:**
```bash
# Serial number search
curl "http://localhost:5000/api/search/instruments?serial_number=9-0824"

# Unknown serial search by model
curl "http://localhost:5000/api/search/instruments?unknown_serial=true&model_name=Les Paul Standard&manufacturer_name=Gibson"

# Unknown serial with year estimate
curl "http://localhost:5000/api/search/instruments?unknown_serial=true&model_name=Stratocaster&year_estimate=1965"
```

**Response Format:**
```json
{
  "individual_guitars": [
    {
      "id": "019820ad-be5e-7e78-af44-bec1e789f601",
      "serial_number": "9-0824",
      "year_estimate": null,
      "description": null,
      "significance_level": "historic",
      "significance_notes": "Famous 1959 Les Paul",
      "current_estimated_value": "500000.00",
      "condition_rating": null,
      "model_name": "Les Paul Standard",
      "manufacturer_name": "Gibson",
      "product_line_name": "Les Paul"
    }
  ],
  "total_records": 1,
  "current_page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

## Search Features

### Fuzzy Matching

The API uses PostgreSQL trigram matching for fuzzy text search:
- Handles typos and misspellings
- Supports partial matches
- Case-insensitive search
- Similarity scoring for result ranking

### Year Extraction

Model names containing years are automatically processed:
```bash
# These are equivalent:
/api/search/models?model_name=Les Paul 1959
/api/search/models?model_name=Les Paul&year=1959
```

### Multi-field Search

Search terms are matched across multiple fields:
- Model names
- Product line names (Les Paul, Stratocaster, etc.)
- Manufacturer names (for manufacturer filtering)

### Hybrid Data Model Support

The API handles both complete and incomplete data:
- **Complete**: Models with full manufacturer/product line relationships
- **Fallback**: Individual guitars with only manufacturer/model name text fields

## Error Handling

The API returns standard HTTP status codes:

- `200 OK`: Successful search
- `400 Bad Request`: Invalid parameters or missing required fields
- `404 Not Found`: Endpoint not found
- `500 Internal Server Error`: Database or server errors

**Error Response Format:**
```json
{
  "error": "Bad Request",
  "message": "model_name parameter is required"
}
```

## Performance Considerations

- Database connection pooling for concurrent requests
- PostgreSQL trigram indexes for fast fuzzy search
- Pagination to limit response sizes
- Efficient JOIN queries with proper indexing

## Architecture

```
api/
├── app.py                 # Flask application entry point
├── config.py             # Configuration management
├── database.py           # Database connection and utilities
├── routes/
│   └── search_routes.py  # API route definitions
└── search/
    ├── model_search.py   # Model search logic
    ├── instrument_search.py # Instrument search logic
    └── utils.py          # Search utilities and helpers
```

## Testing

Run the test suite to verify the API functionality:

```bash
uv run python test_api.py
```

This will test:
- Module imports
- Flask app creation
- Database configuration
- Search service initialization