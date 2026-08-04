import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Tuple, Dict
import os
from pathlib import Path
from itertools import combinations

def get_node_info(node: ET.Element, category: str, index: int = 0) -> Tuple[List[str], List[str], List[str]]:
    """獲取指定Category節點的StrongNumberX、word和n值
    
    Args:
        node: XML節點
        category: 要搜尋的Category值
        index: 要獲取第幾個符合的節點 (0-based)
    """
    strong_numbers = []
    words = []
    macula_ids = []
    
    # 找出所有符合category的節點
    matching_nodes = []
    
    # 檢查當前節點是否為S或O且有Head屬性
    # 檢查直接子節點
    for child in node:
        if child.get('Cat') == category and child.get('Cat') in ['S', 'O']:
            # 檢查子節點是否有Head屬性
            head_value = child.get('Head')
            if head_value:
                # 計算要跳過的節點數
                skip_count = int(head_value)
                # 獲取所有子節點的子節點
                children = list(child)
                # 從指定位置開始查找
                if skip_count < len(children):
                    start_node = children[skip_count]
                    strong_num = start_node.get('StrongNumberX')
                    # print('S|O:', start_node.get('Rule'), strong_num, len(children), skip_count)
                    if strong_num:
                        matching_nodes.append({
                            'node': start_node,
                            'strong': strong_num,
                            'n': start_node.get('n', ''),
                            'word': start_node.findall('.//m')[0].get('word', '') if start_node.findall('.//m') else ''
                        })
                        continue

                    else:
                        # 在跳過的節點之後查找符合的資訊
                        subhead_value = start_node.get('Head')
                        # print('subhead', subhead_value)
                        if subhead_value:
                        # 計算要跳過的節點數
                            subskip_count = int(subhead_value)
                            # 獲取所有子節點的子節點
                            sub_children = list(start_node)
                            # 從指定位置開始查找
                            if subskip_count < len(sub_children):
                                suhstart_node = sub_children[subskip_count]
                                strong_num = suhstart_node.get('StrongNumberX')
                                # print('subnode', suhstart_node.get('Rule'), strong_num, subhead_value, sub_children)
                                # 查找子節點
                                if strong_num:
                                        matching_nodes.append({
                                            'node': suhstart_node,
                                            'strong': strong_num,
                                            'n': suhstart_node.get('n', ''),
                                            'word': suhstart_node.findall('.//m')[0].get('word', '') if suhstart_node.findall('.//m') else ''
                                        })
                                        continue
                                else:
                                    # 在跳過的節點之後查找符合的資訊
                                    sub2head_value = suhstart_node.get('Head')
                                    if sub2head_value:
                                    # 計算要跳過的節點數
                                        sub2skip_count = int(sub2head_value)
                                        # 獲取所有子節點的子節點
                                        sub2_children = list(suhstart_node)
                                        # 從指定位置開始查找
                                        if sub2skip_count < len(sub2_children):
                                            suh2start_node = sub2_children[sub2skip_count]
                                            strong_num = suh2start_node.get('StrongNumberX')
                                            # print('sub2node', suh2start_node.get('Rule'), strong_num, sub2head_value, sub2_children)
                                            if strong_num:
                                                matching_nodes.append({
                                                    'node': suh2start_node,
                                                    'strong': strong_num,
                                                    'n': suh2start_node.get('n', ''),
                                                    'word': suh2start_node.findall('.//m')[0].get('word', '') if suh2start_node.findall('.//m') else ''
                                                })
                                                continue
                                            else:
                                                # 在跳過的節點之後查找符合的資訊
                                                sub3head_value = suh2start_node.get('Head')
                                                if sub3head_value:
                                                # 計算要跳過的節點數
                                                    sub3skip_count = int(sub3head_value)
                                                    # 獲取所有子節點的子節點
                                                    sub3_children = list(suh2start_node)
                                                    # 從指定位置開始查找
                                                    if sub3skip_count < len(sub3_children):
                                                        suh3start_node = sub3_children[sub3skip_count]
                                                        strong_num = suh3start_node.get('StrongNumberX')
                                                        # print('sub3node', suh3start_node.get('Rule'), strong_num, sub3head_value, sub3_children)
                                                        if strong_num:
                                                            matching_nodes.append({
                                                                'node': suh3start_node,
                                                                'strong': strong_num,
                                                                'n': suh3start_node.get('n', ''),
                                                                'word': suh3start_node.findall('.//m')[0].get('word', '') if suh3start_node.findall('.//m') else ''
                                                            })
                                                            continue
                                                        else:
                                                            # 在跳過的節點之後查找符合的資訊
                                                            sub4head_value = suh3start_node.get('Head')
                                                            if sub4head_value:
                                                            # 計算要跳過的節點數
                                                                sub4skip_count = int(sub4head_value)
                                                                # 獲取所有子節點的子節點
                                                                sub4_children = list(suh3start_node)
                                                                # 從指定位置開始查找
                                                                if sub4skip_count < len(sub4_children):
                                                                    suh4start_node = sub4_children[sub4skip_count]
                                                                    strong_num = suh4start_node.get('StrongNumberX')
                                                                    # print('sub4node', suh4start_node.get('Rule'), strong_num, sub4head_value, sub4_children)
                                                                    if strong_num:
                                                                        matching_nodes.append({
                                                                            'node': suh4start_node,
                                                                            'strong': strong_num,
                                                                            'n': suh4start_node.get('n', ''),
                                                                            'word': suh4start_node.findall('.//m')[0].get('word', '') if suh4start_node.findall('.//m') else ''
                                                                        })
                                                                        continue
                                                                    else:
                                                                        # 在跳過的節點之後查找符合的資訊
                                                                        sub5head_value = suh4start_node.get('Head')
                                                                        if sub5head_value:
                                                                        # 計算要跳過的節點數
                                                                            sub5skip_count = int(sub5head_value)
                                                                            # 獲取所有子節點的子節點
                                                                            sub5_children = list(suh4start_node)
                                                                            # 從指定位置開始查找
                                                                            if sub5skip_count < len(sub5_children):
                                                                                suh5start_node = sub5_children[sub5skip_count]
                                                                                strong_num = suh5start_node.get('StrongNumberX')
                                                                                # print('sub5node', suh5start_node.get('Rule'), strong_num, sub5head_value, sub5_children)
                                                                                if strong_num:
                                                                                    matching_nodes.append({
                                                                                        'node': suh5start_node,
                                                                                        'strong': strong_num,
                                                                                        'n': suh5start_node.get('n', ''),
                                                                                        'word': suh5start_node.findall('.//m')[0].get('word', '') if suh5start_node.findall('.//m') else ''
                                                                                    })
                                                                                    continue
                                                                                else:
                                                                                    # 在跳過的節點之後查找符合的資訊
                                                                                    sub6head_value = suh5start_node.get('Head')
                                                                                    if sub6head_value:
                                                                                    # 計算要跳過的節點數
                                                                                        sub6skip_count = int(sub6head_value)
                                                                                        # 獲取所有子節點的子節點
                                                                                        sub6_children = list(suh5start_node)
                                                                                        # 從指定位置開始查找
                                                                                        if sub6skip_count < len(sub6_children):
                                                                                            suh6start_node = sub6_children[sub6skip_count]
                                                                                            strong_num = suh6start_node.get('StrongNumberX')
                                                                                            # print('sub6node', suh6start_node.get('Rule'), strong_num, sub6head_value, sub6_children)
                                                                                            if strong_num:
                                                                                                matching_nodes.append({
                                                                                                    'node': suh6start_node,
                                                                                                    'strong': strong_num,
                                                                                                    'n': suh6start_node.get('n', ''),
                                                                                                    'word': suh6start_node.findall('.//m')[0].get('word', '') if suh6start_node.findall('.//m') else ''
                                                                                                })
                                                                                                continue
                                                                                            else:
                                                                                                # 在跳過的節點之後查找符合的資訊
                                                                                                sub7head_value = suh6start_node.get('Head')
                                                                                                if sub7head_value:
                                                                                                # 計算要跳過的節點數
                                                                                                    sub7skip_count = int(sub7head_value)
                                                                                                    # 獲取所有子節點的子節點
                                                                                                    sub7_children = list(suh6start_node)
                                                                                                    # 從指定位置開始查找
                                                                                                    if sub7skip_count < len(sub7_children):
                                                                                                        suh7start_node = sub7_children[sub7skip_count]
                                                                                                        strong_num = suh7start_node.get('StrongNumberX')
                                                                                                        # print('sub7node', suh7start_node.get('Rule'), strong_num, sub7head_value, sub7_children)
                                                                                                        if strong_num:
                                                                                                            matching_nodes.append({
                                                                                                                'node': suh7start_node,
                                                                                                                'strong': strong_num,
                                                                                                                'n': suh7start_node.get('n', ''),
                                                                                                                'word': suh7start_node.findall('.//m')[0].get('word', '') if suh7start_node.findall('.//m') else ''
                                                                                                            })
                                                                                                            continue

        # 處理非S,O節點
        if child.get('Cat') == category and child.get('Cat') not in ['S', 'O']:
            # print(child.get('Cat'), category)
            # 原有的邏輯
            strong_num = child.get('StrongNumberX')
            if strong_num:
                matching_nodes.append({
                    'node': child,
                    'strong': strong_num,
                    'n': child.get('n', ''),
                    'word': child.findall('.//m')[0].get('word', '') if child.findall('.//m') else ''
                })
                continue
            
            # 檢查子節點
            for subchild in child.findall('.//Node'):
                strong_num = subchild.get('StrongNumberX')
                if strong_num:
                    matching_nodes.append({
                        'node': subchild,
                        'strong': strong_num,
                        'n': subchild.get('n', ''),
                        'word': subchild.findall('.//m')[0].get('word', '') if subchild.findall('.//m') else ''
                    })
                    break
    
    # 如果找到足夠的節點且index有效
    if 0 <= index < len(matching_nodes):
        node_info = matching_nodes[index]
        strong_numbers.append(node_info['strong'])
        words.append(node_info['word'])
        macula_ids.append(node_info['n'])
    
    return strong_numbers, words, macula_ids

