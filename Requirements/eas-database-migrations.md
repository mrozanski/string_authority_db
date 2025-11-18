# EAS Database Migrations - SQL Requirements

**Purpose:** This document contains all SQL-level database changes required for EAS (Ethereum Attestation Service) implementation in the Guitar Registry.

**Target:** Python API project that manages the PostgreSQL schema

**Phase:** Phase 1A (Model Attestations) + Phase 2A (Instrument Attestations)

---

## Overview

This migration adds support for blockchain attestations to the guitar registry:
- **Model Attestations**: Cryptographically signed records for guitar models
- **Instrument Attestations**: Cryptographically signed records for individual guitars
- **Schema Versioning**: Track EAS schema versions and evolution
- **Manufacturer Wallets**: Registry for manufacturer wallet addresses for co-signing

---

## Migration Script

### Step 1: Add Attestation Fields to `models` Table

Add columns to track attestation status and metadata for guitar models.

```sql
-- Add attestation fields to models table
ALTER TABLE models
ADD COLUMN IF NOT EXISTS attestation_uid VARCHAR(66),
ADD COLUMN IF NOT EXISTS ipfs_cid VARCHAR(100),
ADD COLUMN IF NOT EXISTS attestation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS attested_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS attested_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS cosigner_wallet VARCHAR(42),
ADD COLUMN IF NOT EXISTS cosigned_at TIMESTAMPTZ;

-- Add index for attestation lookups
CREATE INDEX IF NOT EXISTS idx_models_attestation_uid ON models(attestation_uid);
CREATE INDEX IF NOT EXISTS idx_models_attestation_status ON models(attestation_status);

-- Add CHECK constraint for attestation_status
ALTER TABLE models
ADD CONSTRAINT check_models_attestation_status 
CHECK (attestation_status IN ('pending', 'official', 'revoked'));
```

**Column Descriptions:**
- `attestation_uid`: EAS attestation UID (66 chars = 0x + 64 hex chars)
- `ipfs_cid`: IPFS Content ID where attestation is pinned
- `attestation_status`: Status enum: 'pending', 'official', 'revoked'
- `attested_by`: Wallet address of the entity that created the attestation
- `attested_at`: Timestamp when attestation was created
- `cosigner_wallet`: Manufacturer wallet address (if co-signed)
- `cosigned_at`: Timestamp when manufacturer co-signed

---

### Step 2: Create `attestations` Tracking Table

Central table to track all attestations (models, instruments, future types).

```sql
-- Create attestations tracking table
CREATE TABLE IF NOT EXISTS attestations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    uid VARCHAR(66) UNIQUE NOT NULL,
    schema_uid VARCHAR(66) NOT NULL,
    schema_type VARCHAR(50) NOT NULL, -- 'model', 'instrument', 'review', etc.
    entity_type VARCHAR(50) NOT NULL, -- 'model', 'individual_guitar', etc.
    entity_id UUID NOT NULL,
    attestation_data JSONB NOT NULL,
    ipfs_cid VARCHAR(100),
    schema_version VARCHAR(20), -- '1.0.0', '2.0.0', etc.
    signer_wallet VARCHAR(42) NOT NULL,
    signer_role VARCHAR(20) DEFAULT 'admin',
    signed_at TIMESTAMPTZ NOT NULL,
    cosigner_wallet VARCHAR(42),
    cosigner_role VARCHAR(20),
    cosigned_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_attestations_status CHECK (status IN ('pending', 'official', 'revoked'))
);

-- Indexes for attestations table
CREATE INDEX IF NOT EXISTS idx_attestations_uid ON attestations(uid);
CREATE INDEX IF NOT EXISTS idx_attestations_schema_uid ON attestations(schema_uid);
CREATE INDEX IF NOT EXISTS idx_attestations_schema_type ON attestations(schema_type);
CREATE INDEX IF NOT EXISTS idx_attestations_entity_type_id ON attestations(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_attestations_schema_version ON attestations(schema_version);
CREATE INDEX IF NOT EXISTS idx_attestations_status ON attestations(status);
CREATE INDEX IF NOT EXISTS idx_attestations_signer_wallet ON attestations(signer_wallet);
CREATE INDEX IF NOT EXISTS idx_attestations_cosigner_wallet ON attestations(cosigner_wallet);
CREATE INDEX IF NOT EXISTS idx_attestations_signed_at ON attestations(signed_at);
```

