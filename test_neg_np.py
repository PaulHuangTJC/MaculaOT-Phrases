#!/usr/bin/env python3
"""Unit tests for Neg-Np / Np-Neg two-pattern rule in phrase_checker.py."""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import phrase_checker as pc


VALID = {'Neg-Np', 'Np-Neg', 'Neg-V', 'Neg-Adjp', 'ADV-V', 'S-P', 'P-S', 'AdvNP'}


def _m(word_idx, text, *, strong, pos, typ='', english='', macula='x'):
    attrs = {
        'word': f'TEST 1:1!{word_idx}',
        'pos': pos,
        'english': english or text,
        'oshb-strongs': strong,
    }
    if typ:
        attrs['type'] = typ
    el = ET.Element('m', attrs)
    el.text = text
    return el


def _term(cat, word_idx, text, *, strong, pos, typ='', n='n1'):
    node = ET.Element('Node', {'Cat': cat, 'n': n, 'StrongNumberX': strong, 'nodeId': n})
    node.append(_m(word_idx, text, strong=strong, pos=pos, typ=typ, macula=n))
    return node


def _wrap(cat, rule, *children, head='0', node_id='p'):
    node = ET.Element('Node', {
        'Cat': cat,
        'Rule': rule,
        'Head': head,
        'nodeId': node_id,
    })
    for ch in children:
        node.append(ch)
    return node


def _adv_role(word_idx, text, strong='3808'):
    adv = _term('adv', word_idx, text, strong=strong, pos='particle', typ='negative', n=f'adv{word_idx}')
    advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id=f'advp{word_idx}')
    return _wrap('ADV', 'Advp2ADV', advp, head='0', node_id=f'ADV{word_idx}')


def _np_noun(word_idx, text, strong='120', pos='noun'):
    noun = _term('noun', word_idx, text, strong=strong, pos=pos, n=f'n{word_idx}')
    return _wrap('np', 'N2NP', noun, head='0', node_id=f'np{word_idx}')


def _s_role(word_idx, text, strong='120', pos='noun'):
    return _wrap('S', 'Np2S', _np_noun(word_idx, text, strong=strong, pos=pos),
                 head='0', node_id=f'S{word_idx}')


def _p_role_noun(word_idx, text, strong='6256'):
    return _wrap('P', 'Np2P', _np_noun(word_idx, text, strong=strong),
                 head='0', node_id=f'P{word_idx}')


def _p_role_adjp(word_idx, text, strong='2896'):
    adj = _term('adj', word_idx, text, strong=strong, pos='adjective', n=f'a{word_idx}')
    adjp = _wrap('adjp', 'Adj2Adjp', adj, head='0', node_id=f'adjp{word_idx}')
    return _wrap('P', 'Adjp2P', adjp, head='0', node_id=f'Padj{word_idx}')


def _v_role(word_idx, text='הלך', strong='1980'):
    verb = _term('verb', word_idx, text, strong=strong, pos='verb', n=f'v{word_idx}')
    vp = _wrap('vp', 'V2VP', verb, head='0', node_id=f'vp{word_idx}')
    return _wrap('V', 'Vp2V', vp, head='0', node_id=f'V{word_idx}')


def _run_on_node(node, extractor):
    hits = Counter()
    return extractor(node, VALID, 'test.xml', 'TEST 1:1', hits), hits


