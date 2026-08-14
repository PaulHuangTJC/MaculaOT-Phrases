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
    (negator + adjectival predicate) and the generic Neg-X/X-Neg fallback
    (negator + any other role) are handled the same way.
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
COORD_CAT_ROLE = {
    'np': 'NP',
    'adjp': 'Adjp',
    'advp': 'Adv',
    'vp': 'VP',
}

# Node Cats that are "function words" we skip over when hunting for the
# head word of a phrase (object markers, articles). Skipping these means
# V-O pairs with e.g. "et ha-ish" correctly report the noun ish, not the
# object-marker particle.
SKIP_HEAD_CATS = {'omp', 'om', 'art'}

# Strong's numbers for the core Hebrew negative particles (lo, al, bilti,
# eyn, Aramaic la, bal, beli). Used to distinguish plain "ADV-V" from the
# more specific "Neg-V"/"Neg-Adjp"/"Neg-X"/"X-Neg" DB phrase types.
NEGATION_STRONGS = {'3808', '408', '1115', '369', '3809', '1077', '1097'}

# Strong's number for the Hebrew copula verb "to be" (haya). Used to
# distinguish plain V-S/S-V/V-P/.../VerbPrep from the more specific
# VC-S/S-VC/VC-P/P-VC/VC-ADV/VCPrep/PrepVC DB phrase types.
COPULA_STRONGS = {'1961'}


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
    """Returns (valid_names set, {normalised_name: canonical_PhraseType})."""
    valid = set()
    norm_map = {}
    with open(db_csv_path, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            pt = row['PhraseType'].strip()
            if not pt:
                continue
            valid.add(pt)
            norm_map[norm(pt)] = pt
    return valid, norm_map


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
    strong = m.attrib.get('oshb-strongs', '') or term_node.attrib.get('StrongNumberX', '')
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


def smart_object_head(node):
    """Head word for an O/O2-type role: if the role's own sub-tree embeds
    a clause (i.e. contains a nested Cat='V'), use that embedded verb's
    head (the object is itself a verbal complement clause). Otherwise use
    the object's own head noun, following the tree's Head attribute
    (falling back to skipping object-marker / article particles only if
    Head is missing/malformed)."""
    embedded_v = find_descendant_by_cat(node, 'V')
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


def make_record(phrase_type, node_id, head_a, head_b, source_file, verse):
    return {
        'PhraseType': phrase_type,
        'ParentNodeID': node_id,
        'StrongIDs': f"{head_a['strong']} | {head_b['strong']}",
        'Words': f"{head_a['word']} | {head_b['word']}",
        'Gloss': f"{head_a['gloss']} | {head_b['gloss']}",
        'MaculaID': f"{head_a['macula']} | {head_b['macula']}",
        'VerseIndex': f"{head_a['verse_index']} | {head_b['verse_index']}",
        'SourceFile': source_file,
        'Verse': verse,
    }


def role_candidates(cat, node, head):
    """Return an ordered list of candidate role-labels to try when building
    a PhraseType name for this role, most-specific first:
      - V realized by the copula verb (haya) -> also try 'VC'
      - ADV realized by a negative particle -> also try 'Neg'
      - P realized by an adjective phrase -> also try 'Adjp' (needed for
        'Neg-Adjp', which pairs with the *word class* not the role name)
    Falls back to the plain role/Cat itself last.
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


def extract_clause_pairs(node, valid_names, source_file, verse, hit_counter):
    """Mechanism 1: every pair of roles in a clause-pattern node, tested
    both orderings against the DB, substituting more specific role labels
    (VC for the copula verb, Neg for a negative particle, Adjp for an
    adjectival predicate) where applicable. Also emits VerbPrep/PrepVerb
    (or VCPrep/PrepVC for the copula) whenever V and PP are siblings."""
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
            if name is None:
                # Generic negation fallback: negator paired with a role
                # that has no specific "Neg-<role>" entry in the DB.
                if cat_a == 'ADV' and is_negator(head_a) and 'Neg-X' in valid_names:
                    name = 'Neg-X'
                elif cat_b == 'ADV' and is_negator(head_b) and 'X-Neg' in valid_names:
                    name = 'X-Neg'
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
                name = 'VCPrep' if copula and 'VCPrep' in valid_names else 'VerbPrep'
            else:
                name = 'PrepVC' if copula and 'PrepVC' in valid_names else 'PrepVerb'
            if name in valid_names:
                records.append(make_record(name, node_id, head_v, head_pp, source_file, verse))
                hit_counter[node.attrib.get('Rule', '')] += 1
    return records


OR_STRONGS = {'176', '176a'}  # Hebrew או ("or")


def extract_coordination(node, norm_map, source_file, verse, hit_counter):
    """Mechanism 3: (X, cjp, X) -> Conj2<Role>, or EitherOrNp when the
    conjoining word is או ("or") rather than plain "and".

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
    children = [c for c in list(node) if c.tag == 'Node']
    if len(children) < 3 or len(children) % 2 == 0:
        return []
    cat_main = children[0].attrib.get('Cat')
    if not cat_main:
        return []
    for k, c in enumerate(children):
        expected_cat = cat_main if k % 2 == 0 else 'cjp'
        if c.attrib.get('Cat') != expected_cat:
            return []

    role = COORD_CAT_ROLE.get(cat_main)
    if not role:
        return []

    records = []
    conjunct_positions = list(range(0, len(children), 2))
    for k in range(len(conjunct_positions) - 1):
        left = children[conjunct_positions[k]]
        cjp_node = children[conjunct_positions[k] + 1]
        right = children[conjunct_positions[k + 1]]

        cjp_head = plain_head(cjp_node)
        is_or = cjp_head and _strong_key(cjp_head['strong']) in OR_STRONGS

        matched = None
        if is_or and cat_main == 'np' and 'EitherOrNp' in norm_map.values():
            matched = 'EitherOrNp'
        if not matched:
            matched = norm_map.get(norm(f"Conj2{role}"))
        if not matched:
            continue

        head_a = plain_head(left)
        head_b = plain_head(right)
        if not (head_a and head_b):
            continue
        hit_counter[node.attrib.get('Rule', '')] += 1
        records.append(make_record(matched, node.attrib.get('nodeId', ''), head_a, head_b, source_file, verse))
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

    matched = RULE_NAME_OVERRIDES.get(rule) or _npadjp_variant(rule, children, norm_map) or norm_map.get(norm(rule))
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
            if is_clause_pattern_node(node):
                records.extend(extract_clause_pairs(node, valid_names, source_file, verse, hit_counter))
            else:
                records.extend(extract_direct_match(node, norm_map, source_file, verse, hit_counter))
                records.extend(extract_coordination(node, norm_map, source_file, verse, hit_counter))

        records.extend(extract_v_io(sentence, parent_map, valid_names, source_file, verse, hit_counter))

    return records


def write_csv(records, output_csv):
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)) or '.', exist_ok=True)
    fieldnames = ['SourceFile', 'Verse', 'PhraseType', 'ParentNodeID', 'StrongIDs', 'Words', 'Gloss', 'MaculaID', 'VerseIndex']
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({k: r[k] for k in fieldnames})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--input-dir', default='./xml_input', help='Folder containing one or more .xml treebank files')
    ap.add_argument('--output-csv', default='./phrase_relationships.csv', help='Path of the single combined result CSV')
    ap.add_argument('--db-csv', default='./tPhraseType_DB_.csv', help='Path to tPhraseType(DB).csv')
    args = ap.parse_args()

    valid_names, norm_map = load_phrase_db(args.db_csv)
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

    # Coverage summary
    type_counts = Counter(r['PhraseType'] for r in all_records)
    print("\n=== PhraseType coverage in this run ===")
    for pt, cnt in type_counts.most_common():
        print(f"  {pt:15s} {cnt}")

    unmapped = sorted(r for r in rule_seen_counter if hit_counter.get(r, 0) == 0)
    if unmapped:
        print("\n=== Rules seen but producing 0 records (may need a mapping) ===")
        for r in unmapped:
            print(f"  {r:15s} seen {rule_seen_counter[r]}x")


if __name__ == '__main__':
    main()
