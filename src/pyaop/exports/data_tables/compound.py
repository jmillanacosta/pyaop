"""
Classes for Compound table.

Generate AOP compound (stressor) tables from AOPNetwork data model.
"""

import logging

from pyaop.aop.core_model import AOPNetwork

logger = logging.getLogger(__name__)

class CompoundTableBuilder:
    """Builds compound table data from AOPNetwork data model"""

    def __init__(self, network: AOPNetwork):
        self.network = network

    def build_compound_table(self) -> list[dict[str, str]]:
        """Build compound table from network compound associations"""
        table_entries = []
        seen_compounds = set()

        for assoc in self.network.compound_associations:
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

        logger.info(f"Built compound table with {len(table_entries)} entries from data model")
        return table_entries
