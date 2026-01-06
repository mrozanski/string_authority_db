"""
Individual guitar/instrument search functionality for the String Authority Database Search API.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging

from ..database import get_db_manager
from .utils import (
    extract_years_from_text, 
    normalize_search_term, 
    normalize_serial_number,
    split_search_terms,
    build_multifield_search_clause,
    paginate_results,
    validate_pagination_params
)

logger = logging.getLogger(__name__)

class InstrumentSearchService:
    """Service for searching individual guitars/instruments."""
    
    def __init__(self):
        self.db = get_db_manager()
    
    def search_instruments(self, serial_number: Optional[str] = None, 
                          unknown_serial: Optional[bool] = None,
                          model_name: Optional[str] = None,
                          manufacturer_name: Optional[str] = None,
                          year_estimate: Optional[int] = None,
                          page: int = 1, page_size: int = 10,
                          max_page_size: int = 10) -> Dict[str, Any]:
        """
        Search for individual guitars/instruments.
        
        Args:
            serial_number: Serial number to search for
            unknown_serial: Boolean indicating unknown serial search
            model_name: Model name for unknown serial search
            manufacturer_name: Manufacturer name for unknown serial search
            year_estimate: Year estimate for unknown serial search
            page: Page number (1-based)
            page_size: Number of results per page
            max_page_size: Maximum allowed page size
            
        Returns:
            Dict with search results and pagination metadata
        """
        try:
            # Validate pagination parameters
            page, page_size = validate_pagination_params(page, page_size, max_page_size)
            
            # Validate search parameters
            if not self._validate_search_params(serial_number, unknown_serial, 
                                              model_name, manufacturer_name):
                raise ValueError("Either serial_number or unknown_serial must be provided")
            
            # Build the search query based on search type
            if serial_number:
                query, count_query, main_params, count_params = self._build_serial_search_query(
                    serial_number, page, page_size
                )
            else:
                query, count_query, main_params, count_params = self._build_model_based_search_query(
                    model_name, manufacturer_name, year_estimate, page, page_size
                )
            
            # Get total count
            total_records = self.db.execute_count_query(count_query, count_params)
            
            # Get results
            results = self.db.execute_query(query, main_params)
            
            # Format results
            formatted_results = [self._format_instrument_result(row) for row in results]
            
            # Return paginated response
            return paginate_results(formatted_results, page, page_size, total_records)
            
        except Exception as e:
            logger.error(f"Error searching instruments: {e}")
            raise
    
    def _validate_search_params(self, serial_number: Optional[str], 
                               unknown_serial: Optional[bool],
                               model_name: Optional[str], 
                               manufacturer_name: Optional[str]) -> bool:
        """Validate that required search parameters are provided."""
        if serial_number:
            return True
        if unknown_serial and (model_name or manufacturer_name):
            return True
        return False
    
    def _build_serial_search_query(self, serial_number: str, page: int, 
                                  page_size: int) -> Tuple[str, str, List[Any], List[Any]]:
        """
        Build SQL query for serial number-based search.
        
        Returns:
            Tuple of (main query, count query, main parameters, count parameters)
        """
        base_select = """
        SELECT
            ig.id,
            ig.serial_number,
            ig.year_estimate,
            ig.description,
            ig.significance_level,
            ig.significance_notes,
            ig.current_estimated_value,
            ig.condition_rating,
            COALESCE(m.name, ig.model_name_fallback) as model_name,
            COALESCE(mfr.name, ig.manufacturer_name_fallback) as manufacturer_name,
            pl.name as product_line_name
        FROM individual_guitars ig
        LEFT JOIN models m ON ig.model_id = m.id
        LEFT JOIN manufacturers mfr ON m.manufacturer_id = mfr.id
        LEFT JOIN product_lines pl ON m.product_line_id = pl.id
        """
        
        count_select = """
        SELECT COUNT(ig.id)
        FROM individual_guitars ig
        LEFT JOIN models m ON ig.model_id = m.id
        LEFT JOIN manufacturers mfr ON m.manufacturer_id = mfr.id
        LEFT JOIN product_lines pl ON m.product_line_id = pl.id
        """
        
        # Build WHERE clause for serial number search
        where_clauses = []
        where_params = []
        
        normalized_serial = normalize_serial_number(serial_number)
        
        # Use exact matching with normalization (remove dashes and leading zeros)
        where_clauses.append("""
        (LOWER(ig.serial_number) = LOWER(%s) 
         OR LOWER(REPLACE(ig.serial_number, '-', '')) = LOWER(%s)
         OR LOWER(TRIM(LEADING '0' FROM REPLACE(ig.serial_number, '-', ''))) = LOWER(%s))
        """)
        where_params.extend([serial_number, normalized_serial, normalized_serial])
        
        where_clause = "WHERE " + " AND ".join(where_clauses)
        
        # Build count query (no ORDER BY, no LIMIT/OFFSET)
        count_query = f"{count_select} {where_clause}"
        count_params = where_params.copy()
        
        # Order by relevance
        order_clause = """
        ORDER BY 
            CASE WHEN LOWER(ig.serial_number) = LOWER(%s) THEN 1 
                 WHEN LOWER(REPLACE(ig.serial_number, '-', '')) = LOWER(%s) THEN 2
                 ELSE 3 END,
            ig.current_estimated_value DESC NULLS LAST,
            ig.serial_number
        """
        
        # Build main query parameters (WHERE + ORDER BY + LIMIT/OFFSET)
        main_params = where_params.copy()
        main_params.extend([serial_number, normalized_serial])  # ORDER BY parameters
        
        # Add pagination parameters
        offset = (page - 1) * page_size
        main_params.extend([page_size, offset])
        
        # Build final main query
        main_query = f"{base_select} {where_clause} {order_clause} LIMIT %s OFFSET %s"
        
        return main_query, count_query, main_params, count_params
    
    def _build_model_based_search_query(self, model_name: Optional[str],
                                       manufacturer_name: Optional[str],
                                       year_estimate: Optional[int],
                                       page: int, page_size: int) -> Tuple[str, str, List[Any], List[Any]]:
        """
        Build SQL query for model-based search (unknown serial).
        
        Returns:
            Tuple of (main query, count query, main parameters, count parameters)
        """
        base_select = """
        SELECT
            ig.id,
            ig.serial_number,
            ig.year_estimate,
            ig.description,
            ig.significance_level,
            ig.significance_notes,
            ig.current_estimated_value,
            ig.condition_rating,
            COALESCE(m.name, ig.model_name_fallback) as model_name,
            COALESCE(mfr.name, ig.manufacturer_name_fallback) as manufacturer_name,
            pl.name as product_line_name,
            m.year as model_year
        FROM individual_guitars ig
        LEFT JOIN models m ON ig.model_id = m.id
        LEFT JOIN manufacturers mfr ON m.manufacturer_id = mfr.id
        LEFT JOIN product_lines pl ON m.product_line_id = pl.id
        """
        
        count_select = """
        SELECT COUNT(ig.id)
        FROM individual_guitars ig
        LEFT JOIN models m ON ig.model_id = m.id
        LEFT JOIN manufacturers mfr ON m.manufacturer_id = mfr.id
        LEFT JOIN product_lines pl ON m.product_line_id = pl.id
        """
        
        where_clauses = []
        where_params = []
        
        # Handle model name search
        if model_name:
            model_terms = split_search_terms(model_name)
            
            # Check for years in model name
            extracted_years = extract_years_from_text(model_name)
            if extracted_years and not year_estimate:
                year_estimate = extracted_years[0]
                # Remove year from search terms
                model_terms = [term for term in model_terms 
                             if not term.isdigit() or int(term) not in extracted_years]
            
            if model_terms:
                # Search in both model tables and fallback fields
                model_clause = """
                (similarity(LOWER(m.name), LOWER(%s)) > 0.3
                 OR similarity(LOWER(ig.model_name_fallback), LOWER(%s)) > 0.3
                 OR similarity(LOWER(pl.name), LOWER(%s)) > 0.3
                 OR LOWER(m.name) ILIKE LOWER(%s)
                 OR LOWER(ig.model_name_fallback) ILIKE LOWER(%s)
                 OR LOWER(pl.name) ILIKE LOWER(%s))
                """
                search_pattern = f"%{' '.join(model_terms)}%"
                where_params.extend([model_name, model_name, model_name, 
                                   search_pattern, search_pattern, search_pattern])
                where_clauses.append(model_clause)
        
        # Handle manufacturer name search
        if manufacturer_name:
            mfr_terms = split_search_terms(manufacturer_name)
            if mfr_terms:
                mfr_clause = """
                (similarity(LOWER(mfr.name), LOWER(%s)) > 0.25
                 OR similarity(LOWER(ig.manufacturer_name_fallback), LOWER(%s)) > 0.25
                 OR LOWER(mfr.name) ILIKE LOWER(%s)
                 OR LOWER(ig.manufacturer_name_fallback) ILIKE LOWER(%s))
                """
                search_pattern = f"%{' '.join(mfr_terms)}%"
                where_params.extend([manufacturer_name, manufacturer_name, 
                                   search_pattern, search_pattern])
                where_clauses.append(mfr_clause)
        
        # Handle year estimate
        if year_estimate:
            year_clause = """
            (m.year = %s 
             OR ig.year_estimate = %s 
             OR ig.year_estimate ILIKE %s)
            """
            where_params.extend([year_estimate, str(year_estimate), f"%{year_estimate}%"])
            where_clauses.append(year_clause)
        
        where_clause = ""
        if where_clauses:
            where_clause = "WHERE " + " AND ".join(where_clauses)
        
        # Build count query (no ORDER BY, no LIMIT/OFFSET)
        count_query = f"{count_select} {where_clause}"
        count_params = where_params.copy()
        
        # Order by relevance and value
        order_clause = """
        ORDER BY 
            CASE WHEN m.year = %s OR ig.year_estimate = %s THEN 1 ELSE 2 END,
            ig.current_estimated_value DESC NULLS LAST,
            ig.significance_level = 'historic' DESC,
            ig.serial_number
        """
        year_for_order = year_estimate if year_estimate else 0
        
        # Build main query parameters (WHERE + ORDER BY + LIMIT/OFFSET)
        main_params = where_params.copy()
        main_params.extend([year_for_order, str(year_for_order)])  # ORDER BY parameters
        
        # Add pagination parameters
        offset = (page - 1) * page_size
        main_params.extend([page_size, offset])
        
        # Build final main query
        main_query = f"{base_select} {where_clause} {order_clause} LIMIT %s OFFSET %s"
        
        return main_query, count_query, main_params, count_params
    
    def _format_instrument_result(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Format an instrument search result according to the API specification."""
        return {
            'id': str(row['id']),
            'serial_number': row['serial_number'],
            'year_estimate': row['year_estimate'],
            'description': row['description'],
            'significance_level': row['significance_level'],
            'significance_notes': row['significance_notes'],
            'current_estimated_value': str(row['current_estimated_value']) if row['current_estimated_value'] else None,
            'condition_rating': row['condition_rating'],
            'model_name': row['model_name'],
            'manufacturer_name': row['manufacturer_name'],
            'product_line_name': row['product_line_name']
        }