**Table Purpose:**
- Centralized tracking of all blockchain attestations
- Stores full attestation data as JSONB for flexible querying
- Tracks schema versions for backward compatibility
- Supports co-signing workflow (admin → manufacturer)

**Key Fields:**
- `uid`: Unique EAS attestation identifier (primary lookup key)
- `schema_uid`: EAS schema UID (identifies which schema version)
- `schema_type`: Logical type ('model', 'instrument')
- `entity_type` + `entity_id`: Links to the actual database record
- `attestation_data`: Full decoded attestation data (JSONB for querying)
- `schema_version`: Semantic version string ('1.0.0', '2.0.0')

---

### Step 3: Create `schema_versions` Registry Table

Tracks EAS schema versions and their relationships (for schema evolution).

```sql
-- Create schema versions registry table
CREATE TABLE IF NOT EXISTS schema_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    schema_name VARCHAR(100) NOT NULL, -- 'GuitarModelAttestation', 'GuitarInstrumentAttestation'
    version VARCHAR(20) NOT NULL, -- '1.0.0', '1.1.0', '2.0.0'
    schema_uid VARCHAR(66) NOT NULL, -- EAS schema UID on blockchain
    previous_version_id UUID REFERENCES schema_versions(id),
    next_version_id UUID REFERENCES schema_versions(id),
    changelog TEXT,
    effective_date TIMESTAMPTZ NOT NULL,
    deprecated_date TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'deprecated'
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(schema_name, version),
    CONSTRAINT check_schema_versions_status CHECK (status IN ('active', 'deprecated'))
);

-- Indexes for schema_versions table
CREATE INDEX IF NOT EXISTS idx_schema_versions_name ON schema_versions(schema_name);
CREATE INDEX IF NOT EXISTS idx_schema_versions_status ON schema_versions(status);
CREATE INDEX IF NOT EXISTS idx_schema_versions_schema_uid ON schema_versions(schema_uid);
CREATE INDEX IF NOT EXISTS idx_schema_versions_effective_date ON schema_versions(effective_date);
```

**Table Purpose:**
- Maintains version chain for each schema type
- Links schema versions via `previous_version_id` / `next_version_id`
- Tracks when schemas become active/deprecated
- Enables backward compatibility when decoding old attestations

**Example Data:**
```
schema_name: 'GuitarModelAttestation'
version: '1.0.0'
schema_uid: '0x1234...'
previous_version_id: NULL
next_version_id: <uuid of v2.0.0>
status: 'active'
```

---

### Step 4: Create `manufacturer_wallets` Registry Table

Stores manufacturer wallet addresses for co-signing attestations.

```sql
-- Create manufacturer wallet registry
CREATE TABLE IF NOT EXISTS manufacturer_wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    manufacturer_id UUID NOT NULL REFERENCES manufacturers(id) ON DELETE CASCADE,
    wallet_address VARCHAR(42) UNIQUE NOT NULL, -- Ethereum address (0x + 40 hex)
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'revoked'
    registered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    registered_by VARCHAR(100), -- Admin who registered the wallet
    notes TEXT, -- Optional notes about the wallet
    CONSTRAINT check_manufacturer_wallets_status CHECK (status IN ('active', 'revoked'))
);

-- Indexes for manufacturer_wallets table
CREATE INDEX IF NOT EXISTS idx_manufacturer_wallets_manufacturer_id ON manufacturer_wallets(manufacturer_id);
CREATE INDEX IF NOT EXISTS idx_manufacturer_wallets_wallet_address ON manufacturer_wallets(wallet_address);
CREATE INDEX IF NOT EXISTS idx_manufacturer_wallets_status ON manufacturer_wallets(status);
```

**Table Purpose:**
- Registry of approved manufacturer wallet addresses
- Enables manufacturer co-signing of model attestations
- Supports wallet revocation (status = 'revoked')
- One manufacturer can have multiple wallets

**Security Note:**
- Wallet addresses must be verified (sign message to prove ownership)
- Only active wallets can co-sign attestations

---

### Step 5: Add Attestation Fields to `individual_guitars` Table (Phase 2A)

Add columns to track attestation status for individual guitar instruments.

