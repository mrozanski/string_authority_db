"""
Search API routes for the String Authority Database.
"""

from flask import Blueprint, request, jsonify, current_app
from typing import Dict, Any, Optional
import logging

from ..search.model_search import ModelSearchService
from ..search.instrument_search import InstrumentSearchService

logger = logging.getLogger(__name__)

# Create blueprint
search_bp = Blueprint('search', __name__)

# Initialize services
model_search_service = ModelSearchService()
instrument_search_service = InstrumentSearchService()

@search_bp.route('/search/models', methods=['GET'])
def search_models():
    """
    Search for guitar models.
    
    Query Parameters:
        model_name (str, required): Model name to search for
        manufacturer_name (str, optional): Manufacturer name filter
        year (int, optional): Year filter
        page (int, optional): Page number (default: 1)
        page_size (int, optional): Results per page (default: 10, max: configurable)
    
    Returns:
        JSON response with search results and pagination metadata
    """
    try:
        # Get and validate required parameters
        model_name = request.args.get('model_name')
        if not model_name or not model_name.strip():
            return jsonify({
                'error': 'Bad Request',
                'message': 'model_name parameter is required'
            }), 400
        
        # Get optional parameters
        manufacturer_name = request.args.get('manufacturer_name')
        year_str = request.args.get('year')
        page_str = request.args.get('page', '1')
        page_size_str = request.args.get('page_size', str(current_app.config['DEFAULT_PAGE_SIZE']))
        
        # Parse and validate numeric parameters
        try:
            page = int(page_str) if page_str else 1
            page_size = int(page_size_str) if page_size_str else current_app.config['DEFAULT_PAGE_SIZE']
            year = int(year_str) if year_str else None
        except ValueError:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Invalid numeric parameter format'
            }), 400
        
        # Validate year range
        if year and (year < 1900 or year > 2030):
            return jsonify({
                'error': 'Bad Request',
                'message': 'Year must be between 1900 and 2030'
            }), 400
        
        # Validate page parameters
        if page < 1:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Page number must be >= 1'
            }), 400
        
        if page_size < 1 or page_size > current_app.config['MAX_PAGE_SIZE']:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Page size must be between 1 and {current_app.config["MAX_PAGE_SIZE"]}'
            }), 400
        
        # Perform search
        search_result = model_search_service.search_models(
            model_name=model_name.strip(),
            manufacturer_name=manufacturer_name.strip() if manufacturer_name else None,
            year=year,
            page=page,
            page_size=page_size,
            max_page_size=current_app.config['MAX_PAGE_SIZE']
        )
        
        # Format response according to specification
        response = {
            'models': search_result['data'],
            'total_records': search_result['pagination']['total_records'],
            'current_page': search_result['pagination']['current_page'],
            'page_size': search_result['pagination']['page_size'],
            'total_pages': search_result['pagination']['total_pages']
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in search_models: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An error occurred while searching models'
        }), 500

@search_bp.route('/search/instruments', methods=['GET'])
def search_instruments():
    """
    Search for individual guitars/instruments.
    
    Query Parameters:
        serial_number (str, optional): Serial number to search for
        unknown_serial (bool, optional): Flag for unknown serial search
        model_name (str, optional): Model name for unknown serial search
        manufacturer_name (str, optional): Manufacturer name for unknown serial search
        year_estimate (int, optional): Year estimate for unknown serial search
        page (int, optional): Page number (default: 1)
        page_size (int, optional): Results per page (default: 10, max: configurable)
    
    Note: Either serial_number or unknown_serial must be provided
    
    Returns:
        JSON response with search results and pagination metadata
    """
    try:
        # Get parameters
        serial_number = request.args.get('serial_number')
        unknown_serial_str = request.args.get('unknown_serial')
        model_name = request.args.get('model_name')
        manufacturer_name = request.args.get('manufacturer_name')
        year_estimate_str = request.args.get('year_estimate')
        page_str = request.args.get('page', '1')
        page_size_str = request.args.get('page_size', str(current_app.config['DEFAULT_PAGE_SIZE']))
        
        # Parse boolean parameter
        unknown_serial = None
        if unknown_serial_str:
            unknown_serial_lower = unknown_serial_str.lower()
            if unknown_serial_lower in ('true', '1', 'yes'):
                unknown_serial = True
            elif unknown_serial_lower in ('false', '0', 'no'):
                unknown_serial = False
            else:
                return jsonify({
                    'error': 'Bad Request',
                    'message': 'unknown_serial must be true or false'
                }), 400
        
        # Validate that either serial_number or unknown_serial is provided
        if not serial_number and not unknown_serial:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Either serial_number or unknown_serial must be provided'
            }), 400
        
        # Validate unknown_serial search parameters
        if unknown_serial and not (model_name or manufacturer_name):
            return jsonify({
                'error': 'Bad Request',
                'message': 'For unknown_serial search, model_name or manufacturer_name must be provided'
            }), 400
        
        # Parse numeric parameters
        try:
            page = int(page_str) if page_str else 1
            page_size = int(page_size_str) if page_size_str else current_app.config['DEFAULT_PAGE_SIZE']
            year_estimate = int(year_estimate_str) if year_estimate_str else None
        except ValueError:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Invalid numeric parameter format'
            }), 400
        
        # Validate year range
        if year_estimate and (year_estimate < 1900 or year_estimate > 2030):
            return jsonify({
                'error': 'Bad Request',
                'message': 'Year estimate must be between 1900 and 2030'
            }), 400
        
        # Validate page parameters
        if page < 1:
            return jsonify({
                'error': 'Bad Request',
                'message': 'Page number must be >= 1'
            }), 400
        
        if page_size < 1 or page_size > current_app.config['MAX_PAGE_SIZE']:
            return jsonify({
                'error': 'Bad Request',
                'message': f'Page size must be between 1 and {current_app.config["MAX_PAGE_SIZE"]}'
            }), 400
        
        # Perform search
        search_result = instrument_search_service.search_instruments(
            serial_number=serial_number.strip() if serial_number else None,
            unknown_serial=unknown_serial,
            model_name=model_name.strip() if model_name else None,
            manufacturer_name=manufacturer_name.strip() if manufacturer_name else None,
            year_estimate=year_estimate,
            page=page,
            page_size=page_size,
            max_page_size=current_app.config['MAX_PAGE_SIZE']
        )
        
        # Format response according to specification
        response = {
            'individual_guitars': search_result['data'],
            'total_records': search_result['pagination']['total_records'],
            'current_page': search_result['pagination']['current_page'],
            'page_size': search_result['pagination']['page_size'],
            'total_pages': search_result['pagination']['total_pages']
        }
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in search_instruments: {e}")
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An error occurred while searching instruments'
        }), 500

@search_bp.errorhandler(400)
def handle_bad_request(error):
    """Handle bad request errors."""
    return jsonify({
        'error': 'Bad Request',
        'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
    }), 400

@search_bp.errorhandler(500)
def handle_internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal Server Error',
        'message': 'An unexpected error occurred'
    }), 500