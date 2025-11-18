-- Guitar Registry - Electric Guitar Provenance and Authentication System
-- Copyright (C) 2025 Mariano Rozanski
-- 
-- This program is free software: you can redistribute it and/or modify
-- it under the terms of the GNU Affero General Public License as published
-- by the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.
--
-- See LICENSE file for full license text.

-- Complete Database Schema - Guitar Registry with Image Management
-- 
-- PREREQUISITES:
-- 1. PostgreSQL 15+ with uuid-ossp extension
-- 2. pg_uuidv7 extension installed (see database/pg_uuidv7/ for installation)
-- 3. Run as superuser or database owner
--
-- USAGE:
-- 1. Create database: CREATE DATABASE guitar_registry;
-- 2. Install extensions: CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE EXTENSION IF NOT EXISTS "pg_uuidv7";
-- 3. Run this script: psql -d guitar_registry -f create-complete.sql
-- 4. Grant permissions (see end of file)

-- ============================================================================
-- CORE SCHEMA TABLES
-- ============================================================================

-- Manufacturers table
CREATE TABLE manufacturers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(50),
    country VARCHAR(50),
    founded_year INTEGER,
    website VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'defunct', 'acquired')),
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Product lines/series
CREATE TABLE product_lines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    manufacturer_id UUID REFERENCES manufacturers(id),
    name VARCHAR(100) NOT NULL,
    description TEXT,
    introduced_year INTEGER,
    discontinued_year INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Models table
CREATE TABLE models (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    manufacturer_id UUID REFERENCES manufacturers(id),
    product_line_id UUID REFERENCES product_lines(id),
    name VARCHAR(150) NOT NULL,
    year INTEGER NOT NULL,
    production_type VARCHAR(20) DEFAULT 'mass' CHECK (production_type IN ('mass', 'limited', 'custom', 'prototype', 'one-off')),
    production_start_date DATE,
    production_end_date DATE,
    estimated_production_quantity INTEGER,
    msrp_original DECIMAL(10,2),
    currency VARCHAR(3) DEFAULT 'USD',
    description TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    -- EAS attestation fields
    attestation_uid VARCHAR(66),
    ipfs_cid VARCHAR(100),
    attestation_status VARCHAR(20) DEFAULT 'pending',
    attested_by VARCHAR(100),
    attested_at TIMESTAMP WITH TIME ZONE,
    cosigner_wallet VARCHAR(42),
    cosigned_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(manufacturer_id, name, year),
    CONSTRAINT check_models_attestation_status CHECK (attestation_status IN ('pending', 'official', 'revoked'))
);

-- Individual guitars table with hybrid FK + fallback approach
CREATE TABLE individual_guitars (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    
    -- Foreign key reference (optional - for complete data)
    model_id UUID REFERENCES models(id),
    
    -- Fallback text fields (for incomplete data)
    manufacturer_name_fallback VARCHAR(100),
    model_name_fallback VARCHAR(150),
    year_estimate VARCHAR(50), -- Allows "circa 1959", "late 1950s", etc.
    description TEXT, -- General description when model info is incomplete
    
    -- Guitar-specific fields
    nickname VARCHAR(50),
    serial_number VARCHAR(50),
    production_date DATE,
    production_number INTEGER,
    significance_level VARCHAR(20) DEFAULT 'notable' CHECK (significance_level IN ('historic', 'notable', 'rare', 'custom')),
    significance_notes TEXT,
    current_estimated_value DECIMAL(12,2),
    last_valuation_date DATE,
    condition_rating VARCHAR(20) CHECK (condition_rating IN ('mint', 'excellent', 'very_good', 'good', 'fair', 'poor', 'relic')),
    modifications TEXT,
    provenance_notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure some form of identification exists
    CONSTRAINT guitar_identification_required CHECK (
        model_id IS NOT NULL OR 
        (manufacturer_name_fallback IS NOT NULL AND 
         (model_name_fallback IS NOT NULL OR description IS NOT NULL))
    ),
    
    -- EAS attestation fields
    attestation_uid VARCHAR(66),
    ipfs_cid VARCHAR(100),
    attestation_status VARCHAR(20) DEFAULT 'pending',
    attested_by VARCHAR(100),
    attested_at TIMESTAMP WITH TIME ZONE,
    cosigner_wallet VARCHAR(42),
    cosigned_at TIMESTAMP WITH TIME ZONE,
    
    UNIQUE(serial_number),
    CONSTRAINT check_individual_guitars_attestation_status CHECK (attestation_status IN ('pending', 'official', 'revoked'))
);

