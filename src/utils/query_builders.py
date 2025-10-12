"""Common database query patterns."""

from typing import List, Optional, Type, TypeVar

from sqlalchemy import or_
from sqlalchemy.orm import Session

T = TypeVar("T")


class QueryBuilder:
    """Reusable query patterns."""

    @staticmethod
    def paginate(query, page: int = 1, per_page: int = 20):
        """
        Paginate a query.

        Args:
            query: SQLAlchemy query
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Paginated query and metadata
        """
        from src.config.constants import DatabaseConstants

        # Validate pagination parameters
        page = max(1, page)
        per_page = min(per_page, DatabaseConstants.MAX_PAGE_SIZE)

        # Get total count
        total = query.count()

        # Apply pagination
        items = query.offset((page - 1) * per_page).limit(per_page).all()

        return {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": (total + per_page - 1) // per_page,
        }

    @staticmethod
    def search(model: Type[T], db: Session, search_fields: List[str], search_term: str):
        """
        Search across multiple fields.

        Args:
            model: SQLAlchemy model class
            db: Database session
            search_fields: List of field names to search
            search_term: Search term

        Returns:
            Query with search filters applied
        """
        query = db.query(model)

        if not search_term:
            return query

        # Build OR conditions for each field
        conditions = []
        for field in search_fields:
            if hasattr(model, field):
                column = getattr(model, field)
                conditions.append(column.ilike(f"%{search_term}%"))

        if conditions:
            query = query.filter(or_(*conditions))

        return query

    @staticmethod
    def filter_by_date_range(
        query,
        date_field,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        Filter query by date range.

        Args:
            query: SQLAlchemy query
            date_field: Date column to filter
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            Query with date filters applied
        """
        from datetime import datetime

        if start_date:
            start = datetime.fromisoformat(start_date)
            query = query.filter(date_field >= start)

        if end_date:
            end = datetime.fromisoformat(end_date)
            query = query.filter(date_field <= end)

        return query