# def split_rule_to_pairs(rule: str) -> List[str]:
#     """將多詞性規則拆分為兩兩一組"""
#     parts = rule.split('-')
#     pairs = []
#     for i in range(len(parts) - 1):
#         pairs.append(f"{parts[i]}-{parts[i+1]}")
#     return pairs

def get_all_pairs(rule: str) -> List[str]:
    """從多詞性規則中獲取所有可能的兩兩組合"""
    parts = rule.split('-')
    pairs = []
    
    # 獲取所有相鄰的兩兩組合
    # for i in range(len(parts) - 1):
    #     pairs.append(f"{parts[i]}-{parts[i+1]}")
    
    # 對於特殊情況 (如 O-PP-V)，也要考慮非相鄰的組合
    if len(parts) >= 2:
        for i, j in combinations(range(len(parts)), 2):
            # if j - i > 1:  # 非相鄰的部分
                pair = f"{parts[i]}-{parts[j]}"
                if pair not in pairs:
                    pairs.append(pair)
    # print(pairs)
    return pairs

def is_phrase_rule(rule: str) -> bool:
    """檢查規則是否包含短語類型"""
    phrase_types = ['V-S', 'S-V', 'V-PP', 'PP-V', 'PP-NP', 'NP-PP', 'NP-NP', 'V-O', 'O-V', 'V-ADV', 'ADV-V', 'V-O2', 'O2-V', 'PP-O', 'O-PP',
                     'Neg-V', 'V-Neg', 'PrepNp', 'NPofNP', 'AdjpNp', 'NpAdjp', 'AdjpofNp', 'NpAdvp', 'AdvpNp', 'Np-Appos', 'NpaNp']
    # add pp-v, np-pp, Np-Appos (12/30 add no test)
    # 如果是直接匹配的情況
    if rule in phrase_types or (rule.startswith('Conj') and rule.endswith('Pp')):
        return True
    
    # 如果是多詞性規則
    if '-' in rule:
        phrase_pairs = get_all_pairs(rule)
        return any(pair in phrase_types for pair in phrase_pairs)
    # print(any(pair in phrase_types for pair in pairs))
    return False

