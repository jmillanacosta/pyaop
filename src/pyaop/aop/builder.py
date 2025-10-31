"""
AOP network builder module for constructing Adverse Outcome Pathway networks.

Provides classes for querying SPARQL endpoint, processing results, and building
structured AOP networks with key events, relationships, and biological
associations.
"""

import logging
from typing import Any

from pyaop.aop.associations import (
    BiologicalProcessAssociation,
    ComponentAssociation,
    CompoundAssociation,
    GeneAssociation,
    GeneExpressionAssociation,
    OrganAssociation,
)
from pyaop.aop.constants import EdgeType, NodeType
from pyaop.aop.core_model import (
    AOPInfo,
    AOPKeyEvent,
    AOPNetwork,
    KeyEventRelationship,
)
from pyaop.cytoscape.elements import CytoscapeEdge, CytoscapeNode
from pyaop.queries.aopwikirdf import AOPQueryService
from pyaop.queries.base_query_service import QueryResult, QueryServiceError
from pyaop.queries.bgee import BgeeQueryService

logger = logging.getLogger(__name__)


class SPARQLResultProcessor:
    """Processes SPARQL query results into AOP domain objects."""

    @staticmethod
    def extract_binding_value(binding: dict[str, Any], key: str) -> str:
        """Extract value from SPARQL binding.

        Args:
            binding: SPARQL binding dict.
            key: Key to extract.

        Returns:
            Extracted value string.
        """
        return str(binding.get(key, {}).get("value", ""))

    @staticmethod
    def extract_id_from_uri(uri: str) -> str:
        """Extract ID from URI.

        Args:
            uri: URI string.

        Returns:
            Extracted ID string.
        """
        return uri.split("/")[-1] if "/" in uri else uri


class AOPSPARQLProcessor(SPARQLResultProcessor):
    """Processes AOP-specific SPARQL results."""

    def process_aop_bindings(
        self, bindings: list[dict[str, Any]]
    ) -> tuple[list[AOPKeyEvent], list[KeyEventRelationship], list[AOPInfo]]:
        """Process AOP SPARQL bindings into structured objects.

        Args:
            bindings: List of SPARQL bindings.

        Returns:
            Tuple of lists: key events, relationships, AOP infos.
        """
        key_events: dict[str, AOPKeyEvent] = {}
        relationships = []
        aop_infos = []

        for binding in bindings:
            # Process AOP info
            aop_info = self._extract_aop_info(binding)
            if aop_info and aop_info not in aop_infos:
                aop_infos.append(aop_info)
            # Process key events
            self._process_key_events_from_binding(binding, key_events, aop_info)
            # Process relationships
            relationship = self._extract_relationship(binding, key_events)
            if relationship:
                relationships.append(relationship)
        return list(key_events.values()), relationships, aop_infos

    def _extract_aop_info(self, binding: dict[str, Any]) -> AOPInfo | None:
        """Extract AOP info from binding.

        Args:
            binding: SPARQL binding dict.

        Returns:
            AOPInfo object or None.
        """
        aop_uri = self.extract_binding_value(binding, "aop")
        aop_title = self.extract_binding_value(binding, "aop_title")

        if aop_uri and aop_title:
            aop_id = self.extract_id_from_uri(aop_uri)
            return AOPInfo(aop_id=aop_id, title=aop_title, uri=aop_uri)
        return None

    def _process_key_events_from_binding(
        self,
        binding: dict[str, Any],
        key_events: dict[str, AOPKeyEvent],
        aop_info: AOPInfo | None,
    ) -> None:
        """Process all key events from a single binding.

        Args:
            binding: SPARQL binding dict.
            key_events: Dict of existing key events.
            aop_info: Associated AOP info.
        """
        # Process MIE
        self._process_single_key_event(
            binding, "MIE", "MIEtitle", NodeType.MIE, key_events, aop_info
        )

        # Process AO
        self._process_single_key_event(binding, "ao", "ao_title", NodeType.AO, key_events, aop_info)

        # Process upstream/downstream KEs
        upstream_uri = self.extract_binding_value(binding, "KE_upstream")
        downstream_uri = self.extract_binding_value(binding, "KE_downstream")
        mie_uri = self.extract_binding_value(binding, "MIE")
        ao_uri = self.extract_binding_value(binding, "ao")

        if upstream_uri and upstream_uri not in [mie_uri, ao_uri]:
            self._process_single_key_event(
                binding,
                "KE_upstream",
                "KE_upstream_title",
                NodeType.KE,
                key_events,
                aop_info,
            )

        if downstream_uri and downstream_uri not in [mie_uri, ao_uri]:
            self._process_single_key_event(
                binding,
                "KE_downstream",
                "KE_downstream_title",
                NodeType.KE,
                key_events,
                aop_info,
            )

    def _process_single_key_event(
        self,
        binding: dict[str, Any],
        uri_key: str,
        title_key: str,
        ke_type: NodeType,
        key_events: dict[str, AOPKeyEvent],
        aop_info: AOPInfo | None,
    ) -> None:
        """Process a single key event from binding.

        Args:
            binding: SPARQL binding dict.
            uri_key: Key for URI in binding.
            title_key: Key for title in binding.
            ke_type: Type of key event.
            key_events: Dict of existing key events.
            aop_info: Associated AOP info.
        """
        uri = self.extract_binding_value(binding, uri_key)
        title = self.extract_binding_value(binding, title_key)

        if not uri:
            return

        if uri in key_events:
            # Update existing KE with new AOP info
            if aop_info:
                key_events[uri].add_aop(aop_info)
        else:
            # Create new KE
            ke_id = self.extract_id_from_uri(uri)
            key_event = AOPKeyEvent(
                ke_id=ke_id, uri=uri, title=title if title else "NA", ke_type=ke_type
            )
            if aop_info:
                key_event.add_aop(aop_info)
            key_events[uri] = key_event

    def _extract_relationship(
        self, binding: dict[str, Any], key_events: dict[str, AOPKeyEvent]
    ) -> KeyEventRelationship | None:
        """Extract relationship from binding.

        Args:
            binding: SPARQL binding dict.
            key_events: Dict of existing key events.

        Returns:
            KeyEventRelationship object or None.
        """
        ker_uri = self.extract_binding_value(binding, "KER")
        upstream_uri = self.extract_binding_value(binding, "KE_upstream")
        downstream_uri = self.extract_binding_value(binding, "KE_downstream")

        if (
            ker_uri
            and upstream_uri
            and downstream_uri
            and upstream_uri in key_events
            and downstream_uri in key_events
        ):
            ker_id = self.extract_id_from_uri(ker_uri)
            return KeyEventRelationship(
                ker_id=ker_id,
                ker_uri=ker_uri,
                upstream_ke=key_events[upstream_uri],
                downstream_ke=key_events[downstream_uri],
            )
        return None


