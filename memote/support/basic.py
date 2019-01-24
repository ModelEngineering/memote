# -*- coding: utf-8 -*-

# Copyright 2017 Novo Nordisk Foundation Center for Biosustainability,
# Technical University of Denmark.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Supporting functions for basic checks performed on the model object."""

from __future__ import absolute_import

import logging
from itertools import combinations
from pylru import lrudecorator

import memote.support.helpers as helpers
from memote.support.gpr_helpers import find_top_level_complex
from memote.utils import filter_none

__all__ = ("check_metabolites_formula_presence",)


LOGGER = logging.getLogger(__name__)


def check_metabolites_formula_presence(model):
    """Return the list of model metabolites that have no associated formula."""
    return [met for met in model.metabolites if met.formula is None]


def check_metabolites_charge_presence(model):
    """Return the list of model metabolites that have no associated charge."""
    return [met for met in model.metabolites if met.charge is None]


def check_gene_protein_reaction_rule_presence(model):
    """Return the list of model reactions that have no associated gene rule."""
    return [rxn for rxn in model.reactions if not rxn.gene_reaction_rule]


def find_nonzero_constrained_reactions(model):
    """Return list of reactions with non-zero, non-maximal bounds."""
    lower_bound, upper_bound = helpers.find_bounds(model)
    return [rxn for rxn in model.reactions if
            0 > rxn.lower_bound > lower_bound or
            0 < rxn.upper_bound < upper_bound]


def find_zero_constrained_reactions(model):
    """Return list of reactions that are constrained to zero flux."""
    return [rxn for rxn in model.reactions if
            rxn.lower_bound == 0 and
            rxn.upper_bound == 0]


def find_irreversible_reactions(model):
    """Return list of reactions that are irreversible."""
    return [rxn for rxn in model.reactions if rxn.reversibility is False]


def find_unconstrained_reactions(model):
    """Return list of reactions that are not constrained at all."""
    lower_bound, upper_bound = helpers.find_bounds(model)
    return [rxn for rxn in model.reactions if
            rxn.lower_bound <= lower_bound and
            rxn.upper_bound >= upper_bound]


def find_ngam(model):
    u"""
    Return all potential non growth-associated maintenance reactions.

    From the list of all reactions that convert ATP to ADP select the reactions
    that match a defined reaction string and whose metabolites are situated
    within the main model compartment. The main model compartment is the
    cytosol, and if that cannot be identified, the compartment with the most
    metabolites.

    Parameters
    ----------
    model : cobra.Model
        The metabolic model under investigation.

    Returns
    -------
    list
        Reactions that qualify as non-growth associated maintenance reactions.

    Notes
    -----
    [1]_ define the non-growth associated maintenance (NGAM) as the energy
    required to maintain all constant processes such as turgor pressure and
    other housekeeping activities. In metabolic models this is expressed by
    requiring a simple ATP hydrolysis reaction to always have a fixed minimal
    amount of flux. This value can be measured as described by [1]_ .

    References
    ----------
    .. [1] Thiele, I., & Palsson, B. Ø. (2010, January). A protocol for
          generating a high-quality genome-scale metabolic reconstruction.
          Nature protocols. Nature Publishing Group.
          http://doi.org/10.1038/nprot.2009.203

    """
    atp_adp_conv_rxns = helpers.find_converting_reactions(
        model, ("MNXM3", "MNXM7")
    )
    id_of_main_compartment = helpers.find_compartment_id_in_model(model, 'c')

    reactants = {
        helpers.find_met_in_model(model, "MNXM3", id_of_main_compartment)[0],
        helpers.find_met_in_model(model, "MNXM2", id_of_main_compartment)[0]
    }

    products = {
        helpers.find_met_in_model(model, "MNXM7", id_of_main_compartment)[0],
        helpers.find_met_in_model(model, "MNXM1", id_of_main_compartment)[0],
        helpers.find_met_in_model(model, "MNXM9", id_of_main_compartment)[0]
    }

    candidates = [rxn for rxn in atp_adp_conv_rxns
                  if rxn.reversibility is False and
                  set(rxn.reactants) == reactants and
                  set(rxn.products) == products]

    buzzwords = ['maintenance', 'atpm', 'requirement',
                 'ngam', 'non-growth', 'associated']

    refined_candidates = [rxn for rxn in candidates if any(
        string in filter_none(rxn.name, '').lower() for string in buzzwords
    )]

    if refined_candidates:
        return refined_candidates
    else:
        return candidates


