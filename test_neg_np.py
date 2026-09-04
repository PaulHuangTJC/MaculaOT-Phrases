#!/usr/bin/env python3
"""Unit tests for Neg-Np / Np-Neg extraction (nnx_* engine) in phrase_checker.py."""

import tempfile
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import phrase_checker as pc


VALID = {'Neg-Np', 'Np-Neg', 'Neg-V', 'Neg-Adjp', 'ADV-V', 'S-P', 'P-S', 'AdvNP'}


def _m(word_idx, text, *, strong, pos, typ='', english='', macula='x', lemma=''):
    attrs = {
        'word': f'TEST 1:1!{word_idx}',
        'pos': pos,
        'english': english or text,
        'oshb-strongs': strong,
    }
    if typ:
        attrs['type'] = typ
    if lemma:
        attrs['lemma'] = lemma
    el = ET.Element('m', attrs)
    el.text = text
    return el


def _term(cat, word_idx, text, *, strong, pos, typ='', n='n1', lemma=''):
    node = ET.Element('Node', {'Cat': cat, 'n': n, 'StrongNumberX': strong, 'nodeId': n})
    node.append(_m(word_idx, text, strong=strong, pos=pos, typ=typ, macula=n, lemma=lemma))
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


def _affirmation_adv_role(word_idx, text, strong='389'):
    adv = _term('adv', word_idx, text, strong=strong, pos='particle', typ='affirmation', n=f'aadv{word_idx}')
    advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id=f'aadvp{word_idx}')
    return _wrap('ADV', 'Advp2ADV', advp, head='0', node_id=f'AADV{word_idx}')


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
    adjp = _wrap('adjp', 'Adjp2Adjp', adj, head='0', node_id=f'adjp{word_idx}')
    return _wrap('P', 'Adjp2P', adjp, head='0', node_id=f'Padj{word_idx}')


def _p_role_pp_noun(prep_idx, prep_text, noun_idx, noun_text, *, prep_strong='5921', noun_strong='7704'):
    prep = _term('prep', prep_idx, prep_text, strong=prep_strong, pos='preposition', n=f'pr{prep_idx}')
    pp = _wrap('pp', 'PrepNp', prep, _np_noun(noun_idx, noun_text, strong=noun_strong),
               head='1', node_id=f'pp{noun_idx}')
    return _wrap('P', 'Pp2P', pp, head='0', node_id=f'Ppp{noun_idx}')


def _p_role_existential(word_idx, text='יֵשׁ', strong='3426'):
    particle = _term('adv', word_idx, text, strong=strong, pos='particle',
                     n=f'ex{word_idx}', lemma=text)
    return _wrap('P', 'Adv2P', particle, head='0', node_id=f'Pex{word_idx}')


def _s_role_construct_participle(part_idx, part_text, gen_idx, gen_text, *,
                                 part_strong='5826', gen_strong='2719'):
    """JOB 29:12-style: Vp2Np substantive participle + genitive noun."""
    verb = _term('verb', part_idx, part_text, strong=part_strong, pos='verb',
                 typ='participle active', n=f'v{part_idx}')
    vp = _wrap('vp', 'V2VP', verb, head='0', node_id=f'vp{part_idx}')
    gen_noun = _term('noun', gen_idx, gen_text, strong=gen_strong, pos='noun', n=f'gn{gen_idx}')
    gen_np = _wrap('np', 'N2NP', gen_noun, head='0', node_id=f'gnp{gen_idx}')
    construct = _wrap('np', 'Vp2Np', vp, gen_np, head='0', node_id=f'cnp{part_idx}')
    return _wrap('S', 'Np2S', construct, head='0', node_id=f'Sp{part_idx}')


def _pp_role(prep_idx, noun_idx, prep_text='בְּ', noun_text='יָד'):
    prep = _term('prep', prep_idx, prep_text, strong='3027', pos='preposition', n=f'p{prep_idx}')
    pp = _wrap('pp', 'PrepNp', prep, _np_noun(noun_idx, noun_text, strong='3027'),
               head='1', node_id=f'pp{noun_idx}')
    return _wrap('PP', 'Pp2PP', pp, head='0', node_id=f'PP{noun_idx}')


