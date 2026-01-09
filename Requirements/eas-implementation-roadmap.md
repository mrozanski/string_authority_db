# EAS Implementation Roadmap - Guitar Registry

**Based on PRD:** `eas-model-instrument-attestations.md`
**Created:** 2025-11-10
**Status:** Ready to Execute

---

## Quick Summary

This roadmap outlines the step-by-step implementation of EAS attestations for guitar models and instruments. The implementation is divided into 3 major phases over 8 weeks, with clear deliverables and milestones.

---

## Implementation Phases

### Phase 1: Model Attestations Foundation (Weeks 1-4)

**Goal:** Enable creation of cryptographically signed model attestations with manufacturer co-signing capability.

#### Phase 1A: Core Infrastructure (Weeks 1-2)

**Setup & Configuration:**
```bash
# 1. Install dependencies
npm install @ethereum-attestation-service/eas-sdk ethers ipfs-http-client

# 2. Setup environment variables
# Copy .env.example to .env.local and add:
# - EAS_CONTRACT_ADDRESS
# - BASE_RPC_URL
# - PINATA_API_KEY
# - VERSION_METADATA_SCHEMA_UID (from schema registration)
# - MODEL_SCHEMA_UID (from schema registration)
# - MODEL_SCHEMA_VERSION (default: 1.0.0)

# 3. Register Version Metadata Schema FIRST (for schema versioning)
npm run register-version-schema

# 4. Register Model and Instrument schemas
npm run register-eas-schemas
```

**Database Migration:**
```sql
-- Step 1: Add attestation fields to models table
ALTER TABLE models
ADD COLUMN attestation_uid VARCHAR(66),
ADD COLUMN ipfs_cid VARCHAR(100),
ADD COLUMN attestation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN attested_by VARCHAR(100),
ADD COLUMN attested_at TIMESTAMPTZ,
ADD COLUMN cosigner_wallet VARCHAR(42),
ADD COLUMN cosigned_at TIMESTAMPTZ;

-- Step 2: Create attestations tracking table
CREATE TABLE attestations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    uid VARCHAR(66) UNIQUE NOT NULL,
    schema_uid VARCHAR(66) NOT NULL,
    schema_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
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
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_attestations_schema_version ON attestations(schema_version);

-- Step 3: Create schema versions registry table
CREATE TABLE schema_versions (
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
    UNIQUE(schema_name, version)
);

CREATE INDEX idx_schema_versions_name ON schema_versions(schema_name);
CREATE INDEX idx_schema_versions_status ON schema_versions(status);

-- Step 4: Create manufacturer wallet registry
CREATE TABLE manufacturer_wallets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v7(),
    manufacturer_id UUID NOT NULL REFERENCES manufacturers(id),
    wallet_address VARCHAR(42) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    registered_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Step 4: Run Prisma update
npx prisma db pull && npx prisma generate
```

**File Structure to Create:**
```
src/
├── lib/
│   ├── eas/
│   │   ├── config.ts          # EAS configuration, schema definitions
│   │   ├── schemas/
│   │   │   ├── versions.ts    # Schema version management utilities
│   │   │   ├── decoders/
│   │   │   │   └── model-v1.ts    # Decoder for model schema v1.0.0
│   │   │   └── encoders/
│   │   │       └── model-v1.ts    # Encoder for model schema v1.0.0
│   │   ├── attestation.ts     # Core attestation creation logic
│   │   └── verification.ts    # Signature verification
│   ├── ipfs/
│   │   ├── client.ts          # IPFS client setup
│   │   └── pinning.ts         # Pinning logic (async queue)
│   ├── actions/
│   │   └── attestations.ts    # Server actions for attestations
│   └── data/
│       └── attestations.ts    # Data fetching functions
└── app/
    └── api/
        └── attestations/
            ├── models/
            │   └── create/
            │       └── route.ts
            ├── cosign/
            │   └── route.ts
            └── [uid]/
                └── route.ts
```

**Key Files to Implement:**