class TestNegNpPattern1(unittest.TestCase):
    """Pattern 1: NP/PP constituent negation with terminal adjacency."""

    def test_neg_np_advp_np(self):
        adv = _term('adv', 7, 'לֹא', strong='3808', pos='particle', typ='negative')
        advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id='advp')
        noun_np = _np_noun(8, 'מִשְׁפָּט', strong='4941')
        parent = _wrap('np', 'AdvpNp', advp, noun_np, head='1', node_id='p1')
        records, _ = _run_on_node(parent, pc.extract_neg_np_constituent)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['PhraseType'], 'Neg-Np')
        self.assertEqual(records[0]['Words'], 'לֹא | מִשְׁפָּט')

    def test_np_neg_reverse_order(self):
        noun_np = _np_noun(3, 'אֱלֹהִים', strong='430')
        adv = _term('adv', 4, 'לֹא', strong='3808', pos='particle', typ='negative')
        advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id='advp')
        parent = _wrap('np', 'NpAdvp', noun_np, advp, head='0', node_id='p1r')
        records, _ = _run_on_node(parent, pc.extract_neg_np_constituent)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['PhraseType'], 'Np-Neg')
        self.assertEqual(records[0]['Words'], 'אֱלֹהִים | לֹא')

    def test_rejects_non_adjacent(self):
        adv = _term('adv', 1, 'לֹא', strong='3808', pos='particle', typ='negative')
        advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id='advp')
        noun_np = _np_noun(3, 'אִישׁ', strong='376')  # gap at !2
        parent = _wrap('np', 'AdvpNp', advp, noun_np, head='1', node_id='gap')
        records, _ = _run_on_node(parent, pc.extract_neg_np_constituent)
        self.assertEqual(records, [])

    def test_rejects_preposition_sibling(self):
        adv = _term('adv', 5, 'לֹא', strong='3808', pos='particle', typ='negative')
        advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id='advp')
        prep = _term('prep', 6, 'עַל', strong='5921', pos='preposition')
        pp = _wrap('pp', 'P2PP', prep, head='0', node_id='pp')
        parent = _wrap('pp', 'AdvpPp', advp, pp, head='1', node_id='ppneg')
        records, _ = _run_on_node(parent, pc.extract_neg_np_constituent)
        self.assertEqual(records, [])

    def test_malformed_child_does_not_raise(self):
        # Empty children / missing m tags must return [] without exception.
        broken = ET.Element('Node', {'Cat': 'np', 'Rule': 'AdvpNp', 'nodeId': 'bad'})
        broken.append(ET.Element('Node', {'Cat': 'advp'}))
        broken.append(ET.Element('Node', {'Cat': 'np'}))
        records, _ = _run_on_node(broken, pc.extract_neg_np_constituent)
        self.assertEqual(records, [])


class TestNegNpPattern2(unittest.TestCase):
    """Pattern 2: verbless CL with ADV + S/P and terminal adjacency."""

    def test_neg_np_adv_p(self):
        cl = _wrap('CL', 'ADV-P', _adv_role(6, 'לֹא'), _p_role_noun(7, 'עֵת'),
                   head='1', node_id='cl1')
        records, _ = _run_on_node(cl, pc.extract_neg_np_clause_pairs)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['PhraseType'], 'Neg-Np')
        self.assertEqual(records[0]['Words'], 'לֹא | עֵת')

    def test_neg_np_adv_s_pronoun(self):
        cl = _wrap('CL', 'ADV-S-P',
                   _adv_role(1, 'לֹא'),
                   _s_role(2, 'זֶה', strong='2088', pos='pronoun'),
                   _p_role_noun(3, 'דָּבָר', strong='1697'),
                   head='2', node_id='cl2')
        records, _ = _run_on_node(cl, pc.extract_neg_np_clause_pairs)
        types = [r['PhraseType'] for r in records]
        self.assertIn('Neg-Np', types)
        neg_s = [r for r in records if r['Words'] == 'לֹא | זֶה']
        self.assertEqual(len(neg_s), 1)

    def test_np_neg_s_before_adv(self):
        cl = _wrap('CL', 'S-ADV-P',
                   _s_role(10, 'אִישׁ', strong='376'),
                   _adv_role(11, 'לֹא'),
                   _p_role_noun(12, 'טּוֹב', strong='2896'),
                   head='2', node_id='cl3')
        # P head is noun טּוֹב - but ADV and S are adjacent: S!10, ADV!11 -> Np-Neg
        records, _ = _run_on_node(cl, pc.extract_neg_np_clause_pairs)
        labels = {(r['PhraseType'], r['Words']) for r in records}
        self.assertIn(('Np-Neg', 'אִישׁ | לֹא'), labels)

    def test_rejects_verbal_clause(self):
        cl = _wrap('CL', 'ADV-S-V',
                   _adv_role(1, 'לֹא'),
                   _s_role(2, 'דָוִד', strong='1732'),
                   _v_role(3),
                   head='2', node_id='verbal')
        records, _ = _run_on_node(cl, pc.extract_neg_np_clause_pairs)
        self.assertEqual(records, [])

    def test_rejects_object_partner(self):
        o = _wrap('O', 'Np2O', _np_noun(2, 'לֶחֶם', strong='3899'), head='0', node_id='O2')
        cl = _wrap('CL', 'ADV-O', _adv_role(1, 'לֹא'), o, head='1', node_id='advO')
        records, _ = _run_on_node(cl, pc.extract_neg_np_clause_pairs)
        self.assertEqual(records, [])

    def test_rejects_adjectival_p(self):
        cl = _wrap('CL', 'ADV-P', _adv_role(4, 'לֹא'), _p_role_adjp(5, 'טוֹב'),
                   head='1', node_id='adjp')
        records, _ = _run_on_node(cl, pc.extract_neg_np_clause_pairs)
        self.assertEqual(records, [])