def _v_role(word_idx, text='הלך', strong='1980'):
    verb = _term('verb', word_idx, text, strong=strong, pos='verb', n=f'v{word_idx}')
    vp = _wrap('vp', 'V2VP', verb, head='0', node_id=f'vp{word_idx}')
    return _wrap('V', 'Vp2V', vp, head='0', node_id=f'V{word_idx}')


def _run_np(node):
    hits = Counter()
    return pc.nnx_extract_np_patterns(node, VALID, 'test.xml', 'TEST 1:1', hits), hits


def _run_cl(node):
    hits = Counter()
    return pc.nnx_extract_cl_patterns(node, VALID, 'test.xml', 'TEST 1:1', hits), hits


class TestNnxNpLevel(unittest.TestCase):
    """NP-level: AdvpNp -> Neg-Np, NpAdvp -> Np-Neg (spec S2)."""

    def test_neg_np_advp_np(self):
        adv = _term('adv', 7, 'לֹא', strong='3808', pos='particle', typ='negative')
        advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id='advp')
        noun_np = _np_noun(8, 'מִשְׁפָּט', strong='4941')
        parent = _wrap('np', 'AdvpNp', advp, noun_np, head='1', node_id='p1')
        records, _ = _run_np(parent)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['PhraseType'], 'Neg-Np')
        self.assertEqual(records[0]['Words'], 'לֹא | מִשְׁפָּט')

    def test_np_neg_reverse_order(self):
        noun_np = _np_noun(3, 'אֱלֹהִים', strong='430')
        adv = _term('adv', 4, 'לֹא', strong='3808', pos='particle', typ='negative')
        advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id='advp')
        parent = _wrap('np', 'NpAdvp', noun_np, advp, head='0', node_id='p1r')
        records, _ = _run_np(parent)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['PhraseType'], 'Np-Neg')
        self.assertEqual(records[0]['Words'], 'אֱלֹהִים | לֹא')

    def test_rejects_affirmation_particle(self):
        adv = _term('adv', 1, 'אַךְ', strong='389', pos='particle', typ='affirmation')
        advp = _wrap('advp', 'Adv2Advp', adv, head='0', node_id='advp')
        noun_np = _np_noun(2, 'גָּמָל', strong='1581')
        parent = _wrap('np', 'AdvpNp', advp, noun_np, head='1', node_id='aff')
        records, _ = _run_np(parent)
        self.assertEqual(records, [])


class TestNnxClBasic(unittest.TestCase):
    """CL-level ADV-S / ADV-P / ADV-S-P patterns."""

    def test_neg_np_adv_p_noun(self):
        cl = _wrap('CL', 'ADV-P', _adv_role(6, 'לֹא'), _p_role_noun(7, 'עֵת'),
                   head='1', node_id='cl1')
        records, _ = _run_cl(cl)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['PhraseType'], 'Neg-Np')
        self.assertEqual(records[0]['Words'], 'לֹא | עֵת')

    def test_neg_np_adv_s(self):
        cl = _wrap('CL', 'ADV-S', _adv_role(1, 'לֹא'), _s_role(2, 'גֶּשֶׁם', strong='1653'),
                   head='1', node_id='cl_adv_s')
        records, _ = _run_cl(cl)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['PhraseType'], 'Neg-Np')

    def test_equative_adv_p_s_reports_p_noun(self):
        cl = _wrap('CL', 'ADV-P-S',
                   _adv_role(1, 'לֹא'),
                   _p_role_noun(2, 'אִישׁ', strong='376'),
                   _s_role(3, 'הוּא', strong='1931', pos='pronoun'),
                   head='2', node_id='cl_equative')
        records, _ = _run_cl(cl)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['Words'], 'לֹא | אִישׁ')

    def test_np_neg_s_before_adv(self):
        # ADV-S with S preceding the negator -> Np-Neg (not ADV-S-P, where P
        # noun would win per the equative table).
        cl = _wrap('CL', 'S-ADV',
                   _s_role(10, 'אִישׁ', strong='376'),
                   _adv_role(11, 'לֹא'),
                   head='1', node_id='cl3')
        records, _ = _run_cl(cl)
        labels = {(r['PhraseType'], r['Words']) for r in records}
        self.assertIn(('Np-Neg', 'אִישׁ | לֹא'), labels)

    def test_rejects_copular_adjective_p(self):
        cl = _wrap('CL', 'ADV-P', _adv_role(4, 'לֹא'), _p_role_adjp(5, 'טוֹב'),
                   head='1', node_id='adjp')
        records, _ = _run_cl(cl)
        self.assertEqual(records, [])

    def test_rejects_verbal_clause(self):
        cl = _wrap('CL', 'ADV-S-V',
                   _adv_role(1, 'לֹא'),
                   _s_role(2, 'דָוִד', strong='1732'),
                   _v_role(3),
                   head='2', node_id='verbal')
        records, _ = _run_cl(cl)
        self.assertEqual(records, [])


