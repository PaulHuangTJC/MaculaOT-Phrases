#!/usr/bin/env python3
"""
phrase_checker.py

Extracts phrase-pair relationships (V-S, V-O, PrepNP, NPofNP, ...) from the
Hebrew syntax-tree XML files and writes them to a single CSV.

------------------------------------------------------------------------
VALIDATION AGAINST THE FULL WLC CORPUS (Aug 2026)
------------------------------------------------------------------------
This version was tested against all 930 book-chapter files in
https://github.com/Clear-Bible/macula-hebrew/tree/main/WLC/nodes (the
entire Hebrew Bible, not just the one sample chapter). Of the 82 phrase
types in tPhraseType(DB).csv, 40 are now populated with real data (up from
24 before this pass), and every rule seen in the full corpus produces at
least one record except two single-occurrence malformed nodes
("12Np", "2Advp_h1" -- 1 and 4 hits total, almost certainly transcription
glitches in the source XML rather than a real pattern).

New in this pass, on top of the original three mechanisms below:
  - Negation detection (Strong's 3808/408/1115/369/3809/1077/1097, i.e.
    lo/al/bilti/eyn/Aramaic la/bal/beli): an ADV-V pairing where the
    adverb is one of these is now correctly labelled Neg-V rather than
    generic ADV-V, mirroring the user's original notice. Neg-Adjp
    (negator + adjectival predicate) is handled the same way. No generic
    Neg-X/X-Neg fallback.
  - Neg-Np / Np-Neg (UPDATED): no longer phrase_checker's own two-
    pattern, terminal-adjacency-only logic. This phrase type now runs
    the SAME extraction engine as the standalone noun_negation_
    extractor_v10.py script -- full Head-attribute/apposition-aware head
    resolution (incl. Rule=2Np dual-noun apposition), word-order-
    agnostic clause-pattern matching, the S1.4a substantive-adjective/
    participle override (participle-only; Vp2Np infinitives excluded
    per v10/S1.4a literal text), P-as-negator existential particles,
    coordinated-PP ADV-P exclusion, and the S1.4d ADV-PP categorical
    exclusion -- covering both NP-level (AdvpNp -> Neg-Np, NpAdvp ->
    Np-Neg) and CL-level (ADV-S, ADV-O, ADV-S-PP, ADV-O-PP, ADV-S-P,
    ADV-S-P-PP, ADV-P) negation. See the "Neg-Np / Np-Neg extraction"
    section further down (functions prefixed `nnx_`) for the full port.
  - Copula detection (Strong's 1961, haya "to be"): S-V/V-S, VerbPrep/
    PrepVerb pairings involving this verb are now labelled with the more
    specific VC-S/S-VC/VCPrep/PrepVC/VC-ADV. (VC-P/P-VC never fire because
    a 'P' role never actually co-occurs with a 'V' role anywhere in the
    corpus -- confirmed empirically, not a bug.)
  - NpAdjp/AdjpNp sub-typing: looking inside the adjective slot now
    distinguishes plain NPAdjp/AdjpNP from NPDetAdj (adjective built via
    DetAdjp, i.e. article+adjective agreement), Np-Demo/Demo-NP (the
    "adjective" is actually a demonstrative pronoun, pos='pronoun'), and
    PtcpNP (the "adjective" is actually a participle, pos='verb').
  - QuanNp -> All-NP and AdvpNp -> AdvNP (rule names that don't survive
    normalisation-based matching against the DB names).
  - EitherOrNp: (np, cjp, np) coordination is now checked for או ("or",
    Strong's 176/176a) and labelled EitherOrNp instead of plain Conj2NP
    when found.
  - V-IO can now also come out as IO-V: the two are distinguished by
    comparing each side's position in the verse (parsed from the '!N'
    suffix macula puts on the verse-index string) rather than always
    assuming the verb comes first.

Three independent extraction strategies run over every sentence:

1. CLAUSE-LEVEL ROLE PAIRS
   Many `Rule` values in the XML are themselves a dash-joined sequence of
   role tags that match the `Cat` of the node's direct children exactly,
   e.g. Rule="V-S-O" has children Cat="V","S","O"; Rule="ADV-V-O-S" has
   children Cat="ADV","V","O","S". Such a node is a "clause pattern" node.
   For every pair of roles present in a clause-pattern node (not just
   adjacent ones -- V and O in V-S-O are not adjacent but V-O is still a
   real relationship) we test both orderings ("V-O" and "O-V") against
   tPhraseType(DB).csv, substituting more specific role labels (VC, Neg,
   Adjp -- see above) where applicable. This single mechanism produces
   V-S/S-V, V-O/O-V, V-O2/O2-V, ADV-V/V-ADV, S-P/P-S, S-VC/VC-S, VC-ADV,
   Neg-V, Neg-Adjp, ... automatically, for every clause pattern rule found
   in the file, without hard-coding each one.

   Special case per the user's notice: "V-S comes from V+S, V-O comes
   from V + main verb of O". When the partner role is an Object-like role
   (O, O2) we first check whether that role's own sub-tree is itself a
   clause (i.e. contains a nested Cat='V' -- an embedded/complement
   clause). If so we pair with that embedded verb, mirroring v0's
   behaviour. If the object is a plain noun phrase we now correctly fall
   back to its head noun (v0 silently produced nothing in this case --
   this was a gap in v0, now fixed).

2. DIRECT RULE-NAME MATCHES (word/phrase-level combinations)
   Rule names such as `NPofNP`, `PrepNp`, `Np-Appos`, `NpAdjp`, `NpPp`,
   `NpAdvp`, ... are, once punctuation/case is stripped, literally the
   same string as a PhraseType in the CSV (PrepNp -> PrepNP, Np-Appos ->
   NP-Appos, ...). Any 2-child Rule node whose normalised name matches a
   normalised DB PhraseType is emitted automatically using the head word
   of each child. A short RULE_NAME_OVERRIDES table covers the handful of
   names that don't survive normalisation (QuanNp -> All-NP, AdvpNp ->
   AdvNP). This is fully data-driven: if the DB gains a new type whose
   name matches a new Rule found in some other book's XML, it will be
   picked up with no code change.

3. COORDINATION (X and X / X or X)
   Rule nodes shaped like (X, cjp, X) -- e.g. NpaNp -> (np, cjp, np) --
   represent "X and X" coordination, mapped to the DB's `Conj2NP` /
   `Conj2Adjp` / `Conj2Adv` family by Cat, or to `EitherOrNp` when the
   conjunction is או ("or").

PLUS one legacy special case kept from v0, generalised:

4. V-IO / IO-V via nested PrepNp
   Wherever a `PrepNp` occurs anywhere in a sentence, we look for the
   *nearest* enclosing clause-pattern node that has a V role among its
   direct children (nearest-governor, computed via real parent pointers
   instead of v0's whole-sentence O(n^2) scan) and emit V-IO or IO-V
   (governing verb + the preposition's NP head, ordered by their actual
   position in the verse). VerbPrep/PrepVerb (or VCPrep/PrepVC for the
   copula) is emitted separately whenever V and PP are siblings in the
   same clause pattern node, pairing V with the preposition word itself.

------------------------------------------------------------------------
STILL UNMAPPED, AND WHY (confirmed empirically against all 930 files,
not guessed):
------------------------------------------------------------------------
- The entire PreC-*/PreO-*/PreS-*/PtcO-*/IO-*(except V-IO/IO-V)/Noun-Sfx
  family, plus a bare "PreS"/"PreO"/"PtcO"/"PrcS": these role tags
  (PreC, PreO, PreS, PtcO, IO, VC as a *Cat*) never appear anywhere in
  the XML's `Cat` attribute across the full corpus. They appear to
  describe morphological features (pronominal suffixes on verbs/nouns)
  rather than tree-shape/Cat distinctions, so they can't be recovered
  from tree structure the way everything above was -- they'd need a
  second pass over each terminal's `morph`/suffix attributes. Tell me
  what the suffix encoding looks like (or point me at an example) and
  I can add that as a distinct (morphology-based, not tree-shape-based)
  extraction mechanism.
- VC-P / P-VC: structurally impossible in this corpus -- a 'P' (Predicate)
  role and a 'V' role never co-occur as siblings anywhere in the 930
  files (verbless clauses use S-P; clauses with an explicit copula verb
  use the ordinary V-headed patterns instead of a separate P slot).
- `ofNPNP` (as opposed to `NPofNP`): no structural signal (e.g. a Head=1
  marker) distinguishes the two in the data -- every (np, np) construct
  chain is currently labelled NPofNP. If ofNPNP means something
  structurally different, tell me and I'll split the logic.
- `NotNpButNP`: no Hebrew "but"-type coordinating conjunction was found
  joining two NPs anywhere in the sampled coordination nodes (Hebrew
  contrast is usually expressed differently, not via cjp coordination).
- `Appo` (as distinct from the already-implemented `NP-Appos`),
  `NPAdjunct`, `V-O-Ellip`, `PreX-V`, `Prep-V`, `PP-NP` (possibly a
  duplicate of PrepNP): no distinguishing structural pattern was found
  for these in the full corpus; they may be rare enough to need manual
  examples, or may be near-duplicates of types already implemented.

Usage
------------------------------------------------------------------------
    python3 phrase_checker.py --input-dir <folder-of-xml> --output-csv <result.csv> \
        [--db-csv tPhraseType_DB_.csv]

Defaults: --input-dir ./xml_input  --output-csv ./phrase_relationships.csv
          --db-csv ./tPhraseType_DB_.csv
"""

import argparse
import csv
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

XML_NS = '{http://www.w3.org/XML/1998/namespace}'

# Cat -> a short "role name" used to build coordination PhraseType names
# (np -> NP gives NpaNp -> Conj2NP, etc.)
# NOTE: 'PP' (capitalised) is included alongside 'pp' because this corpus
# uses both castings for prepositional-phrase nodes (Cat="pp" for the
# inner PrepNp/PPandPP layer, Cat="PP" for the outer Pp2PP/NP2PP wrapper),
# and either casing can in principle appear as the coordination node's Cat.
COORD_CAT_ROLE = {
    'np': 'NP',
    'adjp': 'Adjp',
    'advp': 'Adv',
    'vp': 'VP',
    'pp': 'Pp',
    'PP': 'Pp',
    'prep': 'Pp',
}

# Node Cats that are "function words" we skip over when hunting for the
# head word of a phrase (object markers, articles). Skipping these means
# V-O pairs with e.g. "et ha-ish" correctly report the noun ish, not the
# object-marker particle.
SKIP_HEAD_CATS = {'omp', 'om', 'art'}

# Strong's numbers for the core Hebrew negative particles (lo, al, bilti,
# eyn, Aramaic la, bal, beli). Used to distinguish plain "ADV-V" from the
# more specific "Neg-V"/"Neg-Adjp"/"Neg-Np" DB phrase types.
NEGATION_STRONGS = {'3808', '408', '1115', '369', '3809', '1077', '1097'}

# Strong's number for the Hebrew copula verb "to be" (haya). Used to
# distinguish plain V-S/S-V/V-P/.../VerbPrep from the more specific
# VC-S/S-VC/VC-P/P-VC/VC-ADV/VCPrep/PrepVC DB phrase types.
COPULA_STRONGS = {'1961'}

