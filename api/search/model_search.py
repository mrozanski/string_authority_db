"""
Model search functionality for the String Authority Database Search API.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging

from ..database import get_db_manager
from .utils import (
    extract_years_from_text, 
    normalize_search_term, 
    split_search_terms,
    build_multifield_search_clause,
    paginate_results,
    validate_pagination_params
)

logger = logging.getLogger(__name__)

class ModelSearchService:
    """Service for searching guitar models with fuzzy matching."""
    
    def __init__(self):
        self.db = get_db_manager()
    
    def search_models(self, model_name: str, manufacturer_name: Optional[str] = None,
                     year: Optional[int] = None, page: int = 1, page_size: int = 10,
                     max_page_size: int = 10) -> Dict[str, Any]:
        """
        Search for guitar models with fuzzy matching.
        
        Args:
            model_name: Model name to search for (required)
            manufacturer_name: Optional manufacturer name filter
            year: Optional year filter
            page: Page number (1-based)
            page_size: Number of results per page
            max_page_size: Maximum allowed page size
            
        Returns:
            Dict with search results and pagination metadata
        """
        try:
            # Validate pagination parameters
            page, page_size = validate_pagination_params(page, page_size, max_page_size)
            
            # Build the search query
            query, count_query, main_params, count_params = self._build_search_query(
                model_name, manufacturer_name, year, page, page_size
            )
            
            # Get total count
            total_records = self.db.execute_count_query(count_query, count_params)
            
            # Get results
            results = self.db.execute_query(query, main_params)
            
            # Format results
            formatted_results = [self._format_model_result(row) for row in results]
            
            # Return paginated response
            return paginate_results(formatted_results, page, page_size, total_records)
            
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            raise
    
    def _build_search_query(self, model_name: str, manufacturer_name: Optional[str] = None,
                           year: Optional[int] = None, page: int = 1, 
                           page_size: int = 10) -> Tuple[str, str, List[Any]]:
        """
        Build the SQL query for model search.
        
        Returns:
            Tuple of (main query, count query, parameters)
        """
        # Base query structure
        base_select = """
        SELECT
            m.id,
            m.name as model_name,
            m.year,
            m.description,
            mfr.name as manufacturer_name,
            pl.name as product_line_name
        FROM models m
        JOIN manufacturers mfr ON m.manufacturer_id = mfr.id
        LEFT JOIN product_lines pl ON m.product_line_id = pl.id
        """
        
        count_select = """
        SELECT COUNT(m.id)
        FROM models m
        JOIN manufacturers mfr ON m.manufacturer_id = mfr.id
        LEFT JOIN product_lines pl ON m.product_line_id = pl.id
        """
        
        where_clauses = []
        where_params = []
        
        # Process model name search
        model_search_terms = split_search_terms(model_name)
        
        # Check if model name contains potential years
        extracted_years = extract_years_from_text(model_name)
        if extracted_years and not year:
            # Use the first extracted year if no explicit year provided
            year = extracted_years[0]
            # Remove year from search terms
            model_search_terms = [term for term in model_search_terms 
                                if not term.isdigit() or int(term) not in extracted_years]
        
        if model_search_terms:
            # Search across model name and product line name
            search_fields = ['m.name', 'pl.name']
            clause, search_params = build_multifield_search_clause(
                model_search_terms, search_fields, similarity_threshold=0.3
            )
            if clause:
                where_clauses.append(clause)
                where_params.extend(search_params)
        
        # Add manufacturer filter
        if manufacturer_name:
            mfr_terms = split_search_terms(manufacturer_name)
            if mfr_terms:
                clause, search_params = build_multifield_search_clause(
                    mfr_terms, ['mfr.name'], similarity_threshold=0.25
                )
                if clause:
                    where_clauses.append(clause)
                    where_params.extend(search_params)
        
        # Add year filter
        if year:
            where_clauses.append("m.year = %s")
            where_params.append(year)
        
        # Combine WHERE clauses
        where_clause = ""
        if where_clauses:
            where_clause = "WHERE " + " AND ".join(where_clauses)
        
        # Build count query (no ORDER BY, no LIMIT/OFFSET)
        count_query = f"{count_select} {where_clause}"
        count_params = where_params.copy()
        
        # Add ordering - prioritize exact matches and more recent models
        order_clause = """
        ORDER BY 
            CASE WHEN LOWER(m.name) = LOWER(%s) THEN 1 ELSE 2 END,
            m.year DESC,
            m.name
        """
        
        # Build main query parameters (WHERE + ORDER BY + LIMIT/OFFSET)
        main_params = where_params.copy()
        main_params.append(model_name)  # ORDER BY parameter
        
        # Add pagination parameters
        offset = (page - 1) * page_size
        main_params.extend([page_size, offset])
        
        # Build final main query
        main_query = f"{base_select} {where_clause} {order_clause} LIMIT %s OFFSET %s"
        
        return main_query, count_query, main_params, count_params
    
    def _format_model_result(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """Format a model search result according to the API specification."""
        return {
            'id': str(row['id']),
            'model_name': row['model_name'],
            'year': row['year'],
            'manufacturer_name': row['manufacturer_name'],
            'product_line_name': row['product_line_name'],
            'description': row['description']
        }