**1. `src/lib/eas/config.ts`**
```typescript
export const EAS_CONFIG = {
  contractAddress: process.env.EAS_CONTRACT_ADDRESS!,
  chainId: 8453, // Base mainnet (use 84532 for Sepolia testnet)
  rpcUrl: process.env.BASE_RPC_URL!,
  schemas: {
    versionMetadata: {
      uid: process.env.VERSION_METADATA_SCHEMA_UID!,
      definition: "bytes32 schema_uid,string schema_name,uint8 major_version,uint8 minor_version,bytes32 previous_version_uid,bytes32 next_version_uid,string changelog,uint64 effective_date,bool deprecated"
    },
    model: {
      uid: process.env.MODEL_SCHEMA_UID!,
      version: process.env.MODEL_SCHEMA_VERSION || '1.0.0',
      definition: "string manufacturer_name,string product_line_name,string model_name,uint16 year,string db_reference_id,string production_type,string production_dates,uint32 estimated_quantity,string original_msrp,string currency,string description"
    },
    instrument: {
      uid: process.env.INSTRUMENT_SCHEMA_UID!,
      version: process.env.INSTRUMENT_SCHEMA_VERSION || '1.0.0',
      definition: "bytes32 model_attestation_uid,string serial_number,string db_reference_id,string production_date,uint32 production_number,string significance_level,string current_condition,string modifications,string provenance_summary"
    }
  }
};
```

**2. `src/lib/eas/attestation.ts`**
```typescript
import { EAS, SchemaEncoder } from '@ethereum-attestation-service/eas-sdk';
import { ethers } from 'ethers';
import { EAS_CONFIG } from './config';

export async function createModelAttestation(
  modelData: ModelAttestationData,
  signerWallet: ethers.Wallet
) {
  // 1. Initialize EAS
  const eas = new EAS(EAS_CONFIG.contractAddress);
  const offchain = await eas.getOffchain();

  // 2. Encode data
  const encoder = new SchemaEncoder(EAS_CONFIG.schemas.model.definition);
  const encodedData = encoder.encodeData([
    { name: "manufacturer_name", value: modelData.manufacturer_name, type: "string" },
    { name: "product_line_name", value: modelData.product_line_name, type: "string" },
    { name: "model_name", value: modelData.model_name, type: "string" },
    { name: "year", value: modelData.year, type: "uint16" },
    { name: "db_reference_id", value: modelData.db_reference_id, type: "string" },
    // ... other fields
  ]);

  // 3. Create offchain attestation
  const attestation = await offchain.signOffchainAttestation({
    schema: EAS_CONFIG.schemas.model.uid,
    recipient: "0x0000000000000000000000000000000000000000",
    expirationTime: 0n,
    revocable: true,
    data: encodedData
  }, signerWallet);

  return attestation;
}
```

**3. `src/lib/actions/attestations.ts`**
```typescript
'use server'

import { prisma } from '@/lib/prisma';
import { createModelAttestation } from '@/lib/eas/attestation';
import { pinToIPFS } from '@/lib/ipfs/pinning';
import { ethers } from 'ethers';

export async function createModelAttestationAction(modelId: string) {
  // 1. Fetch model data
  const model = await prisma.models.findUnique({
    where: { id: modelId },
    include: {
      manufacturers: true,
      product_lines: true
    }
  });

  if (!model) {
    throw new Error('Model not found');
  }

  if (model.attestation_uid) {
    throw new Error('Model already has attestation');
  }

  // 2. Create admin wallet (in production, use secure key management)
  const adminWallet = new ethers.Wallet(process.env.ADMIN_WALLET_PRIVATE_KEY!);

  // 3. Create attestation
  const attestation = await createModelAttestation({
    manufacturer_name: model.manufacturers.name,
    product_line_name: model.product_lines.name,
    model_name: model.name,
    year: model.year,
    db_reference_id: model.id,
    // ... other fields from model
  }, adminWallet);

  // 4. Pin to IPFS (async)
  const ipfsCID = await pinToIPFS(attestation);

  // 5. Store in database
  await prisma.attestations.create({
    data: {
      uid: attestation.uid,
      schema_uid: EAS_CONFIG.schemas.model.uid,
      schema_type: 'model',
      entity_type: 'model',
      entity_id: model.id,
      attestation_data: {
        manufacturer_name: model.manufacturers.name,
        model_name: model.name,
        year: model.year,
        // ... full decoded data
      },
      ipfs_cid: ipfsCID,
      schema_version: EAS_CONFIG.schemas.model.version, // Track schema version
      signer_wallet: adminWallet.address,
      signer_role: 'admin',
      signed_at: new Date(),
      status: 'pending'
    }
  });

  // 6. Update model
  await prisma.models.update({
    where: { id: modelId },
    data: {
      attestation_uid: attestation.uid,
      ipfs_cid: ipfsCID,
      attestation_status: 'pending',
      attested_by: adminWallet.address,
      attested_at: new Date()
    }
  });

  return { success: true, uid: attestation.uid, ipfs_cid: ipfsCID };
}
```