# PhraseTypes that we intentionally exclude from the output even if the
# extractor can synthesize them from tree shape.
#
# Motivation:
# - coordination chains like (CL, cjp, CL) may have empty/blank Rule in the
#   XML, but _coord_full_phrase_type() synthesises them as CLaCL / Conj{n}CL.
# - Some users want those sentence-level "whole-chain rows" skipped while
#   keeping all other phrase types untouched.
SKIP_PHRASE_TYPE_PATTERNS = [
    re.compile(r'^CLaCL$', re.IGNORECASE),
    re.compile(r'^CLandCL\d', re.IGNORECASE),
    re.compile(r'^Conj\d+CL$', re.IGNORECASE),
    re.compile(r'^NpaNp', re.IGNORECASE),
    re.compile(r'^AdjpaAdjp', re.IGNORECASE),
    re.compile(r'^PPandPP', re.IGNORECASE),
    re.compile(r'^AdvpaAdvp', re.IGNORECASE),
    re.compile(r'^AdvpandAdvp', re.IGNORECASE),
    re.compile(r'^VPandVP', re.IGNORECASE),
]



def should_skip_phrase_type(phrase_type):
    pt = (phrase_type or '').strip()
    if not pt:
        return False
    return any(pat.match(pt) for pat in SKIP_PHRASE_TYPE_PATTERNS)


def _strong_key(strong):
    return (strong or '').lstrip('0') or '0'


def is_negator(head):
    return bool(head) and _strong_key(head['strong']) in NEGATION_STRONGS


def is_copula(head):
    return bool(head) and _strong_key(head['strong']) in COPULA_STRONGS


# --------------------------------------------------------------------------
# DB loading
# --------------------------------------------------------------------------
def norm(s):
    """Normalise a name for loose matching: lowercase, strip non-alnum."""
    return re.sub(r'[^a-z0-9]', '', (s or '').lower())


