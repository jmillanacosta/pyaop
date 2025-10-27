"""
Classes for AOP table.

Parse the AOPNetwork data model into AOP information tables.
"""

import logging
from dataclasses import dataclass
from typing import Any

from pyaop.aop.core_model import AOPNetwork, AOPKeyEvent, KeyEventRelationship
from pyaop.aop.constants import NodeType

logger = logging.getLogger(__name__)


@dataclass
class AOPRelationshipEntry:
    """Represents an AOP relationship entry for the table"""

    upstream_ke: AOPKeyEvent
    downstream_ke: AOPKeyEvent
    relationship: KeyEventRelationship

    def to_table_entry(self) -> dict[str, str]:
        """Convert to AOP table entry format"""
        # Get all AOP info from both KEs
        all_aop_ids = set()
        all_aop_titles = set()

        for ke in [self.upstream_ke, self.downstream_ke]:
            for aop in ke.associated_aops:
                all_aop_ids.add(f"AOP:{aop.aop_id}")
                all_aop_titles.add(aop.title)

        aop_string = ",".join(sorted(all_aop_ids)) if all_aop_ids else "N/A"
        aop_titles_string = "; ".join(sorted(all_aop_titles)) if all_aop_titles else "N/A"

        return {
            "source_id": self.upstream_ke.uri,
            "source_label": self.upstream_ke.title,
            "source_type": self.upstream_ke.ke_type.value,
            "ker_label": self.relationship.ker_id,
            "curie": f"aop.relationships:{self.relationship.ker_id}",
            "target_id": self.downstream_ke.uri,
            "target_label": self.downstream_ke.title,
            "target_type": self.downstream_ke.ke_type.value,
            "aop_list": aop_string,
            "aop_titles": aop_titles_string,
            "is_connected": True,
        }


class AOPTableBuilder:
    """Builds AOP table data from AOPNetwork data model"""

    def __init__(self, network: AOPNetwork):
        self.network = network

    def build_aop_table(self) -> list[dict[str, str]]:
        """Build AOP table using AOPNetwork data model"""
        table_entries = []

        # Process KER relationships
        for relationship in self.network.relationships:
            entry = AOPRelationshipEntry(
                upstream_ke=relationship.upstream_ke,
                downstream_ke=relationship.downstream_ke,
                relationship=relationship
            )
            table_entries.append(entry.to_table_entry())

        # Process disconnected KEs (KEs not involved in any relationships)
        connected_ke_uris = set()
        for rel in self.network.relationships:
            connected_ke_uris.add(rel.upstream_ke.uri)
            connected_ke_uris.add(rel.downstream_ke.uri)

        for ke_uri, ke in self.network.key_events.items():
            if ke_uri not in connected_ke_uris:
                # Create entry for disconnected KE
                aop_ids = [f"AOP:{aop.aop_id}" for aop in ke.associated_aops]
                aop_titles = [aop.title for aop in ke.associated_aops]

                entry = {
                    "source_id": ke.uri,
                    "source_label": ke.title,
                    "source_type": ke.ke_type.value,
                    "aop_list": ",".join(sorted(aop_ids)) if aop_ids else "N/A",
                    "aop_titles": "; ".join(sorted(aop_titles)) if aop_titles else "N/A",
                    "is_connected": False,
                }
                table_entries.append(entry)

        logger.info(f"Built AOP table with {len(table_entries)} entries from data model")
        return table_entries