**4. `src/lib/eas/schemas/versions.ts`** (New - for schema versioning)
```typescript
'use server'

import { prisma } from '@/lib/prisma';
import { EAS_CONFIG } from '../config';

/**
 * Get the version chain for a schema
 */
export async function getSchemaVersionChain(schemaName: string) {
  const currentVersion = await prisma.schema_versions.findFirst({
    where: {
      schema_name: schemaName,
      status: 'active'
    },
    orderBy: { effective_date: 'desc' }
  });

  if (!currentVersion) return [];

  // Walk the chain backward
  const versions = [];
  let version = currentVersion;
  while (version) {
    versions.push(version);
    version = version.previous_version_id
      ? await prisma.schema_versions.findUnique({
          where: { id: version.previous_version_id }
        })
      : null;
  }

  return versions.reverse(); // [v1.0.0, v1.1.0, v2.0.0]
}

/**
 * Get current active schema version
 */
export async function getCurrentSchemaVersion(schemaName: string) {
  return await prisma.schema_versions.findFirst({
    where: {
      schema_name: schemaName,
      status: 'active'
    },
    orderBy: { effective_date: 'desc' }
  });
}

/**
 * Get schema version by UID
 */
export async function getSchemaVersion(schemaUID: string) {
  const versionRecord = await prisma.schema_versions.findFirst({
    where: { schema_uid: schemaUID }
  });

  return versionRecord?.version || '1.0.0'; // Default to 1.0.0 if not found
}

/**
 * Register initial schema version in database
 * Call this during Phase 1A setup
 */
export async function registerInitialSchemaVersions() {
  // Register Model Schema v1.0.0
  await prisma.schema_versions.create({
    data: {
      schema_name: 'GuitarModelAttestation',
      version: '1.0.0',
      schema_uid: EAS_CONFIG.schemas.model.uid,
      previous_version_id: null,
      next_version_id: null,
      changelog: 'Initial model attestation schema',
      effective_date: new Date(),
      status: 'active'
    }
  });

  // Register Instrument Schema v1.0.0
  await prisma.schema_versions.create({
    data: {
      schema_name: 'GuitarInstrumentAttestation',
      version: '1.0.0',
      schema_uid: EAS_CONFIG.schemas.instrument.uid,
      previous_version_id: null,
      next_version_id: null,
      changelog: 'Initial instrument attestation schema',
      effective_date: new Date(),
      status: 'active'
    }
  });

  console.log('Initial schema versions registered');
}
```

**Testing Checklist for Phase 1A:**
- [ ] EAS SDK initializes correctly
- [ ] Schema encoding produces valid data
- [ ] Attestation creation returns UID
- [ ] IPFS pinning succeeds
- [ ] Database records created correctly
- [ ] Model detail page shows attestation UID
- [ ] Version Metadata Schema registered successfully
- [ ] Schema version recorded in database
- [ ] Version chain query returns correct history

---

#### Phase 1B: Manufacturer Co-Signing (Week 3)

**Components to Build:**

**1. Manufacturer Wallet Registration (`src/app/admin/manufacturers/[id]/wallets/page.tsx`)**
- Form to register manufacturer wallet addresses
- Wallet verification (sign message to prove ownership)
- List of registered wallets with status

**2. Co-Signing API (`src/app/api/attestations/cosign/route.ts`)**
```typescript
import { NextRequest } from 'next/server';
import { prisma } from '@/lib/prisma';
import { ethers } from 'ethers';

export async function POST(req: NextRequest) {
  const { attestation_uid, signature, wallet_address } = await req.json();

  // 1. Verify manufacturer wallet is registered
  const manufacturerWallet = await prisma.manufacturer_wallets.findUnique({
    where: { wallet_address },
    include: { manufacturers: true }
  });

  if (!manufacturerWallet || manufacturerWallet.status !== 'active') {
    return Response.json({ error: 'Unauthorized wallet' }, { status: 403 });
  }

  // 2. Fetch attestation
  const attestation = await prisma.attestations.findUnique({
    where: { uid: attestation_uid }
  });

  if (!attestation) {
    return Response.json({ error: 'Attestation not found' }, { status: 404 });
  }

  // 3. Verify manufacturer matches model manufacturer
  const model = await prisma.models.findUnique({
    where: { id: attestation.entity_id },
    include: { manufacturers: true }
  });

  if (model.manufacturer_id !== manufacturerWallet.manufacturer_id) {
    return Response.json({ error: 'Manufacturer mismatch' }, { status: 403 });
  }

  // 4. Verify signature
  const message = JSON.stringify({
    attestation_uid,
    action: 'cosign',
    timestamp: Date.now()
  });

  const recoveredAddress = ethers.verifyMessage(message, signature);

  if (recoveredAddress.toLowerCase() !== wallet_address.toLowerCase()) {
    return Response.json({ error: 'Invalid signature' }, { status: 400 });
  }

  // 5. Update attestation with cosignature
  await prisma.attestations.update({
    where: { uid: attestation_uid },
    data: {
      cosigner_wallet: wallet_address,
      cosigner_role: 'manufacturer',
      cosigned_at: new Date(),
      status: 'official'
    }
  });

  // 6. Update model
  await prisma.models.update({
    where: { id: attestation.entity_id },
    data: {
      attestation_status: 'official',
      cosigner_wallet: wallet_address,
      cosigned_at: new Date()
    }
  });

  return Response.json({ success: true, status: 'official' });
}
```