class AssociationProcessor(SPARQLResultProcessor):
    """Processes association SPARQL results."""

    def process_gene_associations(
        self, bindings: list[dict[str, Any]], include_proteins: bool = True
    ) -> list[GeneAssociation]:
        """Process gene association bindings.

        Args:
            bindings: List of SPARQL bindings.
            include_proteins: Whether to include protein data.

        Returns:
            List of GeneAssociation objects.
        """
        associations = []
        for binding in bindings:
            ke_uri = self.extract_binding_value(binding, "ke")
            gene_id = self.extract_binding_value(binding, "gene")
            protein_id = (
                self.extract_binding_value(binding, "protein") if include_proteins else None
            )

            if ke_uri and gene_id:
                association = GeneAssociation(ke_uri=ke_uri, gene_id=gene_id, protein_id=protein_id)
                associations.append(association)
        return associations

    def process_compound_associations(
        self, bindings: list[dict[str, Any]]
    ) -> list[CompoundAssociation]:
        """Process compound association bindings.

        Args:
            bindings: List of SPARQL bindings.

        Returns:
            List of CompoundAssociation objects.
        """
        associations = []
        for binding in bindings:
            aop_uri = self.extract_binding_value(binding, "aop")
            chemical_uri = self.extract_binding_value(binding, "chemical")
            pubchem_compound = self.extract_binding_value(binding, "pubchem_compound")
            compound_name = self.extract_binding_value(binding, "compound_name")
            cid = self.extract_binding_value(binding, "cid")
            mie_uri = self.extract_binding_value(binding, "mie")
            if aop_uri and chemical_uri and pubchem_compound:
                association = CompoundAssociation(
                    aop_uri=aop_uri,
                    mie_uri=mie_uri,
                    chemical_uri=chemical_uri,
                    chemical_label=compound_name,
                    pubchem_compound=pubchem_compound,
                    compound_name=compound_name,
                    cas_id=cid if cid else None,
                )
                associations.append(association)
        return associations

    def process_component_associations(
        self, bindings: list[dict[str, Any]]
    ) -> list[ComponentAssociation]:
        """Process component association bindings.

        Args:
            bindings: List of SPARQL bindings.

        Returns:
            List of ComponentAssociation objects.
        """
        associations = []
        for binding in bindings:
            process_iri = self.extract_binding_value(binding, "process")
            if not process_iri:
                continue
            association = ComponentAssociation(
                ke_uri=self.extract_binding_value(binding, "ke"),
                ke_name=self.extract_binding_value(binding, "ke_name"),
                process=process_iri,
                process_name=self.extract_binding_value(binding, "processName"),
                object=self.extract_binding_value(binding, "object"),
                object_name=self.extract_binding_value(binding, "objectName"),
                action=self.extract_binding_value(binding, "action"),
                object_type=self.extract_binding_value(binding, "objectType"),
            )
            associations.append(association)
        return associations

    def process_organ_associations(self, bindings: list[dict[str, Any]]) -> list[OrganAssociation]:
        """Process organ association bindings.

        Args:
            bindings: List of SPARQL bindings.

        Returns:
            List of OrganAssociation objects.
        """
        associations = []
        for binding in bindings:
            ke_uri = self.extract_binding_value(binding, "ke")
            organ_uri = self.extract_binding_value(binding, "organ")
            organ_name = self.extract_binding_value(binding, "organ_name")
            if not ke_uri or not organ_uri:
                continue
            organ_node = CytoscapeNode(
                id=organ_uri,
                label=(organ_name if organ_name else self.extract_id_from_uri(organ_uri)),
                node_type=NodeType.ORGAN.value,
                classes="organ-node",
                properties={
                    "anatomical_id": organ_uri,
                    "anatomical_name": organ_name,
                },
            )
            edge = CytoscapeEdge(
                id=f"{ke_uri}_{organ_uri}",
                source=ke_uri,
                target=organ_uri,
                label=EdgeType.ASSOCIATED_WITH.value,
                properties={"type": EdgeType.ASSOCIATED_WITH.value},
            )
            association = OrganAssociation(ke_uri=ke_uri, organ_data=organ_node, edge_data=edge)
            associations.append(association)
        return associations

    def process_biological_process_associations(self, bindings: list[dict[str, Any]]) -> list[BiologicalProcessAssociation]:
        """Process biological process association bindings.

        Args:
            bindings: List of SPARQL bindings.

        Returns:
            List of BiologicalProcessAssociation objects.
        """
        associations = []
        for binding in bindings:
            ke_uri = self.extract_binding_value(binding, "ke")
            bp_uri = self.extract_binding_value(binding, "biological_process")
            bp_name = self.extract_binding_value(binding, "biological_process_name")
            if not ke_uri or not bp_uri:
                continue
            bp_node = CytoscapeNode(
                id=bp_uri,
                label=bp_name if bp_name else self.extract_id_from_uri(bp_uri),
                node_type=NodeType.COMP_PROC.value,
                classes="biological-process-node",
                properties={
                    "biological_process_id": bp_uri,
                    "biological_process_name": bp_name,
                },
            )
            edge = CytoscapeEdge(
                id=f"{ke_uri}_{bp_uri}",
                source=ke_uri,
                target=bp_uri,
                label=EdgeType.HAS_PROCESS.value,
                properties={"type": EdgeType.HAS_PROCESS.value},
            )
            association = BiologicalProcessAssociation(ke_uri=ke_uri, bp_data=bp_node, edge_data=edge)
            associations.append(association)
        return associations


