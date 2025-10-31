"""Generate gene (expression) information tables from gene associations."""

import logging
from dataclasses import dataclass

from pyaop.aop.associations import GeneAssociation, GeneExpressionAssociation

logger = logging.getLogger(__name__)


@dataclass
class GeneProteinPair:
    """Represent a gene-protein relationship."""

    gene_id: str
    gene_label: str
    protein_id: str
    protein_label: str
    gene_node_id: str
    protein_node_id: str

    def to_table_entry(self) -> dict[str, str]:
        """Convert to gene table entry format.

        Returns:
            Dictionary representing a gene table entry.
        """
        return {
            "gene": (self.gene_label if self.gene_label != "N/A" else "N/A"),
            "protein": (self.protein_label if self.protein_label != "N/A" else "N/A"),
            "protein_id": (self.protein_id if self.protein_id != "N/A" else "N/A"),
            "gene_id": (self.gene_node_id if self.gene_node_id != "N/A" else "N/A"),
            "protein_node_id": (self.protein_node_id if self.protein_node_id != "N/A" else "N/A"),
        }


class GeneTableBuilder:
    """Builds gene table data from gene associations."""

    def __init__(
        self, gene_assc: list[GeneAssociation], gene_expr_assc: list[GeneExpressionAssociation]
    ):
        """Initialize the builder with gene associations.

        Args:
            gene_assc: List of GeneAssociation objects.
            gene_expr_assc: List of GeneExpressionAssociation objects.
        """
        self.gene_associations = gene_assc
        self.gene_expression_associations = gene_expr_assc

    def build_gene_table(self) -> list[dict[str, str]]:
        """Build gene table with expression data.

        Returns:
            List of dictionaries representing gene table entries.
        """
        gene_pairs = self._create_gene_protein_pairs()

        table_entries = []
        seen_pairs = set()

        for pair in gene_pairs:
            entry = pair.to_table_entry()

            # Add expression data from gene expression associations
            expression_data = self._get_expression_data_for_gene(pair.gene_id)
            if expression_data:
                entry.update(
                    {
                        "expression_organs": "; ".join([exp["organ"] for exp in expression_data]),
                        "expression_levels": "; ".join([exp["level"] for exp in expression_data]),
                        "expression_confidence": "; ".join(
                            [exp["confidence"] for exp in expression_data]
                        ),
                        "expression_ids": "; ".join([exp["expr_id"] for exp in expression_data]),
                    }
                )
            else:
                entry.update(
                    {
                        "expression_organs": "N/A",
                        "expression_levels": "N/A",
                        "expression_confidence": "N/A",
                        "expression_ids": "N/A",
                    }
                )

            pair_key = f"{entry['gene']}_{entry['protein']}_{entry['protein_id']}"
            if pair_key not in seen_pairs:
                table_entries.append(entry)
                seen_pairs.add(pair_key)
        return table_entries

    def _get_expression_data_for_gene(self, gene_id: str) -> list[dict[str, str]]:
        """Get expression data for a specific gene.

        Args:
            gene_id: The ID of the gene.

        Returns:
            List of dictionaries with expression data.
        """
        expression_data = []

        for expr_assoc in self.gene_expression_associations:
            if expr_assoc.gene_id == gene_id:
                expression_data.append(
                    {
                        "organ": expr_assoc.anatomical_name,
                        "level": expr_assoc.expression_level,
                        "confidence": expr_assoc.confidence_level_name,
                        "expr_id": expr_assoc.expr or "N/A",
                    }
                )

        return expression_data

    def _create_gene_protein_pairs(self) -> list[GeneProteinPair]:
        """Create gene-protein pairs from associations.

        Returns:
            List of GeneProteinPair objects.
        """
        pairs = []
        seen_genes = set()

        # Create pairs from gene associations
        for gene_assoc in self.gene_associations:
            gene_id = gene_assoc.gene_id
            gene_node_id = f"gene_{gene_id}"

            if gene_assoc.protein_id and gene_assoc.protein_id != "NA":
                # Gene with protein
                protein_id = gene_assoc.protein_id
                protein_node_id = f"protein_{protein_id}"

                pair = GeneProteinPair(
                    gene_id=gene_id,
                    gene_label=gene_id,  # Use gene_id as label
                    protein_id=protein_id,
                    protein_label=protein_id,  # Use protein_id as label
                    gene_node_id=gene_node_id,
                    protein_node_id=protein_node_id,
                )
            else:
                # Gene without protein
                pair = GeneProteinPair(
                    gene_id=gene_id,
                    gene_label=gene_id,
                    protein_id="N/A",
                    protein_label="N/A",
                    gene_node_id=gene_node_id,
                    protein_node_id="N/A",
                )

            pairs.append(pair)
            seen_genes.add(gene_id)

        # Add genes from expression associations that weren't in associations
        for expr_assoc in self.gene_expression_associations:
            if expr_assoc.gene_id not in seen_genes:
                pair = GeneProteinPair(
                    gene_id=expr_assoc.gene_id,
                    gene_label=expr_assoc.gene_id,
                    protein_id="N/A",
                    protein_label="N/A",
                    gene_node_id=f"gene_{expr_assoc.gene_id}",
                    protein_node_id="N/A",
                )
                pairs.append(pair)
                seen_genes.add(expr_assoc.gene_id)
        return pairs


class GeneExpressionTableBuilder:
    """Builds gene expression table data from gene expression associations."""

    def __init__(self, gene_expr_assc: list[GeneExpressionAssociation]):
        """Initialize the builder with gene expression associations.

        Args:
            gene_expr_assc: List of GeneExpressionAssociation objects.
        """
        self.gene_expression_associations = gene_expr_assc

    def build_gene_expression_table(self) -> list[dict[str, str]]:
        """Build gene expression table.

        Returns:
            List of dictionaries representing gene expression table entries.
        """
        table_entries = []
        seen_entries = set()

        for expr_assoc in self.gene_expression_associations:
            entry_key = f"{expr_assoc.gene_id}_{expr_assoc.anatomical_id}"

            if entry_key not in seen_entries:
                entry = {
                    "gene_id": expr_assoc.gene_id,
                    "gene_label": expr_assoc.gene_id,  # Use gene_id as label
                    "organ": expr_assoc.anatomical_name,
                    "organ_id": expr_assoc.anatomical_id,
                    "expression_level": expr_assoc.expression_level,
                    "confidence": expr_assoc.confidence_level_name,
                    "developmental_stage": expr_assoc.developmental_stage_name,
                    "expr_id": expr_assoc.expr or "N/A",
                }
                table_entries.append(entry)
                seen_entries.add(entry_key)
        return table_entries
