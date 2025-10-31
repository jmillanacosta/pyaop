"""
Query manager for Bgee SPARQL.

Prepare, send and retrieve query (results).
"""

import logging

from pyaop.queries.base_query_service import BaseQueryService

# Set up logger
logger = logging.getLogger(__name__)

BGEE_SPARQL_ENDPOINT = "https://www.bgee.org/sparql/"


class BgeeQueryService(BaseQueryService):
    """Service for querying Bgee gene expression data from SPARQL endpoint."""

    def __init__(self) -> None:
        """Initialize the Bgee query service."""
        super().__init__(endpoint=BGEE_SPARQL_ENDPOINT, timeout=30)

    def get_service_name(self) -> str:
        """Return the name of the service for logging.

        Returns:
            Service name string.
        """
        return "Bgee"

    def build_gene_expressions_query(
        self, gene_ids: list[str], organ_ids: list[str], confidence_level: int | None = None
    ) -> str:
        """Build SPARQL Query for Bgee gene expression data.

        Args:
            gene_ids: List of gene IDs.
            organ_ids: List of organ IDs.
            confidence_level: Minimum confidence level.

        Returns:
            SPARQL query string.
        """
        return self._build_bgee_sparql_query(gene_ids, organ_ids, confidence_level)

    def _build_bgee_sparql_query(
        self, gene_ids: list[str], organ_ids: list[str], confidence_level: int | None = None
    ) -> str:
        """Build SPARQL query for Bgee gene expression data.

        Args:
            gene_ids: List of gene IDs.
            organ_ids: List of organ IDs.
            confidence_level: Minimum confidence level.

        Returns:
            SPARQL query string.
        """
        # Build genes clause
        genes_clause = ""
        if gene_ids:
            genes_clause = f"VALUES ?gene_id {{ {' '.join(gene_ids)} }}"

        # Build anatomical entities clause - use organ names directly
        anatomical_entities_clause = ""
        if organ_ids:
            # Remove quotes from organ names and use them directly
            clean_organ_names = [oid.strip('"') for oid in organ_ids]
            organ_values = " ".join(f'"{name}"' for name in clean_organ_names)
            anatomical_entities_clause = f"VALUES ?anatomical_entity_name {{ {organ_values} }}"

        # Build confidence level filter
        confidence_filter = ""
        if confidence_level is not None:
            if confidence_level >= 80:
                confidence_filter = (
                    "?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence"
                )
            elif confidence_level >= 50:
                confidence_filter = """
                {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence
                } UNION {
                    ?expr genex:hasConfidenceLevel obo:CIO_0000031 . # medium confidence
                }
                """
            elif confidence_level >= 20:
                confidence_filter = """
{
    ?expr genex:hasConfidenceLevel obo:CIO_0000029 . # high confidence
} UNION {
    ?expr genex:hasConfidenceLevel obo:CIO_0000031 . # medium confidence
} UNION {
    ?expr genex:hasConfidenceLevel obo:CIO_0000030 . # low confidence
}
"""

        return f"""
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX orth: <http://purl.org/net/orth#>
PREFIX lscr: <http://purl.org/lscr#>
PREFIX genex: <http://purl.org/genex#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX dcterms: <http://purl.org/dc/terms/>
SELECT ?gene_idI ?gene_id ?anatomical_entity_id
?anatomical_entity_name ?developmental_stage_id
?developmental_stage_name ?expression_level ?confidence_level_id
?confidence_level_name ?expr
WHERE {{
  {genes_clause}
  {anatomical_entities_clause}
  ?gene_idI a orth:Gene .
  ?gene_idI dcterms:identifier ?gene_id .
  ?expr genex:hasSequenceUnit ?gene_idI.
  ?expr a genex:Expression .
  {confidence_filter}
  ?expr genex:hasConfidenceLevel ?confidence_level_id .
  ?confidence_level_id rdfs:label ?confidence_level_label.
  BIND(str(?confidence_level_label) as ?confidence_level_name)
  ?expr genex:hasExpressionLevel ?expression_level .
  ?expr genex:hasExpressionCondition ?cond .
  ?cond genex:hasDevelopmentalStage ?developmental_stage_id.
  ?developmental_stage_id rdfs:label ?developmental_stage_name.
  ?cond genex:hasAnatomicalEntity ?anatomical_entity_id . # tissue
  ?anatomical_entity_id rdfs:label ?anatomical_entity_name.
    }}
"""


# Exception classes


class BgeeDataError(Exception):
    """Exception raised for Bgee data errors."""


# Global service instance
bgee_query_service = BgeeQueryService()