def load_phrase_db(db_csv_path):
    """Returns (valid_names set, {normalised_name: canonical_PhraseType},
    ordered list of DB row dicts with PhraseType/Name/Chinese/PhraseTypeID)."""
    valid = set()
    norm_map = {}
    db_rows = []
    with open(db_csv_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            pt = row['PhraseType'].strip()
            if not pt:
                continue
            valid.add(pt)
            norm_map[norm(pt)] = pt
            db_rows.append({
                'PhraseTypeID': (row.get('PhraseTypeID') or '').strip(),
                'PhraseType': pt,
                'Name': (row.get('Name') or '').strip(),
                'Chinese': (row.get('Chinese') or '').strip(),
            })
    return valid, norm_map, db_rows


# --------------------------------------------------------------------------
# Tree helpers
# --------------------------------------------------------------------------
def build_parent_map(root):
    parent = {}
    for node in root.iter('Node'):
        for child in list(node):
            if child.tag == 'Node':
                parent[child] = node
    return parent


def node_word_info(m, term_node):
    """Build the {strong, word, macula, gloss} dict for a terminal <m> tag
    and its wrapping terminal Node (which usually carries StrongNumberX/n).

    NOTE: the <m> tag's `word` ATTRIBUTE is actually a verse/word-index
    reference (e.g. "GEN 30:1!1"), not the Hebrew text -- v0 used this
    attribute directly, which meant its "Words" column never actually
    contained a Hebrew word. The real Hebrew text is the element's text
    content, so that's what's used here instead."""
    strong = term_node.attrib.get('StrongNumberX', '') or m.attrib.get('oshb-strongs', '')
    macula = term_node.attrib.get('n', '') or m.attrib.get(f'{XML_NS}id', '')
    return {
        'strong': strong,
        'word': (m.text or '').strip(),
        'gloss': m.attrib.get('english', '') or m.attrib.get('gloss', ''),
        'macula': macula,
        'verse_index': m.attrib.get('word', ''),  # e.g. "GEN 30:1!1"
        'pos': m.attrib.get('pos', ''),
    }


def first_m_in_subtree(node, skip_cats=None):
    """Depth-first search for the first <m> terminal in document order,
    optionally skipping entire sub-trees whose Cat is in skip_cats
    (used to skip object markers / articles when hunting for a head word).
    Returns the word-info dict, or None."""
    skip_cats = skip_cats or set()

    def walk(n):
        # direct <m> child (n is the terminal wrapper Node)
        for child in list(n):
            if child.tag == 'm':
                return node_word_info(child, n)
        for child in list(n):
            if child.tag == 'Node' and child.attrib.get('Cat') in skip_cats:
                continue
            if child.tag == 'Node':
                found = walk(child)
                if found:
                    return found
        return None

    return walk(node)


def find_descendant_by_cat(node, cat, skip_cats=None):
    """First descendant Node (breadth/doc-order) with the given Cat,
    not crossing into a subtree whose own Cat is in skip_cats."""
    skip_cats = skip_cats or set()
    for child in list(node):
        if child.tag != 'Node':
            continue
        if child.attrib.get('Cat') == cat:
            return child
        if child.attrib.get('Cat') in skip_cats:
            continue
        found = find_descendant_by_cat(child, cat, skip_cats)
        if found is not None:
            return found
    return None


def head_word(node, skip_cats=None):
    """Head word for ANY sub-tree, found by following the tree's own
    `Head` attribute at every branching level, instead of just grabbing
    the first terminal in document order.

    Every multi-child Node in this treebank carries a `Head` attribute
    that is the 0-based index of the child that is the linguistic head
    of that node -- e.g. Cat="S" Rule="Np2S" Head="0" has one child, but
    Cat="np" Rule="cjpNp" Head="1" has children (cjp, np) and Head="1"
    tells us the *second* child (the np) is the head, not the cjp/adverb
    ("gam", "also") sitting in front of it. Likewise DetNP (art, np) has
    Head="1" (skip the article), ObjMarker (omp, np) has Head="1" (skip
    the object marker), and the N-ary coordination rules (Conj3Np,
    Conj5Np, ...) point Head at the *last* conjunct.

    This is what v0/v1 got wrong for clause-level S/O/... roles whose
    own sub-tree happens to start with a conjunction/particle/adjunct
    node: a plain "first <m> in document order" walk (the old
    first_m_in_subtree) picks up that leading function word instead of
    the real head noun. Following Head fixes it structurally, for every
    role, not just S.

    skip_cats is kept as a defensive fallback only, for the rare case a
    Head index is missing/out-of-range/malformed in the source XML; in
    that situation we prefer a child whose Cat isn't a known function-word
    Cat (object markers, articles) over blindly taking child 0.
    """
    skip_cats = skip_cats or set()
    # direct terminal: this Node wraps an <m> directly.
    for child in list(node):
        if child.tag == 'm':
            return node_word_info(child, node)

    children = [c for c in list(node) if c.tag == 'Node']
    if not children:
        return None
    if len(children) == 1:
        return head_word(children[0], skip_cats)

    head_attr = node.attrib.get('Head')
    idx = None
    if head_attr is not None:
        try:
            idx = int(head_attr)
        except ValueError:
            idx = None

    chosen = None
    if idx is not None and 0 <= idx < len(children) and children[idx].attrib.get('Cat') not in skip_cats:
        chosen = children[idx]
    if chosen is None:
        chosen = next((c for c in children if c.attrib.get('Cat') not in skip_cats), children[0])
    return head_word(chosen, skip_cats)


def direct_object_clause(node):
    """True complement-clause detection for an O/O2 role: the object IS a
    clause only when the role node's own DIRECT child is Cat='CL' (the
    Rule2CL2Ox pattern, e.g. Gen 2:19 "whatever he calls it" -- O's only
    child is a full CL). Returns that CL child, or None.

    This is intentionally shallow (checks only the immediate child), NOT
    a recursive/unbounded search of the whole O subtree. An unbounded
    search is wrong: a plain NP object can carry a *relative-clause
    modifier* several levels down (Cat='np' Rule='NpRelp' -> Cat='relp'
    Rule='relCL' -> Cat='CL'), e.g. Gen 2:2's O = 'his work
    (מְלַאכְתּוֹ) which he had done (אֲשֶׁר עָשָׂה)'. That relative
    clause also contains a Cat='V' node, but it modifies the noun --
    it is not the object itself. Treating 'contains a V anywhere' as
    'is a complement clause' incorrectly pulls in the relative clause's
    verb ('done') as the V-O partner instead of the true object head
    ('work')."""
    children = [c for c in list(node) if c.tag == 'Node']
    if len(children) == 1 and children[0].attrib.get('Cat') == 'CL':
        return children[0]
    return None


def smart_object_head(node):
    """Head word for an O/O2-type role: if the role node itself directly
    wraps a clause (see direct_object_clause -- a genuine verbal
    complement clause, not merely a relative clause buried inside an
    NP), use that embedded clause's verb as the head. Otherwise use the
    object's own head noun, following the tree's Head attribute (which
    already correctly skips past any relative-clause modifier on its
    own, since NpRelp's Head index points at the NP conjunct, not the
    relp conjunct)."""
    embedded_cl = direct_object_clause(node)
    if embedded_cl is not None:
        embedded_v = find_descendant_by_cat(embedded_cl, 'V')
        if embedded_v is not None:
            head = head_word(embedded_v, skip_cats=SKIP_HEAD_CATS)
            if head:
                return head
    return head_word(node, skip_cats=SKIP_HEAD_CATS)


def plain_head(node):
    """Head word for a role that isn't object-like: follow the tree's
    Head attribute down to the real head word (falling back to skipping
    function-word sub-trees only if Head is missing/malformed)."""
    return head_word(node, skip_cats=SKIP_HEAD_CATS)


def prep_word_head(pp_or_prepnp_node):
    """The preposition word itself is (by construction) the very first
    terminal in a PP / PrepNp sub-tree, so no skipping is needed here."""
    return first_m_in_subtree(pp_or_prepnp_node)


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------
def is_clause_pattern_node(node):
    """A node is a 'clause pattern' node if Rule is dash-joined and each
    token equals the Cat of the corresponding direct child, in order."""
    rule = node.attrib.get('Rule', '')
    if '-' not in rule:
        return False
    children = [c for c in list(node) if c.tag == 'Node']
    toks = rule.split('-')
    if len(toks) != len(children):
        return False
    return all(t == c.attrib.get('Cat') for t, c in zip(toks, children))


def head_for_role(cat, role_node):
    if cat in ('O', 'O2', 'IO'):
        return smart_object_head(role_node)
    return plain_head(role_node)


def make_record_multi(phrase_type, node_id, heads, source_file, verse):
    """Like make_record, but for an arbitrary number (>=2) of head words --
    used by the clause-level structural (Feature 1) and full-coordination
    (Feature 2) extractors, which report every child/conjunct in one row
    instead of just a single A/B pair."""
    return {
        'PhraseType': phrase_type,
        'ParentNodeID': node_id,
        'StrongIDs': ' | '.join(h['strong'] for h in heads),
        'Words': ' | '.join(h['word'] for h in heads),
        'Gloss': ' | '.join(h['gloss'] for h in heads),
        'MaculaID': ' | '.join(h['macula'] for h in heads),
        'VerseIndex': ' | '.join(h['verse_index'] for h in heads),
        'SourceFile': source_file,
        'Verse': verse,
    }


def make_record(phrase_type, node_id, head_a, head_b, source_file, verse):
    return make_record_multi(phrase_type, node_id, [head_a, head_b], source_file, verse)


def role_candidates(cat, node, head):
    """Return an ordered list of candidate role-labels to try when building
    a PhraseType name for this role, most-specific first:
      - V realized by the copula verb (haya) -> also try 'VC'
      - ADV realized by a negative particle -> also try 'Neg'
      - P realized by an adjective phrase -> also try 'Adjp' (needed for
        'Neg-Adjp', which pairs with the *word class* not the role name)
    Falls back to the plain role/Cat itself last.

    NOTE: Neg-Np / Np-Neg are NOT produced via a generic 'Np' candidate
    here. They are handled by the dedicated nnx_extract_cl_patterns() /
    nnx_extract_np_patterns() engine (ported from
    noun_negation_extractor_v10.py -- see the "Neg-Np / Np-Neg
    extraction" section below) so that Neg-V and Neg-Adjp continue to
    win through this product alone.
    """
    cands = []
    if cat == 'V' and is_copula(head):
        cands.append('VC')
    if cat == 'ADV' and is_negator(head):
        cands.append('Neg')
    if cat == 'P':
        children = [c for c in list(node) if c.tag == 'Node']
        if children and children[0].attrib.get('Cat') == 'adjp':
            cands.append('Adjp')
    cands.append(cat)
    return cands


# ==========================================================================
# Neg-Np / Np-Neg extraction -- ported from noun_negation_extractor_v10.py
# ==========================================================================
# Per user request, this phrase type no longer uses phrase_checker's own
# (older, narrower) two-pattern logic. It now runs the SAME extraction
# engine as the standalone noun_negation_extractor_v10.py script: full
# Head-attribute/apposition-aware head resolution (spec S0/S0.1, incl.
# Rule=2Np dual-noun apposition), word-order-agnostic clause-pattern
# matching (canonical_cl_pattern()), the S1.4a substantive-adjective/
# participle override (participle-only -- v10 reverts v9's infinitive
# extension; PSA 75:7 stays excluded as an open S1.4a question),
# P-as-negator existential particles (S5.1/S5.2), coordinated-PP ADV-P
# exclusion (S1.4d / Action Item 17), and the S1.4d ADV-PP categorical
# exclusion. See noun_negation_extractor_v10.py's own module docstring
# for the full derivation history of each of these.
#
# Functions below are direct ports and are prefixed `nnx_` (noun-negation-
# extractor) so they read as a distinct, traceable unit and don't collide
# with phrase_checker's own (differently-scoped) helpers of similar name
# (e.g. phrase_checker's is_negator() checks a Strong's-number allow-list
# and is used for Neg-V/Neg-Adjp; the ported nnx_has_negative_particle()
# checks the type='negative' attribute instead -- the authoritative
# negation signal per noun_negation_extractor_v10.py -- and is used only
# for Neg-Np/Np-Neg, exactly as in that script).
#
# WHAT CHANGED vs phrase_checker's OLD Neg-Np/Np-Neg logic:
#   - OLD: two hand-rolled patterns (extract_neg_np_constituent /
#     extract_neg_np_clause_pairs, now removed) requiring literal
#     terminal-index adjacency (n / n+1) between the negator and a
#     noun/pronoun -- one for NP/PP constituents, one for verbless-clause
#     ADV+S/P siblings -- using only plain_head()/first_m_in_subtree(),
#     with no apposition handling and no substantive-adjective override.
#   - NEW: the full noun_negation_extractor_v10.py engine --
#       NP-level:  Rule=AdvpNp -> Neg-Np, Rule=NpAdvp -> Np-Neg (type=
#                  'negative' filter + noun/pronoun-anywhere-inside
#                  filter, same as v10's extract_np_patterns()).
#       CL-level:  ADV-S, ADV-O, ADV-S-PP, ADV-O-PP, ADV-S-P (and
#                  ADV-S-P-PP), ADV-P -- matched by the SET of a clause's
#                  direct-child Cats (word-order-agnostic), not by
#                  Rule-string equality, with full resolve_head() /
#                  resolve_apposition() / classify_predicate() logic
#                  (construct-chain substantive override for adjective/
#                  participle only; 2Np dual-noun extra_heads;
#                  P-as-negator; coordinated-PP ADV-P skip).
#                  ADV-PP is a *categorical exclusion* (spec S1.4d) and
#                  never produces a Neg-Np/Np-Neg row, regardless of
#                  what noun sits inside the PP.
#   - Strict n/n+1 adjacency is no longer required: a match now only
#     needs to be one of v10's own validated constructions (already
#     confirmed against the full 930-file corpus in that script). Verse
#     word order (negator before vs. after its target's resolved head)
#     is used only to choose the "Neg-Np" (negator-first) vs "Np-Neg"
#     (noun-first) label -- mirroring AdvpNp -> Neg-Np / NpAdvp -> Np-Neg
#     at the CL level too, instead of always assuming negator-first.
# ==========================================================================

nnx_NP_PATTERN_NAMES = {'AdvpNp', 'NpAdvp'}

nnx_NOUN_LIKE_POS = {'noun', 'pronoun'}
# ^ resolve_simple()'s bare S/O test only (spec S1.1/S1.2/S1.5/S1.6).
#   classify_predicate()'s P-equative test does NOT use this -- it checks
#   pos == 'noun' specifically (a bare-pronoun P is 'anaphoric_pronoun_
#   only', not equative -- verified against JER 14:22).
nnx_COPULAR_ADJ_POS = {'adjective'}
nnx_COPULAR_ADV_POS = {'adverb'}

nnx_CONSTRUCT_CHAIN_RULES = frozenset({
    'NPofNP', 'Adj2NP', 'Vp2Np',
})
# ^ spec S1.4a / S5: nominal-construct wrappers whose Head=0 member can
#   be a substantive adjective/participle ("slain-of-X", JOB 29:12
#   Vp2Np). Vp2Np-wrapped INFINITIVES are intentionally NOT covered
#   (v10 / PSA 75:7 -- outside S1.4a's literal adjective/participle
#   scope; open question, not decided in code).

nnx_EXISTENTIAL_PARTICLE_LEMMAS = frozenset({
    'יֵשׁ', 'אִיתַי', 'אַיִן', 'אֵין',
})
# ^ spec S5.2: lemma-based existential (and existential-negative)
#   particles realized as P via Advp2P -- S-primary, same as Pp2P.

nnx_NPINF_RULE = 'NpInf'
# ^ spec S1.3: idiomatic temporal-copular NpInf noun ("[not] the time
#   when..."), excluded even though it mechanically resolves to a noun.

nnx_CL_PATTERN_CONSTITUENT_SETS = {
    frozenset({'ADV', 'S'}): 'ADV-S',
    frozenset({'ADV', 'O'}): 'ADV-O',
    frozenset({'ADV', 'S', 'P'}): 'ADV-S-P',
    frozenset({'ADV', 'S', 'PP'}): 'ADV-S-PP',
    frozenset({'ADV', 'O', 'PP'}): 'ADV-O-PP',
    frozenset({'ADV', 'S', 'P', 'PP'}): 'ADV-S-P-PP',
    frozenset({'ADV', 'P'}): 'ADV-P',
    frozenset({'ADV', 'PP'}): 'ADV-PP',  # spec S1.4d: categorical exclusion
}


def nnx_canonical_cl_pattern(rule):
    """Map a Cat='CL' Rule string to a canonical pattern label by the SET
    of its dash-joined parts (word-order-agnostic), not by exact string
    match -- so 'S-ADV-P', 'ADV-P-S', 'P-ADV-S', ... all canonicalize to
    the same 'ADV-S-P' as 'ADV-S-P' itself. Returns (canonical, dup_cats);
    dup_cats is the frozenset of Cats named more than once in the Rule
    (e.g. frozenset({'ADV'}) for ADV-S-ADV-P). Callers must not skip on
    ADV/PP duplication alone (spec S5.1); only competing S/O/P duplicates
    are true ambiguity."""
    parts = rule.split('-') if rule else []
    if not parts:
        return None, frozenset()
    pset = frozenset(parts)
    dup_cats = frozenset(c for c in pset if parts.count(c) > 1)
    return nnx_CL_PATTERN_CONSTITUENT_SETS.get(pset), dup_cats


def nnx_direct_children_by_cat(node):
    """Map of Cat -> first matching direct <Node> child."""
    out = {}
    for child in list(node):
        if child.tag == 'Node':
            cat = child.attrib.get('Cat', '')
            if cat and cat not in out:
                out[cat] = child
    return out


def nnx_find_negative_adv_nodes(cl_node):
    """All direct ADV children that genuinely carry a type='negative'
    particle (spec S0 / S5.1). Used instead of taking only the first ADV
    when a clause Rule repeats the ADV Cat (ADV-ADV-P, ADV-S-ADV-P, ...)."""
    if cl_node is None:
        return []
    return [
        child for child in list(cl_node)
        if child.tag == 'Node'
        and child.attrib.get('Cat') == 'ADV'
        and nnx_has_negative_particle(child)
    ]


def nnx_has_negative_particle(node):
    """True if any <m> leaf under node (or node itself) has type='negative'.
    This is the authoritative negation signal (not a Strong's-number
    list) -- deliberately a descendant search, since ADV can wrap the
    negator through several advp/adv layers with no competing embedded-
    clause boundary the way S/O/P have."""
    if node is None:
        return False
    for morph in node.iter('m'):
        if morph.attrib.get('type') == 'negative':
            return True
    return False


def nnx_has_noun_or_pronoun(node):
    """True if any <m> leaf under node has pos in {noun, pronoun}. Used
    only for the NP-level (AdvpNp/NpAdvp) match test -- a blanket
    descendant search is fine there since these are single flat NPs, not
    clauses that can nest a whole competing embedded clause."""
    if node is None:
        return False
    for morph in node.iter('m'):
        if morph.attrib.get('pos') in ('noun', 'pronoun'):
            return True
    return False


def _nnx_leaf_m_child(current):
    """The lexical leaf directly borne by `current`: a plain <m> child,
    or (compound-lexeme case, e.g. 2SA 11:3's Bathsheba) the <m> inside a
    <c> wrapper. Never descends into a nested <Node>."""
    m = current.find('m')
    if m is not None:
        return m
    c = current.find('c')
    if c is not None:
        return c.find('m')
    return None


def _nnx_is_apposition_node(node):
    """Spec S0.1 (v5-narrowed + v8): trigger apposition-aware resolution
    on Rule='Np-Appos' or Rule='2Np' -- NOT on every node with >1 np-Cat
    child, since that also fires on ordinary NPofNP construct chains
    (verified corpus-wide; see noun_negation_extractor_v10.py). Rule=2Np
    is the ISA 57:4 dual-noun apposition shape."""
    if node is None:
        return False
    return node.attrib.get('Rule', '') in ('Np-Appos', '2Np')


def nnx_resolve_head(node, max_depth=40):
    """Walk a constituent node (S, O, P, PP, ...) down through its wrapper
    Rule/Head chain to its true lexical head (spec S0), handing off to
    nnx_resolve_apposition() at any Rule='Np-Appos'/'2Np' node (spec S0.1).
    Returns {'kind': 'lexical'|'pp'|'none', 'node', 'm', 'pos', 'path_rules'}
    (plus optional 'extra_heads' from dual-noun apposition).
    See noun_negation_extractor_v10.py's resolve_head() for full rationale."""
    current = node
    path_rules = []
    for _ in range(max_depth):
        if current is None:
            break
        m_child = _nnx_leaf_m_child(current)
        if m_child is not None:
            return {'kind': 'lexical', 'node': current, 'm': m_child,
                    'pos': m_child.attrib.get('pos', ''), 'path_rules': path_rules}

        cat = current.attrib.get('Cat', '')
        rule = current.attrib.get('Rule', '')
        if rule:
            path_rules.append(rule)

        if cat == 'pp':
            return {'kind': 'pp', 'node': current, 'm': None,
                    'pos': 'preposition', 'path_rules': path_rules}
        if cat == 'CL':
            return {'kind': 'none', 'node': current, 'm': None,
                    'pos': None, 'path_rules': path_rules}

        if _nnx_is_apposition_node(current):
            return nnx_resolve_apposition(current, path_rules, max_depth)

        children = [c for c in list(current) if c.tag == 'Node']
        if not children:
            return {'kind': 'none', 'node': current, 'm': None,
                    'pos': None, 'path_rules': path_rules}

        head_attr = current.attrib.get('Head', '')
        if not head_attr.lstrip('-').isdigit():
            return {'kind': 'none', 'node': current, 'm': None,
                    'pos': None, 'path_rules': path_rules}
        idx = int(head_attr)
        if not (0 <= idx < len(children)):
            return {'kind': 'none', 'node': current, 'm': None,
                    'pos': None, 'path_rules': path_rules}
        current = children[idx]

    return {'kind': 'none', 'node': current, 'm': None, 'pos': None,
            'path_rules': path_rules}


def nnx_resolve_apposition(node, path_rules_so_far, max_depth):
    """Spec S0.1 (+ Sept 3 dual-noun addendum): resolve EVERY direct child
    of an Np-Appos/2Np node (not just the Head-indexed one). Prefer a
    sibling that bottoms out at pos='noun'; when two or more do, return
    the first as primary with the rest under 'extra_heads' (ISA 57:4).
    Else prefer pronoun, else 'no lexical noun head' -- never crossing a
    Cat='CL' boundary. See noun_negation_extractor_v10.py."""
    children = [c for c in list(node) if c.tag == 'Node']
    branch_results = []
    for child in children:
        res = dict(nnx_resolve_head(child, max_depth=max_depth))
        res['path_rules'] = path_rules_so_far + res.get('path_rules', [])
        branch_results.append(res)

    noun_results = [r for r in branch_results
                    if r['kind'] == 'lexical' and r['pos'] == 'noun']
    if len(noun_results) >= 2:
        primary = dict(noun_results[0])
        primary['extra_heads'] = noun_results[1:]
        return primary
    if len(noun_results) == 1:
        return noun_results[0]
    for res in branch_results:
        if res['kind'] == 'lexical' and res['pos'] == 'pronoun':
            return res
    return {'kind': 'none', 'node': node, 'm': None, 'pos': None,
            'path_rules': path_rules_so_far}


def _nnx_is_participle_m(m):
    if m is None:
        return False
    return 'participle' in (m.attrib.get('type', '') or '').lower()


def _nnx_is_participle_or_infinitive_m(m):
    """v9 ADDED, v10 REVERTED -- kept only as a documented dead end so
    this reasoning error is not silently remade. Spec S1.4a names
    adjective or verb/participle only; an infinitive construct is
    neither. Matching code now uses _nnx_is_participle_m() exclusively."""
    if m is None:
        return False
    t = (m.attrib.get('type', '') or '').lower()
    return 'participle' in t or 'infinitive' in t


def _nnx_is_unreverted_infinitive_construct_use(res):
    """v10: True for the PSA 75:7 shape -- pos='verb', type contains
    'infinitive', reached via Vp2Np. Not an inclusion decision; phrase_
    checker has no exclusions CSV, but this helper marks the open
    S1.4a question (should the override extend to infinitives?) so
    callers can treat it distinctly from a generic non-match."""
    if res is None or res.get('kind') != 'lexical' or res.get('pos') != 'verb':
        return False
    m = res.get('m')
    t = (m.attrib.get('type', '') or '').lower() if m is not None else ''
    if 'infinitive' not in t:
        return False
    return 'Vp2Np' in res.get('path_rules', [])


def _nnx_is_existential_particle_m(m):
    """True when P's resolved head is an existential particle
    (יֵשׁ / אִיתַי / אַיִן / אֵין) -- S-primary per S1.4 / S5.2
    (lemma-based check)."""
    if m is None:
        return False
    if 'existential' in (m.attrib.get('type', '') or '').lower():
        return True
    lemma = m.attrib.get('lemma', '')
    return lemma in nnx_EXISTENTIAL_PARTICLE_LEMMAS


def _nnx_is_pp_coordination(pp_node):
    """Action Item 17: True when a PP has a direct Cat='cjp' child
    (PPandPP / Conj3Pp / ...). Bare ADV-P with a coordinated-PP adjunct
    is categorically excluded like ADV-PP (spec S1.4d / 2KI 3:2)."""
    if pp_node is None:
        return False
    return any(
        c.tag == 'Node' and c.attrib.get('Cat') == 'cjp'
        for c in list(pp_node)
    )


def nnx_substantive_override(res):
    """Spec S1.4a / S5 / v10: a resolved adjective or participle head is
    a noun-equivalent when any Rule in CONSTRUCT_CHAIN_RULES (NPofNP,
    Adj2NP, Vp2Np) appears on its resolve path. Infinitives are NOT
    included (v10 reverts v9's PSA 75:7 extension -- S1.4a literal text
    names only adjective or verb/participle)."""
    if res is None or res.get('kind') != 'lexical':
        return False
    pos = res.get('pos')
    is_adjective = pos == 'adjective'
    is_participle = pos == 'verb' and _nnx_is_participle_m(res.get('m'))
    if not (is_adjective or is_participle):
        return False
    path_rules = res.get('path_rules', [])
    return any(r in nnx_CONSTRUCT_CHAIN_RULES for r in path_rules)


def nnx_resolve_pp_object(pp_node):
    """Resolve the NP object inside a PP (PrepNp / Pp2P complement).
    Returns (included, head_result) with the same semantics as
    nnx_resolve_simple() -- used for bare ADV-P + Pp2P (spec S1.3/S5.3)."""
    empty = {'kind': 'none', 'node': None, 'm': None, 'pos': None, 'path_rules': []}
    if pp_node is None:
        return False, empty

    children = [c for c in list(pp_node) if c.tag == 'Node']
    np_child = None
    for ch in children:
        if ch.attrib.get('Cat') == 'np':
            np_child = ch
            break
    if np_child is None:
        head_attr = pp_node.attrib.get('Head', '')
        if head_attr.lstrip('-').isdigit():
            idx = int(head_attr)
            if 0 <= idx < len(children):
                candidate = children[idx]
                if candidate.attrib.get('Cat') == 'np':
                    np_child = candidate
    if np_child is None:
        for ch in children:
            if ch.attrib.get('Cat') in ('pp', 'PP'):
                return nnx_resolve_pp_object(ch)
        return False, empty
    return nnx_resolve_simple(np_child)


def nnx_resolve_simple(constituent_node):
    """spec S1.1/S1.2/S1.5/S1.6 (and S1.4a's PSA 16:2 locative-S case):
    included iff the resolved head is noun/pronoun, or a construct-
    embedded substantive adjective/participle (S1.4a). Returns
    (included: bool, head_result: dict)."""
    if constituent_node is None:
        return False, {'kind': 'none', 'node': None, 'm': None, 'pos': None, 'path_rules': []}
    res = nnx_resolve_head(constituent_node)
    included = (res['kind'] == 'lexical' and res['pos'] in nnx_NOUN_LIKE_POS) or nnx_substantive_override(res)
    return included, res


def nnx_classify_predicate(p_node):
    """Six/seven-way classification of a P constituent for ADV-P / ADV-S-P
    / ADV-S-P-PP (spec S1.3/S1.4/S1.7, plus S1.4a's substantive override
    and existential-particle handling). Returns (clause_type, include,
    use_target, head_result). See noun_negation_extractor_v10.py's
    classify_predicate() for the full per-branch rationale."""
    if p_node is None:
        return ('no_predicate', False, None, None)

    res = nnx_resolve_head(p_node)

    if nnx_NPINF_RULE in res['path_rules']:
        return ('temporal_copular_idiom', False, None, res)
    if res['kind'] == 'pp':
        return ('locative_existential', True, 'S', res)
    if res['kind'] == 'none':
        return ('anaphoric_no_head_noun', False, None, res)

    pos = res['pos']
    if pos in nnx_COPULAR_ADJ_POS:
        if nnx_substantive_override(res):
            return ('equative_predicate_nominal', True, 'P', res)
        return ('copular_adjective', False, None, res)
    if pos in nnx_COPULAR_ADV_POS:
        return ('copular_adverb', False, None, res)
    if pos == 'noun':
        return ('equative_predicate_nominal', True, 'P', res)
    if pos == 'pronoun':
        return ('anaphoric_pronoun_only', False, None, res)
    if pos == 'verb':
        # S1.4a: participle only (v10 -- infinitives not in S1.4a's text).
        if _nnx_is_participle_m(res.get('m')):
            if nnx_substantive_override(res):
                return ('equative_predicate_nominal', True, 'P', res)
            return ('copular_verbal', False, None, res)
        return ('unclassified_pos_verb_non_participle', False, None, res)
    if pos == 'particle':
        # S5.2: existential (incl. אַיִן/אֵין) as P via Advp2P ->
        # same locative_existential / S-primary row as kind=='pp'.
        if _nnx_is_existential_particle_m(res.get('m')):
            return ('locative_existential', True, 'S', res)
        return ('unclassified_pos_particle', False, None, res)
    return (f"unclassified_pos_{pos or 'unknown'}", False, None, res)


def _nnx_negator_heads(adv_node):
    """All type='negative' <m> leaves under adv_node, converted to
    phrase_checker's own head-word dict shape via node_word_info() (so
    Neg-Np/Np-Neg records get the exact same StrongIDs/Words/Gloss/
    MaculaID/VerseIndex columns as every other phrase type). Deliberately
    independent of phrase_checker's Strong's-number-based is_negator():
    the type='negative' attribute is the authoritative signal (see
    LEV 11:4's אַ֤ךְ, type='affirmation', in the module docstring)."""
    heads = []
    for term_node in adv_node.iter('Node'):
        m = term_node.find('m')
        if m is None:
            c = term_node.find('c')
            m = c.find('m') if c is not None else None
        if m is not None and m.attrib.get('type') == 'negative':
            heads.append(node_word_info(m, term_node))
    return heads


def _nnx_head_dict_from_resolved(res):
    """Convert an nnx_resolve_head()/nnx_classify_predicate() 'lexical'
    result into phrase_checker's head-word dict shape via node_word_info()."""
    if not res or res.get('kind') != 'lexical':
        return None
    m, term_node = res.get('m'), res.get('node')
    if m is None or term_node is None:
        return None
    return node_word_info(m, term_node)


def _nnx_order_pair(neg_head, target_head, valid_names):
    """Order a (negator, target) pair by verse position: negator-before-
    target -> Neg-Np, target-before-negator -> Np-Neg -- mirroring
    AdvpNp -> Neg-Np / NpAdvp -> Np-Neg at the CL level too, where the
    Rule string's word order isn't fixed. Falls back to Neg-Np (Biblical
    Hebrew's normal preposed-negator order) if a position can't be
    parsed on either side, rather than silently dropping a real v10 match."""
    neg_pos = _word_position(neg_head)
    tgt_pos = _word_position(target_head)
    if neg_pos is not None and tgt_pos is not None and neg_pos != tgt_pos:
        if neg_pos < tgt_pos and 'Neg-Np' in valid_names:
            return 'Neg-Np', neg_head, target_head
        if tgt_pos < neg_pos and 'Np-Neg' in valid_names:
            return 'Np-Neg', target_head, neg_head
        return None
    if 'Neg-Np' in valid_names:
        return 'Neg-Np', neg_head, target_head
    return None


def nnx_extract_np_patterns(node, valid_names, source_file, verse, hit_counter):
    """Port of noun_negation_extractor_v10.py's extract_np_patterns():
    Rule='AdvpNp' -> Neg-Np, Rule='NpAdvp' -> Np-Neg. Mandatory
    type='negative' filter on the advp child (not a Strong's-number
    match) plus a noun/pronoun-anywhere-inside filter on the np child."""
    records = []
    if 'Neg-Np' not in valid_names and 'Np-Neg' not in valid_names:
        return records
    rule = node.attrib.get('Rule', '')
    if rule not in nnx_NP_PATTERN_NAMES:
        return records
    constituents = nnx_direct_children_by_cat(node)
    advp = constituents.get('advp')
    np_child = constituents.get('np')
    if advp is None or np_child is None:
        return records
    neg_heads = _nnx_negator_heads(advp)
    if not neg_heads:
        return records  # e.g. LEV 11:4 אַ֤ךְ (type='affirmation') is excluded here
    if not nnx_has_noun_or_pronoun(np_child):
        return records

    phrase_type = 'Neg-Np' if rule == 'AdvpNp' else 'Np-Neg'
    if phrase_type not in valid_names:
        return records
    # Head-word resolution (phrase_checker convention: follow Head, fall
    # back to first terminal) -- v10 itself doesn't need a single NP head
    # word since its CSV reports the whole phrase's surface text, but
    # phrase_checker's record shape needs one head word per side.
    target_head = plain_head(np_child) or first_m_in_subtree(np_child)
    if not target_head:
        return records
    node_id = node.attrib.get('nodeId', '')
    for neg_head in neg_heads:
        head_left, head_right = (neg_head, target_head) if phrase_type == 'Neg-Np' else (target_head, neg_head)
        records.append(make_record(phrase_type, node_id, head_left, head_right, source_file, verse))
        hit_counter[f'[nnx-np] {rule}'] += 1
    return records


def nnx_extract_cl_patterns(node, valid_names, source_file, verse, hit_counter):
    """Port of noun_negation_extractor_v10.py's extract_cl_patterns() +
    canonical_cl_pattern()/classify_predicate()/resolve_simple() head-
    resolution engine, emitting Neg-Np/Np-Neg phrase_checker records.
    Runs on every Cat='CL' node (matching v10's own traversal), whether
    or not that node also satisfies phrase_checker's own stricter,
    order-sensitive is_clause_pattern_node() check -- canonical_cl_
    pattern() is already word-order-agnostic and doesn't need that."""
    records = []
    if 'Neg-Np' not in valid_names and 'Np-Neg' not in valid_names:
        return records
    if node.attrib.get('Cat') != 'CL':
        return records

    rule = node.attrib.get('Rule', '')
    canonical_rule, dup_cats = nnx_canonical_cl_pattern(rule)
    if canonical_rule is None:
        return records
    if canonical_rule == 'ADV-PP':
        # spec S1.4d: categorical exclusion -- a bare negated PP with no
        # S/O/P predication is never a Neg-Np/Np-Neg match, regardless
        # of whether the PP's own object resolves to a noun.
        return records

    # v7/S5.1: only competing S/O/P duplicates are true ambiguity.
    # ADV/PP duplication is resolved below (or never used as a target).
    competing_dup = dup_cats - {'ADV', 'PP'}
    if competing_dup:
        return records

    all_children_by_cat = {}
    for child in list(node):
        if child.tag == 'Node':
            cat = child.attrib.get('Cat', '')
            if cat:
                all_children_by_cat.setdefault(cat, []).append(child)

    adv_nodes = all_children_by_cat.get('ADV', [])
    s_node = (all_children_by_cat.get('S') or [None])[0]
    o_node = (all_children_by_cat.get('O') or [None])[0]
    p_node = (all_children_by_cat.get('P') or [None])[0]

    # Negator-source detection (S5.1): every ADV sibling that carries
    # type='negative'; if none, fall back to P itself (אַיִן/אֵין as
    # Advp2P doubling as negator + existential predicate).
    genuine_neg_advs = [a for a in adv_nodes if nnx_has_negative_particle(a)]
    negator_source = None
    if len(genuine_neg_advs) > 1:
        return records  # true ambiguity -- do not guess
    if len(genuine_neg_advs) == 1:
        negator_source = genuine_neg_advs[0]
    elif p_node is not None and nnx_has_negative_particle(p_node):
        negator_source = p_node
    if negator_source is None:
        return records

    neg_heads = _nnx_negator_heads(negator_source)
    if not neg_heads:
        return records
    node_id = node.attrib.get('nodeId', '')

    def emit(target_head):
        if target_head is None:
            return
        for neg_head in neg_heads:
            matched = _nnx_order_pair(neg_head, target_head, valid_names)
            if not matched:
                continue
            name, head_left, head_right = matched
            records.append(make_record(name, node_id, head_left, head_right, source_file, verse))
            hit_counter[f'[nnx-cl] {canonical_rule}'] += 1

    def emit_resolved(res):
        """Emit primary head plus any dual-noun apposition extras (ISA 57:4).
        phrase_checker has no target_head2_* columns, so each extra head
        becomes its own Neg-Np/Np-Neg row."""
        if not res:
            return
        heads = [res] + list(res.get('extra_heads') or [])
        for head_res in heads:
            emit(_nnx_head_dict_from_resolved(head_res))

    if canonical_rule in ('ADV-S', 'ADV-S-PP'):
        included, res = nnx_resolve_simple(s_node)
        if included:
            emit_resolved(res)
        elif _nnx_is_unreverted_infinitive_construct_use(res):
            # v10 / PSA 75:7: Vp2Np + infinitive construct -- outside
            # S1.4a's literal adjective/participle scope; excluded (open
            # question), not emitted as Neg-Np/Np-Neg.
            pass

    elif canonical_rule in ('ADV-O', 'ADV-O-PP'):
        included, res = nnx_resolve_simple(o_node)
        if included:
            emit_resolved(res)

    elif canonical_rule in ('ADV-S-P', 'ADV-S-P-PP'):
        clause_type, include, use_target, res = nnx_classify_predicate(p_node)
        if include and use_target == 'P':
            emit_resolved(res)
        elif include and use_target == 'S':
            # locative_existential (Pp2P / existential-particle predicate):
            # S is primary, but (spec S1.4a / PSA 16:2) must still run
            # through resolve_simple() before being reported.
            if s_node is not None:
                s_included, s_res = nnx_resolve_simple(s_node)
                if s_included:
                    emit_resolved(s_res)
                elif _nnx_is_unreverted_infinitive_construct_use(s_res):
                    # v10 / PSA 75:7-shaped open question -- exclude, no emit.
                    pass

    elif canonical_rule == 'ADV-P':
        clause_type, include, use_target, res = nnx_classify_predicate(p_node)
        if include and use_target == 'P':
            emit_resolved(res)
        elif include and use_target == 'S' and res.get('kind') == 'pp':
            # spec S1.3 / S5.3: bare ADV-P + Pp2P -- no S to compete with;
            # report the PP's own object as the negated noun -- unless the
            # PP is coordinated (S1.4d / Action Item 17), which is the
            # same bare-adjunct shape as ADV-PP.
            pp_node = res.get('node') or p_node
            if _nnx_is_pp_coordination(pp_node):
                return records
            obj_included, obj_res = nnx_resolve_pp_object(pp_node)
            if obj_included:
                emit_resolved(obj_res)

    return records



def extract_clause_pairs(node, valid_names, source_file, verse, hit_counter):
    """Mechanism 1: every pair of roles in a clause-pattern node, tested
    both orderings against the DB, substituting more specific role labels
    (VC for the copula verb, Neg for a negative particle, Adjp for an
    adjectival predicate) where applicable. Also emits VerbPrep/PrepVerb
    (or VCPrep/PrepVC for the copula) whenever V and PP are siblings.

    Negation: 'Neg-V' and 'Neg-Adjp' fall out of the cands_a x cands_b
    product via role_candidates(). 'Neg-Np' / 'Np-Neg' are NOT handled
    here -- see nnx_extract_cl_patterns() (the ported
    noun_negation_extractor_v10.py engine) so verbal clauses and
    O-partners cannot leak into Neg-Np.
    """
    records = []
    children = [c for c in list(node) if c.tag == 'Node']
    roles = [(c.attrib.get('Cat'), c) for c in children]
    node_id = node.attrib.get('nodeId', '')

    for i in range(len(roles)):
        cat_a, node_a = roles[i]
        for j in range(i + 1, len(roles)):
            cat_b, node_b = roles[j]
            if cat_a == 'PP' or cat_b == 'PP':
                continue  # handled by the VerbPrep/PrepVerb branch below
            head_a = head_for_role(cat_a, node_a)
            head_b = head_for_role(cat_b, node_b)
            if not (head_a and head_b):
                continue
            cands_a = role_candidates(cat_a, node_a, head_a)
            cands_b = role_candidates(cat_b, node_b, head_b)
            name = None
            for ca in cands_a:
                for cb in cands_b:
                    candidate = f"{ca}-{cb}"
                    if candidate in valid_names:
                        name = candidate
                        break
                if name:
                    break
            if name:
                records.append(make_record(name, node_id, head_a, head_b, source_file, verse))
                hit_counter[node.attrib.get('Rule', '')] += 1

    # V <-> PP siblings: VerbPrep / PrepVerb (or VCPrep / PrepVC for the
    # copula), paired with the preposition word.
    v_positions = [k for k, (c, _) in enumerate(roles) if c == 'V']
    pp_positions = [k for k, (c, _) in enumerate(roles) if c == 'PP']
    for vi in v_positions:
        for ppi in pp_positions:
            v_node = roles[vi][1]
            pp_node = roles[ppi][1]
            head_v = plain_head(v_node)
            head_pp = prep_word_head(pp_node)
            if not (head_v and head_pp):
                continue
            copula = is_copula(head_v)
            if vi < ppi:
                # V comes first in the verse -> Verb-then-Prep order.
                name = 'VCPrep' if copula and 'VCPrep' in valid_names else 'VerbPrep'
                first, second = head_v, head_pp
            else:
                # PP comes first in the verse -> Prep-then-Verb order.
                # The Words/Gloss/etc. column order must match the label
                # ("PrepVerb"/"PrepVC" implies prep first, verb second),
                # not always verb-first regardless of which label fired.
                name = 'PrepVC' if copula and 'PrepVC' in valid_names else 'PrepVerb'
                first, second = head_pp, head_v
            if name in valid_names:
                records.append(make_record(name, node_id, first, second, source_file, verse))
                hit_counter[node.attrib.get('Rule', '')] += 1
    return records


def extract_clause_full(node, source_file, verse, hit_counter):
    """Feature 1: Clause-Level Structural phrase extraction.

    For every clause-pattern node (Rule is a dash-joined list of role tags
    that matches the Cat of each direct child in order -- see
    is_clause_pattern_node) with 3 or more roles, emit ONE record whose
    PhraseType is the *literal Rule string itself* (e.g. "V-PP-O",
    "V-S-O-PP-PP-PP"), and whose MaculaID/Words/Gloss/StrongIDs/VerseIndex
    columns list the head word of every child role, in tree order, joined
    with " | " -- e.g. Rule="V-PP-O" -> MaculaID
    "<head of V> | <head of PP> | <head of O>".

    This is independent of tPhraseType(DB).csv (the Rule string is used
    as-is), and independent of / additional to extract_clause_pairs's
    pairwise DB-matched output -- both run on the same node.

    2-role clauses (V-S, V-O, ...) are skipped here because
    extract_clause_pairs already reports them (as a DB-matched pair with
    exactly the same two heads); starting at 3 avoids emitting a
    near-duplicate row for every simple two-role clause.
    """
    children = [c for c in list(node) if c.tag == 'Node']
    if len(children) < 3:
        return []
    rule = node.attrib.get('Rule', '')
    if should_skip_phrase_type(rule):
        return []
    heads = []
    for c in children:
        h = head_for_role(c.attrib.get('Cat'), c)
        if not h:
            return []  # any missing head word aborts the whole-clause row
        heads.append(h)
    hit_counter[f"[clause-full] {rule}"] += 1
    return [make_record_multi(rule, node.attrib.get('nodeId', ''), heads, source_file, verse)]


OR_STRONGS = {'176', '176a'}  # Hebrew או ("or")

# When the cjp linking two same-Cat conjuncts is או ("or", Strong 0176/0176a)
# instead of plain ve- ("and"), the coordination gets a more specific DB
# PhraseType than the plain Conj2<Role> one, keyed off the conjuncts' Cat:
#   - np              -> EitherOrNp    ("noun or noun")
#   - pp / PP / prep  -> EitherOrPrep  ("prep-phrase or prep-phrase")
#   - adjp            -> EitherOrAdjp  ("adjective or adjective")
# 'pp'/'PP' both appear in this corpus for prepositional-phrase nodes
# (see COORD_CAT_ROLE); 'prep' is included defensively in case a bare
# Cat="prep" coordination node is ever encountered instead of "pp"/"PP".
EITHER_OR_CAT_MAP = {
    'np': 'EitherOrNp',
    'pp': 'EitherOrPrep',
    'PP': 'EitherOrPrep',
    'prep': 'EitherOrPrep',
    'adjp': 'EitherOrAdjp',
}


# Cats used for PP/prepositional-phrase coordination conjuncts (see
# COORD_CAT_ROLE / _coordination_conjuncts). Shared by both coordination
# extractors so the "use the preposition, not the noun" special-casing
# stays in one place.
PP_COORD_CATS = {'pp', 'PP', 'prep'}


def _pp_conjunct_noun_head(pp_node):
    """Governed-noun head word for a single PP-coordination conjunct.

    A PP conjunct that is a plain PrepNp construction governs a real noun,
    so we can additionally report that noun's head (Conj2Np / Conj{n}Np,
    per the user's spec point 2). We key off Rule=='PrepNp' -- the same
    signal the existing V-IO mechanism (find_prepnp_governor) uses -- 
    rather than checking the first child's Cat directly, because the
    preposition itself is sometimes wrapped in an extra P2PP/Pp2PP layer
    (Cat='pp', not 'prep') before the corpus gets to the actual <m>
    terminal; the complement slot (children[1]) is what matters here.

    Anything else -- a PrepCL conjunct (the complement is a full clause),
    a PpAdvp conjunct (the complement is an adverbial), a missing/extra
    child, or a complement whose own head isn't morphologically a noun --
    has no governed noun to report, so this returns None. It never
    raises: every attribute lookup is guarded, so malformed/unexpected
    conjunct shapes are just skipped.
    """
    if pp_node is None or pp_node.tag != 'Node':
        return None
    if pp_node.attrib.get('Rule') != 'PrepNp':
        return None
    children = [c for c in list(pp_node) if c.tag == 'Node']
    if len(children) != 2:
        return None
    comp_child = children[1]
    if comp_child.attrib.get('Cat') != 'np':
        return None
    head = plain_head(comp_child)
    if head and head.get('pos') == 'noun':
        return head
    return None


def _governed_np_full_phrase_type(n):
    """Whole-chain PhraseType for the governed-noun row synthesised from a
    3+-way PP coordination chain: Conj3Np, Conj4Np, ... -- mirrors the
    naming used for the primary Pp row (Conj{n}Pp) and for the other Cat
    aliases in _coord_full_phrase_type. Never called with n==2 -- see the
    call site in extract_coordination_full for why."""
    return f'Conj{n}Np'


def _coordination_conjuncts(node):
    """If `node` has the (X, cjp, X, cjp, X, ...) coordination shape (odd
    number of children >= 3, alternating the same Cat on every even
    position and 'cjp' on every odd position -- Conj2Np, Conj3Np, Conj5Np,
    Conj4Adjp, ...), return the list of conjunct child Nodes (the X's,
    skipping the 'cjp' nodes). Otherwise return None. Shared by
    extract_coordination (Mechanism 3, pairwise DB-matched output) and
    extract_coordination_full (Feature 2, one whole-chain row)."""
    children = [c for c in list(node) if c.tag == 'Node']
    if len(children) < 3 or len(children) % 2 == 0:
        return None
    cat_main = children[0].attrib.get('Cat')
    if not cat_main:
        return None
    for k, c in enumerate(children):
        expected_cat = cat_main if k % 2 == 0 else 'cjp'
        if c.attrib.get('Cat') != expected_cat:
            return None
    return [children[k] for k in range(0, len(children), 2)]


def extract_coordination_full(node, source_file, verse, hit_counter):
    """Feature 2: full N-ary coordination extraction.

    For every coordination-chain node (Rule="Conj3Np", "Conj5Np",
    "Conj4Adjp", ... -- see _coordination_conjuncts), emit ONE record
    whose PhraseType is the *literal Rule string itself* and whose
    MaculaID/Words/Gloss/StrongIDs/VerseIndex columns list the head word
    of every conjunct (i.e. every X, skipping the 'cjp' conjunction nodes
    themselves), in order, joined with " | " -- e.g. Rule="Conj5Np" with
    5 noun conjuncts -> MaculaID "<n1> | <n2> | <n3> | <n4> | <n5>";
    Rule="Conj4Adjp" with 4 adjective conjuncts -> the 4 adjective heads.

    This is independent of tPhraseType(DB).csv (the Rule string is used
    as-is), and independent of / additional to extract_coordination's
    pairwise Conj2<Role>-per-adjacent-link output -- both run on the same
    node. Applies to 2-conjunct chains (Conj2Np, ...) too, in which case
    this row duplicates the single pairwise record extract_coordination
    already produces (same two heads) -- harmless, kept for uniformity."""
    conjuncts = _coordination_conjuncts(node)
    if not conjuncts:
        return []
    cat_main = conjuncts[0].attrib.get('Cat')
    is_pp_coord = cat_main in PP_COORD_CATS
    # PP coordination reports the leading preposition of each branch, not
    # the noun it governs (point 1 of the user's spec) -- everything else
    # keeps using the ordinary recursive head-of-subtree lookup.
    head_fn = prep_word_head if is_pp_coord else plain_head
    heads = [head_fn(c) for c in conjuncts]
    if not all(heads):
        return []
    phrase_type = _coord_full_phrase_type(node, conjuncts)
    records = []
    if phrase_type and not should_skip_phrase_type(phrase_type):
        hit_counter[f"[coord-full] {phrase_type}"] += 1
        records.append(make_record_multi(phrase_type, node.attrib.get('nodeId', ''), heads, source_file, verse))

    # Point 2 of the spec: if every PP conjunct is a plain PrepNp whose
    # complement has a valid noun head, additionally emit the governed-noun
    # chain -- but only for genuine 3+-way chains (Conj3Np, Conj4Np, ...).
    # For a 2-conjunct chain this would just duplicate the pairwise Conj2NP
    # record extract_coordination() already emits (same two heads, same
    # node) -- exactly the case every other coordination Cat here already
    # avoids by having its n==2 full-chain name (NpaNp, AdjpaAdjp, PPandPP,
    # ...) match SKIP_PHRASE_TYPE_PATTERNS. Non-NP complements (PrepCL,
    # PpAdvp, ...) simply make _pp_conjunct_noun_head return None for that
    # conjunct, so the whole additional row is skipped rather than raising
    # or emitting a partial/incorrect record.
    if is_pp_coord and len(conjuncts) > 2:
        noun_heads = [_pp_conjunct_noun_head(c) for c in conjuncts]
        if all(noun_heads):
            np_phrase_type = _governed_np_full_phrase_type(len(conjuncts))
            if np_phrase_type and not should_skip_phrase_type(np_phrase_type):
                hit_counter[f"[coord-full] {np_phrase_type}"] += 1
                records.append(make_record_multi(
                    np_phrase_type, node.attrib.get('nodeId', ''), noun_heads, source_file, verse))
    return records


def _coord_full_phrase_type(node, conjuncts):
    """PhraseType for a full-coordination row: the node's Rule if present,
    otherwise a name synthesised from the conjunct Cat (so sentence-level
    (CL, cjp, CL) chains with an empty Rule still show up as CLaCL / Conj3CL
    instead of a blank PhraseType)."""
    rule = (node.attrib.get('Rule') or '').strip()
    if rule:
        return rule
    n = len(conjuncts)
    cat = conjuncts[0].attrib.get('Cat') or ''
    aliases = {
        'CL': ('CLaCL', 'Conj{n}CL'),
        'pp': ('Conj2Pp', 'Conj{n}Pp'),
        'PP': ('Conj2Pp', 'Conj{n}Pp'),
        'np': ('NpaNp', 'Conj{n}Np'),
        'adjp': ('AdjpaAdjp', 'Conj{n}Adjp'),
        'advp': ('AdvpaAdvp', 'Conj{n}Advp'),
        'vp': ('VPaVP', 'Conj{n}VP'),
    }
    pair = aliases.get(cat)
    if not pair:
        return ''
    two, many = pair
    return two if n == 2 else many.format(n=n)


def extract_coordination(node, norm_map, source_file, verse, hit_counter):
    """Mechanism 3: (X, cjp, X) -> Conj2<Role>, or EitherOrNp / EitherOrPrep /
    EitherOrAdjp (per EITHER_OR_CAT_MAP, keyed on the conjuncts' Cat) when
    the conjoining word is או ("or", Strong 0176/0176a) rather than plain
    "and".

    Generalised to N-ary coordination chains: (X, cjp, X, cjp, X, ...).
    Rule names like Conj3Np, Conj4Np, Conj5Np, ... (the number = how many
    X's are chained) all share this same (cat, cjp, cat, cjp, cat, ...)
    shape -- an odd number of children, alternating the same Cat on every
    even position and 'cjp' on every odd position. Since the DB only
    defines the pairwise Conj2<Role> family (there's no Conj3NP/Conj4NP
    entry), a 3+-way chain is emitted as one Conj2<Role> (or EitherOrNp)
    record per adjacent (X, cjp, X) link, e.g. Conj3Np "A ve-B ve-C"
    produces two records: A-B and B-C. This is driven entirely by tree
    shape, not by the literal Rule name, so it also covers any future
    ConjNAdjp/ConjNAdvp/ConjNVP chain the corpus might contain."""
    conjuncts = _coordination_conjuncts(node)
    if conjuncts is None:
        return []
    children = [c for c in list(node) if c.tag == 'Node']
    cat_main = children[0].attrib.get('Cat')
    
    role = COORD_CAT_ROLE.get(cat_main)
    if not role:
        return []

    # PP coordination reports the leading preposition of each branch, not
    # the noun it governs (point 1 of the user's spec) -- everything else
    # keeps using the ordinary recursive head-of-subtree lookup.
    is_pp_coord = cat_main in PP_COORD_CATS
    head_fn = prep_word_head if is_pp_coord else plain_head

    records = []
    conjunct_positions = list(range(0, len(children), 2))
    for k in range(len(conjunct_positions) - 1):
        left = children[conjunct_positions[k]]
        cjp_node = children[conjunct_positions[k] + 1]
        right = children[conjunct_positions[k + 1]]

        cjp_head = plain_head(cjp_node)
        is_or = cjp_head and _strong_key(cjp_head['strong']) in OR_STRONGS

        matched = None
        if is_or:
            either_or_name = EITHER_OR_CAT_MAP.get(cat_main)
            if either_or_name and either_or_name in norm_map.values():
                matched = either_or_name
        if not matched:
            matched = norm_map.get(norm(f"Conj2{role}"))
        if matched:
            head_a = head_fn(left)
            head_b = head_fn(right)
            if head_a and head_b:
                hit_counter[node.attrib.get('Rule', '')] += 1
                records.append(make_record(matched, node.attrib.get('nodeId', ''), head_a, head_b, source_file, verse))

        # Point 2 of the spec: additionally link the governed head nouns
        # when both PP conjuncts are plain PrepNp branches with a valid
        # noun complement (PrepCL/PpAdvp/etc. branches gracefully yield
        # None from _pp_conjunct_noun_head and are simply skipped here).
        # Mirror the primary record's and/or distinction: an או ("or")
        # cjp between the PP conjuncts means the nouns it governs are
        # also "noun-or-noun" (EitherOrNp), not "noun-and-noun" (Conj2Np).
        if is_pp_coord:
            noun_a = _pp_conjunct_noun_head(left)
            noun_b = _pp_conjunct_noun_head(right)
            if noun_a and noun_b:
                np_matched = None
                if is_or:
                    either_or_np_name = EITHER_OR_CAT_MAP.get('np')
                    if either_or_np_name and either_or_np_name in norm_map.values():
                        np_matched = either_or_np_name
                if not np_matched:
                    np_matched = norm_map.get(norm('Conj2Np'))
                if np_matched:
                    hit_counter[f"{node.attrib.get('Rule', '')} [Np]"] += 1
                    records.append(make_record(
                        np_matched, node.attrib.get('nodeId', ''), noun_a, noun_b, source_file, verse))
    return records


# A few Rule names don't survive normalisation-based matching against the
# DB (e.g. "AdvpNp" -> "advpnp" vs DB "AdvNP" -> "advnp" -- an extra 'p'),
# or need to point at a differently-named DB entry entirely. Checked before
# the generic normalised-name match.
RULE_NAME_OVERRIDES = {
    'QuanNp': 'All-NP',   # e.g. kol + NP ("every creature") - quantifier first
    'QuanNP': 'All-NP',
    'AdvpNp': 'AdvNP',    # e.g. rak/akh + NP ("only ...") - adverb first
}


def _npadjp_variant(rule, children, norm_map):
    """NpAdjp ('np','adjp') and AdjpNp ('adjp','np') can represent several
    more specific DB phrase types depending on what the adjp slot actually
    is, once we look inside it:
      - adjp built via Rule='DetAdjp' (article+adjective) -> NPDetAdj
        (only defined noun-first in the DB, so only applied for NpAdjp)
      - adjp head word pos='pronoun' (a demonstrative riding the adjective
        slot) -> Np-Demo (noun-first) / Demo-NP (adjective-slot-first)
      - adjp head word pos='verb' (a participle used adjectivally)
        -> PtcpNP (only one direction defined in the DB)
    Falls back to None so the caller uses the plain NPAdjp/AdjpNP match.
    """
    if rule == 'NpAdjp':
        np_child, adjp_child = children
    elif rule == 'AdjpNp':
        adjp_child, np_child = children
    else:
        return None

    if rule == 'NpAdjp' and adjp_child.attrib.get('Rule') == 'DetAdjp':
        if 'NPDetAdj' in norm_map.values():
            return 'NPDetAdj'

    adjp_head = plain_head(adjp_child)
    if adjp_head:
        if adjp_head['pos'] == 'pronoun':
            name = 'Np-Demo' if rule == 'NpAdjp' else 'Demo-NP'
            if name in norm_map.values():
                return name
        if adjp_head['pos'] == 'verb':
            if 'PtcpNP' in norm_map.values():
                return 'PtcpNP'
    return None


def _npofnp_variant(rule, children, norm_map):
    """NPofNP whose second slot is a pronominal suffix (pos='suffix', morph Sp*)
    is the DB's Noun-Sfx rather than a construct chain of two lexical nouns."""
    if rule != 'NPofNP' or len(children) != 2:
        return None
    if 'Noun-Sfx' not in norm_map.values():
        return None
    head_b = plain_head(children[1])
    if head_b and head_b.get('pos') == 'suffix':
        return 'Noun-Sfx'
    return None


def extract_direct_match(node, norm_map, source_file, verse, hit_counter):
    """Mechanism 2: 2-child Rule nodes whose (normalised) Rule name is
    itself a DB PhraseType name (NPofNP, PrepNp->PrepNP, Np-Appos->NP-Appos,
    NpAdjp->NPAdjp, NpPp->NP-PP, NpAdvp->NPAdvp, and anything else that
    matches in future data), plus a short list of overrides for names that
    don't survive normalisation (RULE_NAME_OVERRIDES) and NpAdjp/AdjpNp
    sub-typing (see _npadjp_variant)."""
    rule = node.attrib.get('Rule', '')
    if not rule or is_clause_pattern_node(node):
        return []
    children = [c for c in list(node) if c.tag == 'Node']
    if len(children) != 2:
        return []

    matched = (
        RULE_NAME_OVERRIDES.get(rule)
        or _npadjp_variant(rule, children, norm_map)
        or _npofnp_variant(rule, children, norm_map)
        or norm_map.get(norm(rule))
    )
    if not matched:
        return []
    head_a = plain_head(children[0])
    head_b = plain_head(children[1])
    if not (head_a and head_b):
        return []
    hit_counter[rule] += 1
    return [make_record(matched, node.attrib.get('nodeId', ''), head_a, head_b, source_file, verse)]


def nearest_governing_verb(prepnp_node, parent_map):
    """Walk up the tree from a PrepNp node to the nearest ancestor that is
    a clause-pattern node with a 'V' role among its direct children."""
    current = parent_map.get(prepnp_node)
    seen_ancestors = 0
    while current is not None and seen_ancestors < 200:  # safety bound
        if is_clause_pattern_node(current):
            for child in list(current):
                if child.tag == 'Node' and child.attrib.get('Cat') == 'V':
                    return child
        current = parent_map.get(current)
        seen_ancestors += 1
    return None


def _word_position(head):
    """Extract the trailing word-index number from a VerseIndex string like
    'GEN 30:1!23' -> 23, used only to determine text order (IO before or
    after its governing verb) for naming V-IO vs IO-V."""
    vi = (head or {}).get('verse_index', '')
    m = re.search(r'!(\d+)$', vi)
    return int(m.group(1)) if m else None


def extract_v_io(root, parent_map, valid_names, source_file, verse, hit_counter):
    """Mechanism 4: PrepNp anywhere + nearest governing verb -> V-IO (or
    IO-V if the prepositional phrase actually precedes the verb in the
    text)."""
    if 'V-IO' not in valid_names and 'IO-V' not in valid_names:
        return []
    records = []
    for node in root.iter('Node'):
        if node.attrib.get('Rule') != 'PrepNp':
            continue
        gov_v = nearest_governing_verb(node, parent_map)
        if gov_v is None:
            continue
        children = [c for c in list(node) if c.tag == 'Node']
        if len(children) != 2:
            continue
        np_child = children[1]
        head_v = plain_head(gov_v)
        head_np = smart_object_head(np_child)
        if not (head_v and head_np):
            continue
        pos_v = _word_position(head_v)
        pos_io = _word_position(head_np)
        if pos_io is not None and pos_v is not None and pos_io < pos_v and 'IO-V' in valid_names:
            name, head_a, head_b = 'IO-V', head_np, head_v
        elif 'V-IO' in valid_names:
            name, head_a, head_b = 'V-IO', head_v, head_np
        else:
            continue
        records.append(make_record(name, node.attrib.get('nodeId', ''), head_a, head_b, source_file, verse))
        hit_counter['PrepNp(V-IO)'] += 1
    return records


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
def process_file(xml_path, valid_names, norm_map, hit_counter, rule_seen_counter):
    records = []
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError as e:
        print(f"  !! failed to parse {xml_path}: {e}", file=sys.stderr)
        return records
    root = tree.getroot()
    source_file = os.path.basename(xml_path)

    for sentence in root.findall('.//Sentence'):
        verse = sentence.attrib.get('verse', '')
        parent_map = build_parent_map(sentence)

        for node in sentence.findall('.//Node'):
            rule = node.attrib.get('Rule')
            if rule:
                rule_seen_counter[rule] += 1

            # Neg-Np / Np-Neg: ported wholesale from
            # noun_negation_extractor_v10.py (see the "Neg-Np / Np-Neg
            # extraction" section above). Runs on every Cat='CL' or
            # Cat='np' node, exactly like that script's own traverse_nodes()
            # -- independent of is_clause_pattern_node(), since v10's own
            # clause matching is word-order-agnostic and doesn't need it.
            cat = node.attrib.get('Cat', '')
            if cat == 'CL':
                records.extend(nnx_extract_cl_patterns(node, valid_names, source_file, verse, hit_counter))
            elif cat == 'np':
                records.extend(nnx_extract_np_patterns(node, valid_names, source_file, verse, hit_counter))

            if is_clause_pattern_node(node):
                records.extend(extract_clause_pairs(node, valid_names, source_file, verse, hit_counter))
                records.extend(extract_clause_full(node, source_file, verse, hit_counter))  # Feature 1
            else:
                records.extend(extract_direct_match(node, norm_map, source_file, verse, hit_counter))
                records.extend(extract_coordination(node, norm_map, source_file, verse, hit_counter))
                records.extend(extract_coordination_full(node, source_file, verse, hit_counter))  # Feature 2

        records.extend(extract_v_io(sentence, parent_map, valid_names, source_file, verse, hit_counter))

    return records


def write_csv(records, output_csv):
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)) or '.', exist_ok=True)
    fieldnames = ['SourceFile', 'Verse', 'PhraseType', 'ParentNodeID', 'StrongIDs', 'Words', 'Gloss', 'MaculaID', 'VerseIndex']
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            # Final safety filter: ensure we never emit excluded phrase types
            # due to future extractor changes.
            if should_skip_phrase_type(r.get('PhraseType', '')):
                continue
            writer.writerow({k: r[k] for k in fieldnames})