def get_phrase_info(node: ET.Element, rule: str) -> List[Dict]:
    """根據規則類型獲取短語資訊"""
    results = []
    
    if rule in ['PrepNp', 'NPofNP', 'AdjpNp', 'NpAdjp', 'AdjpofNp', 'NpAdvp', 'AdvpNp', 'Np-Appos', 'NpaNp'] or (rule.startswith('Conj') and rule.endswith('Pp')):
        # 處理現有的特殊規則
        # ... (existing special rule handling code remains the same)
        if rule == 'PrepNp':
            # 處理PrepNp規則
            prep_strongs, prep_words, prep_ids = [], [], []
            noun_strongs, noun_words, noun_ids = [], [], []
            
            # 獲取PrepNp的節點資訊
            for child in node.findall('.//Node[@Cat="prep"]'):
                if child.get('StrongNumberX'):
                    prep_strongs.append(child.get('StrongNumberX', ''))
                    prep_ids.append(child.get('n', ''))
                    m_elements = child.findall('.//m')
                    prep_words.append(m_elements[0].get('word', '') if m_elements else '')
                
            for child in node.findall('.//Node[@Cat="noun"]'):
                if child.get('StrongNumberX'):
                    noun_strongs.append(child.get('StrongNumberX', ''))
                    noun_ids.append(child.get('n', ''))
                    m_elements = child.findall('.//m')
                    noun_words.append(m_elements[0].get('word', '') if m_elements else '')

            # 添加基本的PrepNp結果 不儲存空值
            if prep_strongs and noun_strongs:
                results.append({
                    'PhraseType': rule,
                    'StrongIDs': f"{prep_strongs[0] if prep_strongs else ''} | {noun_strongs[0] if noun_strongs else ''}",
                    'Words': f"{prep_words[0] if prep_words else ''} | {noun_words[0] if noun_words else ''}",
                    'MaculaID': f"{prep_ids[0] if prep_ids else ''} | {noun_ids[0] if noun_ids else ''}"
                })
            
            # 檢查相鄰的動詞節點
            # parent = node.getparent()
            current = node
            while current.get('Cat') != 'CL':
                parent = current.getparent()
                if parent is None or parent.get('Rule') == 'PPandPP':
                    break
                current = parent

            if parent is not None:
                # 獲取所有直接子節點
                children = list(parent.findall('.//Node'))
                current_index = children.index(node)
                
                # 檢查前後節點是否有動詞 並確認動詞父節點與間接受詞之父節點是否相同
                for i, sibling in enumerate(children):
                    if sibling.get('Cat') == 'V' and sibling.getparent().get('Rule') == parent.get('Rule'):
                        verb_node = sibling
                        # 獲取動詞資訊
                        for verb_node in sibling.findall('.//Node[@Cat="verb"]'):
                            verb_strong = verb_node.get('StrongNumberX', '')
                            verb_id = verb_node.get('n', '')
                            m_elements = verb_node.findall('.//m')
                            verb_word = m_elements[0].get('word', '') if m_elements else ''
                        
                        # 根據位置決定短語類型
                        if i < current_index and noun_strongs:  # 動詞在PrepNp前
                            results.append({
                                'PhraseType': 'V-IO',
                                'StrongIDs': f"{verb_strong} | {noun_strongs[0] if noun_strongs else ''}",
                                'Words': f"{verb_word} | {noun_words[0] if noun_words else ''}",
                                'MaculaID': f"{verb_id} | {noun_ids[0] if noun_ids else ''}"
                            })
                        elif i > current_index and noun_strongs:  # 動詞在PrepNp後
                            results.append({
                                'PhraseType': 'IO-V',
                                'StrongIDs': f"{noun_strongs[0] if noun_strongs else ''} | {verb_strong}",
                                'Words': f"{noun_words[0] if noun_words else ''} | {verb_word}",
                                'MaculaID': f"{noun_ids[0] if noun_ids else ''} | {verb_id}"
                            })
            
        elif rule == 'NPofNP' or rule == 'Np-Appos' or rule == 'NpaNp':
            # 處理NPofNP及Np-Appos規則
            noun_strongs, noun_words, noun_ids = [], [], []

            for child in node.findall('.//Node[@Cat="noun"]'):
                if child.get('StrongNumberX'):
                    noun_strongs.append(child.get('StrongNumberX', ''))
                    noun_ids.append(child.get('n', ''))
                    m_elements = child.findall('.//m')
                    noun_words.append(m_elements[0].get('word', '') if m_elements else '')

            # 不儲存空值
            if len(noun_strongs) > 1:
                results.append({
                    'PhraseType': rule,
                    'StrongIDs': f"{noun_strongs[0]} | {noun_strongs[1]}",
                    'Words': f"{noun_words[0]} | {noun_words[1]}",
                    'MaculaID': f"{noun_ids[0]} | {noun_ids[1]}"
                })

        elif rule == 'AdjpNp' or rule == 'NpAdjp' or rule == 'AdjpofNp':
            # 處理NpNump規則
            noun_strongs, noun_words, noun_ids = [], [], []
            adj_strongs, adj_words, adj_ids = [], [], []
            
            for child in node.findall('.//Node[@Cat="noun"]'):
                if child.get('StrongNumberX'):
                    noun_strongs.append(child.get('StrongNumberX', ''))
                    noun_ids.append(child.get('n', ''))
                    m_elements = child.findall('.//m')
                    noun_words.append(m_elements[0].get('word', '') if m_elements else '')

            for child in node.findall('.//Node[@Cat="adj"]'):
                if child.get('StrongNumberX'):
                    adj_strongs.append(child.get('StrongNumberX', ''))
                    adj_ids.append(child.get('n', ''))
                    m_elements = child.findall('.//m')
                    adj_words.append(m_elements[0].get('word', '') if m_elements else '')
            
            if noun_strongs and adj_strongs and (rule == 'AdjpNp' or rule == 'AdjpofNp'):
                results.append({
                    'PhraseType': rule,
                    'StrongIDs': f"{adj_strongs[0] if adj_strongs else ''} | {noun_strongs[0] if noun_strongs else ''}",
                    'Words': f"{adj_words[0] if adj_words else ''} | {noun_words[0] if noun_words else ''}",
                    'MaculaID': f"{adj_ids[0] if adj_ids else ''} | {noun_ids[0] if noun_ids else ''}"
                })

            if noun_strongs and adj_strongs and rule == 'NpAdjp':
                results.append({
                    'PhraseType': rule,
                    'StrongIDs': f"{noun_strongs[0] if noun_strongs else ''} | {adj_strongs[0] if adj_strongs else ''}",
                    'Words': f"{noun_words[0] if noun_words else ''} | {adj_words[0] if adj_words else ''}",
                    'MaculaID': f"{noun_ids[0] if noun_ids else ''} | {adj_ids[0] if adj_ids else ''}"
                })

        elif rule == 'AdvpNp' or rule == 'NpAdvp':
            # 處理NpNump規則
            noun_strongs, noun_words, noun_ids = [], [], []
            adv_strongs, adv_words, adv_ids = [], [], []
            
            for child in node.findall('.//Node[@Cat="noun"]'):
                if child.get('StrongNumberX'):
                    noun_strongs.append(child.get('StrongNumberX', ''))
                    noun_ids.append(child.get('n', ''))
                    m_elements = child.findall('.//m')
                    noun_words.append(m_elements[0].get('word', '') if m_elements else '')

            for child in node.findall('.//Node[@Cat="adv"]'):
                if child.get('StrongNumberX'):
                    adv_strongs.append(child.get('StrongNumberX', ''))
                    adv_ids.append(child.get('n', ''))
                    m_elements = child.findall('.//m')
                    adv_words.append(m_elements[0].get('word', '') if m_elements else '')
            
            if noun_strongs and adv_strongs and rule == 'AdvpNp':
                results.append({
                    'PhraseType': rule,
                    'StrongIDs': f"{adv_strongs[0] if adv_strongs else ''} | {noun_strongs[0] if noun_strongs else ''}",
                    'Words': f"{adv_words[0] if adv_words else ''} | {noun_words[0] if noun_words else ''}",
                    'MaculaID': f"{adv_ids[0] if adv_ids else ''} | {noun_ids[0] if noun_ids else ''}"
                })

            if noun_strongs and adv_strongs and rule == 'NpAdvp':
                results.append({
                    'PhraseType': rule,
                    'StrongIDs': f"{noun_strongs[0] if noun_strongs else ''} | {adv_strongs[0] if adv_strongs else ''}",
                    'Words': f"{noun_words[0] if noun_words else ''} | {adv_words[0] if adv_words else ''}",
                    'MaculaID': f"{noun_ids[0] if noun_ids else ''} | {adv_ids[0] if adv_ids else ''}"
                })
        
        elif rule.startswith('Conj') and rule.endswith('Pp'):
            # 處理 ConjxPp 規則 (x = 3,4,7 等)
            prep_nodes = []  # 存儲所有 pp 節點
            verb_info = None  # 存儲動詞節點資訊
            
            # 找出所有 pp 子節點
            for pp_node in node.findall('.//Node[@Cat="pp"]'):
                # 檢查是否為直接子節點
                if pp_node.getparent() == node:
                    prep_node = pp_node.find('.//Node[@Cat="prep"]')
                    if prep_node is not None and prep_node.get('StrongNumberX'):
                        prep_nodes.append({
                            'strong': prep_node.get('StrongNumberX'),
                            'word': prep_node.findall('.//m')[0].get('word', '') if prep_node.findall('.//m') else '',
                            'id': prep_node.get('n', '')
                        })
            
            # 找出相同父節點下的動詞節點
            parent = node
            while parent is not None and parent.get('Cat') != 'CL':
                parent = parent.getparent()
            
            if parent is not None:
                verb_node = parent.find('.//Node[@Cat="V"]')
                if verb_node is not None:
                    verb_subnode = verb_node.find('.//Node[@Cat="verb"]')
                    if verb_subnode is not None and verb_subnode.get('StrongNumberX'):
                        verb_info = {
                            'strong': verb_subnode.get('StrongNumberX'),
                            'word': verb_subnode.findall('.//m')[0].get('word', '') if verb_subnode.findall('.//m') else '',
                            'id': verb_subnode.get('n', '')
                        }
            
            # 如果找到動詞和介係詞，生成短語
            if verb_info and prep_nodes:
                # 獲取期望的介係詞數量
                expected_count = int(rule[4:-2])  # 從 'ConjXPp' 提取數字
                
                # 確保不超過10組且不超過找到的介係詞數量
                phrase_count = min(expected_count, len(prep_nodes), 10)
                
                # 檢查動詞位置（在介係詞前還是後）
                verb_index = -1
                prep_index = -1
                
                for i, child in enumerate(parent):
                    if child.find('.//Node[@Cat="V"]') is not None:
                        verb_index = i
                    if child.find('.//Node[@Cat="pp"]') is not None:
                        prep_index = i
                        break
                
                # 生成短語
                for i in range(phrase_count):
                    if verb_index < prep_index:
                        # 動詞在前
                        results.append({
                            'PhraseType': 'VerbPrep',
                            'StrongIDs': f"{verb_info['strong']} | {prep_nodes[i]['strong']}",
                            'Words': f"{verb_info['word']} | {prep_nodes[i]['word']}",
                            'MaculaID': f"{verb_info['id']} | {prep_nodes[i]['id']}"
                        })
                    else:
                        # 介係詞在前
                        results.append({
                            'PhraseType': 'PrepVerb',
                            'StrongIDs': f"{prep_nodes[i]['strong']} | {verb_info['strong']}",
                            'Words': f"{prep_nodes[i]['word']} | {verb_info['word']}",
                            'MaculaID': f"{prep_nodes[i]['id']} | {verb_info['id']}"
                        })
        
        #special rule end
        pass
    
    else:
        # 處理多詞性規則
        partsRule = rule.split('-')
        phrase_types = ['V-S', 'S-V', 'V-PP', 'PP-V', 'PP-NP', 'NP-PP', 'NP-NP', 'V-O', 'O-V', 'V-ADV', 'ADV-V', 'Neg-V', 'V-Neg',
                         'V-O2', 'O2-V', 'PP-O', 'O-PP']
        
        # 1. 改用list存儲每個詞性的節點資訊
        node_infos = []  # 用於存儲每個詞性的節點資訊
        part_counts = {}  # 追踪每個part被使用的次數
        for part in partsRule:
            if part not in part_counts:
                part_counts[part] = 0
            
            strongs, words, ids = get_node_info(node, part, part_counts[part])
            if strongs:  # 只保存有資訊的節點
                node_infos.append({
                    'part': "Neg" if node.findall('.//m')[0].get('type', '') == 'negative' and part == 'ADV' else part,
                    'strongs': strongs,
                    'words': words,
                    'ids': ids
                })
                part_counts[part] += 1  # 更新計數器
                print(node.findall('.//m')[0].get('type', ''), part, "Neg" if node.findall('.//m')[0].get('type', '') == 'negative' and part == 'ADV' else part)
        
        # 2. 生成所有可能的兩兩組合
        for i, first_entry in enumerate(node_infos):
            for j, second_entry in enumerate(node_infos[i+1:], i+1):
                pair = f"{first_entry['part']}-{second_entry['part']}"
                
                # 3. 檢查是否為有效的短語類型 
                if pair in phrase_types:
                    # 更改Rule名稱V-PP和PP-V為VerbPrep和PrepVerb
                    if pair == 'V-PP':
                        pair = 'VerbPrep'
                    elif pair == 'PP-V':
                        pair = 'PrepVerb'

                    results.append({
                        'PhraseType': pair,
                        'StrongIDs': f"{first_entry['strongs'][0]} | {second_entry['strongs'][0]}",
                        'Words': f"{first_entry['words'][0]} | {second_entry['words'][0]}",
                        'MaculaID': f"{first_entry['ids'][0]} | {second_entry['ids'][0]}"
                    })
    
    return results

