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


def _set_network_attributes(
    net_cx: CX2Network, aop_network: AOPNetwork, name: str | None, description: str | None
) -> None:
    """Set network attributes on the CX2 network.

    Args:
        net_cx: The CX2Network object.
        aop_network: The AOPNetwork.
        name: Optional network name.
        description: Optional network description.
    """
    net_name = name or f"AOP Network ({len(aop_network.node_list)} nodes)"
    net_cx.add_network_attribute("name", net_name)
    if description:
        net_cx.add_network_attribute("description", description)
    net_cx.add_network_attribute("total_nodes", len(aop_network.node_list))
    net_cx.add_network_attribute("total_edges", len(aop_network.edge_list))


def _extract_positions(aop_network: AOPNetwork) -> dict[str, dict[str, Any]]:
    """Extract node positions from original elements if available.

    Args:
        aop_network: The AOPNetwork.

    Returns:
        Dictionary mapping node IDs to position data.
    """
    position_map = {}
    if hasattr(aop_network, "_original_elements"):
        for element in aop_network._original_elements:
            if element.get("group") != "edges" and "data" in element:
                node_id = element["data"].get("id")
                position = element.get("position", {})
                if node_id and position:
                    position_map[node_id] = position
    return position_map


def _add_nodes(
    net_cx: CX2Network, aop_network: AOPNetwork, position_map: dict[str, dict[str, Any]]
) -> dict[str, int]:
    """Add nodes to the CX2 network.

    Args:
        net_cx: The CX2Network object.
        aop_network: The AOPNetwork.
        position_map: Dictionary of node positions.

    Returns:
        Dictionary mapping original node IDs to CX2 node IDs.
    """
    original_to_cx2_id = {}
    for node in aop_network.node_list:
        node_data = node.to_dict()
        node_data.pop("id", None)  # Remove reserved key

        position = position_map.get(node.id, {})
        x, y = position.get("x"), position.get("y")

        if x is not None and y is not None:
            cx2_node_id = net_cx.add_node(attributes=node_data, x=float(x), y=float(y))
        else:
            cx2_node_id = net_cx.add_node(attributes=node_data)

        original_to_cx2_id[node.id] = cx2_node_id
    return original_to_cx2_id


def _add_edges(
    net_cx: CX2Network, aop_network: AOPNetwork, original_to_cx2_id: dict[str, int]
) -> None:
    """Add edges to the CX2 network.

    Args:
        net_cx: The CX2Network object.
        aop_network: The AOPNetwork.
        original_to_cx2_id: Mapping of original to CX2 node IDs.
    """
    for edge in aop_network.edge_list:
        source_cx2_id = original_to_cx2_id.get(edge.source)
        target_cx2_id = original_to_cx2_id.get(edge.target)

        if source_cx2_id is not None and target_cx2_id is not None:
            edge_data = edge.to_dict()
            # Remove reserved keys
            edge_data.pop("id", None)
            edge_data.pop("source", None)
            edge_data.pop("target", None)

            net_cx.add_edge(source=source_cx2_id, target=target_cx2_id, attributes=edge_data)


def _add_styles(net_cx: CX2Network, cytoscape_styles: dict[str, Any] | None) -> None:
    """Add Cytoscape styles to the CX2 network if provided.

    Args:
        net_cx: The CX2Network object.
        cytoscape_styles: Optional Cytoscape styles.
    """
    if cytoscape_styles:
        visual_properties = {"cytoscape_styles": cytoscape_styles}
        net_cx.set_visual_properties(visual_properties)


def to_ndx_network(
    aop_network: AOPNetwork,
    name: str | None = None,
    description: str | None = None,
    cytoscape_styles: dict[str, Any] | None = None,
) -> CX2Network:
    """Convert AOPNetwork to NDEx CX2 format.

    Args:
        aop_network: The AOPNetwork to convert.
        name: Optional name for the network.
        description: Optional description for the network.
        cytoscape_styles: Optional Cytoscape styles to include.

    Returns:
        CX2Network object.
    """
    net_cx = CX2Network()

    _set_network_attributes(net_cx, aop_network, name, description)

    position_map = _extract_positions(aop_network)

    original_to_cx2_id = _add_nodes(net_cx, aop_network, position_map)

    _add_edges(net_cx, aop_network, original_to_cx2_id)

    _add_styles(net_cx, cytoscape_styles)

    logger.info(
        f"Created CX2 network: {len(aop_network.node_list)} nodes, {len(aop_network.edge_list)} edges"
    )
    return net_cx
