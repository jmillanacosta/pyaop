"""
Core model classes for representing Adverse Outcome Pathway (AOP) networks.

Includes the main container for complete AOP network data (AOPNetwork).
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from pyaop.aop.associations import (
    BaseAssociation,
    ComponentAssociation,
    CompoundAssociation,
    GeneAssociation,
    GeneExpressionAssociation,
    OrganAssociation,
)
from pyaop.aop.constants import EdgeType, NodeType
from pyaop.cytoscape.elements import CytoscapeEdge, CytoscapeNode
from pyaop.cytoscape.parser import CytoscapeNetworkParser
from pyaop.cytoscape.styles import AOPStyleManager

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class AOPInfo:
    """Represents AOP metadata - immutable for safety"""

    aop_id: str
    title: str
    uri: str

    def __post_init__(self):
        """Basic validation"""
        if not self.aop_id or not self.uri:
            raise ValueError("AOP ID and URI are required")

    def __str__(self) -> str:
        return f"AOP(id:{self.aop_id}, title:'{self.title}', URI:{self.uri})"

    @classmethod
    def from_cytoscape_elements(cls, elements: list[dict[str, Any]]) -> list["AOPInfo"]:
        """Parse AOP information from Cytoscape elements"""
        aop_infos = {}  # Use dict to avoid duplicates
        
        for element in elements:
            if element.get("group") != "edges" and "data" in element:
                data = element["data"]
                
                # Extract AOP information from node data
                aop_uris = data.get("aop_uris", [])
                aop_titles = data.get("aop_titles", [])
                
                # Handle single values as well as lists
                if not isinstance(aop_uris, list):
                    aop_uris = [aop_uris] if aop_uris else []
                if not isinstance(aop_titles, list):
                    aop_titles = [aop_titles] if aop_titles else []
                
                # Process each AOP URI/title pair
                for aop_uri, aop_title in zip(aop_uris, aop_titles):
                    if aop_uri and aop_title:
                        # Extract AOP ID from URI
                        aop_id = aop_uri.split("/")[-1] if "/" in aop_uri else aop_uri
                        
                        # Create AOPInfo if not already exists
                        if aop_id not in aop_infos:
                            try:
                                aop_info = cls(aop_id=aop_id, title=aop_title, uri=aop_uri)
                                aop_infos[aop_id] = aop_info
                            except ValueError as e:
                                logger.warning(f"Failed to create AOPInfo: {e}")
        
        return list(aop_infos.values())

@dataclass
class AOPKeyEvent:
    """Represents a Key Event in an AOP"""

    ke_id: str
    uri: str
    title: str
    ke_type: NodeType
    associated_aops: list[AOPInfo] = field(default_factory=list)

    def __post_init__(self):
        """Basic validation"""
        if not self.ke_id or not self.uri:
            raise ValueError("Key Event ID and URI are required")
        if not self.title:
            self.title = self.ke_id  # Use ID as fallback

    def __str__(self) -> str:
        return f"{self.ke_type.value}:{self.ke_id}"

    def add_aop(self, aop_info: AOPInfo) -> bool:
        """Add AOP association. Returns True if added, False if exists"""
        if aop_info not in self.associated_aops:
            self.associated_aops.append(aop_info)
            return True
        return False

    def get_aop_ids(self) -> list[str]:
        """Get list of AOP IDs for this key event"""
        return [aop.aop_id for aop in self.associated_aops]

    def to_cytoscape_data(self) -> dict[str, Any]:
        """Convert to Cytoscape node data"""
        return {
            "id": self.uri,
            "label": self.title,
            "type": self.ke_type.value,
            "is_mie": self.ke_type == NodeType.MIE,
            "is_ao": self.ke_type == NodeType.AO,
            "aop_uris": [aop.uri for aop in self.associated_aops],
            "aop_titles": [aop.title for aop in self.associated_aops],
        }


@dataclass
class KeyEventRelationship:
    """Represents a relationship between two Key Events"""

    ker_id: str
    ker_uri: str
    upstream_ke: AOPKeyEvent
    downstream_ke: AOPKeyEvent

    def __post_init__(self):
        """Basic validation"""
        if not self.ker_id or not self.ker_uri:
            raise ValueError("KER ID and URI are required")
        if self.upstream_ke.uri == self.downstream_ke.uri:
            raise ValueError("Upstream and downstream KEs cannot be the same")

    def __str__(self) -> str:
        return f"KER:{self.ker_id}"

    def to_cytoscape_data(self) -> dict[str, Any]:
        """Convert to Cytoscape edge data"""
        return {
            "id": f"{self.upstream_ke.uri}_{self.downstream_ke.uri}",
            "source": self.upstream_ke.uri,
            "target": self.downstream_ke.uri,
            "curie": f"aop.relationships:{self.ker_id}",
            "ker_label": self.ker_id,
            "type": EdgeType.KER.value,
        }


class AOPNetwork:
    """Main AOP Network model representing a complete AOP query result"""

    def __init__(self):
        self.key_events: dict[str, AOPKeyEvent] = {}
        self.relationships: list[KeyEventRelationship] = []
        self.component_associations: list[ComponentAssociation] = []
        self.gene_associations: list[GeneAssociation] = []
        self.compound_associations: list[CompoundAssociation] = []
        self.organ_associations: list[OrganAssociation] = []
        self.aop_info: dict[str, AOPInfo] = {}
        self.node_list: list[CytoscapeNode] = []
        self.edge_list: list[CytoscapeEdge] = []
        self.gene_expression_associations: list[GeneExpressionAssociation] = []
        self.style_manager = AOPStyleManager()

    def __str__(self) -> str:
        return (f"AOPNetwork({len(self.key_events)} KEs, "
                f"{len(self.relationships)} KERs, {len(self.aop_info)} AOPs)")

    def from_cytoscape_elements(self, elements: list[dict[str, Any]]) -> None:
        """Populate AOPNetwork from Cytoscape elements - parse back into full data model"""
        # Parse all elements using the parser
        parser = CytoscapeNetworkParser(elements)

        # Add ALL nodes to the network
        self.node_list = parser.nodes

        # Add ALL edges to the network
        self.edge_list = parser.edges

        # Store original elements for position and style extraction
        self._original_elements = elements

        # Parse back into data model associations
        self._parse_associations_from_elements(elements)
        
        # Parse AOPInfo, KeyEvents and relationships from elements
        self._parse_aop_info_from_elements(elements)
        self._parse_key_events_from_elements(elements)
        self._parse_relationships_from_elements(elements)

        logger.info(
            f"Populated AOPNetwork from {len(elements)} Cytoscape elements: "
            f"{len(self.node_list)} nodes, {len(self.edge_list)} edges, "
            f"{len(self.key_events)} KEs, {len(self.relationships)} KERs, "
            f"{len(self.aop_info)} AOPs"
        )

    def _parse_associations_from_elements(self, elements: list[dict[str, Any]]) -> None:
        """Parse all association types from Cytoscape elements"""
        # Define association types and their corresponding lists
        association_types = [
            (GeneAssociation, self.gene_associations),
            (ComponentAssociation, self.component_associations),
            (CompoundAssociation, self.compound_associations),
            (GeneExpressionAssociation, self.gene_expression_associations),
            (OrganAssociation, self.organ_associations),
        ]
        
        # Parse each association type
        for assoc_class, assoc_list in association_types:
            parsed_associations = assoc_class.from_cytoscape_elements(elements)
            assoc_list.extend(parsed_associations)

    def _parse_aop_info_from_elements(self, elements: list[dict[str, Any]]) -> None:
        """Parse AOP information from Cytoscape elements using AOPInfo parser"""
        # Use the AOPInfo class parser
        aop_infos = AOPInfo.from_cytoscape_elements(elements)
        
        # Add to network's aop_info dict
        for aop_info in aop_infos:
            if aop_info.aop_id not in self.aop_info:
                self.aop_info[aop_info.aop_id] = aop_info
        
        logger.debug(f"Parsed {len(aop_infos)} AOP info objects from elements")

    def _parse_key_events_from_elements(self, elements: list[dict[str, Any]]) -> None:
        """Parse Key Events from Cytoscape elements"""
        for element in elements:
            if element.get("group") != "edges" and "data" in element:
                data = element["data"]
                node_type = data.get("type", "")
                
                # Check if it's a Key Event node
                if node_type in [NodeType.MIE.value, NodeType.AO.value, NodeType.KE.value]:
                    ke_uri = data.get("id", "")
                    if ke_uri and ke_uri.startswith("https://identifiers.org/aop.events/"):
                        ke_id = ke_uri.split("/")[-1]
                        ke_title = data.get("label", "")
                        
                        # Determine KE type
                        if node_type == NodeType.MIE.value:
                            ke_type = NodeType.MIE
                        elif node_type == NodeType.AO.value:
                            ke_type = NodeType.AO
                        else:
                            ke_type = NodeType.KE
                        
                        # Create Key Event
                        key_event = AOPKeyEvent(
                            ke_id=ke_id,
                            uri=ke_uri,
                            title=ke_title,
                            ke_type=ke_type
                        )
                        
                        # Add associated AOPs
                        aop_uris = data.get("aop_uris", [])
                        aop_titles = data.get("aop_titles", [])
                        for aop_uri, aop_title in zip(aop_uris, aop_titles):
                            if aop_uri and aop_title:
                                aop_id = aop_uri.split("/")[-1] if "/" in aop_uri else aop_uri
                                aop_info = AOPInfo(aop_id=aop_id, title=aop_title, uri=aop_uri)
                                key_event.add_aop(aop_info)
                        
                        self.key_events[ke_uri] = key_event

    def _parse_relationships_from_elements(self, elements: list[dict[str, Any]]) -> None:
        """Parse Key Event Relationships from Cytoscape elements"""
        for element in elements:
            if element.get("group") == "edges" or ("data" in element and "source" in element["data"]):
                data = element["data"]
                
                # Check if it's a KER edge
                if data.get("type") == EdgeType.KER.value and data.get("ker_label"):
                    source_uri = data.get("source", "")
                    target_uri = data.get("target", "")
                    ker_label = data.get("ker_label", "")
                    curie = data.get("curie", "")
                    
                    # Extract KER ID from curie or ker_label
                    ker_id = ker_label
                    if curie and ":" in curie:
                        ker_id = curie.split(":")[-1]
                    
                    # Create KER URI from curie or generate one
                    ker_uri = f"https://identifiers.org/aop.relationships/{ker_id}"
                    
                    # Only create relationship if both KEs exist
                    if source_uri in self.key_events and target_uri in self.key_events:
                        relationship = KeyEventRelationship(
                            ker_id=ker_id,
                            ker_uri=ker_uri,
                            upstream_ke=self.key_events[source_uri],
                            downstream_ke=self.key_events[target_uri]
                        )
                        self.relationships.append(relationship)

    def add_key_event(self, key_event: AOPKeyEvent):
        """Add a key event to the network"""
        self.key_events[key_event.uri] = key_event

        # Register AOP info
        for aop in key_event.associated_aops:
            if aop.aop_id not in self.aop_info:
                self.aop_info[aop.aop_id] = aop

    def add_relationship(self, relationship: KeyEventRelationship):
        """Add a key event relationship"""
        # Ensure both KEs are in the network
        self.add_key_event(relationship.upstream_ke)
        self.add_key_event(relationship.downstream_ke)
        self.relationships.append(relationship)

    def add_gene_association(self, association: GeneAssociation):
        """Add a gene association"""
        self.gene_associations.append(association)
        self._update_nodes_and_edges(association)

    def add_gene_expression_association(self, association: GeneExpressionAssociation):
        """Add a gene expression association"""
        self.gene_expression_associations.append(association)
        self._update_nodes_and_edges(association)

    def add_compound_association(self, association: CompoundAssociation):
        """Add a compound association"""
        self.compound_associations.append(association)
        self._update_nodes_and_edges(association)

    def add_component_association(self, association: ComponentAssociation):
        """Add a component association"""
        self.component_associations.append(association)
        self._update_nodes_and_edges(association)

    def add_organ_association(self, association: OrganAssociation):
        """Add an organ association"""
        self.organ_associations.append(association)
        self._update_nodes_and_edges(association)

    def _update_nodes_and_edges(self, association: BaseAssociation):
        """Update node_list and edge_list with nodes and edges from association"""
        # Add nodes
        new_nodes = association.get_nodes()
        for node in new_nodes:
            # Avoid duplicates by checking node ID
            if not any(existing_node.id == node.id for existing_node in self.node_list):
                self.node_list.append(node)

        # Add edges
        new_edges = association.get_edges()
        for edge in new_edges:
            # Avoid duplicates by checking edge ID
            if not any(existing_edge.id == edge.id for existing_edge in self.edge_list):
                self.edge_list.append(edge)

    def get_genes_for_ke(self, ke_uri: str) -> list[GeneAssociation]:
        """Get all gene associations for a specific Key Event"""
        return [
            assoc for assoc in self.component_associations if assoc.ke_uri == ke_uri
        ]

    def get_compounds_for_aop(self, aop_uri: str) -> list[CompoundAssociation]:
        """Get all compound associations for a specific AOP"""
        return [
            assoc for assoc in self.compound_associations if assoc.aop_uri == aop_uri
        ]

    def get_ke_uris(self) -> list[str]:
        """Get all Key Event URIs in the network"""
        return list(self.key_events.keys())

    def get_aop_uris(self) -> list[str]:
        """Get all AOP URIs in the network"""
        return list(self.aop_info.keys())

    def get_gene_ids(self) -> list[str]:
        """Retrieve all Gene IDs from nodes in the network"""
        gene_ids = []

        # Check node_list for Gene nodes
        for node in self.node_list:
            if node.is_instance_of(NodeType.GENE):
                # Extract Gene ID from node properties or ID
                gene_id = node.properties.get("gene_id", "")
                if not gene_id:
                    # Try to extract from node ID if it starts with gene_
                    if node.id.startswith("gene_"):
                        gene_id = node.id.replace("gene_", "")
                    else:
                        gene_id = node.label

                if gene_id and gene_id not in gene_ids:
                    gene_ids.append(gene_id)

        # Also check gene_associations for backward compatibility
        for gene_assoc in self.gene_associations:
            if gene_assoc.gene_id and gene_assoc.gene_id not in gene_ids:
                gene_ids.append(gene_assoc.gene_id)

        return gene_ids

    def get_organ_ids(self) -> list[str]:
        """Retrieve all organ IDs/names from nodes in the network"""
        organ_ids = []

        # Check node_list for organ nodes
        for node in self.node_list:
            if node.is_instance_of(NodeType.ORGAN):
                # Use anatomical_name (organ name) rather than full URI
                organ_name = node.properties.get("anatomical_name", "")
                if not organ_name:
                    organ_name = node.label

                if organ_name and organ_name not in organ_ids:
                    organ_ids.append(organ_name)

        # Also check organ_associations for backward compatibility
        for organ_assoc in self.organ_associations:
            organ_node = organ_assoc.organ_data
            if organ_node and organ_node.is_instance_of(NodeType.ORGAN):
                # Use anatomical_name (organ name) rather than full URI
                organ_name = organ_node.properties.get(
                    "anatomical_name", organ_node.label
                )
                if organ_name and organ_name not in organ_ids:
                    organ_ids.append(organ_name)
        return organ_ids

    def to_cytoscape_elements(self, include_styles: bool = True) -> dict[str, Any]:
        """Convert entire network to Cytoscape format with optional styles"""
        elements = []

        # Add Key Event nodes
        for ke in self.key_events.values():
            elements.append({"data": ke.to_cytoscape_data()})

        # Add KER edges
        for relationship in self.relationships:
            elements.append({"data": relationship.to_cytoscape_data()})

        # Add gene associations
        for gene_assoc in self.gene_associations:
            elements.extend(gene_assoc.to_cytoscape_elements())

        # Add compound associations
        for compound_assoc in self.compound_associations:
            elements.extend(compound_assoc.to_cytoscape_elements())

        # Add component associations
        for comp_assoc in self.component_associations:
            elements.extend(comp_assoc.to_cytoscape_elements())

        # Add organ associations
        for organ_assoc in self.organ_associations:
            elements.extend(organ_assoc.to_cytoscape_elements())

        # Add gene expression associations
        for expr_assoc in self.gene_expression_associations:
            elements.extend(expr_assoc.to_cytoscape_elements())

        logger.info(f"Generated {len(elements)} Cytoscape elements")

        # Prepare response with elements
        result = {"elements": elements}

        # Add styles and layout if requested
        if include_styles:
            result["style"] = self.get_styles()
            result["layout"] = self.get_layout_config()

        return result

    def get_summary(self) -> dict[str, int]:
        """Get network summary statistics"""
        mie_count = sum(
            1 for ke in self.key_events.values() if ke.ke_type == NodeType.MIE
        )
        ao_count = sum(
            1 for ke in self.key_events.values() if ke.ke_type == NodeType.AO
        )
        ke_count = sum(
            1 for ke in self.key_events.values() if ke.ke_type == NodeType.KE
        )

        return {
            "total_key_events": len(self.key_events),
            "mie_count": mie_count,
            "ao_count": ao_count,
            "ke_count": ke_count,
            "ker_count": len(self.relationships),
            "gene_associations": len(self.gene_associations),
            "gene_expression_associations": len(self.gene_expression_associations),
            "compound_associations": len(self.compound_associations),
            "component_associations": len(self.component_associations),
            "organ_associations": len(self.organ_associations),
            "total_aops": len(self.aop_info),
        }

    def get_styles(self) -> list[dict[str, Any]]:
        """Get styles for the network"""
        if self.style_manager:
            return self.style_manager.get_styles()
        return []

    def get_layout_config(self) -> dict[str, Any]:
        """Get layout configuration for the network"""
        if self.style_manager:
            return self.style_manager.get_layout_config()
        return {"name": "breadthfirst"}
