#!/bin/bash

# Database Recreation Script - VPS Version
# Run as: ./database-recycle-vps.sh
# Prerequisite: string_authority_user must exist
#   Create with: sudo -u postgres psql -c "CREATE USER string_authority_user WITH PASSWORD 'your_password';"

set -e

echo "🔄 Starting database recreation (VPS version)..."

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_status() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Check if running on Linux
if [[ "$(uname)" != "Linux" ]]; then
    print_error "This script is for VPS/Linux environments. Use database-recycle.sh for local development."
    exit 1
fi

# Step 1: Drop existing database
echo "📋 Step 1: Dropping existing database (if it exists)..."
sudo -u postgres psql -c "DROP DATABASE IF EXISTS string_authority;"
print_status "Database dropped (or didn't exist)"

# Step 2: Create database
echo "📋 Step 2: Creating database..."
sudo -u postgres psql -c "CREATE DATABASE string_authority OWNER string_authority_user;"
print_status "Database created"

# Step 3: Grant privileges
echo "📋 Step 3: Granting privileges..."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE string_authority TO string_authority_user;"
sudo -u postgres psql -d string_authority -c "GRANT ALL PRIVILEGES ON SCHEMA public TO string_authority_user;"
print_status "Privileges granted"

# Step 4: Create extensions
echo "📋 Step 4: Creating extensions..."
sudo -u postgres psql -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
sudo -u postgres psql -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"pg_uuidv7\";"
sudo -u postgres psql -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"pg_trgm\";"
print_status "Extensions created"

# Step 5: Run schema
echo "📋 Step 5: Creating database structure..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/database/create.sql" ]; then
    sudo -u postgres psql -d string_authority -f "$SCRIPT_DIR/database/create.sql"
    print_status "Schema created"
else
    print_error "database/create.sql not found!"
    exit 1
fi

# Step 6: Grant privileges on created objects
echo "📋 Step 6: Granting privileges on created objects..."
sudo -u postgres psql -d string_authority -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO string_authority_user;"
sudo -u postgres psql -d string_authority -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO string_authority_user;"
sudo -u postgres psql -d string_authority -c "GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO string_authority_user;"
print_status "Object privileges granted"

# Step 7: Verify
echo "📋 Step 7: Verifying..."
TABLE_COUNT=$(sudo -u postgres psql -d string_authority -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
print_status "Database contains $TABLE_COUNT tables"

# Show table list
echo "📋 Tables created:"
sudo -u postgres psql -d string_authority -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"

echo ""
print_status "🎉 Database recreation completed!"
echo ""
echo "Next steps:"
echo "1. Run your data processing scripts"
echo "2. Or import data using: sudo -u postgres psql -d string_authority -f your_data_file.sql"
echo ""