"""Constants for nodes, edges, and data sources."""

import logging
from enum import Enum

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """
    Enumeration of node types used in the application.

    Attributes:
        MIE: Molecular Initiating Event node.
        KE: Key Event node.
        AO: Adverse Outcome node.
        CHEMICAL: Chemical entity node.
        PROTEIN: Protein entity node.
        GENE: Gene entity node.
        ORGAN: Organ entity node.
        COMP_PROC: Component process node (type to be specified).
        COMP_OBJ: Component object node.
        CUSTOM: Custom node type.
        CELL: Cell entity node.
        QUALITY: Quality attribute node.
        CELL_COMP: Cellular component node.
    """

    MIE = "mie"
    KE = "ke"
    AO = "ao"
    CHEMICAL = "chemical"
    PROTEIN = "protein"
    GENE = "gene"
    ORGAN = "organ"
    COMP_PROC = "component_process"  # TODO get actual types
    COMP_OBJ = "component_object"
    CUSTOM = "custom"
    CELL = "cell"
    QUALITY = "quality"
    CELL_COMP = "cellular_component"


class EdgeType(Enum):
    """
    Types of edges used in the AOPNetwork model.

    Members:
        KER: Key Event Relationship.
        INTERACTION: Represents an interaction between entities.
        PART_OF: Indicates a part-of relationship.
        TRANSLATES_TO: Indicates translation from one entity to another.
        EXPRESSION_IN: Expression occurring in a specific context.
        CUSTOM: Custom edge type for user-defined relationships.
        IS_STRESSOR_OF: Indicates a stressor relationship.
        HAS_PROCESS: Denotes an entity having a process.
        INVOLVES: Indicates involvement in a process or relationship.
        NA: Not applicable or undefined edge type.
        Component action edge types:
            INCREASED: Increased process quality.
            DECREASED: Decreased process quality.
            DELAYED: Delayed process or event.
            OCCURRENCE: Occurrence of a process or event.
            ABNORMAL: Abnormal process or event.
            PREMATURE: Premature process or event.
            DISRUPTED: Disrupted process or event.
            FUNCTIONAL_CHANGE: Functional change in a process or entity.
            MORPHOLOGICAL_CHANGE: Morphological change in a process or entity.
            PATHOLOGICAL: Pathological process or event.
            ARRESTED: Arrested process or event.
            ASSOCIATED_WITH: Involvement or association with another entity.
            HAS_OBJECT: Indicates an entity has an object.
    """

    KER = "ker"
    INTERACTION = "interaction"
    PART_OF = "part_of"
    TRANSLATES_TO = "translates_to"
    EXPRESSION_IN = "expression_in"
    CUSTOM = "custom"
    IS_STRESSOR_OF = "is stressor of"
    HAS_PROCESS = "has process"
    INVOLVES = "involves"
    NA = "na"

    # Component action edge types
    INCREASED = "increased process quality"
    DECREASED = "decreased process quality"
    DELAYED = "delayed"
    OCCURRENCE = "occurrence"
    ABNORMAL = "abnormal"
    PREMATURE = "premature"
    DISRUPTED = "disrupted"
    FUNCTIONAL_CHANGE = "functional change"
    MORPHOLOGICAL_CHANGE = "morphological change"
    PATHOLOGICAL = "pathological"
    ARRESTED = "arrested"
    ASSOCIATED_WITH = "involves"
    HAS_OBJECT = "has object"

    @classmethod
    def get_component_actions(cls) -> set[str]:
        """Get all component action labels."""
        return {
            cls.INCREASED.value,
            cls.DECREASED.value,
            cls.DELAYED.value,
            cls.OCCURRENCE.value,
            cls.ABNORMAL.value,
            cls.PREMATURE.value,
            cls.DISRUPTED.value,
            cls.FUNCTIONAL_CHANGE.value,
            cls.MORPHOLOGICAL_CHANGE.value,
            cls.PATHOLOGICAL.value,
            cls.ARRESTED.value,
        }

    @classmethod
    def get_iri(cls) -> set[str]:
        """
        Return a set of IRIs (Internationalized Resource Identifiers).

        Returns:
            set[str]: An empty set of IRIs.
        """
        return set()

    @classmethod
    def get_label(cls) -> set[str]:
        """
        Return a set of action labels for component actions.

        This method retrieves the set of labels associated with
        component actions by calling `get_component_actions()` on the class.

        Returns:
            set[str]: A set containing the labels of component actions.
        """
        # For component actions, return the action labels directly
        component_actions = cls.get_component_actions()
        return component_actions


class DataSourceType(Enum):
    """
    Types of data sources available.

    Attributes:
        AOPWIKI (str): Data source from AOPWiki.
        QSPRPRED (str): Data source from QSPRPred.
        BGEE (str): Data source from Bgee.
        OPENTARGETS (str): Data source from OpenTargets.
        CUSTOM_TABLE (str): Data source from a custom table.
        MANUAL (str): Data source entered manually.
    """

    AOPWIKI = "aopwiki"
    QSPRPRED = "qsprpred"
    BGEE = "bgee"
    OPENTARGETS = "opentargets"
    CUSTOM_TABLE = "custom_table"
    MANUAL = "manual"