-- Specifications table
CREATE TABLE specifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    model_id UUID REFERENCES models(id),
    individual_guitar_id UUID REFERENCES individual_guitars(id),
    body_wood VARCHAR(50),
    neck_wood VARCHAR(50),
    fingerboard_wood VARCHAR(50),
    scale_length_inches DECIMAL(4,2),
    num_frets INTEGER,
    nut_width_inches DECIMAL(3,2),
    neck_profile VARCHAR(50),
    bridge_type VARCHAR(50),
    pickup_configuration VARCHAR(150),
    electronics_description TEXT,
    hardware_finish VARCHAR(50),
    body_finish TEXT,
    weight_lbs DECIMAL(4,2),
    case_included BOOLEAN DEFAULT FALSE,
    case_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK ((model_id IS NOT NULL AND individual_guitar_id IS NULL) OR 
           (model_id IS NULL AND individual_guitar_id IS NOT NULL))
);



-- Expert reviews table for attestations
CREATE TABLE expert_reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    reviewer_name VARCHAR(100) NOT NULL,
    reviewer_credentials TEXT,
    review_title VARCHAR(200) NOT NULL,
    review_summary TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'review' CHECK (content_type IN ('review', 'comparison', 'overview')),
    
    -- Ratings (optional for some content types)
    condition_rating INTEGER CHECK (condition_rating BETWEEN 1 AND 10),
    build_quality_rating INTEGER CHECK (build_quality_rating BETWEEN 1 AND 10),
    value_rating INTEGER CHECK (value_rating BETWEEN 1 AND 10),
    overall_rating INTEGER CHECK (overall_rating BETWEEN 1 AND 10),
    
    -- Attestation simulation fields
    original_content_url VARCHAR(500), -- YouTube/source URL
    content_archived BOOLEAN DEFAULT FALSE,
    content_hash VARCHAR(64), -- Simulated IPFS hash
    attestation_uid VARCHAR(66), -- Simulated EAS UID
    verification_status VARCHAR(20) DEFAULT 'pending' CHECK (verification_status IN ('pending', 'verified', 'disputed')),
    
    -- Metadata
    review_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Junction table for many-to-many model relationships
CREATE TABLE review_model_associations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    review_id UUID REFERENCES expert_reviews(id) ON DELETE CASCADE,
    model_id UUID REFERENCES models(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(review_id, model_id)
);

-- Data sources and citations
CREATE TABLE data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    source_name VARCHAR(100) NOT NULL,
    source_type VARCHAR(50),
    url VARCHAR(500),
    isbn VARCHAR(20),
    publication_date DATE,
    reliability_score INTEGER CHECK (reliability_score BETWEEN 1 AND 10),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Citations linking data to sources
CREATE TABLE citations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    source_id UUID REFERENCES data_sources(id),
    cited_table VARCHAR(50) NOT NULL,
    cited_record_id UUID NOT NULL,
    page_number INTEGER,
    section VARCHAR(100),
    confidence_level VARCHAR(20) CHECK (confidence_level IN ('high', 'medium', 'low')),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Market data for tracking values over time
