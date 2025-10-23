"""
Query manager for AOP-Wiki RDF.

Prepare, send and retrieve query (results).
"""

import logging
from typing import Any

import requests

# Set up logger
logger = logging.getLogger(__name__)

AOPWIKISPARQL_ENDPOINT = "https://aopwiki.rdf.bigcat-bioinformatics.org/sparql/"
AOPDBSPARQL_ENDPOINT = "https://aopdb.org/sparql/"

class SPARQLQueryError(Exception):
    """Custom exception for SPARQL query errors"""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"SPARQLQueryError: {self.message}"


class AOPQueryService:
    """Service for querying AOP data from SPARQL endpoint"""

    def __init__(self):
        self.endpoint = AOPWIKISPARQL_ENDPOINT # Current mirror

    def build_aop_sparql_query(self, query_type: str, values: str) -> str:
        """Build SPARQL query for AOP data"""
        logger.info(f"Building AOP SPARQL query: {query_type}, values: {values}")

        # Process values to ensure proper URI formatting
        processed_values = []
        for value in values.split():
            if value.startswith("http"):
                processed_values.append(f"<{value}>")
            else:
                processed_values.append(f"<{value}>")

        formatted_values = " ".join(processed_values)

        # Base query template
        base_query = """SELECT DISTINCT ?aop ?aop_title ?MIEtitle ?MIE ?KE_downstream ?KE_downstream_title ?KER ?ao ?ao_title ?KE_upstream ?KE_upstream_title
        WHERE {
          %VALUES_CLAUSE%
          ?aop a aopo:AdverseOutcomePathway ;
               dc:title ?aop_title ;
               aopo:has_adverse_outcome ?ao ;
               aopo:has_molecular_initiating_event ?MIE .
          ?ao dc:title ?ao_title .
          ?MIE dc:title ?MIEtitle .
          OPTIONAL {
            ?aop aopo:has_key_event_relationship ?KER .
            ?KER a aopo:KeyEventRelationship ;
                 aopo:has_upstream_key_event ?KE_upstream ;
                 aopo:has_downstream_key_event ?KE_downstream .
            ?KE_upstream dc:title ?KE_upstream_title .
            ?KE_downstream dc:title ?KE_downstream_title .
          }
        }"""

        # Build VALUES clause based on query type
        values_clause_map = {
            "mie": f"VALUES ?MIE {{ {formatted_values} }}",
            "aop": f"VALUES ?aop {{ {formatted_values} }}",
            "ke_upstream": f"VALUES ?KE_upstream {{ {formatted_values} }}",
            "ke_downstream": f"VALUES ?KE_downstream {{ {formatted_values} }}",
        }

        values_clause = values_clause_map.get(query_type)
        if not values_clause:
            logger.warning(f"Invalid query type: {query_type}")
            return ""

        final_query = base_query.replace("%VALUES_CLAUSE%", values_clause)
        logger.debug(f"Generated SPARQL query length: {len(final_query)}")

        return final_query

    def build_gene_sparql_query(self, ke_uris: str, include_proteins: bool = True) -> str:
        """Build SPARQL query for gene data"""
        if include_proteins:
            return f"""
                SELECT DISTINCT ?ke ?gene ?protein WHERE {{
                    VALUES ?ke {{ {ke_uris} }}
                    ?ke a aopo:KeyEvent; edam:data_1025 ?object .
                    ?object skos:exactMatch ?id .
                    ?id a edam:data_1033; edam:data_1033 ?gene .
                    OPTIONAL {{
                        ?object skos:exactMatch ?prot .
                        ?prot a edam:data_2291 ;
                              edam:data_2291 ?protein .
                    }}
                }}
            """
        else:
            return f"""
                SELECT DISTINCT ?ke ?gene WHERE {{
                    VALUES ?ke {{ {ke_uris} }}
                    ?ke a aopo:KeyEvent; edam:data_1025 ?object .
                    ?object skos:exactMatch ?id .
                    ?id a edam:data_1033; edam:data_1033 ?gene .
                }}
            """

    def build_compound_sparql_query(self, aop_uris: str) -> str:
        """Build SPARQL query for compound data"""
        return f"""
            SELECT DISTINCT ?aop ?compound_name ?cid ?pubchem_compound ?mie ?chemical
            WHERE {{
                VALUES ?aop {{ {aop_uris} }}
                FILTER(STRSTARTS(STR(?pubchem_compound), "https://identifiers.org/pubchem.compound/"))

                ?aop a aopo:AdverseOutcomePathway ; nci:C54571 ?stressor ; aopo:has_molecular_initiating_event ?mie .
                ?chemical skos:exactMatch ?pubchem_compound ; dc:title ?compound_name.
                ?stressor a nci:C54571 ; aopo:has_chemical_entity ?chemical .
                ?pubchem_compound cheminf:000140 ?cid .
            }}
            ORDER BY ?compound_name
        """

    def build_organ_sparql_query(self, ke_uris: str) -> str:
        """Build SPARQL query for organ data"""
        return f"""
        SELECT DISTINCT ?ke ?organ ?organ_name WHERE {{
                    VALUES ?ke {{ {ke_uris} }}
                    ?ke a aopo:KeyEvent; aopo:OrganContext ?organ .
                    ?organ dc:title ?organ_name .
        }}
        """

    def build_components_sparql_query(self, go_only: bool, ke_uris: str) -> str:
        """Build SPARQL query for GO process data"""
        if go_only:
            go_filter = 'FILTER(STRSTARTS(STR(?process), "http://purl.obolibrary.org/obo/GO_"))'
        else:
            go_filter = ""
        return f"""
            SELECT DISTINCT ?ke ?keTitle ?bioEvent ?process ?processName ?object ?objectName ?action ?objectType
            WHERE {{
                {go_filter}
                VALUES ?ke {{ {ke_uris } }}
                ?ke a aopo:KeyEvent ;
                    dc:title ?keTitle .
                OPTIONAL {{ ?ke aopo:hasBiologicalEvent ?bioEvent. ?bioEvent aopo:hasProcess ?process . ?process dc:title ?processName.}}
                OPTIONAL {{ ?ke aopo:hasBiologicalEvent ?bioEvent. ?bioEvent aopo:hasObject ?object . ?object dc:title ?objectName ; a ?objectType . }}
                OPTIONAL {{ ?ke aopo:hasBiologicalEvent ?bioEvent. ?bioEvent aopo:hasAction ?action . }}
            }}
            ORDER BY ?ke
        """

    def execute_sparql_query(self, query: str) -> dict[str, Any]:
        """Execute SPARQL query with standardized error handling"""
        logger.info(f"Executing SPARQL query (length: {len(query)})")

        try:
            response = requests.get(
                self.endpoint,
                params={"query": query, "format": "json"},
                timeout=10,
            )
            logger.debug(f"SPARQL response status: {response.status_code}")
            response.raise_for_status()

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])
            logger.info(f"Retrieved {len(bindings)} SPARQL result bindings")

            return data

        except requests.exceptions.Timeout:
            raise SPARQLQueryError("SPARQL query timeout")
        except requests.exceptions.ConnectionError:
            raise SPARQLQueryError("Failed to connect to SPARQL endpoint")
        except requests.exceptions.HTTPError as e:
            raise SPARQLQueryError(f"HTTP error {e.response.status_code}: {e}")
        except requests.exceptions.RequestException as e:
            raise SPARQLQueryError(f"Request error: {e!s}")
        except ValueError as e:
            raise ValueError(f"Invalid JSON response: {e!s}")


# Global service instance
# aop_query_service = AOPQueryService()