# DB types the extractors cannot produce from Cat/Rule tree shape alone.
# Confirmed against the Macula Hebrew WLC nodes: these role tags never appear
# as Cat, or no distinguishing structural pattern exists.
NO_EXTRACTOR_REASONS = {
    'ofNPNP': 'No Head/structure signal distinct from NPofNP; every (np, np) construct chain is labelled NPofNP',
    'NP-All': 'Reverse of All-NP (noun then kol). Only QuanNP (quantifier-first) occurs; no NpQuan rule',
    'PP-NP': 'Likely duplicate of PrepNP. PrepNp rules are labelled PrepNP',
    'NotNpButNP': 'No Hebrew "but"-type NP coordinator (כי אם / אבל) found joining two NPs',
    'NPAdjunct': 'No distinguishing Rule/Cat pattern found vs NP-PP / NPAdvp',
    'VC-P': 'V and P never co-occur as siblings (verbless clauses use S-P; copula uses V-headed patterns)',
    'P-VC': 'V and P never co-occur as siblings',
    'V-O-Ellip': 'No elliptical-object Rule/Cat marker in the treebank',
    'Prep-V': 'Likely duplicate of PrepVerb (already emitted from PP-before-V siblings)',
    'Appo': 'Likely duplicate of NP-Appos (already emitted from Rule=Np-Appos)',
    'PreX-V': 'PreX is not a Cat in the XML',
    'PreC-S': 'PreC is not a Cat; would need a morph/suffix pass',
    'PreC-V': 'PreC is not a Cat; would need a morph/suffix pass',
    'PreO-IO': 'PreO is not a Cat; object suffixes are segmented as Pron2NP argument NPs',
    'PreO-Prep': 'PreO is not a Cat',
    'PreO-S': 'PreO is not a Cat',
    'PreS-IO': 'PreS is not a Cat',
    'PreS-O': 'PreS is not a Cat',
    'S-PreC': 'PreC is not a Cat',
    'S-PreO': 'PreO is not a Cat',
    'PtcO-Prep': 'PtcO is not a Cat',
    'PreS-Prep': 'PreS is not a Cat',
    'PtcO-O': 'PtcO is not a Cat',
    'PtcO-S': 'PtcO is not a Cat',
    'V-PreC': 'PreC is not a Cat',
    'PreC-O': 'PreC is not a Cat',
    'O-PreC': 'PreC is not a Cat',
    'PreC-IO': 'PreC is not a Cat',
    'IO-PreC': 'PreC is not a Cat',
    'Prep-PreC': 'PreC is not a Cat',
    'PreC-Prep': 'PreC is not a Cat',
    'S-PtcO': 'PtcO is not a Cat',
    'PtcO-IO': 'PtcO is not a Cat',
    'IO-PtcO': 'PtcO is not a Cat',
    'Prep-PtcO': 'PtcO is not a Cat',
    'O-PreO': 'PreO is not a Cat',
    'PreS': 'PreS is not a Cat; subject agreement lives on the verb morph, not a tree role',
    'PrcS': 'PrcS is not a Cat',
    'PreO': 'PreO is not a Cat; object suffixes are segmented as separate Pron2NP nodes',
    'PtcO': 'PtcO is not a Cat',
}