CREATE TABLE market_valuations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    model_id UUID REFERENCES models(id),
    individual_guitar_id UUID REFERENCES individual_guitars(id),
    valuation_date DATE NOT NULL,
    low_estimate DECIMAL(12,2),
    high_estimate DECIMAL(12,2),
    average_estimate DECIMAL(12,2),
    sale_price DECIMAL(12,2),
    sale_venue VARCHAR(100),
    condition_at_valuation VARCHAR(20),
    source_id UUID REFERENCES data_sources(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK ((model_id IS NOT NULL AND individual_guitar_id IS NULL) OR 
           (model_id IS NULL AND individual_guitar_id IS NOT NULL))
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    user_type VARCHAR(20) DEFAULT 'enthusiast' CHECK (user_type IN ('admin', 'curator', 'dealer', 'collector', 'enthusiast')),
    verified_expert BOOLEAN DEFAULT FALSE,
    expertise_areas TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User contributions tracking
CREATE TABLE contributions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    user_id UUID REFERENCES users(id),
    contribution_type VARCHAR(50),
    table_name VARCHAR(50),
    record_id UUID,
    contribution_data JSONB,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'merged')),
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- EAS ATTESTATION TABLES
-- ============================================================================

-- Attestations tracking table
-- Central table to track all blockchain attestations (models, instruments, future types)
CREATE TABLE attestations (
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
    signed_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cosigner_wallet VARCHAR(42),
    cosigner_role VARCHAR(20),
    cosigned_at TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT check_attestations_status CHECK (status IN ('pending', 'official', 'revoked'))
);

-- Schema versions registry table
-- Tracks EAS schema versions and their relationships (for schema evolution)
CREATE TABLE schema_versions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    schema_name VARCHAR(100) NOT NULL, -- 'GuitarModelAttestation', 'GuitarInstrumentAttestation'
    version VARCHAR(20) NOT NULL, -- '1.0.0', '1.1.0', '2.0.0'
    schema_uid VARCHAR(66) NOT NULL, -- EAS schema UID on blockchain
    previous_version_id UUID REFERENCES schema_versions(id),
    next_version_id UUID REFERENCES schema_versions(id),
    changelog TEXT,
    effective_date TIMESTAMP WITH TIME ZONE NOT NULL,
    deprecated_date TIMESTAMP WITH TIME ZONE,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'deprecated'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(schema_name, version),
    CONSTRAINT check_schema_versions_status CHECK (status IN ('active', 'deprecated'))
);

-- Manufacturer wallet registry
-- Stores manufacturer wallet addresses for co-signing attestations
CREATE TABLE manufacturer_wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    manufacturer_id UUID NOT NULL REFERENCES manufacturers(id) ON DELETE CASCADE,
    wallet_address VARCHAR(42) UNIQUE NOT NULL, -- Ethereum address (0x + 40 hex)
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'revoked'
    registered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    registered_by VARCHAR(100), -- Admin who registered the wallet
    notes TEXT, -- Optional notes about the wallet
    CONSTRAINT check_manufacturer_wallets_status CHECK (status IN ('active', 'revoked'))
);

-- ============================================================================
-- IMAGE MANAGEMENT TABLES
-- ============================================================================

