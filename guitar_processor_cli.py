#!/usr/bin/env python3

# Guitar Registry - Electric Guitar Provenance and Authentication System
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

"""
Guitar Data Processor CLI
Command-line interface for processing guitar data submissions.

Usage:
    python guitar_processor_cli.py [options]
    python guitar_processor_cli.py --file data.json
    python guitar_processor_cli.py --file batch_data.json --verbose
    python guitar_processor_cli.py --interactive
"""

import argparse
import json
import sys
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import traceback

# Import the processor classes (assuming they're in the same directory)
from uniqueness_management_system import GuitarDataProcessor, GuitarDataValidator
from image_processing_module import process_guitar_with_photos

class DatabaseConfig:
    """Database connection configuration."""
    
    @staticmethod
    def from_env():
        """Load database config from environment variables."""
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'string_authority'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }
    
    @staticmethod
    def from_file(config_path: str):
        """Load database config from JSON file."""
        with open(config_path, 'r') as f:
            return json.load(f)

class GuitarProcessorCLI:
    """Command-line interface for the guitar data processor."""
    
    def __init__(self, db_config: dict, verbose: bool = False):
        self.db_config = db_config
        self.verbose = verbose
        self.db_connection = None
        self.processor = None
    
    def connect_database(self):
        """Establish database connection."""
        try:
            self.db_connection = psycopg2.connect(**self.db_config)
            self.processor = GuitarDataProcessor(self.db_connection)
            if self.verbose:
                print(f"✓ Connected to database: {self.db_config['database']}@{self.db_config['host']}")
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            sys.exit(1)
    
    def disconnect_database(self):
        """Close database connection."""
        if self.db_connection:
            self.db_connection.close()
            if self.verbose:
                print("✓ Database connection closed")
    
    def load_json_file(self, file_path: str):
        """Load and validate JSON file."""
        try:
            path = Path(file_path)
            if not path.exists():
                print(f"✗ File not found: {file_path}")
                return None
            
            if not path.suffix.lower() == '.json':
                print(f"✗ File must have .json extension: {file_path}")
                return None
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if self.verbose:
                print(f"✓ Loaded JSON file: {file_path}")
                if isinstance(data, list):
                    print(f"  → Batch submission with {len(data)} items")
                else:
                    print(f"  → Single submission")
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"✗ Invalid JSON in file {file_path}: {e}")
            return None
        except Exception as e:
            print(f"✗ Error reading file {file_path}: {e}")
            return None
    
    def print_result_summary(self, result: dict):
        """Print a formatted summary of processing results."""
        if isinstance(result, dict) and 'results' in result:
            # Batch result
            self._print_batch_summary(result)
        else:
            # Single result
            self._print_single_summary(result)
    
    def _print_single_summary(self, result: dict):
        """Print summary for single submission result."""
        success_icon = "✓" if result.get('success') else "✗"
        print(f"\n{success_icon} Single Submission Result:")
        
        if result.get('success'):
            print(f"  Actions: {', '.join(result.get('actions_taken', []))}")
            if result.get('ids_created'):
                print(f"  IDs Created: {len(result['ids_created'])} entities")
                if self.verbose:
                    for entity_type, entity_id in result['ids_created'].items():
                        print(f"    {entity_type}: {entity_id}")
        else:
            print(f"  ✗ Failed")
            if result.get('conflicts'):
                for conflict in result['conflicts']:
                    print(f"    • {conflict}")
        
        if result.get('manual_review_needed'):
            print(f"  ⚠ Manual review required")
    
    def _print_batch_summary(self, result: dict):
        """Print summary for batch submission result."""
        summary = result.get('summary', {})
        success_icon = "✓" if result.get('success') else "✗"
        
        print(f"\n{success_icon} Batch Processing Summary:")
        print(f"  Processed: {result.get('processed_count', 0)}/{result.get('total_count', 0)}")
        print(f"  Successful: {summary.get('successful', 0)}")
        print(f"  Failed: {summary.get('failed', 0)}")
        print(f"  Manual Review Needed: {summary.get('manual_review_needed', 0)}")
        
        if result.get('rolled_back'):
            print(f"  ⚠ Transaction rolled back: {result.get('rollback_reason', 'Unknown reason')}")
        elif result.get('partial_success'):
            print(f"  ⚠ Partial success: some items failed but others were committed")
        
        # Actions summary
        actions = summary.get('actions_taken', {})
        if any(actions.values()):
            print(f"  Actions Performed:")
            for action, count in actions.items():
                if count > 0:
                    action_name = action.replace('_', ' ').title()
                    print(f"    {action_name}: {count}")
        
        # Individual results (if verbose)
        if self.verbose and result.get('results'):
            print(f"\n  Individual Results:")
            for idx, item_result in enumerate(result['results']):
                success_icon = "✓" if item_result.get('success') else "✗"
                actions = ', '.join(item_result.get('actions_taken', []))
                print(f"    [{idx}] {success_icon} {actions}")
                
                if not item_result.get('success') and item_result.get('conflicts'):
                    for conflict in item_result['conflicts']:
                        print(f"         • {conflict}")
    
    def process_file(self, file_path: str):
        """Process a JSON file containing guitar data with support for relative image paths."""
        # Load data
        data = self.load_json_file(file_path)
        if data is None:
            return False
        
        # Load Cloudinary config for image processing
        cloudinary_config = None
        try:
            with open('cloudinary_config.json', 'r') as f:
                cloudinary_config = json.load(f)
            if self.verbose:
                print(f"✓ Loaded Cloudinary config")
        except Exception as e:
            if self.verbose:
                print(f"⚠ Could not load Cloudinary config: {e}")
        
        # Establish working directory context from input file location
        # The working directory should be the JSON file's parent directory
        # So paths in JSON are relative to the JSON file location
        working_dir = Path(file_path).parent
        
        # Process data
        print(f"\n🎸 Processing guitar data...")
        start_time = datetime.now()
        
        try:
            # Pass working directory for relative path resolution
            if isinstance(data, list):
                # Batch processing
                results = []
                for idx, item in enumerate(data):
                    if self.verbose:
                        print(f"  Processing item {idx + 1}/{len(data)}...")
                    
                    result = process_guitar_with_photos(
                        item, 
                        working_dir=working_dir,
                        db_connection=self.db_connection,
                        processor=self.processor,
                        cloudinary_config=cloudinary_config
                    )
                    results.append(result)
                
                # Create batch summary
                successful = sum(1 for r in results if r.get('success'))
                failed = len(results) - successful
                processed_images = sum(r.get('image_count', 0) for r in results)
                
                batch_result = {
                    'success': failed == 0,
                    'processed_count': len(results),
                    'total_count': len(data),
                    'summary': {
                        'successful': successful,
                        'failed': failed,
                        'images_processed': processed_images
                    },
                    'results': results
                }
                
                if self.verbose:
                    print(f"✓ Processed {processed_images} images across {len(results)} items")
                
                self.print_result_summary(batch_result)
                return batch_result['success']
                
            else:
                # Single item processing
                result = process_guitar_with_photos(
                    data, 
                    working_dir=working_dir,
                    db_connection=self.db_connection,
                    processor=self.processor,
                    cloudinary_config=cloudinary_config
                )
                
                if self.verbose:
                    print(f"✓ Processed {result.get('image_count', 0)} images")
                
                self.print_result_summary(result)
                return result.get('success', False)
                
        except Exception as e:
            print(f"✗ Processing failed: {e}")
            if self.verbose:
                traceback.print_exc()
            return False
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            if self.verbose:
                print(f"⏱ Processing completed in {duration:.2f} seconds")
    
    def interactive_mode(self):
        """Run in interactive mode for testing."""
        print("\n🎸 Guitar Data Processor - Interactive Mode")
        print("Enter JSON data (or 'quit' to exit):")
        print("You can paste single submissions or arrays of submissions.")
        
        while True:
            try:
                print("\n> ", end="")
                user_input = input().strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_input:
                    continue
                
                # Try to parse as JSON
                try:
                    data = json.loads(user_input)
                except json.JSONDecodeError:
                    print("✗ Invalid JSON. Please check your syntax.")
                    continue
                
                # Process the data
                print("Processing...")
                result = process_guitar_with_photos(
                    data,
                    working_dir=Path.cwd(),
                    db_connection=self.db_connection,
                    processor=self.processor
                )
                self.print_result_summary(result)
                
            except KeyboardInterrupt:
                print("\n\nExiting interactive mode...")
                break
            except Exception as e:
                print(f"✗ Error: {e}")
                if self.verbose:
                    print(f"Traceback:\n{traceback.format_exc()}")

