# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

String Authority is a comprehensive data management system for cataloging, authenticating, and tracking the provenance of collectible electric guitars. The system processes guitar data through JSON validation, fuzzy matching for duplicate detection, and PostgreSQL storage with UUID v7 primary keys.

## Development Commands

### Dependencies
```bash
# Install dependencies using UV (preferred)
uv add psycopg2-binary jsonschema

# Or manually install
uv pip install psycopg2-binary jsonschema
```

### Database Setup
```bash
# Create database schema
psql -U string_authority_user -d string_authority -f database/create.sql

# Database connection uses db_config.json or environment variables:
# DB_HOST, DB_NAME, DB_USER, DB_PASSWORD
```

### Main Application Commands
```bash
# Process single guitar JSON file
python guitar_processor_cli.py --file sample_single.json --verbose

# Process batch guitar data
python guitar_processor_cli.py --file sample_batch.json --verbose

# Generate sample data files
python guitar_processor_cli.py --create-samples

# Interactive mode for data entry
python guitar_processor_cli.py --interactive

# Basic entry point (placeholder)
python main.py
```

## Architecture Overview

### Core Components

1. **GuitarDataProcessor** (`uniqueness_management_system.py`): Main processing engine that handles data validation, duplicate detection, and database operations
2. **GuitarDataValidator** (`uniqueness_management_system.py`): JSON schema validation and business rule enforcement
3. **CLI Interface** (`guitar_processor_cli.py`): Command-line interface for processing guitar data files

### Data Flow

1. **Input**: JSON files containing manufacturer, model, individual guitar, and created_by field data (VARCHAR(100), e.g., "guitar_processor_cli_v1.0.0" or user identifier)
2. **Validation**: JSON schema validation using jsonschema library
3. **Duplicate Detection**: Fuzzy string matching using PostgreSQL trigrams and Python difflib
4. **Database Operations**: PostgreSQL with UUID v7 primary keys and foreign key relationships

### Database Schema

- **manufacturers**: Guitar manufacturers (Gibson, Fender, etc.)
- **product_lines**: Model families (Les Paul, Stratocaster, etc.)
- **models**: Specific model-year combinations
- **individual_guitars**: Historically significant instruments
- **specifications**: Technical specifications and features

- **market_valuations**: Historical pricing data
- **data_sources**: Source attribution and reliability scoring

### Key Design Patterns

- **Dependency Resolution**: Automatically resolves manufacturer → product line → model → individual guitar relationships
- **Fuzzy Matching**: Uses PostgreSQL trigrams and confidence scoring (95%+ auto-merge, 85-95% manual review)
- **Transaction Safety**: Batch processing with rollback on failures
- **created_by field**: Tracks data origin using created_by field (VARCHAR(100)) for complete data lineage, storing identifiers like "guitar_processor_cli_v1.0.0" or user names

### Data Formats

Guitar data is submitted as JSON with nested structures:
- `manufacturer`: Company information
- `model`: Model specifications and production details
- `individual_guitar`: Specific instrument with serial numbers and significance


See `sample_single.json` and `sample_batch.json` for examples.

### PostgreSQL Extensions

Required extensions:
- `pg_uuidv7`: UUID v7 generation for distributed compatibility
- `pg_trgm`: Trigram indexing for fuzzy text matching

### Error Handling

The system provides detailed error reporting for:
- JSON schema validation failures
- Database connection issues
- Duplicate detection conflicts
- Foreign key resolution problems

## Local Development Utilities

### Database Queries
- Correct way to run PSQL queries from command line in local environment: `psql -h localhost -U string_authority_user -d string_authority -c "[SQL command here]"`
