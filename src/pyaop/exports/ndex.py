"""
Class for ndex export.

Convert the AOPNetwork to ndex/cytoscape exchange format (CX2).
"""

# TBD
import logging
from typing import Any

from ndex2 import CX2Network

from pyaop.aop.core_model import AOPNetwork

logger = logging.getLogger(__name__)

def to_ndx_network(
    aop_network: AOPNetwork,
    name: str | None = None,
    description: str | None = None,
    cytoscape_styles: dict[str, Any] | None = None,
):
    net_cx = CX2Network()
    # Set network attributes
    net_name = name or f"AOP Network ({len(aop_network.node_list)} nodes)"
    net_cx.add_network_attribute("name", net_name)
    if description:
        net_cx.add_network_attribute("description", description)
    # Add simple node and edge counts as metadata
    net_cx.add_network_attribute("total_nodes", len(aop_network.node_list))
    net_cx.add_network_attribute("total_edges", len(aop_network.edge_list))
    # Extract position data from original elements
    position_map = {}
    if hasattr(aop_network, "_original_elements"):
        for element in aop_network._original_elements:
            if element.get("group") != "edges" and "data" in element:
                # Node element - extract position
                node_id = element["data"].get("id")
                position = element.get("position", {})
                if node_id and position:
                    position_map[node_id] = position
    # Add ALL nodes from node_list to CX2 with positions
    original_to_cx2_id = {}  # Map original node IDs to CX2 integer IDs
    for node in aop_network.node_list:
        # Convert node to dict and remove CX2 reserved keys
        node_data = node.to_dict()
        node_data.pop("id", None)  # Remove conflicting id key
        # Extract position for this node
        position = position_map.get(node.id, {})
        x = position.get("x")
        y = position.get("y")
        # Add node with position coordinates if available
        if x is not None and y is not None:
            cx2_node_id = net_cx.add_node(
                attributes=node_data, x=float(x), y=float(y)
            )
        else:
            cx2_node_id = net_cx.add_node(attributes=node_data)
        original_to_cx2_id[node.id] = cx2_node_id
    # Add ALL edges from edge_list to CX2
    for edge in aop_network.edge_list:
        # Map source and target to CX2 node IDs
        source_cx2_id = original_to_cx2_id.get(edge.source)
        target_cx2_id = original_to_cx2_id.get(edge.target)
        if source_cx2_id is not None and target_cx2_id is not None:
            edge_data = edge.to_dict()
            # Remove ALL CX2 reserved keys
            edge_data.pop("id", None)
            edge_data.pop("source", None)
            edge_data.pop("target", None)
            net_cx.add_edge(
                source=source_cx2_id, target=target_cx2_id, attributes=edge_data
            )
    # Use the actual Cytoscape styles if provided
    if cytoscape_styles:
        try:
            # Just pass the Cytoscape styles directly to CX2
            visual_properties = {"cytoscape_styles": cytoscape_styles}
            net_cx.set_visual_properties(visual_properties)
            logger.info(
                f"Added Cytoscape styles to CX2 network ({len(cytoscape_styles)} style rules)"
            )
        except Exception as e:
            logger.warning(f"Could not add Cytoscape styles to CX2: {e}")
    logger.info(
        f"Created CX2 network with {len(aop_network.node_list)} nodes and {len(aop_network.edge_list)} edges, including positions and styles"
    )
    return net_cx
