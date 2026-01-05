# String Authority

A comprehensive data management system for cataloging, authenticating, and tracking the provenance of collectible electric guitars. Built for the future of instrument authentication with blockchain integration planned.

## 🎯 Vision

Building the definitive, decentralized registry for electric guitar heritage - where every instrument's story is permanently preserved, authenticated, and accessible to collectors, researchers, and enthusiasts worldwide.

## 🎸 Overview

String Authority addresses the fragmented landscape of vintage and collectible guitar documentation by providing:

- **Universal Cross-Brand Catalog**: Unlike existing brand-specific systems, this registry covers all manufacturers
- **Intelligent Duplicate Detection**: Advanced fuzzy matching prevents data duplication across sources
- **Provenance Tracking**: Complete instrument lifecycle documentation with cryptographic verification
- **Market Intelligence**: Historical pricing and valuation tracking
- **Expert Attribution**: Notable associations with famous players and performances

## 🚀 Features

### Data Processing Engine
- **JSON Schema Validation**: Ensures data integrity at input
- **Fuzzy String Matching**: Detects similar manufacturers/models using PostgreSQL trigrams
- **Dependency Resolution**: Automatically resolves manufacturer → model → individual guitar relationships
- **Batch Processing**: Handles single submissions or large data imports with transaction safety
- **Conflict Detection**: Identifies duplicates with confidence scoring and manual review flagging

### Database Design
- **Intelligent Granularity**: Mass-produced models vs. individual historically significant instruments
- **Comprehensive Specifications**: Detailed technical specs, finishes, modifications
- **Source Attribution**: Complete data lineage tracking with reliability scoring
- **Market Data**: Historical valuations and sales tracking
- **Expert Associations**: Notable players, recordings, and performances

### Command Line Interface
- **File Processing**: JSON file imports with validation and error reporting
- **Interactive Mode**: Real-time data entry and testing
- **Verbose Logging**: Detailed processing feedback and conflict resolution
- **Sample Generation**: Built-in test data creation

## 🛠 Technology Stack

- **Database**: PostgreSQL 15+ with pg_trgm and pg_uuidv7 extensions
- **Backend**: Python 3.8+ with psycopg2, jsonschema
- **Validation**: JSON Schema with custom business logic
- **Matching**: Trigram similarity and fuzzy string algorithms
- **IDs**: UUID v7 for distributed system compatibility

## 📋 Prerequisites

- PostgreSQL 15+ with contrib extensions
- Python 3.8+
- Required Python packages: `psycopg2-binary`, `jsonschema`

## ⚡ Quick Start

### 1. Database Setup

```bash
# Install postgres if not installed
brew install postgresql@17

# Create database and user
psql -d postgres -c "CREATE DATABASE string_authority OWNER string_authority_user;"

# Start postgres
brew services start postgresql@17

# Create user
psql -d postgres -c "CREATE USER string_authority_user WITH PASSWORD 'password_here';"

# Install required extensions
cd database
git clone https://github.com/fboulnois/pg_uuidv7
cd pg_uuidv7
make
make install

## Grant privileges
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE string_authority TO string_authority_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO string_authority_user;"


## Create extensions
psql -U string_authority_user -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"pg_uuidv7\";"

## Create structure
psql -U string_authority_user -d string_authority -f database/create.sql

## Insert test data (test data not in git)
psql -U string_authority_user -d string_authority -f test-data/test-data.sql



```
### 2. Environment Configuration

```bash
# Set database connection
export DB_HOST=localhost
export DB_NAME=string_authority
export DB_USER=string_authority_user
export DB_PASSWORD=your_password

# Or create db_config.json
{
  "host": "localhost",
  "database": "string_authority", 
  "user": "string_authority_user",
  "password": "your_password"
}
```

### 3. Install Dependencies

```bash
# Install dependencies using UV
uv add psycopg2-binary jsonschema

# Or if you prefer to install manually
uv pip install psycopg2-binary jsonschema
```

### 4. Test the System

```bash
# Generate sample data
python guitar_processor_cli.py --create-samples

# Test single submission
python guitar_processor_cli.py --file sample_single.json --verbose

# Test batch processing
python guitar_processor_cli.py --file sample_batch.json --verbose

# Interactive mode
python guitar_processor_cli.py --interactive
```