-- Image storage metadata table with direct entity associations
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    
    -- Entity association (direct approach)
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID NOT NULL,
    image_type VARCHAR(50) NOT NULL, -- primary, gallery, headstock, serial, detail, etc
    is_primary BOOLEAN DEFAULT FALSE,
    display_order INTEGER DEFAULT 0,
    caption TEXT,
    
    -- Storage information (shared across duplicates)
    storage_provider VARCHAR(50) NOT NULL DEFAULT 'cloudinary',
    storage_key VARCHAR(500) NOT NULL, -- This should be the same for all duplicates of an image
    original_url TEXT NOT NULL,
    
    -- Image variants (responsive images)
    thumbnail_url TEXT,
    small_url TEXT,      -- 400px wide
    medium_url TEXT,     -- 800px wide
    large_url TEXT,      -- 1600px wide
    xlarge_url TEXT,     -- 2400px wide
    
    -- Metadata
    original_filename VARCHAR(255),
    mime_type VARCHAR(100),
    file_size_bytes INTEGER CHECK (file_size_bytes > 0 AND file_size_bytes <= 10485760), -- Max 10MB
    width INTEGER CHECK (width > 0),
    height INTEGER CHECK (height > 0),
    
    -- Image characteristics
    aspect_ratio DECIMAL(5,3),
    dominant_color VARCHAR(7),
    
    -- Management
    uploaded_by UUID REFERENCES users(id),
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    
    -- Validation and moderation
    is_validated BOOLEAN DEFAULT FALSE,
    validation_status VARCHAR(50) DEFAULT 'pending',
    validation_notes TEXT,
    validated_by UUID REFERENCES users(id),
    validated_at TIMESTAMP WITH TIME ZONE,
    
    -- Search and categorization
    tags TEXT[],
    description TEXT,
    
    -- Duplicate management
    is_duplicate BOOLEAN DEFAULT FALSE, -- Marks if this is a duplicate of another image
    original_image_id UUID REFERENCES images(id), -- Points to the "master" image record
    duplicate_reason TEXT, -- Why this duplicate exists (e.g., "represents manufacturer", "catalog display")
    
    -- Constraints
    CONSTRAINT valid_storage_provider CHECK (
        storage_provider IN ('cloudinary', 's3', 'vercel_blob', 'local', 'external')
    ),
    CONSTRAINT valid_mime_type CHECK (
        mime_type IN ('image/jpeg', 'image/png', 'image/webp', 'image/avif')
    ),
    CONSTRAINT valid_validation_status CHECK (
        validation_status IN ('pending', 'approved', 'rejected', 'flagged')
    ),
    CONSTRAINT valid_dominant_color CHECK (
        dominant_color ~ '^#[0-9A-Fa-f]{6}$'
    ),
    CONSTRAINT valid_url_format CHECK (
        original_url ~ '^https?://'
    ),
    CONSTRAINT valid_entity_type CHECK (
        entity_type IN ('manufacturer', 'product_line', 'model', 'individual_guitar', 
                       'specification', 'finish', 'expert_review')
    ),
    CONSTRAINT valid_image_type CHECK (
        image_type IN ('primary', 'logo', 'gallery', 'headstock', 'serial_number', 
                      'body_front', 'body_back', 'neck', 'hardware', 'detail', 
                      'certificate', 'documentation', 'historical')
    ),
    -- Prevent circular references in duplicates
    CONSTRAINT no_circular_duplicates CHECK (
        original_image_id IS NULL OR original_image_id != id
    )
);

-- Image sources for attribution
CREATE TABLE image_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    image_id UUID REFERENCES images(id) ON DELETE CASCADE,
    
    -- Source information
    source_type VARCHAR(50) NOT NULL,
    source_name VARCHAR(255),
    source_url TEXT,
    
    -- Attribution
    copyright_holder VARCHAR(255),
    license_type VARCHAR(50),
    attribution_required BOOLEAN DEFAULT TRUE,
    attribution_text TEXT,
    
    -- Legal and compliance
    usage_rights TEXT,
    expiration_date DATE,
    
    -- Reference to your existing data_sources table
    data_source_id UUID REFERENCES data_sources(id),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_source_type CHECK (
        source_type IN ('user_upload', 'web_scrape', 'api', 'book_scan', 'catalog')
    ),
    CONSTRAINT valid_license_type CHECK (
        license_type IN ('cc0', 'cc_by', 'cc_by_sa', 'copyright', 'fair_use', 'unknown')
    )
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Core schema indexes
CREATE INDEX idx_models_manufacturer_year ON models(manufacturer_id, year);
CREATE INDEX idx_models_attestation_uid ON models(attestation_uid);
CREATE INDEX idx_models_attestation_status ON models(attestation_status);
CREATE INDEX idx_individual_guitars_model ON individual_guitars(model_id);
CREATE INDEX idx_individual_guitars_attestation_uid ON individual_guitars(attestation_uid);
CREATE INDEX idx_individual_guitars_attestation_status ON individual_guitars(attestation_status);
CREATE INDEX idx_specifications_model ON specifications(model_id);
CREATE INDEX idx_specifications_individual ON specifications(individual_guitar_id);
CREATE INDEX idx_citations_cited_record ON citations(cited_table, cited_record_id);
CREATE INDEX idx_market_valuations_date ON market_valuations(valuation_date);