class TestBareAdvPPp2P(unittest.TestCase):
    """Fix 1: bare ADV-P + Pp2P reports PP object (spec S1.3 / S5.3)."""

    def test_adv_p_pp2p_emits_pp_object(self):
        cl = _wrap('CL', 'ADV-P',
                   _adv_role(1, 'לֹא'),
                   _p_role_pp_noun(2, 'כְּ', 3, 'שָׂדֶה', noun_strong='7704'),
                   head='1', node_id='cl_bare_pp')
        records, _ = _run_cl(cl)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['PhraseType'], 'Neg-Np')
        self.assertEqual(records[0]['Words'], 'לֹא | שָׂדֶה')


class TestAmbiguousDuplicateCat(unittest.TestCase):
    """Fix 2: duplicate Cat in Rule string no longer blanket-skips (spec S5.1)."""

    def test_adv_adv_p_finds_real_negator(self):
        cl = _wrap('CL', 'ADV-ADV-P',
                   _adv_role(1, 'לֹא'),
                   _affirmation_adv_role(2, 'אַךְ'),
                   _p_role_noun(3, 'בַּת', strong='1323'),
                   head='2', node_id='cl_dup_adv')
        records, _ = _run_cl(cl)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['Words'], 'לֹא | בַּת')

    def test_adv_s_adv_p_finds_real_negator(self):
        cl = _wrap('CL', 'ADV-S-ADV-P',
                   _adv_role(1, 'לֹא'),
                   _s_role(2, 'מֶלֶךְ', strong='4428'),
                   _term('adv', 3, 'יַחְדָּו', strong='3162', pos='adverb'),
                   _p_role_noun(4, 'אֱלֹהִים', strong='430'),
                   head='2', node_id='cl_dup_adv2')
        # Wrap the bare adverb in ADV for the second ADV slot.
        bare_adv = cl[2]
        cl.remove(bare_adv)
        adv2 = _wrap('ADV', 'Adv2ADV', bare_adv, head='0', node_id='ADV3')
        cl.append(adv2)
        records, _ = _run_cl(cl)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['Words'], 'לֹא | אֱלֹהִים')


class TestExistentialParticleOnP(unittest.TestCase):
    """Fix 3: existential particle on P -> S-primary (spec S5.2 / S5.5)."""

    def test_adv_p_s_existential_reports_s_noun(self):
        cl = _wrap('CL', 'ADV-P-S',
                   _adv_role(1, 'לֹא'),
                   _p_role_existential(2, 'יֵשׁ', strong='3426'),
                   _s_role(3, 'רוּחַ', strong='7307'),
                   head='2', node_id='cl_exist')
        records, _ = _run_cl(cl)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['Words'], 'לֹא | רוּחַ')


