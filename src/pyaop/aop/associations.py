"""
Association classes for AOP relationships w/ biological entities.

This module defines association types for genes, components, compounds, gene
expressions and organs with their corresponding Key Events (KEs) and Adverse
Outcome Pathways (AOPs).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pyaop.aop.constants import EdgeType, NodeType
from pyaop.cytoscape.elements import CytoscapeEdge, CytoscapeNode

logger = logging.getLogger(__name__)


@dataclass
class BaseAssociation(ABC):
    """Abstract base class for all association types."""

    @abstractmethod
    def to_cytoscape_elements(self) -> list[dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges).

        Returns:
            List of dictionaries representing Cytoscape elements.
        """

    @classmethod
    @abstractmethod
    def from_cytoscape_elements(cls, elements: list[dict[str, Any]]) -> Sequence[BaseAssociation]:
        """Parse Cytoscape elements back into association objects.

        Args:
            elements: List of Cytoscape elements.

        Returns:
            List of association objects.
        """

    def get_nodes(self) -> list[CytoscapeNode]:
        """Extract nodes from cytoscape elements.

        Returns:
            List of CytoscapeNode objects.
        """
        elements = self.to_cytoscape_elements()
        nodes = []
        for element in elements:
            if element.get("group") != "edges" and "data" in element:
                data = element["data"]
                if "source" not in data and "target" not in data:
                    node = CytoscapeNode(
                        id=data.get("id", ""),
                        label=data.get("label", ""),
                        node_type=data.get("type", ""),
                        classes=element.get("classes", ""),
                        properties=data,
                    )
                    nodes.append(node)
        return nodes

    def get_edges(self) -> list[CytoscapeEdge]:
        """Extract edges from cytoscape elements.

        Returns:
            List of CytoscapeEdge objects.
        """
        elements = self.to_cytoscape_elements()
        edges = []
        for element in elements:
            if element.get("group") == "edges" or (
                "data" in element and "source" in element["data"]
            ):
                data = element["data"]
                if "source" in data and "target" in data:  # It's an edge
                    edge = CytoscapeEdge(
                        id=data.get("id", ""),
                        source=data.get("source", ""),
                        target=data.get("target", ""),
                        label=data.get("label", ""),
                        properties=data,
                    )
                    edges.append(edge)
        return edges

    @staticmethod
    def _collect_nodes_by_type(
        elements: list[dict[str, Any]], node_types: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Collect nodes of specific types from elements.

        Args:
            elements: List of Cytoscape elements.
            node_types: List of node types to collect.

        Returns:
            Dictionary of node IDs to node data.
        """
        nodes = {}
        for element in elements:
            if element.get("group") != "edges" and "data" in element:
                data = element["data"]
                if data.get("type") in node_types:
                    nodes[data.get("id")] = data
        return nodes

    @staticmethod
    def _collect_edges_by_type(
        elements: list[dict[str, Any]], edge_types: list[str]
    ) -> list[dict[str, Any]]:
        """Collect edges of specific types from elements.

        Args:
            elements: List of Cytoscape elements.
            edge_types: List of edge types to collect.

        Returns:
            List of edge data dictionaries.
        """
        edges = []
        for element in elements:
            if element.get("group") == "edges" or (
                "data" in element and "source" in element["data"]
            ):
                data = element["data"]
                if data.get("type") in edge_types:
                    edges.append(data)
        return edges

    @staticmethod
    def _is_ke_uri(uri: str) -> bool:
        """Check if URI is a Key Event URI.

        Args:
            uri: URI string.

        Returns:
            True if Key Event URI, False otherwise.
        """
        return uri.startswith("https://identifiers.org/aop.events/")


@dataclass
class GeneAssociation(BaseAssociation):
    """Represent gene associations with Key Events."""

    ke_uri: str
    gene_id: str
    protein_id: str | None = None

    def __post_init__(self) -> None:
        """Perform basic validation after initialization."""
        if not self.ke_uri or not self.gene_id:
            raise ValueError("KE URI and gene ID are required")

    def to_cytoscape_elements(self) -> list[dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges).

        Returns:
            List of dictionaries representing Cytoscape elements.
        """
        elements = []

        # Gene node
        gene_node_id = f"gene_{self.gene_id}"
        elements.append(
            {
                "data": {
                    "id": gene_node_id,
                    "label": self.gene_id,
                    "type": NodeType.GENE.value,
                    "gene_id": self.gene_id,
                },
                "classes": "gene-node",
            }
        )

        # Protein node and relationships (only if proteins are included)
        if self.protein_id and self.protein_id != "NA":
            protein_node_id = f"protein_{self.protein_id}"
            elements.append(
                {
                    "data": {
                        "id": protein_node_id,
                        "label": self.protein_id,
                        "type": NodeType.PROTEIN.value,
                        "protein_id": self.protein_id,
                    },
                    "classes": "protein-node",
                }
            )

            # Translates to edge
            elements.append(
                {
                    "data": {
                        "id": f"{gene_node_id}_{protein_node_id}",
                        "source": gene_node_id,
                        "target": protein_node_id,
                        "label": "translates to",
                        "type": EdgeType.TRANSLATES_TO.value,
                    }
                }
            )

            # Part of edge (protein to KE)
            elements.append(
                {
                    "data": {
                        "id": f"{protein_node_id}_{self.ke_uri}",
                        "source": protein_node_id,
                        "target": self.ke_uri,
                        "label": "part of",
                        "type": EdgeType.PART_OF.value,
                    }
                }
            )
        else:
            # Direct gene to KE connection when no protein is included
            elements.append(
                {
                    "data": {
                        "id": f"{gene_node_id}_{self.ke_uri}",
                        "source": gene_node_id,
                        "target": self.ke_uri,
                        "label": "part of",
                        "type": EdgeType.PART_OF.value,
                    }
                }
            )

        return elements

    @classmethod
    def from_cytoscape_elements(cls, elements: list[dict[str, Any]]) -> Sequence[BaseAssociation]:
        """Parse Cytoscape elements back into GeneAssociation objects.

        Args:
            elements: List of Cytoscape elements.

        Returns:
            List of GeneAssociation objects.
        """
        associations = []

        # Collect relevant nodes
        gene_nodes = cls._collect_nodes_by_type(elements, [NodeType.GENE.value])
        protein_nodes = cls._collect_nodes_by_type(elements, [NodeType.PROTEIN.value])

        # Collect part_of edges
        part_of_edges = cls._collect_edges_by_type(elements, [EdgeType.PART_OF.value])
        translates_to_edges = cls._collect_edges_by_type(elements, [EdgeType.TRANSLATES_TO.value])

        # Build gene->protein mapping
        gene_to_protein = {}
        for edge in translates_to_edges:
            source_id = edge.get("source", "")
            target_id = edge.get("target", "")
            if source_id in gene_nodes and target_id in protein_nodes:
                gene_id = gene_nodes[source_id].get(
                    "gene_id", gene_nodes[source_id].get("label", "")
                )
                protein_id = protein_nodes[target_id].get(
                    "protein_id", protein_nodes[target_id].get("label", "")
                )
                gene_to_protein[gene_id] = protein_id

        # Process part_of edges
        for edge in part_of_edges:
            source_id = edge.get("source", "")
            target_uri = edge.get("target", "")

            if cls._is_ke_uri(target_uri):
                # Direct gene -> KE
                if source_id in gene_nodes:
                    gene_id = gene_nodes[source_id].get(
                        "gene_id", gene_nodes[source_id].get("label", "")
                    )
                    associations.append(cls(ke_uri=target_uri, gene_id=gene_id, protein_id=None))

                # Protein -> KE (find corresponding gene)
                elif source_id in protein_nodes:
                    protein_id = protein_nodes[source_id].get(
                        "protein_id", protein_nodes[source_id].get("label", "")
                    )
                    # Find gene that translates to this protein
                    gene_id = next((g for g, p in gene_to_protein.items() if p == protein_id), None)
                    if gene_id:
                        associations.append(
                            cls(ke_uri=target_uri, gene_id=gene_id, protein_id=protein_id)
                        )

        return associations


@dataclass
class ComponentAssociation(BaseAssociation):
    """Represent component associations with KEs."""

    ke_uri: str
    ke_name: str
    process: str
    process_name: str
    object: str
    object_name: str
    action: str
    object_type: str

    def __post_init__(self) -> None:
        """Perform basic validation after initialization."""
        if not self.ke_uri or not self.process:
            raise ValueError("KE URI and process are required")

    def to_cytoscape_elements(self) -> list[dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges).

        Returns:
            List of dictionaries representing Cytoscape elements.
        """
        if not self.process:  # DROP components with empty process IRI
            return []
        ke = "aop.events_" + self.ke_uri.split("/")[-1]
        process = self.process.split("/")[-1] if "/" in self.process else self.process
        object_n = self.object.split("/")[-1] if "/" in self.object else self.object
        elements = []
        process_node_id = f"process_{process}"

        elements.append(
            {
                "data": {
                    "id": process_node_id,
                    "label": self.process_name,
                    "type": NodeType.COMP_PROC.value,
                    "process_iri": self.process,
                    "process_name": self.process_name,
                    "process_id": process,
                },
                "classes": NodeType.COMP_PROC.value,
            }
        )

        # Determine edge label
        edge_label = (
            self.action
            if self.action in EdgeType.get_component_actions()
            else EdgeType.HAS_PROCESS.value
        )
        edge_type = EdgeType.HAS_PROCESS.value

        # KE -> Process edge (action)
        elements.append(
            {
                "data": {
                    "id": f"{ke}_{process_node_id}",
                    "source": self.ke_uri,
                    "target": process_node_id,
                    "label": edge_label,
                    "type": edge_type,
                }
            }
        )

        if self.object:
            object_node_id = f"object_{object_n}"

            # Determine the type based on object_type or object_iri
            # Hacky patch for misassigned types in AOP WIKI RDF
            if self.object_type == "http://aopkb.org/aop_ontology#OrganContext" or any(
                substring in object_n for substring in ["FMA", "UBERON"]
            ):
                object_node_type = NodeType.ORGAN.value
                obj_cls = f"{NodeType.ORGAN.value} {NodeType.COMP_OBJ.value}"
            elif (
                "CellTypeContext" in self.object_type
                or any(substring in object_n for substring in ["CL", "EFO"])
                or self.object_name in ["cell", "mitochondrion"]
            ):
                object_node_type = NodeType.CELL.value
                obj_cls = f"{NodeType.CELL.value} {NodeType.COMP_OBJ.value}"
            elif self.object.endswith("PATO_0001241") or any(
                substring in object_n for substring in ["PR"]
            ):
                object_node_type = NodeType.PROTEIN.value
                obj_cls = f"{NodeType.PROTEIN.value} {NodeType.COMP_OBJ.value}"
            elif any(substring in object_n for substring in ["GO"]):
                object_node_type = NodeType.CELL_COMP.value
                obj_cls = f"{NodeType.CELL_COMP.value} {NodeType.COMP_OBJ.value}"
            else:
                # Default to component object type
                object_node_type = NodeType.COMP_OBJ.value
                obj_cls = f"{NodeType.COMP_OBJ.value}"

            elements.append(
                {
                    "data": {
                        "id": object_node_id,
                        "label": self.object_name,
                        "type": object_node_type,
                        "object_iri": self.object,
                        "object_name": self.object_name,
                        "object_id": object_n,
                    },
                    "classes": obj_cls,
                }
            )

            # NEW: KE -> Object edge instead of Process -> Object
            elements.append(
                {
                    "data": {
                        "id": f"{ke}_{object_node_id}",
                        "source": self.ke_uri,
                        "target": object_node_id,
                        "label": EdgeType.INVOLVES.value,
                        "type": EdgeType.INVOLVES.value,
                    }
                }
            )
        return elements

    def to_table_entry(self) -> dict[str, str]:
        """Convert to component table entry format.

        Returns:
            Dictionary representing a component table entry.
        """
        # Extract KE ID from URI
        ke_id = self.ke_uri.split("/")[-1] if "/" in self.ke_uri else self.ke_uri
        # Extract process ID from URI
        process_id = self.process.split("/")[-1] if "/" in self.process else self.process

        # Extract object ID from URI
        object_id = self.object.split("/")[-1] if "/" in self.object else self.object

        return {
            "ke_id": ke_id,
            "ke_uri": self.ke_uri,
            "ke_label": self.ke_name if self.ke_name else "N/A",
            "process_id": process_id,
            "process_name": self.process_name,
            "process_iri": self.process,
            "object_id": object_id if self.object else "N/A",
            "object_name": self.object_name if self.object_name else "N/A",
            "object_iri": self.object if self.object else "N/A",
            "action": self.action if self.action else "N/A",
            "node_id": f"process_{process_id}",
        }

    @classmethod
    def from_cytoscape_elements(cls, elements: list[dict[str, Any]]) -> Sequence[BaseAssociation]:
        """Parse Cytoscape elements back into ComponentAssociation objects.

        Args:
            elements: List of Cytoscape elements.

        Returns:
            List of ComponentAssociation objects.
        """
        associations = []

        # Collect relevant nodes
        process_nodes = cls._collect_nodes_by_type(elements, [NodeType.COMP_PROC.value])
        object_node_types = [
            NodeType.COMP_OBJ.value,
            NodeType.ORGAN.value,
            NodeType.CELL.value,
            NodeType.PROTEIN.value,
            NodeType.CELL_COMP.value,
        ]
        object_nodes = cls._collect_nodes_by_type(elements, object_node_types)

        # Collect relevant edges
        has_process_edges = cls._collect_edges_by_type(elements, [EdgeType.HAS_PROCESS.value])
        involves_edges = cls._collect_edges_by_type(elements, [EdgeType.INVOLVES.value])

        # Build KE -> object mapping
        ke_to_object = {}
        for edge in involves_edges:
            source_uri = edge.get("source", "")
            target_id = edge.get("target", "")
            if cls._is_ke_uri(source_uri) and target_id in object_nodes:
                ke_to_object[source_uri] = object_nodes[target_id]

        # Process has_process edges
        for edge in has_process_edges:
            source_uri = edge.get("source", "")
            target_id = edge.get("target", "")

            if cls._is_ke_uri(source_uri) and target_id in process_nodes:
                process_data = process_nodes[target_id]
                object_data = ke_to_object.get(source_uri, {})

                associations.append(
                    cls(
                        ke_uri=source_uri,
                        ke_name="",
                        process=process_data.get("process_iri", ""),
                        process_name=process_data.get(
                            "process_name", process_data.get("label", "")
                        ),
                        object=object_data.get("object_iri", ""),
                        object_name=object_data.get("object_name", object_data.get("label", "")),
                        action=edge.get("label", ""),
                        object_type=object_data.get("type", ""),
                    )
                )

        return associations


@dataclass
class CompoundAssociation(BaseAssociation):
    """Represent compound associations with AOPs."""

    aop_uri: str
    mie_uri: str
    chemical_uri: str
    chemical_label: str
    pubchem_compound: str
    compound_name: str
    cas_id: str | None = None

    def __post_init__(self) -> None:
        """Perform basic validation after initialization."""
        if not self.aop_uri or not self.chemical_uri:
            raise ValueError("AOP URI and chemical URI are required")

    def to_cytoscape_elements(self) -> list[dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges).

        Returns:
            List of dictionaries representing Cytoscape elements.
        """
        elements = []

        # Extract identifiers
        pubchem_id = (
            self.pubchem_compound.split("/")[-1]
            if "/" in self.pubchem_compound
            else self.pubchem_compound
        )
        chemical_node_id = f"chemical_{pubchem_id}"

        # Chemical node - include aop_uri and chemical_uri for back-parsing
        elements.append(
            {
                "data": {
                    "id": chemical_node_id,
                    "label": self.compound_name or self.chemical_label,
                    "type": NodeType.CHEMICAL.value,
                    "pubchem_id": pubchem_id,
                    "cas_id": self.cas_id,
                    "chemical_label": self.chemical_label,
                    "compound_name": self.compound_name,
                    "pubchem_compound": self.pubchem_compound,
                    "aop_uri": self.aop_uri,
                    "chemical_uri": self.chemical_uri,
                },
                "classes": "chemical-node",
            }
        )

        # Edge from chemical to MIE
        if self.mie_uri:
            elements.append(
                {
                    "data": {
                        "id": f"{chemical_node_id}_{self.mie_uri}",
                        "source": chemical_node_id,
                        "target": self.mie_uri,
                        "label": EdgeType.IS_STRESSOR_OF.value,
                        "type": EdgeType.IS_STRESSOR_OF.value,
                    }
                }
            )

        return elements

    def to_table_entry(self) -> dict[str, str]:
        """Convert to compound table entry format.

        Returns:
            Dictionary representing a compound table entry.
        """
        # Extract PubChem ID from compound URI
        pubchem_id = (
            self.pubchem_compound.split("/")[-1]
            if "/" in self.pubchem_compound
            else self.pubchem_compound
        )

        # Extract AOP ID from URI
        aop_id = self.aop_uri.split("/")[-1] if "/" in self.aop_uri else self.aop_uri

        return {
            "compound_name": self.compound_name or self.chemical_label,
            "chemical_label": self.chemical_label,
            "pubchem_id": pubchem_id,
            "pubchem_compound": self.pubchem_compound,
            "cas_id": self.cas_id if self.cas_id else "N/A",
            "aop_id": f"AOP:{aop_id}",
            "aop_uri": self.aop_uri,
            "mie_uri": self.mie_uri,
            "chemical_uri": self.chemical_uri,
        }

    @classmethod
    def from_cytoscape_elements(cls, elements: list[dict[str, Any]]) -> Sequence[BaseAssociation]:
        """Parse Cytoscape elements back into CompoundAssociation objects.

        Args:
            elements: List of Cytoscape elements.

        Returns:
            List of CompoundAssociation objects.
        """
        associations = []

        # Collect chemical nodes and stressor edges
        chemical_nodes = cls._collect_nodes_by_type(elements, [NodeType.CHEMICAL.value])
        stressor_edges = cls._collect_edges_by_type(elements, [EdgeType.IS_STRESSOR_OF.value])

        # Process stressor relationships
        for edge in stressor_edges:
            source_id = edge.get("source", "")
            target_uri = edge.get("target", "")

            if source_id in chemical_nodes and cls._is_ke_uri(target_uri):
                chem_data = chemical_nodes[source_id]

                # Get the required URIs from the chemical node data
                aop_uri = chem_data.get("aop_uri", "")
                chemical_uri = chem_data.get("chemical_uri", "")

                # Only create association if we have the required aop_uri
                if aop_uri:  # Only create if we have AOP URI
                    associations.append(
                        cls(
                            aop_uri=aop_uri,
                            mie_uri=target_uri,
                            chemical_uri=chemical_uri,
                            chemical_label=chem_data.get(
                                "chemical_label", chem_data.get("label", "")
                            ),
                            pubchem_compound=chem_data.get("pubchem_compound", ""),
                            compound_name=chem_data.get(
                                "compound_name", chem_data.get("label", "")
                            ),
                            cas_id=chem_data.get("cas_id"),
                        )
                    )

        return associations


@dataclass
class GeneExpressionAssociation(BaseAssociation):
    """Represent gene expression associations with organs."""

    gene_id: str
    anatomical_id: str
    anatomical_name: str
    expression_level: str
    confidence_id: str = ""
    confidence_level_name: str = ""
    developmental_id: str = ""
    developmental_stage_name: str = ""
    expr: str = ""

    def __post_init__(self) -> None:
        """Perform basic validation after initialization."""
        if not self.gene_id or not self.anatomical_id:
            raise ValueError("Gene ID and anatomical ID are required")

    def to_cytoscape_elements(self) -> list[dict[str, Any]]:
        """Convert to Cytoscape elements (nodes and edges).

        Returns:
            List of dictionaries representing Cytoscape elements.
        """
        elements = []

        # Organ node
        organ_node_id = f"{self.anatomical_id}"
        elements.append(
            {
                "data": {
                    "id": organ_node_id,
                    "label": self.anatomical_name,
                    "type": NodeType.ORGAN.value,
                    "anatomical_id": self.anatomical_id,
                    "anatomical_name": self.anatomical_name,
                },
                "classes": "organ-node",
            }
        )

        # Expression edge from gene to organ
        gene_node_id = f"gene_{self.gene_id}"
        expression_edge_id = f"{gene_node_id}_{organ_node_id}_expression"
        elements.append(
            {
                "data": {
                    "id": expression_edge_id,
                    "source": gene_node_id,
                    "target": organ_node_id,
                    "label": f"expressed in ({self.expression_level})",
                    "type": EdgeType.EXPRESSION_IN.value,
                    "expression_level": self.expression_level,
                    "confidence_level": self.confidence_level_name,
                    "developmental_stage": self.developmental_stage_name,
                }
            }
        )

        return elements

    def to_table_entry(self) -> dict[str, str]:
        """Convert to gene expression table entry format.

        Returns:
            Dictionary representing a gene expression table entry.
        """
        return {
            "gene_id": self.gene_id,
            "organ": self.anatomical_name,
            "expression_level": self.expression_level,
            "confidence": self.confidence_level_name,
            "developmental_stage": self.developmental_stage_name,
        }

    @classmethod
    def from_cytoscape_elements(cls, elements: list[dict[str, Any]]) -> Sequence[BaseAssociation]:
        """Parse Cytoscape elements to GeneExpressionAssociation..

        Args:
            elements: List of Cytoscape elements.
        Returns:
            List of GeneExpressionAssociation objects.
        """
        associations = []

        # Collect nodes and edges
        gene_nodes = cls._collect_nodes_by_type(elements, [NodeType.GENE.value])
        organ_nodes = cls._collect_nodes_by_type(elements, [NodeType.ORGAN.value])
        expression_edges = cls._collect_edges_by_type(elements, [EdgeType.EXPRESSION_IN.value])

        # Process expression relationships
        for edge in expression_edges:
            source_id = edge.get("source", "")
            target_id = edge.get("target", "")

            if source_id in gene_nodes and target_id in organ_nodes:
                gene_data = gene_nodes[source_id]
                organ_data = organ_nodes[target_id]

                associations.append(
                    cls(
                        gene_id=gene_data.get("gene_id", gene_data.get("label", "")),
                        anatomical_id=organ_data.get("anatomical_id", organ_data.get("id", "")),
                        anatomical_name=organ_data.get(
                            "anatomical_name", organ_data.get("label", "")
                        ),
                        expression_level=edge.get("expression_level", ""),
                        confidence_level_name=edge.get("confidence_level", ""),
                        developmental_stage_name=edge.get("developmental_stage", ""),
                    )
                )

        return associations


@dataclass
class OrganAssociation(BaseAssociation):
    """Represent an organ-key event association."""

    ke_uri: str
    organ_data: CytoscapeNode
    edge_data: CytoscapeEdge

    def __post_init__(self) -> None:
        """Perform basic validation after initialization."""
        if not self.ke_uri:
            raise ValueError("KE URI is required")

    def to_cytoscape_elements(self) -> list[dict[str, Any]]:
        """Convert to Cytoscape elements.

        Returns:
            List of dictionaries representing Cytoscape elements.
        """
        return [{"data": self.organ_data.to_dict()}, {"data": self.edge_data.to_dict()}]

    @classmethod
    def from_cytoscape_elements(cls, elements: list[dict[str, Any]]) -> Sequence[BaseAssociation]:
        """Parse Cytoscape elements back into OrganAssociation objects.

        Args:
            elements: List of Cytoscape elements.

        Returns:
            List of OrganAssociation objects.
        """
        associations = []

        # Collect nodes and edges
        organ_nodes = cls._collect_nodes_by_type(elements, [NodeType.ORGAN.value])
        associated_edges = cls._collect_edges_by_type(elements, [EdgeType.ASSOCIATED_WITH.value])

        # Process organ-KE associations
        for edge in associated_edges:
            source_uri = edge.get("source", "")
            target_id = edge.get("target", "")

            if cls._is_ke_uri(source_uri) and target_id in organ_nodes:
                organ_data = organ_nodes[target_id]

                # Find original element for classes
                organ_element = next(
                    (e for e in elements if e.get("data", {}).get("id") == target_id), {}
                )

                organ_node = CytoscapeNode(
                    id=organ_data.get("id", ""),
                    label=organ_data.get("label", ""),
                    node_type=organ_data.get("type", ""),
                    classes=organ_element.get("classes", ""),
                    properties=organ_data,
                )

                edge_obj = CytoscapeEdge(
                    id=edge.get("id", ""),
                    source=edge.get("source", ""),
                    target=edge.get("target", ""),
                    label=edge.get("label", ""),
                    properties=edge,
                )

                associations.append(
                    cls(ke_uri=source_uri, organ_data=organ_node, edge_data=edge_obj)
                )

        return associations
