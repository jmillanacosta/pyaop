"""Core AOP information classes."""

from dataclasses import dataclass, field
from typing import Any

from pyaop.aop.constants import EdgeType, NodeType


@dataclass(frozen=True)
class AOPInfo:
    """Represents AOP metadata."""

    aop_id: str
    title: str
    uri: str

    def __post_init__(self) -> None:
        """Perform basic validation after initialization."""
        if not self.aop_id or not self.uri:
            raise ValueError("AOP ID and URI are required")

    def __str__(self) -> str:
        return f"AOP(id:{self.aop_id}, title:'{self.title}', URI:{self.uri})"

    @classmethod
    def from_cytoscape_elements(cls, elements: list[dict[str, Any]]) -> list["AOPInfo"]:
        """Parse AOP information from Cytoscape elements.

        Args:
            elements: List of Cytoscape elements to parse.

        Returns:
            List of AOPInfo objects.
        """
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
                for aop_uri, aop_title in zip(aop_uris, aop_titles, strict=True):
                    if aop_uri and aop_title:
                        # Extract AOP ID from URI
                        aop_id = aop_uri.split("/")[-1] if "/" in aop_uri else aop_uri
                        # Create AOPInfo if not already exists
                        if aop_id not in aop_infos:
                            try:
                                aop_info = cls(aop_id=aop_id, title=aop_title, uri=aop_uri)
                                aop_infos[aop_id] = aop_info
                            except ValueError:
                                return []
        return list(aop_infos.values())


@dataclass
class AOPKeyEvent:
    """Represents a Key Event in an AOP."""

    ke_id: str
    uri: str
    title: str
    ke_type: NodeType
    associated_aops: list[AOPInfo] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Perform basic validation after initialization."""
        if not self.ke_id or not self.uri:
            raise ValueError("Key Event ID and URI are required")
        if not self.title:
            self.title = self.ke_id  # Use ID as fallback

    def __str__(self) -> str:
        return f"{self.ke_type.value}:{self.ke_id}"

    def add_aop(self, aop_info: AOPInfo) -> bool:
        """Add AOP association.

        Args:
            aop_info: AOPInfo to add.

        Returns:
            True if added, False if exists.
        """
        if aop_info not in self.associated_aops:
            self.associated_aops.append(aop_info)
            return True
        return False

    def get_aop_ids(self) -> list[str]:
        """Get list of AOP IDs for this key event.

        Returns:
            List of AOP IDs.
        """
        return [aop.aop_id for aop in self.associated_aops]

    def to_cytoscape_data(self) -> dict[str, Any]:
        """Convert to Cytoscape node data.

        Returns:
            Dictionary for Cytoscape node data.
        """
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
    """Represents a relationship between two Key Events."""

    ker_id: str
    ker_uri: str
    upstream_ke: AOPKeyEvent
    downstream_ke: AOPKeyEvent

    def __post_init__(self) -> None:
        """Perform basic validation after initialization."""
        if not self.ker_id or not self.ker_uri:
            raise ValueError("KER ID and URI are required")
        if self.upstream_ke.uri == self.downstream_ke.uri:
            raise ValueError("Upstream and downstream KEs cannot be the same")

    def __str__(self) -> str:
        return f"KER:{self.ker_id}"

    def to_cytoscape_data(self) -> dict[str, Any]:
        """Convert to Cytoscape edge data.

        Returns:
            Dictionary for Cytoscape edge data.
        """
        return {
            "id": f"{self.upstream_ke.uri}_{self.downstream_ke.uri}",
            "source": self.upstream_ke.uri,
            "target": self.downstream_ke.uri,
            "curie": f"aop.relationships:{self.ker_id}",
            "ker_label": self.ker_id,
            "type": EdgeType.KER.value,
        }
