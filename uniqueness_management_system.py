# String Authority Database - Electric Guitar Provenance and Authentication System
# Copyright (C) 2025 Mariano Rozanski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# String Authority Database Uniqueness Management System
# JSON Schema + Python Pre-Insert Validation Approach

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import difflib
from datetime import datetime
import uuid
import psycopg2
from psycopg2.extras import RealDictCursor
import jsonschema
from difflib import SequenceMatcher
from guitar_registry_shared_models.validation import validate_individual_components
from pydantic import ValidationError
import importlib.metadata

class MatchLevel(Enum):
    EXACT = "exact"
    LIKELY = "likely" 
    POSSIBLE = "possible"
    NEW = "new"

class ConflictResolution(Enum):
    MERGE = "merge"
    REPLACE = "replace"
    KEEP_EXISTING = "keep_existing"
    MANUAL_REVIEW = "manual_review"

def get_created_by_info():
    """Get the created_by string for records added by the guitar processor."""
    try:
        version = importlib.metadata.version('gtr-reg')
        return f"guitar_processor_cli_v{version}"
    except Exception:
        # Fallback if version can't be determined
        return "guitar_processor_cli_v0.1.0"

@dataclass
class ValidationResult:
    is_valid: bool
    action: str  # "insert", "update", "merge", "conflict"
    target_id: Optional[str] = None
    conflicts: List[str] = None
    confidence: float = 0.0
    suggested_resolution: Optional[ConflictResolution] = None
    
    def __post_init__(self):
        if self.conflicts is None:
            self.conflicts = []

# JSON Schemas for data validation
MANUFACTURER_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1, "maxLength": 100},
        "display_name": {"type": ["string", "null"], "maxLength": 50},
        "country": {"type": ["string", "null"], "maxLength": 50},
        "founded_year": {"type": ["integer", "null"], "minimum": 1800, "maximum": 2030},
        "website": {"type": ["string", "null"], "format": "uri"},
        "status": {"type": "string", "enum": ["active", "defunct", "acquired"], "default": "active"},
        "notes": {"type": ["string", "null"]},
        "logo_source": {"type": ["string", "null"]}
    },
    "required": ["name"],
    "additionalProperties": False
}

SPECIFICATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "body_wood": {"type": ["string", "null"], "maxLength": 50},
        "neck_wood": {"type": ["string", "null"], "maxLength": 50},
        "fingerboard_wood": {"type": ["string", "null"], "maxLength": 50},
        "scale_length_inches": {"type": ["number", "null"], "minimum": 20, "maximum": 30},
        "num_frets": {"type": ["integer", "null"], "minimum": 12, "maximum": 36},
        "nut_width_inches": {"type": ["number", "null"], "minimum": 1.0, "maximum": 2.5},
        "neck_profile": {"type": ["string", "null"], "maxLength": 50},
        "bridge_type": {"type": ["string", "null"], "maxLength": 50},
        "pickup_configuration": {"type": ["string", "null"], "maxLength": 150},
        "electronics_description": {"type": ["string", "null"]},
        "hardware_finish": {"type": ["string", "null"], "maxLength": 50},
        "body_finish": {"type": ["string", "null"]}, # TEXT field allows longer finish descriptions with multiple colors/variations
        "weight_lbs": {"type": ["number", "null"], "minimum": 1, "maximum": 20},
        "case_included": {"type": ["boolean", "null"]},
        "case_type": {"type": ["string", "null"], "maxLength": 50}
    },
    "additionalProperties": False
}

MODEL_SCHEMA = {
    "type": "object", 
    "properties": {
        "manufacturer_name": {"type": "string"},  # Will be resolved to manufacturer_id
        "product_line_name": {"type": ["string", "null"]},  # Will be resolved to product_line_id
        "name": {"type": "string", "minLength": 1, "maxLength": 150},
        "year": {"type": "integer", "minimum": 1900, "maximum": 2030},
        "production_type": {"type": "string", "enum": ["mass", "limited", "custom", "prototype", "one-off"], "default": "mass"},
        "production_start_date": {"type": ["string", "null"], "format": "date"},
        "production_end_date": {"type": ["string", "null"], "format": "date"},
        "estimated_production_quantity": {"type": ["integer", "null"], "minimum": 1},
        "msrp_original": {"type": ["number", "null"], "minimum": 0},
        "currency": {"type": "string", "default": "USD", "maxLength": 3},
        "description": {"type": ["string", "null"]},
        "specifications": {
            "oneOf": [
                {"type": "null"},
                SPECIFICATIONS_SCHEMA,
                {
                    "type": "array",
                    "items": SPECIFICATIONS_SCHEMA,
                    "minItems": 1
                }
            ]
        }  # Single specification object OR array of specification objects
    },
    "required": ["manufacturer_name", "name", "year"],
    "additionalProperties": False
}