def create_sample_files():
    """Create sample JSON files for testing."""
    
    # Single submission sample
    single_sample = {
        "manufacturer": {
            "name": "Gibson Guitar Corporation",
            "display_name": "Gibson",
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
            "nickname": "The Holy Grail",
            "serial_number": "9-0824",
            "significance_level": "historic",
            "significance_notes": "Famous 1959 Les Paul",
            "current_estimated_value": 500000.00
        }
    }
    
    # Batch submission sample
    batch_sample = [
        {
            "manufacturer": {
                "name": "Fender Musical Instruments Corporation",
                "display_name": "Fender",
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
            "model": {
                "manufacturer_name": "Fender Musical Instruments Corporation",
                "product_line_name": "Telecaster", 
                "name": "Telecaster",
                "year": 1950,
                "production_type": "mass",
                "msrp_original": 189.50,
                "currency": "USD"
            }
        },
        {
            "manufacturer": {
                "name": "Gretsch Company",
                "display_name": "Gretsch",
                "country": "USA",
                "founded_year": 1883,
                "status": "active"
            },
            "model": {
                "manufacturer_name": "Gretsch Company",
                "product_line_name": "6120",
                "name": "6120 Nashville",
                "year": 1954,
                "production_type": "mass",
                "msrp_original": 385.00,
                "currency": "USD"
            }
        }
    ]
    
    # Write sample files
    with open('sample_single.json', 'w') as f:
        json.dump(single_sample, f, indent=2)
    
    with open('sample_batch.json', 'w') as f:
        json.dump(batch_sample, f, indent=2)
    
    print("✓ Created sample files:")
    print("  • sample_single.json - Single guitar submission")
    print("  • sample_batch.json - Batch of 3 guitars")

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Guitar Data Processor CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python guitar_processor_cli.py --file data.json
  python guitar_processor_cli.py --file batch.json --verbose
  python guitar_processor_cli.py --interactive
  python guitar_processor_cli.py --create-samples
  python guitar_processor_cli.py --db-config db_config.json --file data.json
        """
    )
    
    parser.add_argument(
        '--file', '-f',
        help='Path to JSON file containing guitar data'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Run in interactive mode'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '--db-config',
        help='Path to database configuration JSON file'
    )
    
    parser.add_argument(
        '--create-samples',
        action='store_true',
        help='Create sample JSON files for testing'
    )
    
    args = parser.parse_args()
    
    # Handle sample creation
    if args.create_samples:
        create_sample_files()
        return
    
    # Validate arguments
    if not args.file and not args.interactive:
        parser.print_help()
        print("\nError: Must specify either --file or --interactive")
        sys.exit(1)
    
    # Load database configuration
    if args.db_config:
        db_config = DatabaseConfig.from_file(args.db_config)
    else:
        db_config = DatabaseConfig.from_env()
    
    # Initialize CLI processor
    cli = GuitarProcessorCLI(db_config, verbose=args.verbose)
    
    try:
        # Connect to database
        cli.connect_database()
        
        # Process based on mode
        if args.interactive:
            cli.interactive_mode()
        elif args.file:
            success = cli.process_file(args.file)
            sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        if args.verbose:
            print(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)
    finally:
        cli.disconnect_database()

if __name__ == "__main__":
    main()