```sql
-- Add attestation fields to individual_guitars table
ALTER TABLE individual_guitars
ADD COLUMN IF NOT EXISTS attestation_uid VARCHAR(66),
ADD COLUMN IF NOT EXISTS ipfs_cid VARCHAR(100),
ADD COLUMN IF NOT EXISTS attestation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS attested_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS attested_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS cosigner_wallet VARCHAR(42),
ADD COLUMN IF NOT EXISTS cosigned_at TIMESTAMPTZ;

-- Add indexes for attestation lookups
CREATE INDEX IF NOT EXISTS idx_individual_guitars_attestation_uid ON individual_guitars(attestation_uid);
CREATE INDEX IF NOT EXISTS idx_individual_guitars_attestation_status ON individual_guitars(attestation_status);

-- Add CHECK constraint for attestation_status
ALTER TABLE individual_guitars
ADD CONSTRAINT check_individual_guitars_attestation_status
CHECK (attestation_status IN ('pending', 'official', 'revoked'));
```

**Note:** This is for Phase 2A (Instrument Attestations), but can be included in the same migration if desired.

---

## Complete Migration Script (All Steps Combined)

```sql
-- ============================================
-- EAS Database Migration
-- Phase 1A + Phase 2A
-- ============================================

BEGIN;

-- Step 1: Add attestation fields to models table
ALTER TABLE models
ADD COLUMN IF NOT EXISTS attestation_uid VARCHAR(66),
ADD COLUMN IF NOT EXISTS ipfs_cid VARCHAR(100),
ADD COLUMN IF NOT EXISTS attestation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS attested_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS attested_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS cosigner_wallet VARCHAR(42),
ADD COLUMN IF NOT EXISTS cosigned_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_models_attestation_uid ON models(attestation_uid);
CREATE INDEX IF NOT EXISTS idx_models_attestation_status ON models(attestation_status);

-- Add CHECK constraint for models.attestation_status
ALTER TABLE models
ADD CONSTRAINT check_models_attestation_status 
CHECK (attestation_status IN ('pending', 'official', 'revoked'));

-- Step 2: Create attestations tracking table
CREATE TABLE IF NOT EXISTS attestations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    uid VARCHAR(66) UNIQUE NOT NULL,
    schema_uid VARCHAR(66) NOT NULL,
    schema_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    attestation_data JSONB NOT NULL,
    ipfs_cid VARCHAR(100),
    schema_version VARCHAR(20),
    signer_wallet VARCHAR(42) NOT NULL,
    signer_role VARCHAR(20) DEFAULT 'admin',
    signed_at TIMESTAMPTZ NOT NULL,
    cosigner_wallet VARCHAR(42),
    cosigner_role VARCHAR(20),
    cosigned_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_attestations_status CHECK (status IN ('pending', 'official', 'revoked'))
);

CREATE INDEX IF NOT EXISTS idx_attestations_uid ON attestations(uid);
CREATE INDEX IF NOT EXISTS idx_attestations_schema_uid ON attestations(schema_uid);
CREATE INDEX IF NOT EXISTS idx_attestations_schema_type ON attestations(schema_type);
CREATE INDEX IF NOT EXISTS idx_attestations_entity_type_id ON attestations(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_attestations_schema_version ON attestations(schema_version);
CREATE INDEX IF NOT EXISTS idx_attestations_status ON attestations(status);
CREATE INDEX IF NOT EXISTS idx_attestations_signer_wallet ON attestations(signer_wallet);
CREATE INDEX IF NOT EXISTS idx_attestations_cosigner_wallet ON attestations(cosigner_wallet);
CREATE INDEX IF NOT EXISTS idx_attestations_signed_at ON attestations(signed_at);

-- Step 3: Create schema versions registry table
CREATE TABLE IF NOT EXISTS schema_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    schema_name VARCHAR(100) NOT NULL,
    version VARCHAR(20) NOT NULL,
    schema_uid VARCHAR(66) NOT NULL,
    previous_version_id UUID REFERENCES schema_versions(id),
    next_version_id UUID REFERENCES schema_versions(id),
    changelog TEXT,
    effective_date TIMESTAMPTZ NOT NULL,
    deprecated_date TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(schema_name, version),
    CONSTRAINT check_schema_versions_status CHECK (status IN ('active', 'deprecated'))
);

CREATE INDEX IF NOT EXISTS idx_schema_versions_name ON schema_versions(schema_name);
CREATE INDEX IF NOT EXISTS idx_schema_versions_status ON schema_versions(status);
CREATE INDEX IF NOT EXISTS idx_schema_versions_schema_uid ON schema_versions(schema_uid);
CREATE INDEX IF NOT EXISTS idx_schema_versions_effective_date ON schema_versions(effective_date);

-- Step 4: Create manufacturer wallet registry
CREATE TABLE IF NOT EXISTS manufacturer_wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    manufacturer_id UUID NOT NULL REFERENCES manufacturers(id) ON DELETE CASCADE,
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    registered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    registered_by VARCHAR(100),
    notes TEXT,
    CONSTRAINT check_manufacturer_wallets_status CHECK (status IN ('active', 'revoked'))
);

CREATE INDEX IF NOT EXISTS idx_manufacturer_wallets_manufacturer_id ON manufacturer_wallets(manufacturer_id);
CREATE INDEX IF NOT EXISTS idx_manufacturer_wallets_wallet_address ON manufacturer_wallets(wallet_address);
CREATE INDEX IF NOT EXISTS idx_manufacturer_wallets_status ON manufacturer_wallets(status);

-- Step 5: Add attestation fields to individual_guitars table (Phase 2A)
ALTER TABLE individual_guitars
ADD COLUMN IF NOT EXISTS attestation_uid VARCHAR(66),
ADD COLUMN IF NOT EXISTS ipfs_cid VARCHAR(100),
ADD COLUMN IF NOT EXISTS attestation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS attested_by VARCHAR(100),
ADD COLUMN IF NOT EXISTS attested_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS cosigner_wallet VARCHAR(42),
ADD COLUMN IF NOT EXISTS cosigned_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_individual_guitars_attestation_uid ON individual_guitars(attestation_uid);
CREATE INDEX IF NOT EXISTS idx_individual_guitars_attestation_status ON individual_guitars(attestation_status);

-- Add CHECK constraint for individual_guitars.attestation_status
ALTER TABLE individual_guitars
ADD CONSTRAINT check_individual_guitars_attestation_status
CHECK (attestation_status IN ('pending', 'official', 'revoked'));

COMMIT;
```