class AOPNetworkBuilder:
    """
    Builder class for orchestrating AOP network construction.

    Coordinate between query service and result processors to build networks.
    """

    def __init__(self) -> None:
        """Initialize the AOP network builder."""
        self.network = AOPNetwork()
        self._aop_query_service = AOPQueryService()
        self._aop_processor = AOPSPARQLProcessor()
        self._assoc_processor = AssociationProcessor()
        self._bgee_query_service = BgeeQueryService()

    def query_by_identifier(
        self, query_type: str, values: str, status: list[str]
    ) -> tuple[AOPNetwork, str]:
        """
        Query AOP network data by identifier and return structured model.

        Args:
            query_type: Type of query (e.g., 'mie', 'aop').
            values: Values for the query.

        Returns:
            Tuple of AOPNetwork and query string.
        """
        # Step 1: Execute query
        query_result = self._execute_aop_query(query_type, values, status)
        if query_result.success:
            # Step 2: Process results
            self._process_aop_query_results(query_result.data)
            # Step 3: Build and return network
            self.network = self._build_network()
            return self.network, query_result.query
        return self.network, "# Identifier query failed"

    def query_organs_for_kes(self) -> tuple[AOPNetwork, str]:
        """Query organ associations for all KEs in the network.

        Returns:
            Tuple of AOPNetwork and query string.
        """
        ke_uris = self.network.get_ke_uris()
        if not ke_uris:
            logger.warning("No Key Events found for organ querying")
            return self.network, "# No KEs to query"
        query_result = self._execute_organ_query(ke_uris)
        if query_result.success:
            self._process_organ_query_results(query_result.data)
            self.network = self._build_network()
            return self.network, query_result.query
        return self.network, "# Organ query failed"

    def query_compounds_for_network(self) -> tuple[AOPNetwork, str]:
        """Query compound associations for all AOPs in the network.

        Returns:
            Tuple of AOPNetwork and query string.
        """
        aop_uris = self.network.get_aop_uris()
        if not aop_uris:
            logger.warning("No AOPs found for compound querying")
            return self.network, "# No AOPs to query"
        query_result = self._execute_compound_query(aop_uris)
        if query_result.success:
            self._process_compound_query_results(query_result.data)
            self.network = self._build_network()
            return self.network, query_result.query
        return self.network, "# Compound query failed"

    def query_components_for_network(self, go_only: bool = False) -> tuple[AOPNetwork, str]:
        """Query components for all KEs in the network.

        Args:
            go_only: Whether to filter for GO only.

        Returns:
            Tuple of AOPNetwork and query string.
        """
        ke_uris = self.network.get_ke_uris()
        if not ke_uris:
            logger.warning("No Key Events found for component querying")
            return self.network, "# No KEs to query"
        query_result = self._execute_component_query(ke_uris, go_only)
        if query_result.success:
            self._process_component_query_results(query_result.data)
            self.network = self._build_network()
            return self.network, query_result.query
        return self.network, "# Component query failed"

    def query_gene_expression(
        self,
        confidence_level: int,
    ) -> tuple[AOPNetwork, str]:
        """Query gene expression values for all KEs in the network.

        Args:
            confidence_level: Minimum confidence level.

        Returns:
            Tuple of AOPNetwork and query string.
        """
        gene_ids = self.network.get_gene_ids()
        organ_ids = self.network.get_organ_ids()
        if gene_ids and organ_ids:
            # Execute gene expression query
            updated_network, query = self._execute_gene_expression_query(
                confidence_level=confidence_level,
            )
            self.network = updated_network
            return self.network, query
        return self.network, "# Gene query failed"

    def query_genes_for_ke(self, include_proteins: bool = True) -> tuple[AOPNetwork, str]:
        """Query gene associations for all KEs in the network.

        Args:
            include_proteins: Whether to include protein data.

        Returns:
            Tuple of AOPNetwork and query string.
        """
        ke_uris = self.network.get_ke_uris()
        if not ke_uris:
            logger.warning("No Key Events found for gene querying")
            return self.network, "# No KEs to query"
        # Execute gene query
        query_result = self._execute_gene_query(ke_uris, include_proteins)
        if query_result.success:
            # Process results
            self._process_gene_query_results(query_result.data, include_proteins)
            self.network = self._build_network()
            return self.network, query_result.query
        return self.network, "# Gene query failed"

    def query_biological_processes_for_kes(self) -> tuple[AOPNetwork, str]:
        """Query biological processes for all KEs in the network.

        Returns:
            Tuple of AOPNetwork and query string.
        """
        ke_uris = self.network.get_ke_uris()
        if not ke_uris:
            logger.warning("No Key Events found for biological process querying")
            return self.network, "# No KEs to query"
        query_result = self._execute_biological_process_query(ke_uris)
        if query_result.success:
            self._process_biological_process_query_results(query_result.data)
            self.network = self._build_network()
            return self.network, query_result.query
        return self.network, "# Biological process query failed"

    def _execute_aop_query(self, query_type: str, values: str, status: list[str]) -> QueryResult:
        """Execute AOP SPARQL query and return structured result.

        Args:
            query_type: Type of query.
            values: Values for the query.

        Returns:
            QueryResult object.
        """
        formatted_status = " ".join([f'"{i}"' for i in status])
        if len(status) == 3:
            formatted_status = ""
        query = self._aop_query_service.build_aop_sparql_query(query_type, values, formatted_status)
        if not query:
            return QueryResult(
                data={}, query="", success=False, error=(f"Invalid query type: {query_type}")
            )
        results = self._aop_query_service.execute_sparql_query(query)
        bindings = results.get("results", {}).get("bindings", [])
        logger.debug("Retrieved %d bindings", len(bindings))
        return QueryResult(data=results, query=query, success=True)

    def _process_aop_query_results(self, sparql_data: dict[str, Any]) -> None:
        """Process AOP SPARQL results using the processor.

        Args:
            sparql_data: SPARQL query results.
        """
        bindings = sparql_data.get("results", {}).get("bindings", [])

        kes, rels, _ = self._aop_processor.process_aop_bindings(bindings)

        # Add to network
        for ke in kes:
            self.network.add_key_event(ke)

        for rel in rels:
            self.network.add_relationship(rel)

        # AOP infos are already added through key events

    def _execute_gene_query(self, ke_uris: list[str], include_proteins: bool = True) -> QueryResult:
        """Execute gene association query.

        Args:
            ke_uris: List of key event URIs.
            include_proteins: Whether to include protein data.

        Returns:
            QueryResult object.
        """
        try:
            formatted_uris = " ".join([f"<{uri}>" for uri in ke_uris])
            query = self._aop_query_service.build_gene_sparql_query(
                formatted_uris, include_proteins
            )
            results = self._aop_query_service.execute_sparql_query(query)
            return QueryResult(data=results, query=query, success=True)
        except QueryServiceError as e:
            return QueryResult(data={}, query="", success=False, error=str(e))

    def _process_gene_query_results(
        self, sparql_data: dict[str, Any], include_proteins: bool = True
    ) -> None:
        """Process gene query results.

        Args:
            sparql_data: SPARQL query results.
            include_proteins: Whether proteins were included.
        """
        bindings = sparql_data.get("results", {}).get("bindings", [])
        associations = self._assoc_processor.process_gene_associations(bindings, include_proteins)

        for assoc in associations:
            self.network.add_gene_association(assoc)

    def _execute_compound_query(self, aop_uris: list[str]) -> QueryResult:
        """Execute compound association query.

        Args:
            aop_uris: List of AOP URIs.

        Returns:
            QueryResult object.
        """
        try:
            formatted_uris = " ".join([f"<https://identifiers.org/aop/{uri}>" for uri in aop_uris])
            query = self._aop_query_service.build_compound_sparql_query(formatted_uris)
            results = self._aop_query_service.execute_sparql_query(query)
            return QueryResult(data=results, query=query, success=True)
        except QueryServiceError as e:
            return QueryResult(data={}, query="", success=False, error=str(e))

    def _execute_gene_expression_query(
        self,
        confidence_level: int = 50,
    ) -> tuple[AOPNetwork, str]:
        """Execute gene expression query.

        Args:
            confidence_level: Minimum confidence level.

        Returns:
            Tuple of AOPNetwork and query string.
        """
        try:
            # Get gene and organ IDs from current network
            gene_ids = self.network.get_gene_ids()
            organ_ids = self.network.get_organ_ids()

            # Format for SPARQL query
            formatted_gene_ids = [f'"{eid}"' for eid in gene_ids if eid]
            formatted_organ_ids = [f'"{oid}"' for oid in organ_ids if oid]

            # Build and execute query
            query = self._bgee_query_service.build_gene_expressions_query(
                formatted_gene_ids, formatted_organ_ids, confidence_level
            )
            results = self._bgee_query_service.execute_sparql_query(query)

            # Process results into associations
            gene_expression_results = results.get("results", {}).get("bindings", [])
            for result in gene_expression_results:
                try:
                    gene_id = result.get("gene_id", {}).get("value", "")
                    if not gene_id:
                        continue

                    association = GeneExpressionAssociation(
                        gene_id=gene_id,
                        anatomical_id=result.get("anatomical_entity_id", {}).get("value", ""),
                        anatomical_name=result.get("anatomical_entity_name", {}).get("value", ""),
                        expression_level=result.get("expression_level", {}).get("value", ""),
                        confidence_id=result.get("confidence_level_id", {}).get("value", ""),
                        confidence_level_name=result.get("confidence_level_name", {}).get(
                            "value", ""
                        ),
                        developmental_id=result.get("developmental_stage_id", {}).get("value", ""),
                        developmental_stage_name=result.get("developmental_stage_name", {}).get(
                            "value", ""
                        ),
                        expr=result.get("expr", {}).get("value", ""),
                    )
                    self.network.add_gene_expression_association(association)
                except QueryServiceError as e:
                    logger.warning("Failed to process gene expression result: %s", e)
                    continue

            return self.network, query
        except QueryServiceError as e:
            logger.error("Failed to execute gene expression query: %s", e)
            return self.network, "# Gene expression query failed"

    def _execute_organ_query(self, ke_uris: list[str]) -> QueryResult:
        """Execute organ association query.

        Args:
            ke_uris: List of key event URIs.

        Returns:
            QueryResult object.
        """
        try:
            formatted_uris = " ".join([f"<{uri}>" for uri in ke_uris])
            query = self._aop_query_service.build_organ_sparql_query(formatted_uris)
            results = self._aop_query_service.execute_sparql_query(query)
            return QueryResult(data=results, query=query, success=True)
        except QueryServiceError as e:
            return QueryResult(data={}, query="", success=False, error=str(e))

    def _execute_component_query(self, ke_uris: list[str], go_only: bool = False) -> QueryResult:
        """Execute component association query.

        Args:
            ke_uris: List of key event URIs.
            go_only: Whether to filter for GO only.

        Returns:
            QueryResult object.
        """
        try:
            formatted_uris = " ".join([f"<{uri}>" for uri in ke_uris])
            query = self._aop_query_service.build_components_sparql_query(go_only, formatted_uris)
            results = self._aop_query_service.execute_sparql_query(query)
            return QueryResult(data=results, query=query, success=True)
        except QueryServiceError as e:
            return QueryResult(data={}, query="", success=False, error=str(e))

    def _execute_biological_process_query(self, ke_uris: list[str]) -> QueryResult:
        """Execute biological process association query.

        Args:
            ke_uris: List of key event URIs.

        Returns:
            QueryResult object.
        """
        try:
            formatted_uris = " ".join([f"<{uri}>" for uri in ke_uris])
            query = self._aop_query_service.build_biological_process_sparql_query(formatted_uris)
            results = self._aop_query_service.execute_sparql_query(query)
            return QueryResult(data=results, query=query, success=True)
        except QueryServiceError as e:
            return QueryResult(data={}, query="", success=False, error=str(e))

    def _process_compound_query_results(self, sparql_data: dict[str, Any]) -> None:
        """Process compound query results.

        Args:
            sparql_data: SPARQL query results.
        """
        bindings = sparql_data.get("results", {}).get("bindings", [])
        associations = self._assoc_processor.process_compound_associations(bindings)

        for assoc in associations:
            self.network.add_compound_association(assoc)

    def _process_organ_query_results(self, sparql_data: dict[str, Any]) -> None:
        """Process organ query results.

        Args:
            sparql_data: SPARQL query results.
        """
        bindings = sparql_data.get("results", {}).get("bindings", [])
        associations = self._assoc_processor.process_organ_associations(bindings)

        for assoc in associations:
            self.network.add_organ_association(assoc)

    def _process_component_query_results(self, sparql_data: dict[str, Any]) -> None:
        """Process component query results.

        Args:
            sparql_data: SPARQL query results.
        """
        bindings = sparql_data.get("results", {}).get("bindings", [])
        associations = self._assoc_processor.process_component_associations(bindings)

        for assoc in associations:
            self.network.add_component_association(assoc)

    def _process_biological_process_query_results(self, sparql_data: dict[str, Any]) -> None:
        """Process biological process query results.

        Args:
            sparql_data: SPARQL query results.
        """
        bindings = sparql_data.get("results", {}).get("bindings", [])
        associations = self._assoc_processor.process_biological_process_associations(bindings)

        for assoc in associations:
            self.network.add_biological_process_association(assoc)

    def update_from_json(self, cytoscape_json: dict[str, Any]) -> AOPNetwork:
        """
        Update self.network from a cytoscape JSON coming from request data.

        Args:
            cytoscape_json: The Cytoscape JSON data containing elements.

        Returns:
            Updated AOPNetwork.
        """
        # Extract elements from the JSON
        elements = cytoscape_json.get("elements", [])
        if not elements:
            logger.warning("No elements found in cytoscape JSON")
            return self.network
        # Update the network using the from_cytoscape_elements method
        self.network.from_cytoscape_elements(elements)
        return self.network

    def _build_network(self) -> AOPNetwork:
        """Build and return the current network state.

        Returns:
            AOPNetwork object.
        """
        return self.network