INDIVIDUAL_GUITAR_SCHEMA = {
    "type": "object",
    "properties": {
        # Foreign key reference (optional - for complete data)
        "model_reference": {  # Will be resolved to model_id
            "type": ["object", "null"],
            "properties": {
                "manufacturer_name": {"type": "string"},
                "model_name": {"type": "string"}, 
                "year": {"type": "integer"}
            },
            "required": ["manufacturer_name", "model_name", "year"],
            "additionalProperties": False
        },
        # Fallback text fields (for incomplete data)
        "manufacturer_name_fallback": {"type": ["string", "null"], "maxLength": 100},
        "model_name_fallback": {"type": ["string", "null"], "maxLength": 150},
        "year_estimate": {"type": ["string", "null"], "maxLength": 50},  # "circa 1959", "late 1950s", etc.
        "description": {"type": ["string", "null"]},  # General description when model info is incomplete
        
        # Guitar-specific fields
        "nickname": {"type": ["string", "null"], "maxLength": 50},
        "serial_number": {"type": ["string", "null"], "maxLength": 50},
        "production_date": {"type": ["string", "null"], "format": "date"},
        "production_number": {"type": ["integer", "null"]},
        "significance_level": {"type": "string", "enum": ["historic", "notable", "rare", "custom"], "default": "notable"},
        "significance_notes": {"type": ["string", "null"]},
        "current_estimated_value": {"type": ["number", "null"]},
        "last_valuation_date": {"type": ["string", "null"], "format": "date"},
        "condition_rating": {"type": ["string", "null"], "enum": ["mint", "excellent", "very_good", "good", "fair", "poor", "relic"]},
        "modifications": {"type": ["string", "null"]},
        "provenance_notes": {"type": ["string", "null"]},
        "specifications": {"type": ["object", "null"]},  # Individual-specific specs
        "photos": {"type": ["array", "null"]}  # Array of photo objects for image processing
    },
    # Require either model_reference OR fallback manufacturer + (model OR description)
    "anyOf": [
        {"required": ["model_reference"]},
        {"required": ["manufacturer_name_fallback", "model_name_fallback"]},
        {"required": ["manufacturer_name_fallback", "description"]}
    ],
    "additionalProperties": False
}





