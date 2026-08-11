#!/usr/bin/env python3
"""
phrase_checker.py

Extracts phrase-pair relationships (V-S, V-O, PrepNP, NPofNP, ...) from the
Hebrew syntax-tree XML files and writes them to a single CSV.

------------------------------------------------------------------------
WHAT CHANGED FROM phrase_checker_v0.py
------------------------------------------------------------------------
v0 only knew about three hard-coded XML `Rule` patterns (V-S-O, ADV-V-PP,
PrepNp) and therefore only ever produced 4 PhraseTypes (V-S, V-O, Neg-V,
VerbPrep, PrepNp, V-IO). This version is driven by tPhraseType(DB).csv, so
adding a new phrase type to the CSV does NOT require touching this code
(as long as it falls into one of the generic patterns below).

Three independent extraction strategies run over every sentence:

1. CLAUSE-LEVEL ROLE PAIRS
   Many `Rule` values in the XML are themselves a dash-joined sequence of
   role tags that match the `Cat` of the node's direct children exactly,
   e.g. Rule="V-S-O" has children Cat="V","S","O"; Rule="ADV-V-O-S" has
   children Cat="ADV","V","O","S". Such a node is a "clause pattern" node.
   For every pair of roles present in a clause-pattern node (not just
   adjacent ones -- V and O in V-S-O are not adjacent but V-O is still a
   real relationship) we test both orderings ("V-O" and "O-V") against
   tPhraseType(DB).csv. Whichever ordering matches actual DB PhraseType is
   emitted. This single mechanism produces V-S/S-V, V-O/O-V, V-O2/O2-V,
   ADV-V/V-ADV, S-P/P-S, S-VC/VC-S, VC-P/P-VC, VC-ADV, ... automatically,
   for every clause pattern rule found in the file, without hard-coding
   each one.

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
   of each child. This is fully data-driven: if the DB gains a new type
   whose name matches a new Rule found in some other book's XML, it will
   be picked up with no code change.

3. COORDINATION (X and X)
   Rule nodes shaped like (X, cjp, X) -- e.g. NpaNp -> (np, cjp, np) --
   represent "X and X" coordination. These are mapped to the DB's
   `Conj2NP` / `Conj2Adjp` / `Conj2Adv` family by Cat.

PLUS one legacy special case kept from v0, generalised:

4. V-IO via nested PrepNp
   Wherever a `PrepNp` occurs anywhere in a sentence, we look for the
   *nearest* enclosing clause-pattern node that has a V role among its
   direct children (nearest-governor, computed via real parent pointers
   instead of v0's whole-sentence O(n^2) scan) and emit V-IO (governing
   verb + the preposition's NP head). VerbPrep/PrepVerb is emitted
   separately whenever V and PP are siblings in the same clause pattern
   node, pairing V with the preposition word itself.

------------------------------------------------------------------------
KNOWN LIMITATIONS / THINGS TO VERIFY (please sanity-check against your
reference doc -- the shared Gemini link required sign-in so this script
could not be checked against it directly):
------------------------------------------------------------------------
- V-IO uses a nearest-governing-verb heuristic (same idea as v0, just
  implemented correctly/efficiently). For a PrepNp buried inside a
  relative clause or a deeply nested modifier, "nearest governing verb"
  may not always be the linguistically intended one.
- `ofNPNP` (as opposed to `NPofNP`) could not be distinguished in the
  sample XML -- there was no structural signal (e.g. a Head=1 marker)
  telling the two apart, so every (np, np) construct-chain node is
  currently labelled NPofNP. If ofNPNP means something structurally
  different, tell me and I'll split the logic.
- Fine-grained coordination types that depend on the conjunction's own
  meaning (EitherOrNp = "or", NotNpButNP = "but") are not yet
  distinguished from plain Conj2NP; only plain "X and X" is implemented.
- A handful of DB phrase types (e.g. NPDetAdj, All-NP/NP-All, Demo-NP,
  the "PreO/PreS/PtcO" suffix-verb family) depend on morphological
  features (definite article + adjective ordering, demonstrative
  pronouns, pronominal suffixes) that were not clearly recoverable from
  generic tree shape alone in the sample file (no example nodes were
  found in 01-Gen-030.xml to confirm the pattern against). These are
  left unmapped rather than guessed -- see the "unmapped rule" report
  printed at the end of a run, which lists every Rule that fired zero
  extractions so you can tell me how it should map.

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


def smart_object_head(node):
    """Head word for an O/O2-type role: if the role's own sub-tree embeds
    a clause (i.e. contains a nested Cat='V'), use that embedded verb's
    head (the object is itself a verbal complement clause). Otherwise use
    the object's own head noun, skipping object-marker / article particles."""
    embedded_v = find_descendant_by_cat(node, 'V')
    if embedded_v is not None:
        head = first_m_in_subtree(embedded_v)
        if head:
            return head
    return first_m_in_subtree(node, skip_cats=SKIP_HEAD_CATS)