**3. Manufacturer Dashboard (`src/app/dashboard/manufacturer/page.tsx`)**
```typescript
import { getPendingModelAttestations } from '@/lib/data/attestations';
import { CosignButton } from '@/components/attestations/CosignButton';

export default async function ManufacturerDashboard() {
  // Get manufacturer from session/wallet
  const pendingAttestations = await getPendingModelAttestations();

  return (
    <div className="container mx-auto py-8">
      <h1 className="text-3xl font-bold mb-6">Manufacturer Dashboard</h1>

      <section>
        <h2 className="text-2xl font-semibold mb-4">
          Pending Verifications ({pendingAttestations.length})
        </h2>

        <div className="grid gap-4">
          {pendingAttestations.map(attestation => (
            <div key={attestation.uid} className="border rounded-lg p-4">
              <h3 className="font-semibold">
                {attestation.attestation_data.model_name} ({attestation.attestation_data.year})
              </h3>
              <p className="text-sm text-muted-foreground">
                Created: {new Date(attestation.signed_at).toLocaleDateString()}
              </p>
              <CosignButton attestationUid={attestation.uid} />
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
```

**Testing Checklist for Phase 1B:**
- [ ] Manufacturer can register wallet
- [ ] Wallet verification works
- [ ] Co-signing API validates manufacturer correctly
- [ ] Signature verification works
- [ ] Status updates from 'pending' to 'official'
- [ ] Manufacturer dashboard shows correct pending attestations

---

#### Phase 1C: UI Polish (Week 4)

**Components to Update:**

**1. Model Detail Page - Attestation Section**
```typescript
// src/app/models/[id]/page.tsx

import { AttestationBadge } from '@/components/attestations/AttestationBadge';
import { CopyButton } from '@/components/ui/copy-button';

export default async function ModelPage({ params }: { params: { id: string } }) {
  const model = await getModelWithAttestation(params.id);

  return (
    <div className="container mx-auto py-8">
      {/* Existing model details */}

      {/* NEW: Attestation Section */}
      {model.attestation_uid && (
        <section className="mt-8 border rounded-lg p-6 bg-card">
          <h2 className="text-xl font-semibold mb-4">Blockchain Attestation</h2>

          <div className="space-y-4">
            <div>
              <AttestationBadge
                status={model.attestation_status}
                uid={model.attestation_uid}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="font-medium">Attestation UID:</span>
                <div className="flex items-center gap-2 mt-1">
                  <code className="text-xs bg-muted px-2 py-1 rounded">
                    {model.attestation_uid}
                  </code>
                  <CopyButton value={model.attestation_uid} />
                </div>
              </div>

              <div>
                <span className="font-medium">IPFS CID:</span>
                <div className="flex items-center gap-2 mt-1">
                  <code className="text-xs bg-muted px-2 py-1 rounded">
                    {model.ipfs_cid}
                  </code>
                  <a
                    href={`https://gateway.pinata.cloud/ipfs/${model.ipfs_cid}`}
                    target="_blank"
                    className="text-blue-600 hover:underline text-xs"
                  >
                    View on IPFS
                  </a>
                </div>
              </div>

              <div>
                <span className="font-medium">Attested by:</span>
                <div className="mt-1">
                  <code className="text-xs bg-muted px-2 py-1 rounded">
                    {model.attested_by}
                  </code>
                  <span className="text-xs text-muted-foreground ml-2">
                    ({new Date(model.attested_at).toLocaleDateString()})
                  </span>
                </div>
              </div>

              {model.cosigner_wallet && (
                <div>
                  <span className="font-medium">Verified by Manufacturer:</span>
                  <div className="mt-1">
                    <code className="text-xs bg-muted px-2 py-1 rounded">
                      {model.cosigner_wallet}
                    </code>
                    <span className="text-xs text-muted-foreground ml-2">
                      ({new Date(model.cosigned_at).toLocaleDateString()})
                    </span>
                  </div>
                </div>
              )}
            </div>

            <div className="pt-4 border-t">
              <p className="text-xs text-muted-foreground">
                This model has been cryptographically attested using the Ethereum Attestation Service (EAS).
                The attestation is stored on IPFS for permanent, decentralized access.
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
```

**2. Model Creation Flow Update**
```typescript
// src/app/models/create/page.tsx

