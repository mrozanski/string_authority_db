#!/usr/bin/env python3

"""
Startup script for the String Authority database search API.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def main():
    """Start the API server."""
    try:
        from api.app import create_app
        
        print("🎸 Starting String Authority Database Search API...")
        
        # Create the Flask app
        app = create_app()
        
        port = int(os.environ.get('PORT', 8000))
        print(f"📡 Server starting on http://localhost:{port}")
        print("🔍 Available endpoints:")
        print(f"   GET http://localhost:{port}/api/health")
        print(f"   GET http://localhost:{port}/api/search/models?model_name=<name>")
        print(f"   GET http://localhost:{port}/api/search/instruments?serial_number=<serial>")
        print(f"   GET http://localhost:{port}/api/search/instruments?unknown_serial=true&model_name=<name>")
        print("\n📖 See api/README.md for full documentation")
        print("🛑 Press Ctrl+C to stop the server\n")
        
        # Start the server
        app.run(
            debug=True,
            host='0.0.0.0',
            port=port,
            use_reloader=True
        )
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()