def find_parent_nodeid(node: ET.Element) -> str:
    """找出父節點中Cat='CL'或Head='1'或Cat='np'的nodeId"""
    current = node
    while current is not None:
        if current.get('Cat') == 'CL' or current.get('Head') == '1' or current.get('Cat') == 'np':
            return current.get('nodeId', '')
        parent = current.getparent() if hasattr(current, 'getparent') else None
        if parent is None:
            break
        current = parent
    return ''

def extract_phrases(xml_file: str) -> List[dict]:
    """從XML文件中提取短語資訊"""
    try:
        from lxml import etree
        parser = etree.XMLParser(recover=True)
        
        if not os.path.exists(xml_file):
            raise FileNotFoundError(f"找不到檔案: {xml_file}")
            
        print(f"正在處理檔案: {xml_file}")
        tree = etree.parse(xml_file, parser)
        root = tree.getroot()
        
        results = []
        
        # 搜尋所有Node元素
        for node in root.findall('.//Node'):
            rule = node.get('Rule', '')
            if is_phrase_rule(rule):
                # 獲取父節點ID
                parent_node_id = find_parent_nodeid(node)
                
                # 獲取短語資訊
                phrase_infos = get_phrase_info(node, rule)
                
                # 添加父節點ID到每個結果
                for info in phrase_infos:
                    info['ParentNodeID'] = parent_node_id
                    results.append(info)

        # 去除重複資料
        unique_results = []
        seen = set()
        
        for result in results:
            # 將字典轉換為可雜湊的元組
            result_tuple = tuple(sorted(result.items()))
            
            # 如果這個組合還沒有看過，就加入結果
            if result_tuple not in seen:
                seen.add(result_tuple)
                unique_results.append(result)
        
        return unique_results
        
    except Exception as e:
        print(f"處理檔案時發生錯誤: {str(e)}")
        return []

