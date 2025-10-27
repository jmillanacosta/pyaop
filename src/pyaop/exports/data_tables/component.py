"""
Classes for KE Component table.

Generate KE Component information tables from AOPNetwork data model.
"""

import logging
from typing import Any
from collections import defaultdict

from pyaop.aop.core_model import AOPNetwork
from pyaop.aop.constants import NodeType

logger = logging.getLogger(__name__)


class ComponentTableBuilder:
    """Builds component table data from AOPNetwork data model - one row per KE"""

    def __init__(self, network: AOPNetwork):
        self.network = network

    def build_component_table(self) -> list[dict[str, Any]]:
        """Build component table with one row per Key Event that has component associations"""
        table_entries = []

        # Group component associations by KE URI
        ke_components = defaultdict(list)
        for assoc in self.network.component_associations:
            ke_components[assoc.ke_uri].append(assoc)

        # Group organ associations by KE URI  
        ke_organs = defaultdict(list)
        for assoc in self.network.organ_associations:
            ke_organs[assoc.ke_uri].append(assoc)

        # Get all KEs that have either component or organ associations
        all_associated_ke_uris = set(ke_components.keys()) | set(ke_organs.keys())

        for ke_uri in all_associated_ke_uris:
            ke = self.network.key_events.get(ke_uri)
            if not ke:
                logger.warning(f"KE not found for URI: {ke_uri}")
                continue

            # Build action-processes from component associations
            action_processes = []
            for comp_assoc in ke_components[ke_uri]:
                if comp_assoc.process:  # Only include if process exists
                    action_processes.append({
                        "action": comp_assoc.action or "has_process",
                        "process_id": f"process_{comp_assoc.process.split('/')[-1] if '/' in comp_assoc.process else comp_assoc.process}",
                        "process_name": comp_assoc.process_name,
                        "process_iri": comp_assoc.process
                    })

            # Build organs from both component associations and organ associations
            organs = []
            organ_ids_seen = set()

            # From component associations (objects that are organs)
            for comp_assoc in ke_components[ke_uri]:
                if comp_assoc.object and comp_assoc.object_type in [NodeType.ORGAN.value, "http://aopkb.org/aop_ontology#OrganContext"]:
                    organ_id = comp_assoc.object.split('/')[-1] if '/' in comp_assoc.object else comp_assoc.object
                    if organ_id not in organ_ids_seen:
                        organs.append({
                            "organ_id": f"object_{organ_id}",
                            "organ_name": comp_assoc.object_name,
                            "organ_iri": comp_assoc.object,
                        })
                        organ_ids_seen.add(organ_id)

            # From organ associations
            for organ_assoc in ke_organs[ke_uri]:
                organ_data = organ_assoc.organ_data
                organ_id = organ_data.id
                if organ_id not in organ_ids_seen:
                    organs.append({
                        "organ_id": organ_id,
                        "organ_name": organ_data.properties.get("anatomical_name", organ_data.label),
                        "organ_iri": organ_data.properties.get("anatomical_id", organ_id),
                    })
                    organ_ids_seen.add(organ_id)

            # Extract KE number from URI
            ke_number = ke.ke_id

            # Create table entry
            entry = {
                "ke_id": f"aop.events_{ke_number}",
                "ke_number": ke_number,
                "ke_uri": ke.uri,
                "ke_name": ke.title,
                "action_processes": action_processes,
                "organs": organs,
                "action_process_count": len(action_processes),
                "organ_count": len(organs),
            }

            table_entries.append(entry)

        logger.info(f"Built component table with {len(table_entries)} entries from data model")
        return table_entries