def calculate_metabolic_coverage(model):
    u"""
    Return the ratio of reactions and genes included in the model.

    Determine whether the amount of reactions and genes in model not equal to
    zero, then return the ratio.

    Parameters
    ----------
    model : cobra.Model
        The metabolic model under investigation.

    Returns
    -------
    float
        The ratio of reactions to genes also called metabolic coverage.

    Raises
    ------
    ValueError
        If the model does not contain either reactions or genes.

    Notes
    -----
    According to [1]_ this is a good quality indicator expressing the degree of
    metabolic coverage i.e. modeling detail of a given reconstruction. The
    authors explain that models with a 'high level of modeling detail have
    ratios >1, and [models] with low level of detail have ratios <1'. They
    explain that 'this difference arises because [models] with basic or
    intermediate levels of detail often include many reactions in which several
    gene products and their enzymatic transformations are ‘lumped’'.

    References
    ----------
    .. [1] Monk, J., Nogales, J., & Palsson, B. O. (2014). Optimizing
          genome-scale network reconstructions. Nature Biotechnology, 32(5),
          447–452. http://doi.org/10.1038/nbt.2870

    """
    if len(model.reactions) == 0 or len(model.genes) == 0:
        raise ValueError("The model contains no reactions or genes.")
    return float(len(model.reactions)) / float(len(model.genes))


def find_protein_complexes(model):
    """
    Find reactions that are catalyzed by at least a heterodimer.

    Parameters
    ----------
    model : cobra.Model
        The metabolic model under investigation.

    Returns
    -------
    list
        Reactions whose gene-protein-reaction association contains at least one
        logical AND combining different gene products (heterodimer).

    """
    complexes = []
    for rxn in model.reactions:
        if not rxn.gene_reaction_rule:
            continue
        size = find_top_level_complex(rxn.gene_reaction_rule)
        if size >= 2:
            complexes.append(rxn)
    return complexes


@lrudecorator(size=2)
def find_pure_metabolic_reactions(model):
    """
    Return reactions that are neither transporters, exchanges, nor pseudo.

    Parameters
    ----------
    model : cobra.Model
        The metabolic model under investigation.

    """
    return set(model.reactions) - helpers.find_interchange_biomass_reactions(
        model)


def is_constrained_reaction(model, rxn):
    """Return whether a reaction has fixed constraints."""
    lower_bound, upper_bound = helpers.find_bounds(model)
    if rxn.reversibility:
        return rxn.lower_bound > lower_bound or rxn.upper_bound < upper_bound
    else:
        return rxn.lower_bound > 0 or rxn.upper_bound < upper_bound


def find_oxygen_reactions(model):
    """Return list of oxygen-producing/-consuming reactions."""
    o2_in_model = helpers.find_met_in_model(model, "MNXM4")
    return set([rxn for met in model.metabolites for
                rxn in met.reactions if met.formula == "O2" or
                met in o2_in_model])


def find_unique_metabolites(model):
    """Return set of metabolite IDs without duplicates from compartments."""
    return set(met.id.split("_", 1)[0] for met in model.metabolites)


def find_duplicate_metabolites_in_compartments(model):
    """
    Return list of metabolites with duplicates in the same compartment.

    This function identifies duplicate metabolites in each compartment by
    determining if any two metabolites have identical InChI-key annotations.
    For instance, this function would find compounds with IDs ATP1 and ATP2 in
    the cytosolic compartment, with both having the same InChI annotations.

    Parameters
    ----------
    model : cobra.Model
        The metabolic model under investigation.

    Returns
    -------
    list
        A list of tuples of duplicate metabolites.

    """
    duplicates = []
    for compartment in model.compartments:
        ann_mets = [(met, met.annotation) for met in model.metabolites
                    if met.compartment == compartment and
                    "inchikey" in met.annotation]
        for a, b in combinations(ann_mets, 2):
            if a[1]["inchikey"] == b[1]["inchikey"]:
                duplicates.append((a[0].id, b[0].id))
    return duplicates


def find_duplicate_reactions_by_annotations(model):
    """
    Return list of reactions with duplicates based on identical annotations.

    This function identifies duplicate reactions globally by checking if any
    two reactions have the same entries in their annotation attributes.
    This can be useful to identify one 'type' of reactions that occurs in
    several compartments, to curate merged models or to clean-up bulk model
    modifications. The heuristic looks at annotations with the keys
    "metanetx.reaction", "kegg.reaction", "brenda", "rhea", "biocyc",
    "bigg.reaction" only.

    Parameters
    ----------
    model : cobra.Model
        The metabolic model under investigation.

    Returns
    -------
    list
        A list of tuples of duplicate reactions based on annotations.

    """
    duplicates = dict()
    rxn_db_identifiers = ["metanetx.reaction", "kegg.reaction", "brenda",
                          "rhea", "biocyc", "bigg.reaction"]

    ann_rxns = []
    for rxn in model.reactions:
        ann = []
        for key in rxn_db_identifiers:
            if key in rxn.annotation:
                if type(rxn.annotation[key]) is list:
                    ann.extend([(key, elem) for elem in rxn.annotation[key]])
                else:
                    ann.append((key, rxn.annotation[key]))
        ann_rxns.append((rxn, frozenset(ann)))
    for (rxn_a, ann_a), (rxn_b, ann_b) in combinations(ann_rxns, 2):
        if len(ann_a & ann_b) > 0:
            mutual_pair = ann_a & ann_b
            duplicates.setdefault(mutual_pair , set())
            duplicates[mutual_pair].update([rxn_a.id,rxn_b.id])
    return list(duplicates.items())