async function handleSubmit(formData: FormData) {
  // 1. Create model in database
  const model = await createModel(formData);

  // 2. Create attestation
  const attestation = await createModelAttestationAction(model.id);

  // 3. Show success with attestation details
  toast.success(
    `Model created successfully! Attestation UID: ${attestation.uid.slice(0, 10)}...`
  );

  // 4. Redirect to model detail page
  router.push(`/models/${model.id}`);
}
```

**Testing Checklist for Phase 1C:**
- [ ] Model detail page shows attestation section
- [ ] Attestation badge displays correct status
- [ ] Copy buttons work
- [ ] IPFS link opens correctly
- [ ] Model creation flow includes attestation
- [ ] Success messages are clear and helpful

---

### Phase 2: Instrument Attestations (Weeks 5-7)

**Goal:** Enable creation of instrument attestations that reference model attestations.

#### Phase 2A: Database & Schema (Week 5)

**Database Migration:**
```sql
-- Add attestation fields to individual_guitars
ALTER TABLE individual_guitars
ADD COLUMN attestation_uid VARCHAR(66),
ADD COLUMN ipfs_cid VARCHAR(100),
ADD COLUMN attestation_status VARCHAR(20) DEFAULT 'pending',
ADD COLUMN attested_by VARCHAR(100),
ADD COLUMN attested_at TIMESTAMPTZ,
ADD COLUMN cosigner_wallet VARCHAR(42),
ADD COLUMN cosigned_at TIMESTAMPTZ;

-- Create indexes
CREATE INDEX idx_individual_guitars_attestation_uid ON individual_guitars(attestation_uid);
```

**Register Instrument Schema:**
```bash
# Run schema registration script
npm run register-instrument-schema
```

**Implementation Similar to Model Attestations:**
1. `createInstrumentAttestation()` function in `src/lib/eas/attestation.ts`
2. `createInstrumentAttestationAction()` server action
3. API endpoint `/api/attestations/instruments/create`
4. Update instrument creation form

**Key Difference:**
- Instrument attestation includes `model_attestation_uid` field
- Validation: Model must have attestation before instrument can be attested

```typescript
export async function createInstrumentAttestation(
  instrumentData: InstrumentAttestationData,
  signerWallet: ethers.Wallet
) {
  // Encode with model_attestation_uid as bytes32
  const encodedData = encoder.encodeData([
    { name: "model_attestation_uid", value: instrumentData.model_attestation_uid, type: "bytes32" },
    { name: "serial_number", value: instrumentData.serial_number, type: "string" },
    // ... other fields
  ]);

  // ... rest same as model attestation
}
```

---

#### Phase 2B: Chain Visualization (Week 6-7)

**Provenance Chain Component:**
```typescript
// src/components/attestations/ProvenanceChain.tsx

