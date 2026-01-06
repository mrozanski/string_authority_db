# Database re-creation

## Drop database
```
psql -d postgres -c "DROP database string_authority;
```

## Create database
```
psql -d postgres -c "CREATE DATABASE string_authority OWNER string_authority_user;"
```

## Grant privileges
```
psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE string_authority TO string_authority_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO string_authority_user;"
```

## Create extensions
```
psql -U string_authority_user -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d string_authority -c "CREATE EXTENSION IF NOT EXISTS \"pg_uuidv7\";"
```

## Create structure
```
psql -U string_authority_user -d string_authority -f database/create.sql
```

Recommended: use the comprehensive shell script `database-recycle.sh` to create the database and structure.
It will give you a completely clean, consistent database ready for processing your JSON data.

Here's what the script does:

## **🔄 Database Recreation Script Features:**

### **✅ Complete Automation:**
1. **Drops existing database** (if it exists)
2. **Creates new database** with proper ownership
3. **Grants all privileges** to `string_authority_user`
4. **Creates all required extensions** (uuid-ossp, pg_uuidv7, pg_trgm)
5. **Runs the structure creation** from `database/create.sql`
6. **Verifies the setup** and confirms all tables are empty

### **✅ Safety Features:**
- **Error handling** - Exits on any error with clear messages
- **Colored output** - Easy to read status messages
- **Verification steps** - Confirms each step completed successfully
- **Table count verification** - Ensures all tables are created and empty

### **✅ Usage:**
```bash
# Run the script
./database-recycle.sh
```

### **✅ What You'll See:**
- Step-by-step progress with colored status messages
- Confirmation that all tables are created and empty
- Clear next steps for data processing