def find_duplicate_reactions_by_metabolites(model):
    """
    Return list of reactions with duplicates based on identical metabolites.

    This function identifies duplicate reactions globally by checking if any
    two reactions have the same metabolites, same directionality and are in
    the same compartment.
    This can be useful to curate merged models or to clean-up bulk model
    modifications. The heuristic compares reactions in a pairwise manner.
    First, if there are duplicate metabolites in the set of
    metabolites of each reaction, they are added to the set of each reaction
    respectively. Then, if the sets for each reaction are
    identical the reversibility of each reaction is checked:
    - If both reactions differ in reversibility they are assumed to be
    different.
    - If both are reversible they are assumed to be identical.
    - If both are irreversible, the upper bound and product metabolites
     have to be identical for the reactions to be assumed to be identical.

    Parameters
    ----------
    model : cobra.Model
        The metabolic model under investigation.

    Returns
    -------
    list
        A list of sets of duplicate reactions based on metabolites.

    """

    def include_duplicates(rxn, duplicate_metabolites):
        expanded_metabolites = []
        for met in rxn.metabolites.keys():
            for tup in duplicate_metabolites:
                if met in tup:
                    expanded_metabolites.extend(tup)
                else:
                    expanded_metabolites.append(met)
        return expanded_metabolites

    # Get a list of pure metabolic reactions
    duplicates = dict()
    # Get a list of duplicate metabolites in each compartment
    duplicate_metabolites = find_duplicate_metabolites_in_compartments(
        model)
    # For each combination of reactions
    for rxn_a, rxn_b in combinations(model.reactions, 2):
        # ..generate a set of metabolites including possible
        # duplicate metabolites.
        met_set_a = set(include_duplicates(rxn_a, duplicate_metabolites))
        met_set_b = set(include_duplicates(rxn_b, duplicate_metabolites))
        symm_difference = met_set_a ^ met_set_b
        # For the reactions whose sets of metabolites are identical
        if len(symm_difference) == 0:
            # ..check if the reversibility is identical
            if rxn_a.reversibility != rxn_b.reversibility:
                continue
            # ..if not, are they both reversible
            elif all([rxn_a.reversibility, rxn_b.reversibility]):
                duplicates.setdefault(met_set_a, set())
                duplicates[met_set_a].update([rxn_a.id, rxn_b.id])
            # ..or are they are both irreversible?
            else:
                if rxn_a.products == rxn_b.products \
                        and rxn_a.upper_bound == rxn_b.upper_bound:
                    duplicates.setdefault(met_set_a, set())
                    duplicates[met_set_a].update([rxn_a.id, rxn_b.id])
    return list(duplicates.values())


def find_reactions_with_identical_genes(model):
    """
    Return list of reaction that have identical genes.

    This function identifies duplicate reactions globally by checking if any
    two reactions have the same genes.
    This can be useful to curate merged models or to clean-up bulk model
    modifications, but also to identify promiscuous enzymes.
    The heuristic compares reactions in a pairwise manner and reports on
    reaction pairs whose genes are identical. Reactions with missing genes are
    skipped.

    Parameters
    ----------
    model : cobra.Model
        The metabolic model under investigation.

    Returns
    -------
    list
        A list of sets of duplicate reactions based on genes.

    """
    duplicates = dict()
    for rxn_a, rxn_b in combinations(model.reactions, 2):
        try:
            symm_difference = rxn_a.genes ^ rxn_b.genes
        except TypeError:
            continue
        else:
            if len(symm_difference) == 0:
                duplicates.setdefault(rxn_a.genes, set())
                duplicates[rxn_a.genes].update([rxn_a.id, rxn_b.id])
    return list(duplicates.values())


def check_transport_reaction_gpr_presence(model):
    """Return the list of transport reactions that have no associated gpr."""
    return [rxn for rxn in helpers.find_transport_reactions(model)
            if not rxn.gene_reaction_rule]


def find_medium_metabolites(model):
    """Return the list of metabolites ingested/excreted by the model."""
    return [met.id for rxn in model.medium
            for met in model.reactions.get_by_id(rxn).metabolites]