## 📖 Usage Examples

### Single Guitar Submission

```json
{
  "manufacturer": {
    "name": "Gibson Guitar Corporation",
    "country": "USA",
    "founded_year": 1902,
    "status": "active"
  },
  "model": {
    "manufacturer_name": "Gibson Guitar Corporation",
    "product_line_name": "Les Paul",
    "name": "Les Paul Standard",
    "year": 1959,
    "production_type": "mass",
    "msrp_original": 247.50
  },
  "individual_guitar": {
    "model_reference": {
      "manufacturer_name": "Gibson Guitar Corporation", 
      "model_name": "Les Paul Standard",
      "year": 1959
    },
    "serial_number": "9-0824",
    "significance_level": "historic",
    "current_estimated_value": 500000.00
  }
}
```

### CLI Processing

```bash
# Process with detailed output
python guitar_processor_cli.py --file my_guitars.json --verbose

# Expected output:
✓ Connected to database: string_authority@localhost
✓ Loaded JSON file: my_guitars.json
🎸 Processing guitar data...
✓ Single Submission Result:
  Actions: Manufacturer insert, Model insert, Guitar insert
  IDs Created: 3 entities
⏱ Processing completed in 0.15 seconds
```

### Batch Processing

```bash
# Large dataset import
python guitar_processor_cli.py --file vintage_collection.json

# Batch results:
✓ Batch Processing Summary:
  Processed: 150/150
  Successful: 147
  Failed: 3
  Manual Review Needed: 2
```

## 🏗 Database Schema

### Core Tables
- **manufacturers**: Guitar manufacturers (Gibson, Fender, etc.)
- **product_lines**: Model families (Les Paul, Stratocaster, etc.)
- **models**: Specific model-year combinations
- **individual_guitars**: Historically significant instruments
- **specifications**: Detailed technical specifications


### Supporting Tables

- **market_valuations**: Historical pricing data
- **data_sources**: Source attribution and reliability
- **citations**: Data lineage tracking
- **users** & **contributions**: Community management

### Key Features
- **Trigram indexes** for fuzzy text matching
- **UUID v7 primary keys** for distributed compatibility
- **Check constraints** for data integrity
- **Partial indexes** for query optimization
- **Audit triggers** for change tracking

## 🔍 Data Validation

### Duplicate Detection
- **Manufacturer fuzzy matching**: Handles spelling variations
- **Model year-specific tracking**: Prevents duplicate entries
- **Serial number uniqueness**: Enforced across all guitars
- **Confidence scoring**: 95%+ auto-merge, 85-95% manual review

### Schema Validation
- **JSON Schema enforcement** for all entity types
- **Foreign key resolution** with clear error messages
- **Business rule validation** (dates, ranges, enums)
- **Cross-reference checking** between related entities

## 🚦 Roadmap

### Phase 1: Core System ✅ 
- [x] Database schema design
- [x] Data validation engine
- [x] CLI processing tool
- [x] Duplicate detection
- [x] Basic documentation

### Phase 2: API & Integration 🚧
- [ ] REST API server
- [ ] Authentication system
- [ ] Data source integrations
- [ ] Bulk import tools
- [ ] API documentation

### Phase 3: Blockchain Integration 🔮
- [ ] Cryptographic attestations
- [ ] EAS integration
- [ ] Decentralized storage
- [ ] NFT compatibility
- [ ] Cross-chain support

### Phase 4: Advanced Features 🔮
- [ ] Machine learning for authenticity
- [ ] Image recognition
- [ ] Market prediction models
- [ ] Expert verification network
- [ ] Mobile applications

## 🤝 Contributing

We welcome contributions! The system is designed to handle data from multiple sources:

### Supported Data Sources
- Manufacturer catalogs and specifications
- Auction records and sale data
- Museum and collection databases
- Expert knowledge and verification
- Historical documentation

### Data Quality Standards
- **Source attribution required** for all submissions
- **Reliability scoring** for source credibility
- **Expert verification** for significant claims
- **Community review** for disputed information

## 📄 License

This code is licensed under the GNU Affero General Public License. See the LICENSE file for details.

## 🆘 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review sample data formats

---

*"Every guitar has a story. We're building the place to tell it."*