def main():
    try:
        current_dir = os.getcwd()
        print(f"目前工作目錄: {current_dir}")
        
        # 定義輸入和輸出目錄
        #input_dir = os.path.join(current_dir, "Rhema-Backend", "ReNew-Phrases-OT", "XML-Source")
        #output_dir = os.path.join(current_dir, "Rhema-Backend", "ReNew-Phrases-OT", "CSV-Output")
        input_dir = os.path.join(current_dir, "XML-Source")
        output_dir = os.path.join(current_dir, "CSV-Output") 

        print(f"輸入目錄: {input_dir}")
        print(f"輸出目錄: {output_dir}")
        
        # 確保輸出目錄存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 檢查輸入目錄是否存在
        if not os.path.exists(input_dir):
            print(f"錯誤: 找不到輸入目錄 {input_dir}")
            return
            
        # 獲取所有XML文件
        xml_files = [f for f in os.listdir(input_dir) if f.endswith('.xml')]
        
        if not xml_files:
            print(f"在 {input_dir} 中沒有找到XML文件")
            return
            
        print(f"找到 {len(xml_files)} 個XML文件")
        
        # 處理每個XML文件
        for xml_file in xml_files:
            input_path = os.path.join(input_dir, xml_file)
            # 創建對應的CSV文件名（保持相同名稱，但改變副檔名）
            csv_file = os.path.splitext(xml_file)[0] + '.csv'
            output_path = os.path.join(output_dir, csv_file)
            
            print(f"\n處理文件: {xml_file}")
            print(f"輸出至: {csv_file}")
            
            # 提取短語
            phrases = extract_phrases(input_path)
            
            if not phrases:
                print(f"在 {xml_file} 中沒有找到任何符合條件的短語")
                continue
                
            # 創建DataFrame並保存
            df = pd.DataFrame(phrases)
            # 確保列的順序
            df = df[['PhraseType', 'ParentNodeID', 'StrongIDs', 'Words', 'MaculaID']]
            df.to_csv(output_path, index=False, encoding='utf-8')
            print(f'已成功將結果儲存至 {output_path}')
            print(f'找到 {len(phrases)} 個短語')
            
        print("\n所有文件處理完成")
        
    except Exception as e:
        print(f"程式執行時發生錯誤: {str(e)}")

if __name__ == '__main__':
    main() 