def plain_head(node):
    """Head word for a role that isn't object-like: skip function-word
    sub-trees (article/object-marker) but don't hunt for embedded verbs."""
    return first_m_in_subtree(node, skip_cats=SKIP_HEAD_CATS)


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


def extract_clause_pairs(node, valid_names, source_file, verse, hit_counter):
    """Mechanism 1: every pair of roles in a clause-pattern node, tested
    both orderings against the DB. Also emits VerbPrep/PrepVerb whenever
    V and PP are siblings here."""
    records = []
    children = [c for c in list(node) if c.tag == 'Node']
    roles = [(c.attrib.get('Cat'), c) for c in children]
    node_id = node.attrib.get('nodeId', '')

    for i in range(len(roles)):
        cat_a, node_a = roles[i]
        for j in range(len(roles)):
            if i == j:
                continue
            cat_b, node_b = roles[j]
            if cat_a == 'PP' or cat_b == 'PP':
                continue  # handled by the VerbPrep/PrepVerb branch below
            name = f"{cat_a}-{cat_b}"
            if name in valid_names:
                head_a = head_for_role(cat_a, node_a)
                head_b = head_for_role(cat_b, node_b)
                if head_a and head_b:
                    records.append(make_record(name, node_id, head_a, head_b, source_file, verse))
                    hit_counter[node.attrib.get('Rule', '')] += 1

    # V <-> PP siblings: VerbPrep / PrepVerb (paired with the preposition word)
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
            name = 'VerbPrep' if vi < ppi else 'PrepVerb'
            if name in valid_names:
                records.append(make_record(name, node_id, head_v, head_pp, source_file, verse))
                hit_counter[node.attrib.get('Rule', '')] += 1
    return records


def extract_coordination(node, norm_map, source_file, verse, hit_counter):
    """Mechanism 3: (X, cjp, X) -> Conj2<Role>."""
    children = [c for c in list(node) if c.tag == 'Node']
    if len(children) != 3:
        return []
    cat_a = children[0].attrib.get('Cat')
    cat_mid = children[1].attrib.get('Cat')
    cat_b = children[2].attrib.get('Cat')
    if cat_mid != 'cjp' or cat_a != cat_b:
        return []
    role = COORD_CAT_ROLE.get(cat_a)
    if not role:
        return []
    candidate = f"Conj2{role}"
    matched = norm_map.get(norm(candidate))
    if not matched:
        return []
    head_a = plain_head(children[0])
    head_b = plain_head(children[2])
    if not (head_a and head_b):
        return []
    hit_counter[node.attrib.get('Rule', '')] += 1
    return [make_record(matched, node.attrib.get('nodeId', ''), head_a, head_b, source_file, verse)]


def extract_direct_match(node, norm_map, source_file, verse, hit_counter):
    """Mechanism 2: 2-child Rule nodes whose (normalised) Rule name is
    itself a DB PhraseType name (NPofNP, PrepNp->PrepNP, Np-Appos->NP-Appos,
    NpAdjp->NPAdjp, NpPp->NP-PP, NpAdvp->NPAdvp, and anything else that
    matches in future data)."""
    rule = node.attrib.get('Rule', '')
    if not rule or is_clause_pattern_node(node):
        return []
    children = [c for c in list(node) if c.tag == 'Node']
    if len(children) != 2:
        return []
    matched = norm_map.get(norm(rule))
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


def extract_v_io(root, parent_map, valid_names, source_file, verse, hit_counter):
    """Mechanism 4: PrepNp anywhere + nearest governing verb -> V-IO."""
    if 'V-IO' not in valid_names:
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
        records.append(make_record('V-IO', node.attrib.get('nodeId', ''), head_v, head_np, source_file, verse))
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
    ap.add_argument('--input-dir', default='./XML-Source', help='Folder containing one or more .xml treebank files')
    ap.add_argument('--output-csv', default='./phrase_relationships.csv', help='Path of the single combined result CSV')
    ap.add_argument('--db-csv', default='./tPhraseTypeDB.csv', help='Path to tPhraseType(DB).csv')
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