-- Text search indexes (if pg_trgm extension is available)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
        CREATE INDEX idx_manufacturers_name_trgm ON manufacturers USING gin(name gin_trgm_ops);
        CREATE INDEX idx_models_name_trgm ON models USING gin(name gin_trgm_ops);
        CREATE INDEX idx_product_lines_name_trgm ON product_lines USING gin(name gin_trgm_ops);
    END IF;
END $$;

-- Pattern matching indexes
CREATE INDEX idx_manufacturers_name_pattern ON manufacturers(name varchar_pattern_ops);
CREATE INDEX idx_models_name_pattern ON models(name varchar_pattern_ops);
CREATE INDEX idx_product_lines_name_pattern ON product_lines(name varchar_pattern_ops);

-- Composite lookup indexes
CREATE INDEX idx_models_full_lookup ON models(manufacturer_id, LOWER(name), year, production_type);
CREATE INDEX idx_individual_guitars_lookup ON individual_guitars(model_id, serial_number, production_date) WHERE serial_number IS NOT NULL;

-- Fallback lookup indexes for individual guitars
CREATE INDEX idx_individual_guitars_fallback_lookup ON individual_guitars(
    LOWER(manufacturer_name_fallback), 
    LOWER(model_name_fallback), 
    year_estimate
) WHERE manufacturer_name_fallback IS NOT NULL;

CREATE INDEX idx_individual_guitars_serial_lower ON individual_guitars(LOWER(serial_number)) WHERE serial_number IS NOT NULL;

-- Specification indexes
CREATE INDEX idx_specifications_body_wood ON specifications(body_wood) WHERE body_wood IS NOT NULL;
CREATE INDEX idx_specifications_neck_wood ON specifications(neck_wood) WHERE neck_wood IS NOT NULL;
CREATE INDEX idx_specifications_pickup_config ON specifications(pickup_configuration) WHERE pickup_configuration IS NOT NULL;
CREATE INDEX idx_specifications_year_range ON specifications(scale_length_inches, num_frets) WHERE scale_length_inches IS NOT NULL;



-- Expert reviews indexes
CREATE INDEX idx_expert_reviews_reviewer ON expert_reviews(reviewer_name);
CREATE INDEX idx_expert_reviews_verification ON expert_reviews(verification_status);
CREATE INDEX idx_expert_reviews_type ON expert_reviews(content_type);
CREATE INDEX idx_expert_reviews_date ON expert_reviews(review_date);

-- Review model associations indexes
CREATE INDEX idx_review_model_associations_review ON review_model_associations(review_id);
CREATE INDEX idx_review_model_associations_model ON review_model_associations(model_id);

-- Market valuations indexes
CREATE INDEX idx_market_valuations_model_date ON market_valuations(model_id, valuation_date) WHERE model_id IS NOT NULL;
CREATE INDEX idx_market_valuations_individual_date ON market_valuations(individual_guitar_id, valuation_date) WHERE individual_guitar_id IS NOT NULL;
CREATE INDEX idx_market_valuations_price_range ON market_valuations(average_estimate, valuation_date) WHERE average_estimate IS NOT NULL;
CREATE INDEX idx_market_valuations_venue ON market_valuations(sale_venue) WHERE sale_venue IS NOT NULL;

-- Data sources and citations indexes
CREATE INDEX idx_data_sources_type ON data_sources(source_type);
CREATE INDEX idx_data_sources_reliability ON data_sources(reliability_score) WHERE reliability_score IS NOT NULL;
CREATE INDEX idx_data_sources_date ON data_sources(publication_date) WHERE publication_date IS NOT NULL;
CREATE INDEX idx_citations_source ON citations(source_id);
CREATE INDEX idx_citations_confidence ON citations(confidence_level);