class TestNegNpDoesNotAffectOtherRules(unittest.TestCase):
    """Neg-V / Neg-Adjp still come from extract_clause_pairs only."""

    def test_neg_v_still_emitted(self):
        cl = _wrap('CL', 'ADV-V', _adv_role(1, 'לֹא'), _v_role(2), head='1', node_id='negv')
        hits = Counter()
        records = pc.extract_clause_pairs(cl, VALID, 't.xml', 'TEST 1:1', hits)
        self.assertTrue(any(r['PhraseType'] == 'Neg-V' for r in records))
        # Pattern 2 must not also invent Neg-Np on a verbal clause.
        neg_np = pc.extract_neg_np_clause_pairs(cl, VALID, 't.xml', 'TEST 1:1', hits)
        self.assertEqual(neg_np, [])

    def test_neg_adjp_still_emitted(self):
        cl = _wrap('CL', 'ADV-P', _adv_role(1, 'לֹא'), _p_role_adjp(2, 'טוֹב'),
                   head='1', node_id='negadj')
        hits = Counter()
        records = pc.extract_clause_pairs(cl, VALID, 't.xml', 'TEST 1:1', hits)
        self.assertTrue(any(r['PhraseType'] == 'Neg-Adjp' for r in records))
        neg_np = pc.extract_neg_np_clause_pairs(cl, VALID, 't.xml', 'TEST 1:1', hits)
        self.assertEqual(neg_np, [])


class TestNegNpProcessFileIntegration(unittest.TestCase):
    """End-to-end: process_file wires both patterns and stays exception-safe."""

    def test_process_file_both_patterns(self):
        # Sentence with Pattern 1 AdvpNp and Pattern 2 ADV-P.
        sentence = ET.Element('Sentence', {'verse': 'TEST 1:1'})
        trees = ET.SubElement(sentence, 'Trees')
        tree = ET.SubElement(trees, 'Tree')
        root = ET.SubElement(tree, 'Node', {'Cat': 'S', 'Head': '0', 'nodeId': 'root'})

        adv = _term('adv', 1, 'לֹא', strong='3808', pos='particle', typ='negative')
        advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id='advp1')
        noun_np = _np_noun(2, 'אֱלֹהִים', strong='430')
        root.append(_wrap('np', 'AdvpNp', advp, noun_np, head='1', node_id='p1'))

        root.append(_wrap('CL', 'ADV-P', _adv_role(3, 'אַל', strong='408'),
                          _p_role_noun(4, 'אִישׁ', strong='376'),
                          head='1', node_id='clp2'))

        doc = ET.Element('Treebank')
        doc.append(sentence)

        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / 'sample.xml'
            ET.ElementTree(doc).write(xml_path, encoding='utf-8', xml_declaration=True)
            records = pc.process_file(
                str(xml_path), VALID, {}, Counter(), Counter())
        types = {r['PhraseType'] for r in records}
        self.assertIn('Neg-Np', types)
        words = {r['Words'] for r in records if r['PhraseType'] == 'Neg-Np'}
        self.assertIn('לֹא | אֱלֹהִים', words)
        self.assertIn('אַל | אִישׁ', words)

    def test_process_file_bad_xml_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            xml_path = Path(tmp) / 'bad.xml'
            xml_path.write_text('not xml at all', encoding='utf-8')
            records = pc.process_file(
                str(xml_path), VALID, {}, Counter(), Counter())
        self.assertEqual(records, [])


if __name__ == '__main__':
    unittest.main()