# Types the code CAN emit, with the XML signal that produces them.
# Used only to explain 0-count types in a given sample (not a code gap).
ABSENT_IN_SAMPLE_HINT = {
    'AdjpNP': 'Needs Rule=AdjpNp (adjective before noun)',
    'Demo-NP': 'Needs Rule=AdjpNp whose adjp head is a demonstrative pronoun',
    'EitherOrNp': 'Needs NP coordination whose conjunction is או (Strong 176)',
    'Conj2Adv': 'Needs (advp, cjp, advp) coordination',
    'Conj2VP': 'Needs (vp, cjp, vp) coordination',
    'O2-V': 'Needs an O2 role appearing before V in a clause-pattern node',
    'VC-ADV': 'Needs copula haya (Strong 1961) sibling to an ADV role',
    'PrepVC': 'Needs a PP role appearing before copula V',
    'Neg-Adjp': 'Needs a negator ADV sibling to an adjectival P (Adjp2P)',
    'Neg-Np': 'Needs the ported noun_negation_extractor_v10.py engine to find a match (AdvpNp/NpAdvp, or ADV-S/ADV-O/ADV-S-P/ADV-S-PP/ADV-O-PP/ADV-S-P-PP/ADV-P with negator before the resolved noun/pronoun head)',
    'Np-Neg': 'Same engine as Neg-Np, reverse order (resolved noun/pronoun head before the negator)',
}