-- User and contribution indexes
CREATE INDEX idx_users_type ON users(user_type);
CREATE INDEX idx_users_verified ON users(verified_expert) WHERE verified_expert = true;
CREATE INDEX idx_contributions_user ON contributions(user_id);
CREATE INDEX idx_contributions_status ON contributions(status);
CREATE INDEX idx_contributions_type ON contributions(contribution_type);
CREATE INDEX idx_contributions_table_record ON contributions(table_name, record_id);

-- Specialized indexes for common queries
CREATE INDEX idx_manufacturers_active ON manufacturers(id, name) WHERE status = 'active' OR status IS NULL;
CREATE INDEX idx_models_current_production ON models(id, manufacturer_id, name) WHERE production_end_date IS NULL;
CREATE INDEX idx_individual_guitars_high_value ON individual_guitars(id, model_id) WHERE current_estimated_value > 10000;

-- Additional individual guitars indexes for hybrid approach
CREATE INDEX idx_individual_guitars_model_production ON individual_guitars(model_id, production_date) WHERE model_id IS NOT NULL;
CREATE INDEX idx_individual_guitars_serial_unique ON individual_guitars(serial_number) WHERE serial_number IS NOT NULL;
CREATE INDEX idx_individual_guitars_significance ON individual_guitars(significance_level, current_estimated_value);

-- Partial indexes for performance
CREATE INDEX idx_models_with_details ON models(manufacturer_id, year) 
    WHERE description IS NOT NULL OR estimated_production_quantity IS NOT NULL;

CREATE INDEX idx_individual_guitars_with_value ON individual_guitars(model_id) 
    WHERE current_estimated_value IS NOT NULL AND current_estimated_value > 0;

-- Image management indexes
CREATE INDEX idx_images_entity ON images(entity_type, entity_id);
CREATE INDEX idx_images_type ON images(image_type);
CREATE INDEX idx_images_primary ON images(entity_type, entity_id) WHERE is_primary = TRUE;
CREATE INDEX idx_images_validation ON images(validation_status) WHERE validation_status != 'approved';
CREATE INDEX idx_images_uploaded_by ON images(uploaded_by);
CREATE INDEX idx_images_uploaded_at ON images(uploaded_at);
CREATE INDEX idx_images_storage_key ON images(storage_key);

-- Duplicate management indexes
CREATE INDEX idx_images_duplicates ON images(original_image_id) WHERE is_duplicate = TRUE;
CREATE INDEX idx_images_storage_duplicates ON images(storage_key, entity_type, entity_id);

-- Partial index for tags (only if tags exist)
CREATE INDEX idx_images_tags ON images USING gin(tags) WHERE array_length(tags, 1) > 0;

CREATE INDEX idx_image_sources_image ON image_sources(image_id);
CREATE INDEX idx_image_sources_type ON image_sources(source_type);

-- EAS attestation indexes
CREATE INDEX idx_attestations_uid ON attestations(uid);
CREATE INDEX idx_attestations_schema_uid ON attestations(schema_uid);
CREATE INDEX idx_attestations_schema_type ON attestations(schema_type);
CREATE INDEX idx_attestations_entity_type_id ON attestations(entity_type, entity_id);
CREATE INDEX idx_attestations_schema_version ON attestations(schema_version);
CREATE INDEX idx_attestations_status ON attestations(status);
CREATE INDEX idx_attestations_signer_wallet ON attestations(signer_wallet);
CREATE INDEX idx_attestations_cosigner_wallet ON attestations(cosigner_wallet);
CREATE INDEX idx_attestations_signed_at ON attestations(signed_at);

-- Schema versions indexes
CREATE INDEX idx_schema_versions_name ON schema_versions(schema_name);
CREATE INDEX idx_schema_versions_status ON schema_versions(status);
CREATE INDEX idx_schema_versions_schema_uid ON schema_versions(schema_uid);
CREATE INDEX idx_schema_versions_effective_date ON schema_versions(effective_date);

-- Manufacturer wallets indexes
CREATE INDEX idx_manufacturer_wallets_manufacturer_id ON manufacturer_wallets(manufacturer_id);
CREATE INDEX idx_manufacturer_wallets_wallet_address ON manufacturer_wallets(wallet_address);
CREATE INDEX idx_manufacturer_wallets_status ON manufacturer_wallets(status);

