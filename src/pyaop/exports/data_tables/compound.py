"""Generate AOP compound (stressor) tables from compound associations."""

import logging

from pyaop.aop.associations import CompoundAssociation

logger = logging.getLogger(__name__)


class CompoundTableBuilder:
    """Builds compound table data from compound associations."""

    def __init__(self, compound_associations: list[CompoundAssociation]):
        """Initialize the builder with compound associations.

        Args:
            compound_associations: List of CompoundAssociation objects to build the table from.
        """
        self.compound_associations = compound_associations

    def build_compound_table(self) -> list[dict[str, str]]:
        """Build compound table from compound associations.

        Returns:
            List of dictionaries representing compound table entries.
        """
        table_entries = []
        seen_compounds = set()

        for assoc in self.compound_associations:
            # Extract compound identifiers
            pubchem_id = (
                assoc.pubchem_compound.split("/")[-1]
                if "/" in assoc.pubchem_compound
                else assoc.pubchem_compound
            )

            compound_name = assoc.compound_name or assoc.chemical_label
            compound_key = f"{compound_name}_{pubchem_id}"

            if compound_key not in seen_compounds:
                entry = {
                    "compound_name": compound_name,
                    "chemical_label": assoc.chemical_label,
                    "pubchem_id": pubchem_id,
                    "pubchem_compound": assoc.pubchem_compound,
                    "cas_id": assoc.cas_id if assoc.cas_id else "N/A",
                    "chemical_uri": assoc.chemical_uri,
                    "smiles": "",  # Not available in current data model
                    "node_id": f"chemical_{pubchem_id}",
                }
                table_entries.append(entry)
                seen_compounds.add(compound_key)
        return table_entries