export function ProvenanceChain({ instrumentId }: { instrumentId: string }) {
  const chain = await getAttestationChain(instrumentId);

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Chain of Provenance</h3>

      <div className="relative">
        {/* Model Attestation */}
        <div className="border rounded-lg p-4 bg-blue-50">
          <div className="text-sm font-medium">Model Attestation</div>
          <code className="text-xs">{chain.model.attestation_uid}</code>
          <div className="text-xs text-muted-foreground mt-1">
            {chain.model.manufacturer_name} - {chain.model.model_name} ({chain.model.year})
          </div>
        </div>

        {/* Arrow Down */}
        <div className="h-8 w-0.5 bg-gray-300 mx-auto"></div>

        {/* Instrument Attestation */}
        <div className="border rounded-lg p-4 bg-green-50">
          <div className="text-sm font-medium">Instrument Attestation</div>
          <code className="text-xs">{chain.instrument.attestation_uid}</code>
          <div className="text-xs text-muted-foreground mt-1">
            Serial: {chain.instrument.serial_number}
          </div>
        </div>

        {/* Arrow Down */}
        {chain.reviews.length > 0 && (
          <>
            <div className="h-8 w-0.5 bg-gray-300 mx-auto"></div>

            {/* Reviews */}
            <div className="border rounded-lg p-4 bg-yellow-50">
              <div className="text-sm font-medium">Reviews ({chain.reviews.length})</div>
              {chain.reviews.map(review => (
                <div key={review.attestation_uid} className="text-xs mt-1">
                  <code>{review.attestation_uid.slice(0, 10)}...</code>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
```

---

### Phase 3: Production Deployment (Week 8)

**Pre-Launch Checklist:**
- [ ] All tests passing (unit, integration, e2e)
- [ ] Security audit complete
- [ ] Register schemas on Base mainnet
- [ ] Setup production IPFS pinning service
- [ ] Configure production environment variables
- [ ] Database migration on production
- [ ] Manufacturer wallets registered
- [ ] Documentation complete (user guides, API docs)
- [ ] Monitoring and logging configured

**Deployment Steps:**
1. Register schemas on Base mainnet
2. Update environment variables with mainnet schema UIDs
3. Run database migration on production
4. Deploy Next.js application
5. Test with one manufacturer
6. Announce launch to other manufacturers

---

## Schema Evolution Procedures

**When You Need to Update a Schema (Future)**

This section provides step-by-step guidance for creating new schema versions when requirements change.

### Determining Version Bump

**Decision Tree:**

1. **Will this change break existing attestations?**
   - Yes (field removed, renamed, or type changed incompatibly) → **Major version** (1.0.0 → 2.0.0)
   - No → Continue to next question

2. **Are you adding new fields or expanding functionality?**
   - Yes (new optional fields, type expansion) → **Minor version** (1.0.0 → 1.1.0)
   - No → Continue to next question

3. **Are you only updating documentation or descriptions?**
   - Yes → **Patch version** (1.0.0 → 1.0.1, no schema re-registration needed)

### Step-by-Step Schema Update Process

#### Step 1: Register New Schema on Blockchain

```typescript
// scripts/register-schema-v2.ts
import { SchemaRegistry } from '@ethereum-attestation-service/eas-sdk';
import { ethers } from 'ethers';

async function registerModelSchemaV2() {
  const provider = new ethers.JsonRpcProvider(process.env.BASE_RPC_URL);
  const signer = new ethers.Wallet(process.env.ADMIN_PRIVATE_KEY, provider);

  const schemaRegistry = new SchemaRegistry(SCHEMA_REGISTRY_ADDRESS);
  schemaRegistry.connect(signer);

  // New schema with added fields
  const schemaV2 = "string manufacturer_name,string product_line_name,string model_name,uint16 year,string db_reference_id,string production_type,string production_dates,uint32 estimated_quantity,string original_msrp,string currency,string description,string finish_options,string pickup_variations";

  const tx = await schemaRegistry.register({
    schema: schemaV2,
    resolverAddress: "0x0000000000000000000000000000000000000000",
    revocable: true
  });

  await tx.wait();
  console.log("Model Schema v2.0.0 registered with UID:", tx.uid);

  // Save to .env: MODEL_SCHEMA_V2_UID=0x...
  return tx.uid;
}
```

#### Step 2: Create Version Link Attestation

```typescript
// Create attestation using Version Metadata Schema
import { EAS } from '@ethereum-attestation-service/eas-sdk';

async function createVersionLinkAttestation(newSchemaUID: string, previousSchemaUID: string) {
  const eas = new EAS(EAS_CONTRACT_ADDRESS);
  const offchain = await eas.getOffchain();

  const encoder = new SchemaEncoder(EAS_CONFIG.schemas.versionMetadata.definition);
  const encodedData = encoder.encodeData([
    { name: "schema_uid", value: newSchemaUID, type: "bytes32" },
    { name: "schema_name", value: "GuitarModelAttestation", type: "string" },
    { name: "major_version", value: 2, type: "uint8" },
    { name: "minor_version", value: 0, type: "uint8" },
    { name: "previous_version_uid", value: previousSchemaUID, type: "bytes32" },
    { name: "next_version_uid", value: "0x0000000000000000000000000000000000000000000000000000000000000000", type: "bytes32" },
    { name: "changelog", value: "Added finish_options and pickup_variations fields", type: "string" },
    { name: "effective_date", value: Math.floor(Date.now() / 1000), type: "uint64" },
    { name: "deprecated", value: false, type: "bool" }
  ]);

  const attestation = await offchain.signOffchainAttestation({
    schema: EAS_CONFIG.schemas.versionMetadata.uid,
    recipient: "0x0000000000000000000000000000000000000000",
    expirationTime: 0n,
    revocable: true,
    data: encodedData
  }, signer);

  // Pin to IPFS
  const ipfsCID = await pinToIPFS(attestation);

  console.log("Version link attestation created:", attestation.uid);
  return { attestation, ipfsCID };
}
```

#### Step 3: Update Database Version Registry

```typescript
// Add new version to database
async function registerSchemaVersionV2(newSchemaUID: string) {
  // Get v1 record
  const v1Record = await prisma.schema_versions.findFirst({
    where: {
      schema_name: 'GuitarModelAttestation',
      version: '1.0.0'
    }
  });

  // Create v2 record
  const v2Record = await prisma.schema_versions.create({
    data: {
      schema_name: 'GuitarModelAttestation',
      version: '2.0.0',
      schema_uid: newSchemaUID,
      previous_version_id: v1Record.id,
      next_version_id: null,
      changelog: 'Added finish_options and pickup_variations fields',
      effective_date: new Date(),
      status: 'active'
    }
  });

  // Update v1 to point to v2
  await prisma.schema_versions.update({
    where: { id: v1Record.id },
    data: {
      next_version_id: v2Record.id,
      status: 'deprecated' // Mark v1 as deprecated (optional)
    }
  });

  console.log('Database version registry updated');
}
```

#### Step 4: Create Decoder for New Version

```typescript
// src/lib/eas/schemas/decoders/model-v2.ts
import { SchemaDecoder } from '@ethereum-attestation-service/eas-sdk';

const SCHEMA_V2_DEFINITION = "string manufacturer_name,string product_line_name,string model_name,uint16 year,string db_reference_id,string production_type,string production_dates,uint32 estimated_quantity,string original_msrp,string currency,string description,string finish_options,string pickup_variations";

export function decodeModelV2(attestation: Attestation) {
  const decoder = new SchemaDecoder(SCHEMA_V2_DEFINITION);
  const decodedData = decoder.decodeData(attestation.data);

  return {
    manufacturer_name: decodedData[0].value.value as string,
    product_line_name: decodedData[1].value.value as string,
    model_name: decodedData[2].value.value as string,
    year: Number(decodedData[3].value.value),
    db_reference_id: decodedData[4].value.value as string,
    // ... other fields
    finish_options: decodedData[11].value.value as string, // NEW
    pickup_variations: decodedData[12].value.value as string // NEW
  };
}
```

#### Step 5: Update Application to Use New Schema

```typescript
// Update src/lib/eas/config.ts
export const EAS_CONFIG = {
  // ... other config
  schemas: {
    model: {
      uid: process.env.MODEL_SCHEMA_V2_UID!, // Point to new schema
      version: '2.0.0', // Update version
      definition: "string manufacturer_name,string product_line_name,string model_name,uint16 year,string db_reference_id,string production_type,string production_dates,uint32 estimated_quantity,string original_msrp,string currency,string description,string finish_options,string pickup_variations"
    }
  }
};

// Update decoder abstraction to handle both versions
export function decodeModelAttestation(attestation: Attestation) {
  const schemaVersion = getSchemaVersion(attestation.schema_uid);

  if (schemaVersion.startsWith('1.')) {
    return decodeModelV1(attestation);
  } else if (schemaVersion.startsWith('2.')) {
    return decodeModelV2(attestation);
  }

  throw new Error(`Unsupported schema version: ${schemaVersion}`);
}
```

#### Step 6: Test Backward Compatibility

```typescript
// tests/schema-compatibility.test.ts
describe('Schema Version Compatibility', () => {
  it('should decode v1 attestations correctly', async () => {
    const v1Attestation = await fetchAttestationByUID(V1_ATTESTATION_UID);
    const decoded = decodeModelAttestation(v1Attestation);

    expect(decoded.manufacturer_name).toBe('Fender');
    expect(decoded.finish_options).toBeUndefined(); // v1 doesn't have this
  });

  it('should decode v2 attestations correctly', async () => {
    const v2Attestation = await fetchAttestationByUID(V2_ATTESTATION_UID);
    const decoded = decodeModelAttestation(v2Attestation);

    expect(decoded.manufacturer_name).toBe('Fender');
    expect(decoded.finish_options).toBe('Sunburst, Black'); // v2 has this
  });

  it('should handle mixed versions in queries', async () => {
    const allAttestations = await prisma.attestations.findMany({
      where: { schema_type: 'model' }
    });

    const decoded = allAttestations.map(a => decodeModelAttestation(a));
    expect(decoded).toHaveLength(allAttestations.length);
  });
});
```

#### Step 7: Document the Change

**Update Documentation:**
- [ ] Add changelog entry to `CHANGELOG.md`
- [ ] Update API documentation with new fields
- [ ] Create migration guide for developers
- [ ] Update schema registry documentation

**Example Changelog Entry:**
```markdown
## [2.0.0] - 2025-06-01

### Added
- `finish_options` field to GuitarModelAttestation schema
- `pickup_variations` field to GuitarModelAttestation schema

### Changed
- Schema version bumped from 1.0.0 to 2.0.0

### Migration Guide
Existing attestations using v1.0.0 schema will continue to work. New attestations
will use v2.0.0 schema automatically. No re-attestation required.

To query attestations across versions:
```typescript
const allModels = await getAllModels(); // Handles both v1 and v2
```

### Breaking Changes
None - new fields are optional and additive.
```

### Complete Update Checklist

Before deploying a schema update:

- [ ] Determine correct version bump (major/minor/patch)
- [ ] Register new schema on blockchain
- [ ] Create version link attestation
- [ ] Update database version registry
- [ ] Create decoder for new version
- [ ] Update encoder for new version
- [ ] Update application code to use new schema
- [ ] Update decoder abstraction to handle all versions
- [ ] Write backward compatibility tests
- [ ] Test with real attestations (testnet first)
- [ ] Document changes in CHANGELOG
- [ ] Update API documentation
- [ ] Create migration guide
- [ ] Deploy to staging environment
- [ ] Verify both old and new attestations work
- [ ] Deploy to production
- [ ] Monitor for errors
- [ ] Announce change to stakeholders

---

## Development Best Practices

### Git Workflow
```bash
# Feature branch naming
git checkout -b feature/eas-model-attestations

# Commit message format
git commit -m "feat(attestations): Add model attestation creation API"
git commit -m "fix(eas): Handle IPFS pinning failures gracefully"
git commit -m "docs(prd): Update schema definitions"

# Pull request
gh pr create --title "EAS Model Attestations - Phase 1A" --body "..."
```

### Testing Strategy
```bash
# Run unit tests
npm test

# Run integration tests
npm run test:integration

# Run type checking
npx tsc --noEmit

# Run linting
npm run lint

# Test attestation creation manually
npm run test:attestation
```

### Monitoring
```typescript
// Add logging to all attestation operations
import { logger } from '@/lib/logger';

logger.info('Attestation created', {
  uid: attestation.uid,
  schema_type: 'model',
  entity_id: model.id,
  signer: wallet.address,
  duration_ms: Date.now() - startTime
});
```

---

## Success Metrics

### Week-by-Week Goals

**Week 1-2 (Phase 1A):**
- ✅ 5 test models with attestations created
- ✅ 100% IPFS pinning success rate
- ✅ Attestation UIDs displayed correctly on model pages

**Week 3 (Phase 1B):**
- ✅ 1 manufacturer wallet registered
- ✅ 3 attestations co-signed successfully
- ✅ Manufacturer dashboard functional

**Week 4 (Phase 1C):**
- ✅ UI polish complete
- ✅ Documentation published
- ✅ Demo ready for stakeholders

**Week 5-7 (Phase 2):**
- ✅ 10 instrument attestations created
- ✅ Provenance chain visualization working
- ✅ All instrument attestations correctly reference model attestations

**Week 8 (Phase 3):**
- ✅ Production deployment complete
- ✅ 3 manufacturers onboarded
- ✅ 20+ official (co-signed) model attestations

---

## Risk Mitigation

### Technical Risks

**IPFS Downtime:**
- Mitigation: Queue-based retry system, dual storage in PSQL
- Fallback: Show attestation from database even if IPFS unavailable

**EAS SDK Breaking Changes:**
- Mitigation: Pin exact version in package.json
- Monitor: Subscribe to EAS release notes

**Wallet Security:**
- Mitigation: Use hardware wallet for admin in production
- Never commit private keys to git

### Schedule Risks

**Falling Behind:**
- Mitigation: Focus on MVP features first, defer nice-to-haves
- Adjust scope: Phase 2 can be delayed if Phase 1 takes longer

**Manufacturer Adoption:**
- Mitigation: Partner with 1-2 friendly manufacturers early
- Provide white-glove onboarding support

---

## Questions & Support

### Who to Contact

- **Technical Questions:** [Engineering Lead]
- **Product Questions:** [Product Owner]
- **Schema/EAS Help:** [Blockchain Developer]
- **Database Issues:** [Database Admin]

### Resources

- PRD: `/PRD/eas-model-instrument-attestations.md`
- EAS Docs: https://docs.attest.org/
- Base Docs: https://docs.base.org/
- Project Slack: #eas-implementation

---

**Ready to Start?** Begin with Phase 1A - Setup & Configuration (above).

**Next Review:** End of Week 2 - Phase 1A Retrospective
