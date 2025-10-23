"""
Cytoscape graph elements.

Provides classes for representing and managing nodes and edges in Cytoscape format.
"""

import logging
from typing import Any, Optional

from pyaop.aop.constants import EdgeType, NodeType

logger = logging.getLogger(__name__)

# Global registries to track existing nodes
_existing_nodes: dict[str, "CytoscapeNode"] = {}
_existing_node_labels: dict[str, "CytoscapeNode"] = {}


class CytoscapeEdge:
    """Represents an edge in Cytoscape format"""

    def __init__(
        self,
        id: str,
        source: str,
        target: str,
        label: str,
        properties: dict[str, Any]
    ):
        """Initialize the edge"""
        self.id = id
        self.source = source
        self.target = target
        self.label = label
        self.properties = properties

    @classmethod
    def from_cytoscape_element(
        cls, element: dict[str, Any]
    ) -> Optional["CytoscapeEdge"]:
        """Create an edge from a Cytoscape element"""
        if element.get("group") != "edges":
            return None

        data = element.get("data", {})
        edge_id = data.get("id", "")
        source = data.get("source", "")
        target = data.get("target", "")

        if not source or not target:
            return None

        # Generate ID if not provided
        if not edge_id:
            edge_id = f"{source}_{target}"

        edge = cls(
            id=edge_id,
            source=source,
            target=target,
            label=data.get("label", ""),
            properties=data,
        )

        return edge

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for Cytoscape"""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "label": self.label,
            **self.properties,
        }

    def is_gene_relationship(self) -> bool:
        """Check if this is a gene-related relationship"""
        return self.label in ["translates to", "part of"]

    def merge_properties(self, other_properties: dict[str, Any]) -> None:
        """Merge additional properties into this edge"""
        self.properties.update(other_properties)

    def is_instance_of(self, label: EdgeType) -> bool:
        """Check if this node is an instance of the specified NodeType"""
        # Check node_type property
        if self.label == label.value:
            return True

        return False


class CytoscapeNode:
    """Represents a node in Cytoscape format"""

    def __new__(
        cls,
        id: str,
        label: str,
        node_type: str,
        classes: str,
        properties: dict[str, Any],
    ):
        """Check if node already exists before creating new instance"""
        # First check if node with same label already exists
        if label and label.lower() in _existing_node_labels:
            existing_node = _existing_node_labels[label.lower()]
            # Optionally merge additional properties from the new element
            new_properties = {
                k: v for k, v in properties.items()
                if k not in ["id", "label", "type"]
            }
            if new_properties:
                existing_node.merge_properties(new_properties)
            return existing_node

        # Then check by ID
        if id in _existing_nodes:
            existing_node = _existing_nodes[id]
            # Optionally merge additional properties from the new element
            new_properties = {
                k: v for k, v in properties.items()
                if k not in ["id", "label", "type"]
            }
            if new_properties:
                existing_node.merge_properties(new_properties)

            return existing_node

        # Create new instance
        instance = object.__new__(cls)
        return instance

    def __init__(
        self,
        id: str,
        label: str,
        node_type: str,
        classes: str,
        properties: dict[str, Any],
    ):
        """Initialize the node if it's a new instance"""
        # Only initialize if this is a new instance (not already in registry)
        if hasattr(self, "id"):
            return  # Already initialized

        self.id = id
        self.label = label
        self.node_type = node_type
        self.classes = classes
        self.properties = properties

        # Register this node in the global registry
        _existing_nodes[self.id] = self
        if self.label:
            _existing_node_labels[self.label.lower()] = self

    @classmethod
    def from_cytoscape_element(
        cls, element: dict[str, Any]
    ) -> Optional["CytoscapeNode"]:
        """Create a node from a Cytoscape element"""
        if element.get("group") == "edges":
            return None

        data = element.get("data", {})
        node_id = data.get("id", "")
        label = data.get("label", "")

        if not node_id:
            return None

        # Create instance (deduplication will be handled by __new__)
        node = cls(
            id=node_id,
            label=label,
            node_type=data.get("type", ""),
            classes=element.get("classes", ""),
            properties=data,
        )

        return node

    @classmethod
    def get_existing_node(cls, node_id: str) -> Optional["CytoscapeNode"]:
        """Get an existing node by ID"""
        return _existing_nodes.get(node_id)

    @classmethod
    def node_exists(cls, node_id: str) -> bool:
        """Check if a node with the given ID exists"""
        return node_id in _existing_nodes

    @classmethod
    def clear_registry(cls):
        """Clear the node registry (useful for testing)"""
        global _existing_nodes, _existing_node_labels
        _existing_nodes.clear()
        _existing_node_labels.clear()

    @classmethod
    def get_all_existing_ids(cls) -> set[str]:
        """Get all existing node IDs"""
        return set(_existing_nodes.keys())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for Cytoscape"""
        return {
            "id": self.id,
            "label": self.label,
            "type": self.node_type,
            **self.properties,
        }

    def merge_properties(self, other_properties: dict[str, Any]) -> None:
        """Merge additional properties into this node"""
        self.properties.update(other_properties)

    def update_label(self, new_label: str) -> None:
        """Update the node's label"""
        if new_label and new_label != self.label:
            self.label = new_label
            self.properties["label"] = new_label

    def is_instance_of(self, node_type: NodeType) -> bool:
        """Check if this node is an instance of the specified NodeType"""
        # Check node_type property
        if self.node_type == node_type.value:
            return True

        return False
