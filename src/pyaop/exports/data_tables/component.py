"""
Component table class.

Generate KE Component information tables from component and organ associations.
"""

import logging
from collections import defaultdict
from typing import Any

from pyaop.aop.associations import ComponentAssociation, OrganAssociation
from pyaop.aop.constants import NodeType
from pyaop.aop.core_model import AOPKeyEvent

logger = logging.getLogger(__name__)


class ComponentTableBuilder:
    """Builds component table data from component and organ associations."""

    def __init__(
        self,
        comp_assc: list[ComponentAssociation],
        organ_assc: list[OrganAssociation],
        kes: dict[str, AOPKeyEvent],
    ):
        """Initialize the builder with associations and key events.

        Args:
            component_associations: List of ComponentAssociation objects.
            organ_assc: List of OrganAssociation objects.
            kes: Dictionary of key event URIs to AOPKeyEvent objects.
        """
        self.component_associations = comp_assc
        self.organ_associations = organ_assc
        self.key_events = kes

    def build_component_table(self) -> list[dict[str, Any]]:
        """Build component table from associations.

        Returns:
            List of dictionaries representing component table entries.
        """
        ke_components, ke_organs = self._group_associations_by_ke()
        all_associated_ke_uris = set(ke_components.keys()) | set(ke_organs.keys())

        table_entries = []
        for ke_uri in all_associated_ke_uris:
            ke = self.key_events.get(ke_uri)
            if not ke:
                continue

            action_processes = self._build_action_processes_for_ke(ke_uri, ke_components)

            organs = self._build_organs_for_ke(ke_uri, ke_components, ke_organs)
            entry = self._create_table_entry(ke, action_processes, organs)
            table_entries.append(entry)

        return table_entries

    def _group_associations_by_ke(
        self,
    ) -> tuple[dict[str, list[ComponentAssociation]], dict[str, list[OrganAssociation]]]:
        """Group associations by KE URI.

        Returns:
            Tuple of dictionaries: ke_components and ke_organs.
        """
        ke_components: dict[str, list[ComponentAssociation]] = defaultdict(list)
        for comp_assoc in self.component_associations:
            ke_components[comp_assoc.ke_uri].append(comp_assoc)

        ke_organs: dict[str, list[OrganAssociation]] = defaultdict(list)
        for organ_assoc in self.organ_associations:
            ke_organs[organ_assoc.ke_uri].append(organ_assoc)

        return ke_components, ke_organs

    def _build_action_processes_for_ke(
        self, ke_uri: str, ke_components: dict[str, list[ComponentAssociation]]
    ) -> list[dict[str, str]]:
        """Build action-processes for a specific KE.

        Args:
            ke_uri: Key event URI.
            ke_components: Dictionary of component associations by KE.

        Returns:
            List of action-process dictionaries.
        """
        action_processes = []
        for comp_assoc in ke_components.get(ke_uri, []):
            if comp_assoc.process:  # Only include if process exists
                process_suffix = (
                    comp_assoc.process.split("/")[-1]
                    if "/" in comp_assoc.process
                    else comp_assoc.process
                )
                action_processes.append(
                    {
                        "action": comp_assoc.action or "has_process",
                        "process_id": f"process_{process_suffix}",
                        "process_name": comp_assoc.process_name,
                        "process_iri": comp_assoc.process,
                    }
                )
        return action_processes

    def _build_organs_for_ke(
        self,
        ke_uri: str,
        ke_components: dict[str, list[ComponentAssociation]],
        ke_organs: dict[str, list[OrganAssociation]],
    ) -> list[dict[str, str]]:
        """Build organs for a specific KE.

        Args:
            ke_uri: Key event URI.
            ke_components: Dictionary of component associations by KE.
            ke_organs: Dictionary of organ associations by KE.

        Returns:
            List of organ dictionaries.
        """
        organs = []
        organ_ids_seen = set()

        # From component associations (objects that are organs)
        for comp_assoc in ke_components.get(ke_uri, []):
            if comp_assoc.object and comp_assoc.object_type in [
                NodeType.ORGAN.value,
                "http://aopkb.org/aop_ontology#OrganContext",
            ]:
                organ_id = (
                    comp_assoc.object.split("/")[-1]
                    if "/" in comp_assoc.object
                    else comp_assoc.object
                )
                if organ_id not in organ_ids_seen:
                    organs.append(
                        {
                            "organ_id": f"object_{organ_id}",
                            "organ_name": comp_assoc.object_name,
                            "organ_iri": comp_assoc.object,
                        }
                    )
                    organ_ids_seen.add(organ_id)

        # From organ associations
        for organ_assoc in ke_organs.get(ke_uri, []):
            organ_data = organ_assoc.organ_data
            organ_id = organ_data.id
            if organ_id not in organ_ids_seen:
                organs.append(
                    {
                        "organ_id": organ_id,
                        "organ_name": organ_data.properties.get(
                            "anatomical_name", organ_data.label
                        ),
                        "organ_iri": organ_data.properties.get("anatomical_id", organ_id),
                    }
                )
                organ_ids_seen.add(organ_id)

        return organs

    def _create_table_entry(
        self, ke: AOPKeyEvent, action_processes: list[dict[str, str]], organs: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Create a table entry for a KE.

        Args:
            ke: AOPKeyEvent object.
            action_processes: List of action-process dictionaries.
            organs: List of organ dictionaries.

        Returns:
            Dictionary representing a table entry.
        """
        # Extract KE number from URI
        ke_number = ke.ke_id
        return {
            "ke_id": f"aop.events_{ke_number}",
            "ke_number": ke_number,
            "ke_uri": ke.uri,
            "ke_name": ke.title,
            "action_processes": action_processes,
            "organs": organs,
            "action_process_count": len(action_processes),
            "organ_count": len(organs),
        }
