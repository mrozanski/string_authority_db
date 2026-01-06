#!/usr/bin/env python3

"""
Simple test script for the String Authority Database Search API endpoints.
"""

import sys
import os
from pathlib import Path

# Add API directory to path
sys.path.append(str(Path(__file__).parent))

def test_basic_import():
    """Test that all modules can be imported without errors."""
    try:
        print("Testing imports...")
        
        from api.app import create_app
        from api.config import get_database_config
        from api.database import get_db_manager
        from api.search.model_search import ModelSearchService
        from api.search.instrument_search import InstrumentSearchService
        from api.routes.search_routes import search_bp
        
        print("✓ All imports successful")
        return True
        
    except Exception as e:
        print(f"✗ Import error: {e}")
        return False

def test_app_creation():
    """Test Flask app creation."""
    try:
        print("Testing Flask app creation...")
        
        from api.app import create_app
        app = create_app()
        
        print("✓ Flask app created successfully")
        print(f"  - Registered blueprints: {list(app.blueprints.keys())}")
        print(f"  - Max page size config: {app.config.get('MAX_PAGE_SIZE')}")
        
        return True
        
    except Exception as e:
        print(f"✗ App creation error: {e}")
        return False

def test_database_config():
    """Test database configuration loading."""
    try:
        print("Testing database configuration...")
        
        from api.config import get_database_config
        config = get_database_config()
        
        if config:
            print("✓ Database configuration loaded")
            print(f"  - Host: {config.get('host')}")
            print(f"  - Database: {config.get('database')}")
            print(f"  - User: {config.get('user')}")
        else:
            print("✗ No database configuration found")
            return False
            
        return True
        
    except Exception as e:
        print(f"✗ Database config error: {e}")
        return False

def test_search_services():
    """Test search service initialization."""
    try:
        print("Testing search services...")
        
        from api.search.model_search import ModelSearchService
        from api.search.instrument_search import InstrumentSearchService
        
        model_service = ModelSearchService()
        instrument_service = InstrumentSearchService()
        
        print("✓ Search services initialized")
        return True
        
    except Exception as e:
        print(f"✗ Search services error: {e}")
        return False

def run_tests():
    """Run all tests."""
    print("=" * 50)
    print("String Authority Database Search API Test Suite")
    print("=" * 50)
    
    tests = [
        test_basic_import,
        test_app_creation,
        test_database_config,
        test_search_services
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test failed with exception: {e}")
            print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All tests passed! API is ready for use.")
        print("\nTo start the API server, run:")
        print("  python api/app.py")
        print("\nAPI endpoints will be available at:")
        print("  GET /api/search/models?model_name=<name>")
        print("  GET /api/search/instruments?serial_number=<serial>")
        print("  GET /api/health")
        return True
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)