-- ============================================================================
-- TRIGGERS AND FUNCTIONS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at columns
CREATE TRIGGER update_manufacturers_updated_at BEFORE UPDATE ON manufacturers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_product_lines_updated_at BEFORE UPDATE ON product_lines FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_models_updated_at BEFORE UPDATE ON models FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_individual_guitars_updated_at BEFORE UPDATE ON individual_guitars FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_expert_reviews_updated_at BEFORE UPDATE ON expert_reviews FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- IMAGE MANAGEMENT FUNCTIONS AND VIEWS
-- ============================================================================

-- Primary images for catalog display
CREATE VIEW catalog_images AS
SELECT 
    entity_type,
    entity_id,
    id as image_id,
    medium_url as display_url,
    thumbnail_url,
    caption
FROM images
WHERE is_primary = TRUE
  AND validation_status = 'approved'
  AND is_duplicate = FALSE; -- Only show original images, not duplicates

-- All images for a given entity with full details
CREATE OR REPLACE FUNCTION get_entity_images(
    p_entity_type VARCHAR,
    p_entity_id UUID
) RETURNS TABLE (
    image_id UUID,
    image_type VARCHAR,
    display_order INTEGER,
    urls JSONB,
    metadata JSONB,
    source JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id,
        i.image_type,
        i.display_order,
        jsonb_build_object(
            'thumbnail', i.thumbnail_url,
            'small', i.small_url,
            'medium', i.medium_url,
            'large', i.large_url,
            'xlarge', i.xlarge_url,
            'original', i.original_url
        ) as urls,
        jsonb_build_object(
            'filename', i.original_filename,
            'dimensions', jsonb_build_object('width', i.width, 'height', i.height),
            'aspect_ratio', i.aspect_ratio,
            'size_bytes', i.file_size_bytes,
            'caption', i.caption,
            'tags', i.tags
        ) as metadata,
        jsonb_build_object(
            'type', s.source_type,
            'name', s.source_name,
            'attribution', s.attribution_text,
            'license', s.license_type
        ) as source
    FROM images i
    LEFT JOIN image_sources s ON s.image_id = i.id
    WHERE i.entity_type = p_entity_type
      AND i.entity_id = p_entity_id
      AND i.validation_status = 'approved'
    ORDER BY i.is_primary DESC, i.display_order, i.uploaded_at;
END;
$$ LANGUAGE plpgsql;

-- Function to create a duplicate image for another entity
CREATE OR REPLACE FUNCTION create_image_duplicate(
    p_original_image_id UUID,
    p_target_entity_type VARCHAR,
    p_target_entity_id UUID,
    p_image_type VARCHAR DEFAULT 'gallery',
    p_is_primary BOOLEAN DEFAULT FALSE,
    p_caption TEXT DEFAULT NULL,
    p_duplicate_reason TEXT DEFAULT NULL
) RETURNS UUID AS $$
DECLARE
    v_new_image_id UUID;
    v_original_image RECORD;
BEGIN
    -- Get the original image data
    SELECT * INTO v_original_image 
    FROM images 
    WHERE id = p_original_image_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Original image not found: %', p_original_image_id;
    END IF;
    
    -- If setting as primary, unset any existing primary for this entity
    IF p_is_primary THEN
        UPDATE images 
        SET is_primary = FALSE 
        WHERE entity_type = p_target_entity_type 
          AND entity_id = p_target_entity_id 
          AND is_primary = TRUE;
    END IF;
    
    -- Get next display order
    SELECT COALESCE(MAX(display_order), 0) + 1 
    INTO v_original_image.display_order
    FROM images 
    WHERE entity_type = p_target_entity_type 
      AND entity_id = p_target_entity_id;
    
    -- Create the duplicate
    INSERT INTO images (
        entity_type, entity_id, image_type, is_primary, display_order, caption,
        storage_provider, storage_key, original_url,
        thumbnail_url, small_url, medium_url, large_url, xlarge_url,
        original_filename, mime_type, file_size_bytes, width, height,
        aspect_ratio, dominant_color, uploaded_by, validation_status,
        tags, description, is_duplicate, original_image_id, duplicate_reason
    ) VALUES (
        p_target_entity_type, p_target_entity_id, p_image_type, p_is_primary, 
        v_original_image.display_order, COALESCE(p_caption, v_original_image.caption),
        v_original_image.storage_provider, v_original_image.storage_key, v_original_image.original_url,
        v_original_image.thumbnail_url, v_original_image.small_url, v_original_image.medium_url,
        v_original_image.large_url, v_original_image.xlarge_url,
        v_original_image.original_filename, v_original_image.mime_type, v_original_image.file_size_bytes,
        v_original_image.width, v_original_image.height,
        v_original_image.aspect_ratio, v_original_image.dominant_color, v_original_image.uploaded_by,
        v_original_image.validation_status,
        v_original_image.tags, v_original_image.description,
        TRUE, p_original_image_id, p_duplicate_reason
    ) RETURNING id INTO v_new_image_id;
    
    RETURN v_new_image_id;
END;
$$ LANGUAGE plpgsql;

-- Function to find all duplicates of an image
CREATE OR REPLACE FUNCTION get_image_duplicates(p_image_id UUID)
RETURNS TABLE (
    duplicate_id UUID,
    entity_type VARCHAR,
    entity_id UUID,
    image_type VARCHAR,
    is_primary BOOLEAN,
    caption TEXT,
    duplicate_reason TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id,
        i.entity_type,
        i.entity_id,
        i.image_type,
        i.is_primary,
        i.caption,
        i.duplicate_reason
    FROM images i
    WHERE i.original_image_id = p_image_id
    ORDER BY i.entity_type, i.entity_id, i.display_order;
END;
$$ LANGUAGE plpgsql;

-- Function to find images by storage key (all duplicates)
CREATE OR REPLACE FUNCTION get_images_by_storage_key(p_storage_key VARCHAR)
RETURNS TABLE (
    image_id UUID,
    entity_type VARCHAR,
    entity_id UUID,
    image_type VARCHAR,
    is_primary BOOLEAN,
    is_duplicate BOOLEAN,
    original_image_id UUID,
    caption TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id,
        i.entity_type,
        i.entity_id,
        i.image_type,
        i.is_primary,
        i.is_duplicate,
        i.original_image_id,
        i.caption
    FROM images i
    WHERE i.storage_key = p_storage_key
    ORDER BY i.is_duplicate, i.entity_type, i.entity_id, i.display_order;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- COMMENTS AND DOCUMENTATION
-- ============================================================================

-- Add comments for documentation
COMMENT ON TABLE images IS 'Stores image metadata with direct entity associations, supports duplicates for many-to-many relationships';
COMMENT ON TABLE image_sources IS 'Tracks image sources and attribution requirements';
COMMENT ON VIEW catalog_images IS 'Simplified view for catalog display showing only primary approved images (no duplicates)';
COMMENT ON FUNCTION create_image_duplicate IS 'Creates a duplicate image record for another entity, sharing the same storage asset';
COMMENT ON FUNCTION get_image_duplicates IS 'Returns all duplicate images of a given original image';
COMMENT ON FUNCTION get_images_by_storage_key IS 'Returns all images (original and duplicates) that share the same storage key';

-- ============================================================================
-- POST-INSTALLATION SETUP
-- ============================================================================

-- IMPORTANT: After running this script, you need to grant permissions to your application user:
-- 
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO guitar_registry_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO guitar_registry_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO guitar_registry_user;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA public TO guitar_registry_user;
--
-- Replace 'guitar_registry_user' with your actual application database user.
--
-- Example:
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO guitar_registry_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO guitar_registry_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO guitar_registry_user;
-- GRANT SELECT ON ALL VIEWS IN SCHEMA public TO guitar_registry_user; 