class TestSubstantiveOverrideVp2Np(unittest.TestCase):
    """Fix 4: Vp2Np construct participle on S counts as noun-equivalent (S1.4a)."""

    def test_locative_existential_with_vp2np_s(self):
        cl = _wrap('CL', 'ADV-S-P',
                   _adv_role(1, 'לֹא'),
                   _s_role_construct_participle(2, 'עֹזֵר', 3, 'אֶבְיוֹן'),
                   _p_role_pp_noun(4, 'לְ', 5, 'רֶגֶל', noun_strong='7272'),
                   head='2', node_id='cl_vp2np')
        records, _ = _run_cl(cl)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['Words'], 'לֹא | עֹזֵר')


class TestV10InfinitiveConstructExcluded(unittest.TestCase):
    """v10: Vp2Np + infinitive construct is NOT a Neg-Np match (PSA 75:7)."""

    def test_adv_s_pp_vp2np_infinitive_excluded(self):
        verb = _term('verb', 2, 'הָרִים', strong='7311', pos='verb',
                     typ='infinitive construct', n='v2')
        vp = _wrap('vp', 'V2VP', verb, head='0', node_id='vp2')
        gen_noun = _term('noun', 3, 'מִזְרָח', strong='4217', pos='noun', n='gn3')
        gen_np = _wrap('np', 'N2NP', gen_noun, head='0', node_id='gnp3')
        construct = _wrap('np', 'Vp2Np', vp, gen_np, head='0', node_id='cnp2')
        s_role = _wrap('S', 'Np2S', construct, head='0', node_id='S2')
        cl = _wrap('CL', 'ADV-S-PP',
                   _adv_role(1, 'לֹא'),
                   s_role,
                   _pp_role(4, 5, noun_text='מִדְבָּר'),
                   head='1', node_id='cl_inf')
        records, _ = _run_cl(cl)
        self.assertEqual(records, [])
        included, res = pc.nnx_resolve_simple(s_role)
        self.assertFalse(included)
        self.assertTrue(pc._nnx_is_unreverted_infinitive_construct_use(res))


class TestAdvPpExclusion(unittest.TestCase):
    """ADV-PP is categorically excluded (spec S1.4d)."""

    def test_adv_pp_excluded_even_with_noun_inside(self):
        cl = _wrap('CL', 'ADV-PP',
                   _adv_role(1, 'לֹא'),
                   _pp_role(2, 3, noun_text='חֶרֶב'),
                   head='1', node_id='cl_adv_pp')
        records, _ = _run_cl(cl)
        self.assertEqual(records, [])


class TestNegNpDoesNotAffectOtherRules(unittest.TestCase):
    """Neg-V / Neg-Adjp still come from extract_clause_pairs only."""

    def test_neg_v_still_emitted(self):
        cl = _wrap('CL', 'ADV-V', _adv_role(1, 'לֹא'), _v_role(2), head='1', node_id='negv')
        hits = Counter()
        records = pc.extract_clause_pairs(cl, VALID, 't.xml', 'TEST 1:1', hits)
        self.assertTrue(any(r['PhraseType'] == 'Neg-V' for r in records))
        neg_np, _ = _run_cl(cl)
        self.assertEqual(neg_np, [])

    def test_neg_adjp_still_emitted(self):
        cl = _wrap('CL', 'ADV-P', _adv_role(1, 'לֹא'), _p_role_adjp(2, 'טוֹב'),
                   head='1', node_id='negadj')
        hits = Counter()
        records = pc.extract_clause_pairs(cl, VALID, 't.xml', 'TEST 1:1', hits)
        self.assertTrue(any(r['PhraseType'] == 'Neg-Adjp' for r in records))
        neg_np, _ = _run_cl(cl)
        self.assertEqual(neg_np, [])


class TestNegNpProcessFileIntegration(unittest.TestCase):
    """End-to-end: process_file wires the nnx_* engine."""

    def test_process_file_both_patterns(self):
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
