"""
Base query service providing shared SPARQL functionality.

Defines common patterns for SPARQL query execution, error handling,
and result processing that can be inherited by specific query services.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, cast

import requests

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Container for query results with metadata."""

    data: dict[str, Any]
    query: str
    success: bool = True
    error: str | None = None


class QueryServiceError(Exception):
    """Base exception for query service errors."""


class SPARQLTimeoutError(QueryServiceError):
    """Exception raised for SPARQL query timeouts."""


class SPARQLConnectionError(QueryServiceError):
    """Exception raised for SPARQL connection errors."""


class SPARQLHTTPError(QueryServiceError):
    """Exception raised for SPARQL HTTP errors."""


class BaseQueryService(ABC):
    """
    Abstract base class for SPARQL query services.

    Provides common functionality for executing SPARQL queries,
    handling errors, and processing results. Concrete implementations
    should inherit from this class and implement the abstract methods.
    """

    def __init__(self, endpoint: str, timeout: int = 30):
        """
        Initialize the query service.

        Args:
            endpoint: SPARQL endpoint URL
            timeout: Query timeout in seconds
        """
        self.endpoint = endpoint
        self.timeout = timeout

    def execute_sparql_query(self, query: str) -> dict[str, Any]:
        """
        Execute SPARQL query with standardized error handling.

        Args:
            query: SPARQL query string

        Returns:
            Dictionary containing query results

        Raises:
            SPARQLTimeoutError: If query times out
            SPARQLConnectionError: If connection fails
            SPARQLHTTPError: If HTTP error occurs
            QueryServiceError: For other query-related errors
        """
        try:
            response = requests.get(
                self.endpoint,
                params={"query": query, "format": "json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = cast(dict[str, Any], response.json())
            return data

        except requests.exceptions.Timeout as e:
            error_msg = f"{e} SPARQL query timeout after {self.timeout}s"
            logger.error(error_msg)
            raise SPARQLTimeoutError(error_msg) from e
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Failed to connect to SPARQL endpoint: {e}"
            logger.error(error_msg)
            raise SPARQLConnectionError(error_msg) from e
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP error {e.response.status_code}: {e}"
            logger.error(error_msg)
            raise SPARQLHTTPError(error_msg) from e
        except requests.exceptions.RequestException as e:
            error_msg = f"Request error: {e}"
            logger.error(error_msg)
            raise QueryServiceError(error_msg) from e
        except ValueError as e:
            error_msg = f"Invalid JSON response: {e}"
            logger.error(error_msg)
            raise QueryServiceError(error_msg) from e

    def execute_query_safe(self, query: str) -> QueryResult:
        """
        Execute SPARQL query with exception handling.

        Args:
            query: SPARQL query string

        Returns:
            QueryResult with data and success status
        """
        try:
            data = self.execute_sparql_query(query)
            return QueryResult(data=data, query=query, success=True)
        except QueryServiceError as e:
            return QueryResult(data={}, query=query, success=False, error=str(e))

    @staticmethod
    def extract_binding_value(binding: dict[str, Any], key: str) -> str:
        """Extract value from SPARQL binding.

        Args:
            binding: SPARQL binding dict.
            key: Key to extract.

        Returns:
            Extracted value string.
        """
        val = binding.get(key, {}).get("value", "")
        return str(val)

    @staticmethod
    def extract_id_from_uri(uri: str) -> str:
        """Extract ID from URI.

        Args:
            uri: URI string.

        Returns:
            Extracted ID string.
        """
        return uri.split("/")[-1] if "/" in uri else uri

    @staticmethod
    def format_uris_for_sparql(uris: list[str]) -> str:
        """Format list of URIs for use in SPARQL VALUES clause.

        Args:
            uris: List of URI strings.

        Returns:
            Formatted string for SPARQL.
        """
        return " ".join([f"<{uri}>" if not uri.startswith("<") else uri for uri in uris])

    @abstractmethod
    def get_service_name(self) -> str:
        """Return the name of the service for logging.

        Returns:
            Service name string.
        """

    def log_query(self, query: str, description: str = "") -> None:
        """Log the complete query for debugging.

        Args:
            query: SPARQL query string.
            description: Optional description.
        """
        service_name = self.get_service_name()
        logger.info("=" * 60)
        logger.info("GENERATED %s SPARQL QUERY: %s", service_name, description)
        logger.info("=" * 60)
        logger.info(query)
        logger.info("=" * 60)