def write_test_report(path, xml_files, db_rows, valid_names, records, hit_counter, rule_seen_counter):
    """Write a scannable coverage report: DB types processed vs not, plus
    extra Conjunction / Clause-Level Structural rows that are not in the DB."""
    type_counts = Counter(r['PhraseType'] for r in records)
    by_file = Counter(r['SourceFile'] for r in records)

    clause_full = Counter()
    coord_full = Counter()
    for key, n in hit_counter.items():
        if key.startswith('[clause-full] '):
            clause_full[key[len('[clause-full] '):]] += n
        elif key.startswith('[coord-full] '):
            coord_full[key[len('[coord-full] '):]] += n

    processed = []
    absent = []
    no_extractor = []
    for row in db_rows:
        pt = row['PhraseType']
        cnt = type_counts.get(pt, 0)
        if cnt > 0:
            processed.append((row, cnt))
        elif pt in NO_EXTRACTOR_REASONS:
            no_extractor.append((row, NO_EXTRACTOR_REASONS[pt]))
        else:
            hint = ABSENT_IN_SAMPLE_HINT.get(pt, 'Extractor exists; pattern not found in this XML sample')
            absent.append((row, hint))

    extra_clause = [(pt, n) for pt, n in type_counts.most_common()
                    if pt not in valid_names and pt in clause_full]
    extra_coord = [(pt, n) for pt, n in type_counts.most_common()
                   if pt not in valid_names and pt in coord_full]
    extra_other = [(pt, n) for pt, n in type_counts.most_common()
                   if pt not in valid_names and pt not in clause_full and pt not in coord_full]

    def fmt_db(row, extra):
        return f"  {row['PhraseType']:<16s} {extra:<8} {row['Name']}"

    lines = []
    a = lines.append
    a('=' * 78)
    a('phrase_checker.py  PHRASE TYPE REPORT')
    a('=' * 78)
    a(f'XML input : {len(xml_files)} file(s)  ({", ".join(os.path.basename(f) for f in xml_files)})')
    a(f'DB types  : {len(db_rows)} in tPhraseType_DB_.csv')
    a(f'Rows out  : {len(records)}')
    for fn, n in sorted(by_file.items()):
        a(f'            {n:5d}  from {fn}')
    a('')
    a(f'DB processed          : {len(processed):3d} / {len(db_rows)}')
    a(f'DB not in this sample : {len(absent):3d} / {len(db_rows)}  (code can handle; XML has no instance)')
    a(f'DB no extractor       : {len(no_extractor):3d} / {len(db_rows)}  (needs morph/suffix or has no tree signal)')
    a(f'Clause-level extra    : {len(extra_clause):3d} Rule names (3+ role patterns, not in DB)')
    a(f'Conjunction extra     : {len(extra_coord):3d} Rule names (full N-ary chains, not in DB)')
    a('')

    a('-' * 78)
    a(f'A. PROCESSED  — DB PhraseTypes found in this run  ({len(processed)})')
    a('-' * 78)
    a(f'  {"PhraseType":<16s} {"Count":<8} Name')
    for row, cnt in sorted(processed, key=lambda x: (-x[1], x[0]['PhraseType'])):
        a(fmt_db(row, str(cnt)))
    a('')

    a('-' * 78)
    a(f'B. NOT PROCESSED  — in DB, code CAN handle, but not in this XML  ({len(absent)})')
    a('-' * 78)
    a(f'  {"PhraseType":<16s} {"Why 0":<8} Name  |  needed signal')
    for row, hint in absent:
        a(fmt_db(row, '0'))
        a(f'  {" ":16s}          -> {hint}')
    a('')

    a('-' * 78)
    a(f'C. NOT PROCESSED  — in DB, no tree-shape extractor  ({len(no_extractor)})')
    a('-' * 78)
    a(f'  {"PhraseType":<16s} {"Why 0":<8} Name')
    for row, reason in no_extractor:
        a(fmt_db(row, '0'))
        a(f'  {" ":16s}          -> {reason}')
    a('')

    a('-' * 78)
    a(f'D. Clause-Level Structural Rules  (Feature 1: 3+ role nodes, PhraseType = Rule)  ({len(extra_clause)})')
    a('-' * 78)
    if extra_clause:
        for pt, n in extra_clause:
            a(f'  {pt:<28s} {n}')
    else:
        a('  (none)')
    a('')

    a('-' * 78)
    a(f'E. Conjunction Phrases  (Feature 2: full N-ary X-cjp-X chains, PhraseType = Rule)  ({len(extra_coord)})')
    a('-' * 78)
    a('  Pairwise DB types Conj2NP / Conj2Adjp / Conj2Adv / Conj2VP / Conj2Pp / EitherOrNp are in section A.')
    a('  This section is the extra whole-chain rows (NpaNp, Conj3Np, Conj3Pp, ...).')
    if extra_coord:
        for pt, n in extra_coord:
            a(f'  {pt:<28s} {n}')
    else:
        a('  (none)')
    a('')

    if extra_other:
        a('-' * 78)
        a(f'F. Other extra PhraseTypes (not in DB, not clause-full / coord-full)  ({len(extra_other)})')
        a('-' * 78)
        for pt, n in extra_other:
            label = pt if pt else '(empty)'
            a(f'  {label:<28s} {n}')
        a('')

    a('=' * 78)
    a('Quick check: every DB PhraseType is in A (processed), B (absent from sample), or C (no extractor).')
    a('Conjunction + clause-level extras are in D and E; they are expected and are not DB types.')
    a('=' * 78)

    text = '\n'.join(lines) + '\n'
    if path:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    return text, {
        'n_records': len(records),
        'n_db': len(db_rows),
        'n_processed': len(processed),
        'n_absent': len(absent),
        'n_no_extractor': len(no_extractor),
        'n_clause': len(extra_clause),
        'n_coord': len(extra_coord),
        'processed': [(r['PhraseType'], c, r['Name'], r['Chinese'], r['PhraseTypeID']) for r, c in processed],
        'absent': [(r['PhraseType'], r['Name'], r['Chinese'], h) for r, h in absent],
        'no_extractor': [(r['PhraseType'], r['Name'], r['Chinese'], h) for r, h in no_extractor],
        'clause': extra_clause,
        'coord': extra_coord,
        'by_file': dict(by_file),
        'xml_files': [os.path.basename(f) for f in xml_files],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input-dir', default='./xml_input', help='Folder containing one or more .xml treebank files')
    ap.add_argument('--output-csv', default='./phrase_relationships.csv', help='Path of the single combined result CSV')
    ap.add_argument('--db-csv', default='./tPhraseType_DB_.csv', help='Path to tPhraseType(DB).csv')
    ap.add_argument('--report', default='', help='Path of the coverage test report (default: <output-csv>.report.txt)')
    args = ap.parse_args()

    valid_names, norm_map, db_rows = load_phrase_db(args.db_csv)
    print(f"Loaded {len(valid_names)} phrase types from {args.db_csv}")

    xml_files = sorted(
        os.path.join(args.input_dir, fn)
        for fn in os.listdir(args.input_dir)
        if fn.lower().endswith('.xml')
    )
    if not xml_files:
        print(f"No .xml files found in {args.input_dir}", file=sys.stderr)
        sys.exit(1)

    all_records = []
    hit_counter = Counter()       # Rule -> number of records it produced
    rule_seen_counter = Counter()  # Rule -> number of times the Rule occurred at all

    for xf in xml_files:
        print(f"Processing {xf} ...")
        recs = process_file(xf, valid_names, norm_map, hit_counter, rule_seen_counter)
        print(f"  -> {len(recs)} phrase relationships")
        all_records.extend(recs)

    write_csv(all_records, args.output_csv)
    print(f"\nWrote {len(all_records)} total rows to {args.output_csv}")

    report_path = args.report or (os.path.splitext(args.output_csv)[0] + '.report.txt')
    text, _summary = write_test_report(
        report_path, xml_files, db_rows, valid_names, all_records, hit_counter, rule_seen_counter
    )
    print(text)
    print(f"Wrote test report to {report_path}")


if __name__ == '__main__':
    main()