import xml.etree.ElementTree as ET
import pandas as pd
from typing import List, Tuple, Dict
import os
from pathlib import Path
from itertools import combinations

def _node_to_info(node: ET.Element) -> Dict:
    """將節點轉換為包含 strong / word / n 的資訊字典（供 matching_nodes 使用）"""
    m_elements = node.findall('.//m')
    return {
        'node': node,
        'strong': node.get('StrongNumberX'),
        'n': node.get('n', ''),
        'word': m_elements[0].get('word', '') if m_elements else ''
    }


def _follow_head_chain(start_node: ET.Element, max_depth: int = 20) -> Dict:
    """
    從 start_node（帶有 Head 屬性的節點）開始，沿著 Head 屬性一路往下找出
    真正帶有 StrongNumberX 的節點。

    這是原本手動展開 8 層（start_node -> subhead -> sub2head -> ... -> sub7head）
    的邏輯，改用迴圈實作。行為完全等價：
      - 每一層都必須有 Head 屬性才能往下跳一層，否則視為找不到，回傳 None
      - Head 值若超出子節點範圍（skip_count >= len(children)），視為找不到，回傳 None
      - 只要跳到的節點帶有 StrongNumberX，就回傳該節點的資訊
    max_depth 只是防呆用的安全上限（原本硬編碼只支援到第8層深度，
    這裡預設放寬到 20 層，避免未來若語法樹更深時又要手動再展開一層）。
    """
    current = start_node
    depth = 0

    while depth < max_depth:
        head_value = current.get('Head')
        if not head_value:
            return None

        skip_count = int(head_value)
        children = list(current)
        if skip_count >= len(children):
            return None

        current = children[skip_count]
        if current.get('StrongNumberX'):
            return _node_to_info(current)

        depth += 1

    return None


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

    for child in node:
        if child.get('Cat') != category:
            continue

        if category in ['S', 'O']:
            # S / O 節點：需沿著 Head 屬性往下找出真正的頭詞
            info = _follow_head_chain(child)
            if info is not None:
                matching_nodes.append(info)
        else:
            # 非 S/O 節點：先看自己是否直接有 StrongNumberX
            strong_num = child.get('StrongNumberX')
            if strong_num:
                matching_nodes.append(_node_to_info(child))
                continue

            # 否則往下找第一個帶有 StrongNumberX 的子節點
            for subchild in child.findall('.//Node'):
                if subchild.get('StrongNumberX'):
                    matching_nodes.append(_node_to_info(subchild))
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
        # 處理多詞性規則, ex: V-S-O
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