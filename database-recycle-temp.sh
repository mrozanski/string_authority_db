#!/bin/bash

# TEMPORARY Database Migration Script
# Migrates from guitar_registry to string_authority
# Run this ONCE to transition your local dev database to the new naming convention.
# After running this, use database-recycle.sh for future recreations.

set -e  # Exit on any error

echo "🔄 Starting database migration: guitar_registry → string_authority..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if OLD database exists and drop it
echo "📋 Step 1: Dropping OLD database 'guitar_registry' (if it exists)..."
if psql -d postgres -c "SELECT 1 FROM pg_database WHERE datname='guitar_registry';" | grep -q 1; then
    print_warning "Database 'guitar_registry' exists. Dropping it..."
    psql -d postgres -c "DROP DATABASE guitar_registry;" || {
        print_error "Failed to drop database. Make sure no connections are active."
        exit 1
    }
    print_status "Old database 'guitar_registry' dropped successfully"
else
    print_status "Database 'guitar_registry' does not exist (no need to drop)"
fi

# Check if NEW database already exists and drop it (in case of re-run)
echo "📋 Step 2: Dropping NEW database 'string_authority' (if it exists from a previous run)..."
if psql -d postgres -c "SELECT 1 FROM pg_database WHERE datname='string_authority';" | grep -q 1; then
    print_warning "Database 'string_authority' already exists. Dropping it..."
    psql -d postgres -c "DROP DATABASE string_authority;" || {
        print_error "Failed to drop database. Make sure no connections are active."
        exit 1
    }
    print_status "Database 'string_authority' dropped successfully"
else
    print_status "Database 'string_authority' does not exist (no need to drop)"
fi

# Create new database with new name
echo "📋 Step 3: Creating new database 'string_authority'..."
psql -d postgres -c "CREATE DATABASE string_authority OWNER string_authority_user;" || {
    print_error "Failed to create database. Make sure string_authority_user exists."
    print_warning "If the user doesn't exist, create it with:"
    echo "  psql -d postgres -c \"CREATE USER string_authority_user WITH PASSWORD 'your_password';\""
    exit 1
}
print_status "Database 'string_authority' created successfully"

# Grant privileges
echo "📋 Step 4: Granting privileges..."
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE string_authority TO string_authority_user;" || {
    print_error "Failed to grant database privileges"
    exit 1
}
psql -U string_authority_user -d string_authority -c "GRANT ALL PRIVILEGES ON SCHEMA public TO string_authority_user;" || {
    print_error "Failed to grant schema privileges"
    exit 1
}
print_status "Privileges granted successfully"

# Create extensions
echo "📋 Step 5: Creating extensions..."
psql -U string_authority_user -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";" || {
    print_error "Failed to create uuid-ossp extension"
    exit 1
}
psql -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"pg_uuidv7\";" || {
    print_error "Failed to create pg_uuidv7 extension (requires superuser privileges)"
    exit 1
}
psql -U string_authority_user -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"pg_trgm\";" || {
    print_error "Failed to create pg_trgm extension"
    exit 1
}
print_status "Extensions created successfully"

# Create structure
echo "📋 Step 6: Creating database structure..."
if [ -f "database/create.sql" ]; then
    psql -U string_authority_user -d string_authority -f database/create.sql || {
        print_error "Failed to create database structure"
        exit 1
    }
    print_status "Database structure created successfully"
else
    print_error "database/create.sql file not found!"
    exit 1
fi

# Verify the setup
echo "📋 Step 7: Verifying database setup..."
TABLE_COUNT=$(psql -U string_authority_user -d string_authority -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | xargs)
print_status "Database contains $TABLE_COUNT tables"

# Show table list
echo "📋 Tables created:"
psql -U string_authority_user -d string_authority -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;" || {
    print_warning "Could not list tables (this is not critical)"
}

# Verify all tables are empty
echo "📋 Verifying all tables are empty..."
EMPTY_TABLES=$(psql -U string_authority_user -d string_authority -t -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_type = 'BASE TABLE'
ORDER BY table_name;" | xargs)

for table in $EMPTY_TABLES; do
    COUNT=$(psql -U string_authority_user -d string_authority -t -c "SELECT COUNT(*) FROM $table;" | xargs)
    if [ "$COUNT" -eq 0 ]; then
        print_status "$table: $COUNT rows"
    else
        print_warning "$table: $COUNT rows (should be 0)"
    fi
done

echo ""
print_status "🎉 Database migration completed successfully!"
echo ""
echo "Migration summary:"
echo "  - Old database 'guitar_registry' has been dropped"
echo "  - New database 'string_authority' has been created"
echo "  - User: string_authority_user"
echo ""
echo "Next steps:"
echo "1. Run your data processing scripts"
echo "2. Or import data using: psql -U string_authority_user -d string_authority -f your_data_file.sql"
echo ""
echo "⚠️  NOTE: This script is for one-time migration. For future database recreations,"
echo "    use: ./database-recycle.sh"
echo ""