---

## Data Type Specifications

### VARCHAR Lengths
- `VARCHAR(66)`: EAS attestation UID (0x prefix + 64 hex chars)
- `VARCHAR(42)`: Ethereum wallet address (0x prefix + 40 hex chars)
- `VARCHAR(100)`: IPFS CID (base58 encoded, typically 46-59 chars, but allow extra)
- `VARCHAR(20)`: Status/enum fields ('pending', 'official', 'revoked', 'active', 'deprecated')
- `VARCHAR(50)`: Type fields ('model', 'instrument', 'admin', 'manufacturer')
- `VARCHAR(100)`: Schema names and wallet addresses (display)

### Status Values
- `attestation_status`: 'pending', 'official', 'revoked'
- `status` (attestations table): 'pending', 'official', 'revoked'
- `status` (schema_versions): 'active', 'deprecated'
- `status` (manufacturer_wallets): 'active', 'revoked'

---

## Dependencies

1. **Existing Tables Required:**
   - `models` table must exist
   - `individual_guitars` table must exist
   - `manufacturers` table must exist

2. **PostgreSQL Extensions:**
   - `uuid_generate_v7()` function (PostgreSQL 13+ with uuid-ossp extension, or custom function)
   - If `uuid_generate_v7()` is not available, use `gen_random_uuid()` or `uuid_generate_v4()`

3. **Foreign Key Constraints:**
   - `manufacturer_wallets.manufacturer_id` → `manufacturers.id` (CASCADE on delete)

4. **CHECK Constraints:**
   - `models.attestation_status`: 'pending', 'official', 'revoked'
   - `individual_guitars.attestation_status`: 'pending', 'official', 'revoked'
   - `attestations.status`: 'pending', 'official', 'revoked'
   - `schema_versions.status`: 'active', 'deprecated'
   - `manufacturer_wallets.status`: 'active', 'revoked'

---

## Rollback Script (If Needed)

