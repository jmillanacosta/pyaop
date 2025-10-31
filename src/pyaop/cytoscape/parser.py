"""
Cytoscape JSON parser.

Parses a Cytoscape JSON as dictionary into the Cytoscape data model.
"""

import logging
from typing import Any

from pyaop.aop.constants import EdgeType, NodeType
from pyaop.cytoscape.elements import CytoscapeEdge, CytoscapeNode

logger = logging.getLogger(__name__)


class CytoscapeNetworkParser:
    """Parse Cytoscape network elements into structured data."""

    def __init__(self, elements: list[dict[str, Any]]):
        """Initialize the parser with elements.

        Args:
            elements: List of Cytoscape elements.
        """
        self.elements = elements
        self.nodes = self._parse_nodes()
        self.edges = self._parse_edges()
        logger.info(f"Parsed {len(self.nodes)} nodes and {len(self.edges)} edges")

    def _parse_nodes(self) -> list[CytoscapeNode]:
        """Parse all nodes from elements.

        Returns:
            List of CytoscapeNode objects.
        """
        nodes = []
        for element in self.elements:
            node = CytoscapeNode.from_cytoscape_element(element)
            if node:
                nodes.append(node)
        return nodes

    def _parse_edges(self) -> list[CytoscapeEdge]:
        """Parse all edges from elements.

        Returns:
            List of CytoscapeEdge objects.
        """
        edges = []
        for element in self.elements:
            edge = CytoscapeEdge.from_cytoscape_element(element)
            if edge:
                edges.append(edge)
        return edges

    def get_nodes_by_type(self, node_type: NodeType) -> list[CytoscapeNode]:
        """Get nodes of a specific type.

        Args:
            node_type: The NodeType to filter by.

        Returns:
            List of CytoscapeNode objects.
        """
        return [node for node in self.nodes if node.is_instance_of(node_type)]

    def get_edges_by_type(self, edge_type: EdgeType) -> list[CytoscapeEdge]:
        """Get edges of a specific type.

        Args:
            edge_type: The EdgeType to filter by.

        Returns:
            List of CytoscapeEdge objects.
        """
        return [edge for edge in self.edges if edge.is_instance_of(edge_type)]
