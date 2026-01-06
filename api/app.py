#!/usr/bin/env python3

# String Authority Database - Electric Guitar Provenance and Authentication System
# Copyright (C) 2025 Mariano Rozanski
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

"""
String Authority Database Search API
Flask REST API for searching guitar models and individual instruments.
"""

from flask import Flask, jsonify
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Add parent directory to path to import from main project
sys.path.append(str(Path(__file__).parent.parent))

from api.routes.search_routes import search_bp
from api.config import get_database_config

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Enable CORS for all routes
    CORS(app)
    
    # Configuration
    app.config['MAX_PAGE_SIZE'] = int(os.environ.get('MAX_PAGE_SIZE', 10))
    app.config['DEFAULT_PAGE_SIZE'] = int(os.environ.get('DEFAULT_PAGE_SIZE', 10))
    
    # Register blueprints
    app.register_blueprint(search_bp, url_prefix='/api')
    
    # Health check endpoint
    @app.route('/api/health')
    def health_check():
        """Health check endpoint."""
        try:
            # Test database connection
            db_config = get_database_config()
            return jsonify({
                'status': 'healthy',
                'database': 'connected' if db_config else 'error'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': str(e)
            }), 500
    
    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'error': 'Bad request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not found',
            'message': 'The requested resource was not found'
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred'
        }), 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)