```sql
BEGIN;

-- Drop CHECK constraints first
ALTER TABLE individual_guitars DROP CONSTRAINT IF EXISTS check_individual_guitars_attestation_status;
ALTER TABLE models DROP CONSTRAINT IF EXISTS check_models_attestation_status;
ALTER TABLE attestations DROP CONSTRAINT IF EXISTS check_attestations_status;
ALTER TABLE schema_versions DROP CONSTRAINT IF EXISTS check_schema_versions_status;
ALTER TABLE manufacturer_wallets DROP CONSTRAINT IF EXISTS check_manufacturer_wallets_status;

-- Remove indexes
DROP INDEX IF EXISTS idx_individual_guitars_attestation_status;
DROP INDEX IF EXISTS idx_individual_guitars_attestation_uid;
DROP INDEX IF EXISTS idx_manufacturer_wallets_status;
DROP INDEX IF EXISTS idx_manufacturer_wallets_wallet_address;
DROP INDEX IF EXISTS idx_manufacturer_wallets_manufacturer_id;
DROP INDEX IF EXISTS idx_schema_versions_effective_date;
DROP INDEX IF EXISTS idx_schema_versions_schema_uid;
DROP INDEX IF EXISTS idx_schema_versions_status;
DROP INDEX IF EXISTS idx_schema_versions_name;
DROP INDEX IF EXISTS idx_attestations_signed_at;
DROP INDEX IF EXISTS idx_attestations_cosigner_wallet;
DROP INDEX IF EXISTS idx_attestations_signer_wallet;
DROP INDEX IF EXISTS idx_attestations_status;
DROP INDEX IF EXISTS idx_attestations_schema_version;
DROP INDEX IF EXISTS idx_attestations_entity_type_id;
DROP INDEX IF EXISTS idx_attestations_schema_type;
DROP INDEX IF EXISTS idx_attestations_schema_uid;
DROP INDEX IF EXISTS idx_attestations_uid;
DROP INDEX IF EXISTS idx_models_attestation_status;
DROP INDEX IF EXISTS idx_models_attestation_uid;

-- Drop tables (order matters due to foreign keys)
DROP TABLE IF EXISTS manufacturer_wallets;
DROP TABLE IF EXISTS schema_versions;
DROP TABLE IF EXISTS attestations;

-- Remove columns from individual_guitars
ALTER TABLE individual_guitars
DROP COLUMN IF EXISTS cosigned_at,
DROP COLUMN IF EXISTS cosigner_wallet,
DROP COLUMN IF EXISTS attested_at,
DROP COLUMN IF EXISTS attested_by,
DROP COLUMN IF EXISTS attestation_status,
DROP COLUMN IF EXISTS ipfs_cid,
DROP COLUMN IF EXISTS attestation_uid;

-- Remove columns from models
ALTER TABLE models
DROP COLUMN IF EXISTS cosigned_at,
DROP COLUMN IF EXISTS cosigner_wallet,
DROP COLUMN IF EXISTS attested_at,
DROP COLUMN IF EXISTS attested_by,
DROP COLUMN IF EXISTS attestation_status,
DROP COLUMN IF EXISTS ipfs_cid,
DROP COLUMN IF EXISTS attestation_uid;

COMMIT;
```

---

## Post-Migration Steps (Next.js Project)

After this migration is applied:

1. **Update Prisma Schema:**
   ```bash
   npx prisma db pull
   npx prisma generate
   ```

2. **Verify Schema:**
   - Check that all new columns appear in Prisma schema
   - Verify indexes are recognized
   - Test Prisma client generation

---

## Questions for Python API Team

1. **UUID Function:** Does your database have `uuid_generate_v7()` or should we use `gen_random_uuid()` / `uuid_generate_v4()`?

2. **Migration Tool:** What migration tool/framework does the Python API use? (Alembic, Django migrations, raw SQL scripts?)

3. **Timing:** When can this migration be applied? (Before Phase 1A starts, or can it be coordinated?)

4. **Testing:** Should we provide a test data script to verify the migration?

5. **Constraints:** ✅ CHECK constraints have been added for all status fields to ensure data integrity and consistency with existing schema patterns.

---

**Document Version:** 1.0  
**Created:** 2025-01-XX  
**For:** EAS Implementation Phase 1A + 2A