class GuitarDataValidator:
    def __init__(self, db_connection):
        self.db = db_connection
        self.cursor = db_connection.cursor(cursor_factory=RealDictCursor)
        
    def normalize_string(self, text: str) -> str:
        """Normalize strings for comparison - remove extra spaces, lowercase, etc."""
        if not text:
            return ""
        return " ".join(text.lower().strip().split())
    
    def calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using sequence matcher."""
        return SequenceMatcher(None, 
                             self.normalize_string(str1), 
                             self.normalize_string(str2)).ratio()
    
    def find_manufacturer_matches(self, manufacturer_data: Dict) -> List[Tuple[str, float, Dict]]:
        """Find potential manufacturer matches in database."""
        name = manufacturer_data.get('name', '')
        country = manufacturer_data.get('country')
        founded_year = manufacturer_data.get('founded_year')
        
        # Query existing manufacturers
        query = """
            SELECT id, name, country, founded_year, status
            FROM manufacturers 
            WHERE status != 'defunct' OR status IS NULL
        """
        self.cursor.execute(query)
        existing_manufacturers = self.cursor.fetchall()
        
        matches = []
        for existing in existing_manufacturers:
            # Name similarity
            name_similarity = self.calculate_similarity(name, existing['name'])
            
            # Additional checks
            country_match = (country == existing['country']) if country and existing['country'] else True
            year_match = (founded_year == existing['founded_year']) if founded_year and existing['founded_year'] else True
            
            # Calculate overall confidence
            confidence = name_similarity
            if country_match and country:
                confidence += 0.1
            if year_match and founded_year:
                confidence += 0.1
                
            if confidence >= 0.7:  # Threshold for potential match
                matches.append((existing['id'], confidence, dict(existing)))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def find_model_matches(self, model_data: Dict, manufacturer_id: str) -> List[Tuple[str, float, Dict]]:
        """Find potential model matches for a given manufacturer."""
        name = model_data.get('name', '')
        year = model_data.get('year')
        
        query = """
            SELECT m.id, m.name, m.year, m.production_type, 
                   pl.name as product_line_name,
                   mfr.name as manufacturer_name
            FROM models m
            JOIN manufacturers mfr ON m.manufacturer_id = mfr.id
            LEFT JOIN product_lines pl ON m.product_line_id = pl.id
            WHERE m.manufacturer_id = %s
        """
        self.cursor.execute(query, (manufacturer_id,))
        existing_models = self.cursor.fetchall()
        
        matches = []
        for existing in existing_models:
            # For guitar models, year is critical - skip if years don't match
            # This prevents "Firebird III 1976" from matching "Firebird I 1963"
            if year and existing['year'] and year != existing['year']:
                continue
            
            # Name similarity
            name_similarity = self.calculate_similarity(name, existing['name'])
            
            # Year match
            year_match = (year == existing['year']) if year else False
            
            # Calculate confidence
            confidence = name_similarity
            if year_match:
                confidence += 0.3  # Year is very important for models
                
            if confidence >= 0.8:  # Higher threshold for models
                matches.append((existing['id'], confidence, dict(existing)))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def find_individual_guitar_matches(self, guitar_data: Dict, model_id: Optional[str]) -> List[Tuple[str, float, Dict]]:
        """Find potential individual guitar matches using both FK and fallback approaches."""
        serial_number = guitar_data.get('serial_number', '')
        
        # Serial number is the primary unique identifier (works for both FK and fallback)
        if serial_number:
            query = """
                SELECT id, serial_number, model_id, manufacturer_name_fallback, 
                       model_name_fallback, year_estimate, significance_level
                FROM individual_guitars
                WHERE serial_number = %s
            """
            self.cursor.execute(query, (serial_number,))
            existing = self.cursor.fetchone()
            
            if existing:
                return [(existing['id'], 1.0, dict(existing))]
        
        # Different search strategies based on whether we have model_id or fallback data
        if model_id:
            # FK-based search: look for guitars with the same model_id
            query = """
                SELECT id, serial_number, production_date, significance_level,
                       manufacturer_name_fallback, model_name_fallback, year_estimate
                FROM individual_guitars
                WHERE model_id = %s
            """
            self.cursor.execute(query, (model_id,))
            existing_guitars = self.cursor.fetchall()
        else:
            # Fallback-based search: look for guitars with similar fallback text
            manufacturer_fallback = guitar_data.get('manufacturer_name_fallback', '')
            model_fallback = guitar_data.get('model_name_fallback', '')
            year_estimate = guitar_data.get('year_estimate', '')
            
            if not manufacturer_fallback:
                return []  # Can't match without at least manufacturer
            
            query = """
                SELECT id, serial_number, production_date, significance_level,
                       manufacturer_name_fallback, model_name_fallback, year_estimate
                FROM individual_guitars
                WHERE manufacturer_name_fallback IS NOT NULL
                AND LOWER(manufacturer_name_fallback) = LOWER(%s)
            """
            params = [manufacturer_fallback]
            
            if model_fallback:
                query += " AND LOWER(model_name_fallback) = LOWER(%s)"
                params.append(model_fallback)
            
            if year_estimate:
                query += " AND year_estimate = %s"
                params.append(year_estimate)
            
            self.cursor.execute(query, params)
            existing_guitars = self.cursor.fetchall()
        
        # Calculate similarity scores for potential matches
        matches = []
        production_date = guitar_data.get('production_date')
        
        for existing in existing_guitars:
            confidence = 0.0
            
            # Date similarity
            if production_date and existing['production_date']:
                if production_date == str(existing['production_date']):
                    confidence += 0.5
            
            # For fallback matches, add text similarity scoring
            if not model_id and existing.get('manufacturer_name_fallback'):
                confidence += 0.3  # Base score for manufacturer match
                
                if (guitar_data.get('model_name_fallback') and 
                    existing.get('model_name_fallback') and
                    guitar_data.get('model_name_fallback').lower() == existing.get('model_name_fallback').lower()):
                    confidence += 0.4  # Model name match
                
                if (guitar_data.get('year_estimate') and 
                    existing.get('year_estimate') and
                    guitar_data.get('year_estimate') == existing.get('year_estimate')):
                    confidence += 0.3  # Year estimate match
                    
            if confidence >= 0.5:
                matches.append((existing['id'], confidence, dict(existing)))
        
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def validate_manufacturer(self, data: Dict) -> ValidationResult:
        """Validate and check uniqueness for manufacturer data."""
        try:
            # validate_individual_components expects the full data structure with 'manufacturer' key
            full_data = {'manufacturer': data}
            validated_components = validate_individual_components(full_data)
            manufacturer = validated_components['manufacturer']
            print(f"✅ Validated: {manufacturer.name}")
            print(f"   Status: {manufacturer.status}")  # Defaults to "active"
    
        except ValidationError as e:
            print(f"❌ Validation failed: {e}")
            return ValidationResult(False, "invalid_schema", conflicts=[str(e)])
        # Find matches
        matches = self.find_manufacturer_matches(data)
        
        if not matches:
            return ValidationResult(True, "insert", confidence=1.0)
        
        best_match = matches[0]
        confidence = best_match[1]
        
        if confidence >= 0.95:
            # Very likely the same manufacturer
            return ValidationResult(
                True, "update", 
                target_id=best_match[0], 
                confidence=confidence,
                suggested_resolution=ConflictResolution.MERGE
            )
        elif confidence >= 0.85:
            # Likely match, but should review
            return ValidationResult(
                True, "conflict",
                target_id=best_match[0],
                confidence=confidence,
                conflicts=[f"Similar manufacturer found: {best_match[2]['name']}"],
                suggested_resolution=ConflictResolution.MANUAL_REVIEW
            )
        else:
            return ValidationResult(True, "insert", confidence=1.0)
    
    def validate_model(self, data: Dict) -> ValidationResult:
        """Validate and check uniqueness for model data."""
        # Schema validation
        try:
            jsonschema.validate(data, MODEL_SCHEMA)
        except jsonschema.ValidationError as e:
            return ValidationResult(False, "invalid_schema", conflicts=[str(e)])
        
        # Resolve manufacturer
        manufacturer_name = data.get('manufacturer_name')
        self.cursor.execute(
            "SELECT id FROM manufacturers WHERE LOWER(name) = LOWER(%s)",
            (manufacturer_name,)
        )
        manufacturer = self.cursor.fetchone()
        
        if not manufacturer:
            return ValidationResult(
                False, "missing_dependency",
                conflicts=[f"Manufacturer '{manufacturer_name}' not found"]
            )
        
        manufacturer_id = manufacturer['id']
        
        # Find model matches
        matches = self.find_model_matches(data, manufacturer_id)
        
        if not matches:
            return ValidationResult(True, "insert", confidence=1.0)
        
        best_match = matches[0]
        confidence = best_match[1]
        
        if confidence >= 0.95:
            return ValidationResult(
                True, "update",
                target_id=best_match[0],
                confidence=confidence,
                suggested_resolution=ConflictResolution.MERGE
            )
        elif confidence >= 0.85:
            return ValidationResult(
                True, "conflict",
                target_id=best_match[0],
                confidence=confidence,
                conflicts=[f"Similar model found: {best_match[2]['name']} ({best_match[2]['year']})"],
                suggested_resolution=ConflictResolution.MANUAL_REVIEW
            )
        else:
            return ValidationResult(True, "insert", confidence=1.0)

    
    def validate_individual_guitar(self, data: Dict) -> ValidationResult:
        """Validate and check uniqueness for individual guitar data."""
        # Schema validation
        try:
            jsonschema.validate(data, INDIVIDUAL_GUITAR_SCHEMA)
        except jsonschema.ValidationError as e:
            return ValidationResult(False, "invalid_schema", conflicts=[str(e)])
        
        # Try to resolve model_id (hybrid approach)
        model_id = self._resolve_model_reference(data)
        
        # Find guitar matches (works with both FK and fallback data)
        matches = self.find_individual_guitar_matches(data, model_id)
        
        if not matches:
            return ValidationResult(True, "insert", confidence=1.0)
        
        best_match = matches[0]
        confidence = best_match[1]
        
        if confidence == 1.0:  # Exact serial number match
            return ValidationResult(
                True, "update",
                target_id=best_match[0],
                confidence=confidence,
                suggested_resolution=ConflictResolution.MERGE
            )
        else:
            return ValidationResult(True, "insert", confidence=1.0)
    
    def _resolve_model_reference(self, data: Dict) -> Optional[str]:
        """
        Try to resolve model_reference to model_id, return None if using fallback approach.
        """
        model_ref = data.get('model_reference')
        if not model_ref:
            return None  # Using fallback fields
        
        manufacturer_name = model_ref.get('manufacturer_name')
        model_name = model_ref.get('model_name')
        year = model_ref.get('year')
        
        query = """
            SELECT m.id 
            FROM models m 
            JOIN manufacturers mfr ON m.manufacturer_id = mfr.id
            WHERE LOWER(mfr.name) = LOWER(%s) 
            AND LOWER(m.name) = LOWER(%s) 
            AND m.year = %s
        """
        self.cursor.execute(query, (manufacturer_name, model_name, year))
        model = self.cursor.fetchone()
        
        return model['id'] if model else None

class GuitarDataProcessor:
    """Main class for processing guitar data submissions."""
    
    def __init__(self, db_connection):
        self.validator = GuitarDataValidator(db_connection)
        self.db = db_connection
        self.cursor = db_connection.cursor(cursor_factory=RealDictCursor)
    
    def process_submission(self, submission_data) -> Dict:
        """
        Process guitar data submissions. Accepts either a single dict or list of dicts.
        
        Single submission format:
        {
            "manufacturer": {...},
            "model": {...},
            "individual_guitar": {...} (optional)
        }
        
        Batch submission format:
        [
            {"manufacturer": {...}, "model": {...}, ...},
            {"manufacturer": {...}, "model": {...}, ...},
            ...
        ]
        """
        # Handle both single dict and list of dicts
        if isinstance(submission_data, dict):
            submissions = [submission_data]
            is_batch = False
        elif isinstance(submission_data, list):
            submissions = submission_data
            is_batch = True
        else:
            return {
                "success": False,
                "error": "Invalid submission format. Expected dict or list of dicts.",
                "processed_count": 0,
                "results": []
            }
        
        # Initialize batch results
        batch_results = {
            "success": True,
            "processed_count": 0,
            "total_count": len(submissions),
            "results": [],
            "summary": {
                "successful": 0,
                "failed": 0,
                "manual_review_needed": 0,
                "actions_taken": {
                    "manufacturers_inserted": 0,
                    "manufacturers_updated": 0,
                    "models_inserted": 0,
                    "models_updated": 0,
                    "guitars_inserted": 0,
                    "guitars_updated": 0
                }
            }
        }
        
        try:
            # Start transaction for the entire batch (manual transaction management)
            # Note: We don't use 'with self.db:' context manager because we need
            # conditional rollback based on failure rate, which conflicts with
            # the context manager's automatic commit-on-exit behavior.
            for idx, single_submission in enumerate(submissions):
                try:
                    result = self._process_single_submission(single_submission, idx)
                    batch_results["results"].append(result)
                    batch_results["processed_count"] += 1
                    
                    # Update summary statistics
                    if result["success"]:
                        batch_results["summary"]["successful"] += 1
                        # Aggregate action counts
                        for action in result.get("actions_taken", []):
                            if "Manufacturer insert" in action:
                                batch_results["summary"]["actions_taken"]["manufacturers_inserted"] += 1
                            elif "Manufacturer update" in action:
                                batch_results["summary"]["actions_taken"]["manufacturers_updated"] += 1
                            elif "Model insert" in action:
                                batch_results["summary"]["actions_taken"]["models_inserted"] += 1
                            elif "Model update" in action:
                                batch_results["summary"]["actions_taken"]["models_updated"] += 1
                            elif "Guitar insert" in action:
                                batch_results["summary"]["actions_taken"]["guitars_inserted"] += 1
                            elif "Guitar update" in action:
                                batch_results["summary"]["actions_taken"]["guitars_updated"] += 1
                    else:
                        batch_results["summary"]["failed"] += 1
                        batch_results["success"] = False  # Mark entire batch as having failures
                    
                    if result.get("manual_review_needed"):
                        batch_results["summary"]["manual_review_needed"] += 1
                        
                except Exception as e:
                    error_result = {
                        "index": idx,
                        "success": False,
                        "error": f"Processing error: {str(e)}",
                        "submission_preview": str(single_submission)[:100] + "..." if len(str(single_submission)) > 100 else str(single_submission)
                    }
                    batch_results["results"].append(error_result)
                    batch_results["summary"]["failed"] += 1
                    batch_results["success"] = False
            
            # Transaction decision logic: commit or rollback based on results
            if not batch_results["success"] and is_batch:
                failed_count = batch_results["summary"]["failed"]
                total_count = batch_results["total_count"]
                failure_rate = failed_count / total_count
                
                # If more than 50% failed, rollback the entire batch
                if failure_rate > 0.5:
                    self.db.rollback()
                    batch_results["rolled_back"] = True
                    batch_results["rollback_reason"] = f"High failure rate: {failed_count}/{total_count} submissions failed"
                else:
                    # Partial success - commit what worked
                    self.db.commit()
                    batch_results["partial_success"] = True
            else:
                # All successful or single submission
                self.db.commit()
        
        except Exception as e:
            # Rollback on any unexpected exception during batch processing
            self.db.rollback()
            batch_results["success"] = False
            batch_results["error"] = f"Batch processing error: {str(e)}"
            batch_results["rolled_back"] = True
        
        # Return single result format for single submissions (backward compatibility)
        if not is_batch and len(batch_results["results"]) == 1:
            return batch_results["results"][0]
        
        return batch_results
    
    def _process_single_submission(self, submission_data: Dict, index: int = 0) -> Dict:
        """Process a single guitar data submission."""
        results = {
            "index": index,
            "success": False,
            "actions_taken": [],
            "conflicts": [],
            "ids_created": {},
            "manual_review_needed": False
        }
        
        try:
            # Process manufacturer first
            if 'manufacturer' in submission_data:
                mfr_result = self.validator.validate_manufacturer(submission_data['manufacturer'])
                if not mfr_result.is_valid:
                    results['conflicts'].extend(mfr_result.conflicts or [])
                    return results
                
                if mfr_result.suggested_resolution == ConflictResolution.MANUAL_REVIEW:
                    results['manual_review_needed'] = True
                    results['conflicts'].append(f"Manufacturer conflict: {mfr_result.conflicts}")
                    return results
                
                # Execute manufacturer action
                if mfr_result.action == "insert":
                    mfr_id = self._insert_manufacturer(submission_data['manufacturer'])
                    results['ids_created']['manufacturer'] = mfr_id
                elif mfr_result.action == "update":
                    mfr_id = mfr_result.target_id
                    if mfr_id is not None:
                        self._update_manufacturer(mfr_id, submission_data['manufacturer'])
                
                results['actions_taken'].append(f"Manufacturer {mfr_result.action}")
            
            # Process model
            if 'model' in submission_data:
                model_result = self.validator.validate_model(submission_data['model'])
                if not model_result.is_valid:
                    results['conflicts'].extend(model_result.conflicts or [])
                    return results
                
                if model_result.suggested_resolution == ConflictResolution.MANUAL_REVIEW:
                    results['manual_review_needed'] = True
                    results['conflicts'].append(f"Model conflict: {model_result.conflicts}")
                    return results
                
                # Execute model action
                if model_result.action == "insert":
                    model_id = self._insert_model(submission_data['model'])
                    results['ids_created']['model'] = model_id
                    
                    # Process model specifications if present
                    if submission_data['model'].get('specifications'):
                        spec_ids = self._insert_specifications(submission_data['model']['specifications'], 'model', model_id)
                        results['ids_created']['model_specifications'] = spec_ids
                    

                        
                elif model_result.action == "update":
                    model_id = model_result.target_id
                    if model_id is not None:
                        self._update_model(model_id, submission_data['model'])
                
                results['actions_taken'].append(f"Model {model_result.action}")
                
            # Process individual guitar if present
            if 'individual_guitar' in submission_data:
                guitar_result = self.validator.validate_individual_guitar(submission_data['individual_guitar'])
                if not guitar_result.is_valid:
                    results['conflicts'].extend(guitar_result.conflicts or [])
                    return results
                
                if guitar_result.suggested_resolution == ConflictResolution.MANUAL_REVIEW:
                    results['manual_review_needed'] = True
                    results['conflicts'].append(f"Guitar conflict: {guitar_result.conflicts}")
                    return results
                
                # Execute guitar action
                if guitar_result.action == "insert":
                    guitar_id = self._insert_individual_guitar(submission_data['individual_guitar'])
                    results['ids_created']['individual_guitar'] = guitar_id
                    
                    # Process individual guitar specifications if present
                    if submission_data['individual_guitar'].get('specifications'):
                        spec_id = self._insert_specifications(submission_data['individual_guitar']['specifications'], 'individual_guitar', guitar_id)
                        results['ids_created']['guitar_specifications'] = spec_id
                    
                elif guitar_result.action == "update":
                    guitar_id = guitar_result.target_id
                    if guitar_id is not None:
                        self._update_individual_guitar(guitar_id, submission_data['individual_guitar'])
                
                results['actions_taken'].append(f"Guitar {guitar_result.action}")
            

            
            results['success'] = True
            return results
            
        except Exception as e:
            results['conflicts'].append(f"Processing error: {str(e)}")
            return results
    
    def _insert_model(self, data: Dict) -> str:
        """Insert new model and return ID."""
        # Resolve manufacturer_id from manufacturer_name
        self.cursor.execute(
            "SELECT id FROM manufacturers WHERE LOWER(name) = LOWER(%s)",
            (data.get('manufacturer_name'),)
        )
        manufacturer = self.cursor.fetchone()
        manufacturer_id = manufacturer['id']
        
        # Resolve or create product_line_id if specified
        product_line_id = None
        if data.get('product_line_name'):
            self.cursor.execute(
                "SELECT id FROM product_lines WHERE manufacturer_id = %s AND LOWER(name) = LOWER(%s)",
                (manufacturer_id, data.get('product_line_name'))
            )
            product_line = self.cursor.fetchone()
            if not product_line:
                # Create new product line
                self.cursor.execute(
                    "INSERT INTO product_lines (manufacturer_id, name) VALUES (%s, %s) RETURNING id",
                    (manufacturer_id, data.get('product_line_name'))
                )
                product_line_id = self.cursor.fetchone()['id']
            else:
                product_line_id = product_line['id']
        
        query = """
            INSERT INTO models (manufacturer_id, product_line_id, name, year, production_type, 
                              production_start_date, production_end_date, estimated_production_quantity,
                              msrp_original, currency, description, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        values = (
            manufacturer_id, product_line_id, data.get('name'), data.get('year'),
            data.get('production_type', 'mass'), data.get('production_start_date'),
            data.get('production_end_date'), data.get('estimated_production_quantity'),
            data.get('msrp_original'), data.get('currency', 'USD'), data.get('description'),
            get_created_by_info()
        )
        self.cursor.execute(query, values)
        return self.cursor.fetchone()['id']
    
    def _insert_individual_guitar(self, data: Dict) -> str:
        """Insert new individual guitar and return ID."""
        # Try to resolve model_id using hybrid approach
        model_id = self.validator._resolve_model_reference(data)
        
        query = """
            INSERT INTO individual_guitars (
                model_id, manufacturer_name_fallback, model_name_fallback, year_estimate, description,
                nickname, serial_number, production_date, production_number, significance_level, significance_notes, 
                current_estimated_value, condition_rating, modifications, provenance_notes, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        values = (
            model_id, 
            data.get('manufacturer_name_fallback'), 
            data.get('model_name_fallback'),
            data.get('year_estimate'), 
            data.get('description'),
            data.get('nickname'),
            data.get('serial_number'), 
            data.get('production_date'),
            data.get('production_number'), 
            data.get('significance_level'),
            data.get('significance_notes'), 
            data.get('current_estimated_value'),
            data.get('condition_rating'), 
            data.get('modifications'), 
            data.get('provenance_notes'),
            get_created_by_info()
        )
        self.cursor.execute(query, values)
        return self.cursor.fetchone()['id']
    
    def _insert_manufacturer(self, data: Dict) -> str:
        """Insert new manufacturer and return ID."""
        query = """
            INSERT INTO manufacturers (name, display_name, country, founded_year, website, status, notes, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        values = (
            data.get('name'), data.get('display_name'), data.get('country'), data.get('founded_year'),
            data.get('website'), data.get('status', 'active'), data.get('notes'), 
            get_created_by_info()
        )
        self.cursor.execute(query, values)
        return self.cursor.fetchone()['id']
    
    def _update_manufacturer(self, manufacturer_id: str, data: Dict):
        """Update existing manufacturer with new data."""
        # Implement merge logic - update non-null fields
        update_fields = []
        values = []
        
        for field in ['display_name', 'country', 'founded_year', 'website', 'status', 'notes']:
            if data.get(field) is not None:
                update_fields.append(f"{field} = %s")
                values.append(data[field])
        
        if update_fields:
            values.append(manufacturer_id)
            query = f"""
                UPDATE manufacturers 
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.cursor.execute(query, values)
    
    def _insert_specifications(self, data, target_type: str, target_id: str):
        """Insert specifications for either a model or individual guitar.
        
        Args:
            data: Either a single Dict or List[Dict] (both supported for models and individual guitars)
            target_type: 'model' or 'individual_guitar'
            target_id: The ID of the target entity
        """
        if target_type == 'model':
            model_id = target_id
            individual_guitar_id = None
        else:
            model_id = None
            individual_guitar_id = target_id
        
        # Handle both single specification object and array
        if isinstance(data, list):
            # Multiple specifications (array format)
            spec_ids = []
            for spec_data in data:
                spec_id = self._insert_single_specification(spec_data, model_id, individual_guitar_id)
                spec_ids.append(spec_id)
            return spec_ids
        else:
            # Single specification object
            return self._insert_single_specification(data, model_id, individual_guitar_id)
    
    def _insert_single_specification(self, spec_data: Dict, model_id: str, individual_guitar_id: str) -> str:
        """Insert a single specification record."""
        query = """
            INSERT INTO specifications (model_id, individual_guitar_id, body_wood, neck_wood, fingerboard_wood,
                                     scale_length_inches, num_frets, nut_width_inches, neck_profile, bridge_type,
                                     pickup_configuration, electronics_description,
                                     hardware_finish, body_finish, weight_lbs, case_included, case_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        values = (
            model_id, individual_guitar_id, spec_data.get('body_wood'), spec_data.get('neck_wood'),
            spec_data.get('fingerboard_wood'), spec_data.get('scale_length_inches'), spec_data.get('num_frets'),
            spec_data.get('nut_width_inches'), spec_data.get('neck_profile'), spec_data.get('bridge_type'),
            spec_data.get('pickup_configuration'),
            spec_data.get('electronics_description'), spec_data.get('hardware_finish'), spec_data.get('body_finish'),
            spec_data.get('weight_lbs'), spec_data.get('case_included'), spec_data.get('case_type')
        )
        self.cursor.execute(query, values)
        return self.cursor.fetchone()['id']
    

    
    def _update_model(self, model_id: str, data: Dict):
        """Update existing model with new data."""
        # Similar merge logic for models
        update_fields = []
        values = []
        
        for field in ['production_start_date', 'production_end_date', 'estimated_production_quantity', 
                     'msrp_original', 'currency', 'description']:
            if data.get(field) is not None:
                update_fields.append(f"{field} = %s")
                values.append(data[field])
        
        if update_fields:
            values.append(model_id)
            query = f"""
                UPDATE models 
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.cursor.execute(query, values)
    
    def _update_individual_guitar(self, guitar_id: str, data: Dict):
        """Update existing individual guitar with new data."""
        # Merge logic for individual guitars - include new fallback fields
        update_fields = []
        values = []
        
        # Handle model_id update if we can resolve it
        model_id = self.validator._resolve_model_reference(data)
        if model_id is not None:
            update_fields.append("model_id = %s")
            values.append(model_id)
        
        # Update fallback fields if provided
        for field in ['manufacturer_name_fallback', 'model_name_fallback', 'year_estimate', 'description']:
            if data.get(field) is not None:
                update_fields.append(f"{field} = %s")
                values.append(data[field])
        
        # Update other guitar fields
        for field in ['nickname', 'production_date', 'production_number', 'significance_notes', 
                     'current_estimated_value', 'condition_rating', 'modifications', 'provenance_notes']:
            if data.get(field) is not None:
                update_fields.append(f"{field} = %s")
                values.append(data[field])
        
        if update_fields:
            values.append(guitar_id)
            query = f"""
                UPDATE individual_guitars 
                SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.cursor.execute(query, values)


# Example usage
def example_usage():
    """Example of how to use the system with both single and batch submissions."""
    
    # Single submission example
    single_submission = {
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
            "msrp_original": 247.50,
            "currency": "USD"
        },
        "individual_guitar": {
            "model_reference": {
                "manufacturer_name": "Gibson Guitar Corporation",
                "model_name": "Les Paul Standard", 
                "year": 1959
            },
            "serial_number": "9-0824",
            "significance_level": "historic",
            "significance_notes": "Owned by Jimmy Page",
            "current_estimated_value": 500000.00
        }
    }
    
    # Batch submission example
    batch_submissions = [
        {
            "manufacturer": {
                "name": "Fender Musical Instruments Corporation",
                "country": "USA",
                "founded_year": 1946,
                "status": "active"
            },
            "model": {
                "manufacturer_name": "Fender Musical Instruments Corporation",
                "product_line_name": "Stratocaster",
                "name": "Stratocaster",
                "year": 1954,
                "production_type": "mass",
                "msrp_original": 249.50,
                "currency": "USD"
            }
        },
        {
            "manufacturer": {
                "name": "Gibson Guitar Corporation",  # Duplicate - should be detected
                "country": "USA",
                "founded_year": 1902,
                "status": "active"
            },
            "model": {
                "manufacturer_name": "Gibson Guitar Corporation",
                "product_line_name": "SG",
                "name": "SG Standard",
                "year": 1961,
                "production_type": "mass",
                "msrp_original": 225.00,
                "currency": "USD"
            }
        },
        {
            "model": {  # Model-only submission
                "manufacturer_name": "Fender Musical Instruments Corporation",
                "product_line_name": "Telecaster",
                "name": "Telecaster",
                "year": 1950,
                "production_type": "mass",
                "msrp_original": 189.50,
                "currency": "USD"
            }
        }
    ]
    
    # Usage examples:
    # processor = GuitarDataProcessor(db_connection)
    
    # Process single submission
    # single_result = processor.process_submission(single_submission)
    # print("Single submission result:")
    # print(json.dumps(single_result, indent=2))
    
    # Process batch submission
    # batch_result = processor.process_submission(batch_submissions)
    # print("\nBatch submission result:")
    # print(json.dumps(batch_result, indent=2))
    
    # Example outputs:
    print("Expected single result format:")
    print(json.dumps({
        "index": 0,
        "success": True,
        "actions_taken": ["Manufacturer insert", "Model insert", "Guitar insert"],
        "conflicts": [],
        "ids_created": {
            "manufacturer": "uuid-here",
            "model": "uuid-here", 
            "individual_guitar": "uuid-here"
        },
        "manual_review_needed": False
    }, indent=2))
    
    print("\nExpected batch result format:")
    print(json.dumps({
        "success": True,
        "processed_count": 3,
        "total_count": 3,
        "results": [
            {"index": 0, "success": True, "actions_taken": ["Manufacturer insert", "Model insert"]},
            {"index": 1, "success": True, "actions_taken": ["Manufacturer update", "Model insert"]},
            {"index": 2, "success": True, "actions_taken": ["Model insert"]}
        ],
        "summary": {
            "successful": 3,
            "failed": 0,
            "manual_review_needed": 0,
            "actions_taken": {
                "manufacturers_inserted": 1,
                "manufacturers_updated": 1,
                "models_inserted": 3,
                "models_updated": 0,
                "guitars_inserted": 0,
                "guitars_updated": 0
            }
        }
    }, indent=2))

if __name__ == "__main__":
    example_usage()