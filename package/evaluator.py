import io, os, json, base64, pathlib, re
import package.utils as utils
import package.reformatter as reformatter
from package.logger import cmLog
import numpy as np
from collections import OrderedDict
from datetime import datetime

def get_latest_shipment(content):
    """
    Get latest shipment (44C and 44D)
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    key = '44C'
    if key in content.keys():
        result = re.findall('\d+', content[key])
        if len(result) > 0:
            value = result[0]
    else:
        cmLog('[W] 最後裝船期限: Missing 44C')
        value = '[W] 最後裝船期限: Missing 44C'
    return value

def get_latest_negociation(content):
    """
    Get latest negociation (Not important, told no need to get this info)
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    cmLog('[W] 押匯期限: 不重要，應該與信用狀有效期限相同')        
    value = '[W] 押匯期限: 不重要，應該與信用狀有效期限相同'
    return value

def get_expiry_date(content):
    """
    Get expiry date (31D). Warning when place is not in 台灣
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    key = '31D'
    if key in content.keys():
        result = content[key]
        datetime = re.findall('\d+', result)
        if len(datetime) > 0:
            value = datetime[0]
        place = result.replace(value, '')
        tmp = re.findall('taiwan', place, re.IGNORECASE)
        if len(tmp) == 0:
            cmLog('[W] 地點『{}』不是台灣!'.format(place))        
            place = '[W] 地點『{}』不是台灣!'.format(place)
        value = [value, place]
    else:
        cmLog('[W] 信用狀有效期限: Missing 31D (必要欄位)')    
        value = ['[W] 信用狀有效期限: Missing 31D (必要欄位)']
    return value

def get_presented_in_7_days(content):
    """
    Get presented in 7 days (48). Default 21 when not specified
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    key = '48'
    if key in content.keys():
        result = re.findall('\d+', content[key])
        if len(result) > 0:
            value = result[0]
            # value = int(value) <= 7 ### 應要求只要有值就顯示，不論是否在七天內
    else:
        value = 21 ### 應要求 預設 21 天
        cmLog('[W] 應要求 預設 21 天')
    return value

### Get main infomatiion
def get_revocable(content):
    """
    Get revocable (40A and 40B). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '40A' in content.keys():
        value = not ('IRREVOCABLE' in content['40A'].upper()) 
    elif '40B' in content.keys():
        value = not ('IRREVOCABLE' in content['40B'].upper())
    else:
        cmLog('[W] 可否撤銷: Missing 40A or 40B (必要欄位)')
        value = '[W] 可否撤銷: Missing 40A or 40B (必要欄位)'

    return value   

def get_transferable(content):
    """
    Get transferable (40A and 40B). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '40A' in content.keys():
        value = 'TRANSFERABLE' in content['40A'].upper() 
    elif '40B' in content.keys():
        value = 'TRANSFERABLE' in content['40B'].upper() 
    else:
        cmLog('[W] 可否轉讓: Missing 40A or 40B (必要欄位)')
        value = '[W] 可否轉讓: Missing 40A or 40B (必要欄位)'

    return value

def get_confirmed(content):
    """
    Get confirmed (49). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '49' in content.keys():
        value = content['49']
        if 'WITHOUT' in value.upper() :
            value = 'WITHOUT'
    else:
        cmLog('[W] 是否保兌: Missing 49 (必要欄位)')
        value = '[W] 是否保兌: Missing 49 (必要欄位)'
        
    return value

def get_beneficiary_name(content):
    """
    Get beneficiary name (59). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '59' in content.keys():
        value = 'FORMOSA PLASTICS CORPORATION' in content['59'].upper()
        if value:
            value = 'FORMOSA PLASTICS CORPORATION'
        else:
            value = content['59']    
    else:
        cmLog('[W] 受益人名稱: Missing 59 (必要欄位)')
        value = '[W] 受益人名稱: Missing 59 (必要欄位)'
    return value

def get_name_correctness(content):
    """
    Get name correctness (59). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '59' in content.keys():
        value = 'FORMOSA PLASTICS CORPORATION' in content['59'].upper()
    else:
        cmLog('[W] 受益人名稱: Missing 59 (必要欄位)')
        value = '[W] 受益人名稱: Missing 59 (必要欄位)'
    return value

def get_UCP660(content):
    """
    Get UCP660 (40E). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '40E' in content.keys():
        result = content['40E']
        if 'latest' in content['40E'].lower() or '600' in content['40E'].lower():
            value = True
        else:
            cmLog('[W] 是否依國際商會2007修定之UCP600: {} is not the latest version (UCP 600)'.format(result))
            value = '[W] 是否依國際商會2007修定之UCP600: {} is not the latest version (UCP 600)'.format(result)
    else:
        cmLog('[W] 是否依國際商會2007修定之UCP600: Missing 40E')
        value = '[W] 是否依國際商會2007修定之UCP600: Missing 40E'

    return value

### get term infomations
def get_descrption(content, productnames):
    """
    Get product descrption (45A or 45B). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '45A' in content.keys() or '45B' in content.keys():
        if '45A' in content.keys(): 
            temp = content['45A']
        else:
            temp = content['45B']
        found = False
        value =  '[W] 貨品名稱: Not found in 45A ->' + temp
        ### find name by pattern
        reg = re.compile('GOODS DESCRIPTION: ?(.*)\n', re.IGNORECASE)
        result = reg.findall(temp)
        if len(result) > 0:
            found = True
            value = result[0]
        ### find name by vlookup
        if not found:
            for item in productnames:
                if item in value:
                    value = item
                    break
        if '[W]' in value:
            cmLog('[W] 貨品名稱: Not found in 45A ->' + temp)
    else:
        cmLog('[W] 貨品名稱: Missing 45A')
        value = '[W] 貨品名稱: Missing 45A'
    return value

def get_quantity(content):
    """
    Get quantity descrption (45A or 45B). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '45A' in content.keys():
        temp = content['45A']
        found = False
        value =  '[W] 貨品數量: Not found in 45A ->' + temp

        ### find quantity by pattern
        reg = re.compile('QUANTITY: ?(.*)\n', re.IGNORECASE)
        result = reg.findall(temp)
        if len(result) > 0:
            found = True
            value = result[0]

        ### find quantity by unit pattern
        if not found:
            units = ['mt', 'mts', 'metric tons']
            pattern = '(\d+\.?\d*) *'
            for u in units:
                reg = re.compile(pattern + u, re.IGNORECASE)
                result = reg.findall(temp)
                if len(result) > 0:
                    value = result[0] + ' ' + u

        if '[W]' in value:
            cmLog('[W] 貨品數量: Not found in 45A ->' + temp)
    else:
        cmLog('[W] 數量: Missing 45A')
        value = '[W] 數量: Missing 45A'
    return value

def get_amount(content):
    """
    Get amount descrption (45A or 45B). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '32B' in content.keys():
        value = content['32B'].replace('\n', '') 
        if len(re.findall('usd', value, re.IGNORECASE)) == 0:
            cmLog('[W] 信用狀金額: {} is not in USD'.format(value))
            value = '[W] 信用狀金額: {} is not in USD'.format(value) 
    else:
        cmLog('[W] 信用狀金額: Missing 32B (必要欄位)')
        value = '[W] 信用狀金額: Missing 32B (必要欄位)'
    return value

def get_terms(content):
    """
    Get terms descrption (45A or 45B). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    incoterms = ['CIP', 'DAT', 'DAP', 'DDP', 'CIF', 'EXW', 'FCA', 'CPT', 'FAS', 'FOB', 'CFR']

    value = ""
    if '45A' in content.keys():       
        termtext = content['45A']
        if 'INCOTERMS' in termtext:
            token = termtext.split('INCOTERMS')[1]
            for term in incoterms:
                if term in token:
                    value = term
                    break
            if len(value) <= 0:
                cmLog('[W] 交易條件: no term are found in 45A: {}'.format(termtext))
                value = '[W] 交易條件: no term are found in 45A: {}'.format(termtext)
        else:
            splitted = termtext.split(' ')
            inetersects = set(incoterms).intersection(splitted)
            if len(inetersects) == 1:
                value = inetersects.pop()
            elif len(inetersects) == 0:
                cmLog('[W] 交易條件: no term are found in 45A: {}'.format(termtext))
                value = '[W] 交易條件: no term are found in 45A: {}'.format(termtext)
            else:
                cmLog('[W] 交易條件: More than one term are found in 45A: {}'.format(termtext))
                value = '[W] 交易條件: More than one term are found in 45A: {}'.format(termtext)
    else:
        cmLog('[W] 交易條件: Missing 45A')
        value = '[W] 交易條件: Missing 45A'

    return value

def get_insurance(content):
    """
    Get insurance descrption (45A or 45B). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = get_terms(content)
    if '[W]' in value:
        cmLog('[W] 保險指示: 交易條件有誤 無法判斷')
        value = '[W] 保險指示: 交易條件有誤 無法判斷'
    else:
        need_isr = ['CIP', 'DAT', 'DAP', 'DDP', 'CIF']
        noneed_isr = ['EXW', 'FCA', 'CPT', 'FAS', 'FOB', 'CFR']
        if value in noneed_isr:
            value = False
        elif value in need_isr:
            cmLog('[W] 保險指示: {} 需要再從 Document Req 中確認一致性'.format(value))
            value = '[W] 保險指示: {} 需要再從 Document Req 中確認一致性'.format(value)
        else:
            cmLog('[W] 保險指示: 交易條件 {} 有誤：Unknown error'.format(value))
            value = '[W] 保險指示: 交易條件 {} 有誤：Unknown error'.format(value)

    return value

### get negociation infomations
def get_nominated_bank(content):
    """
    Get nominated bank descrption (41A or 41D). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    def find_bank(temp, key):
        result = temp[key]
        result = 'ANY BANK' in result
        if result:
            result = 'Any bank'
        else:
            result = temp[key]
        return result

    value = ""
    if '41A' in content.keys():
        value = find_bank(content, '41A')
    elif '41D' in content.keys():
        value = find_bank(content, '41D')
    else:
        cmLog('[W] 指定押匯銀行: Missing 41A and 41D (必要欄位)')
        value = '[W] 指定押匯銀行: Missing 41A and 41D (必要欄位)' 
    return value

def get_at_sight(content):
    """
    Get at sight descrption (42C). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '42C' in content.keys():
        value = content['42C']
        temp = re.findall('at sight', value, re.IGNORECASE)
        if len(temp) > 0:
            value = 'AT SIGHT'
    else:
        cmLog('[W] 是否即期: Missing 42C')
        value = '[W] 是否即期: Missing 42C'
    return value

def get_interest(content):
    """
    Get interest descrption (39C). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '39C' in content.keys():
        value = content['39C']
        cmLog('[W] 利息負擔: 39C -> {}'.format(value))
        value = '[W] 利息負擔: 39C -> {}'.format(value)
    else:        
        cmLog('[W] 利息負擔: Missing 39C 預設『客戶負擔』')
        value = '[W] 利息負擔: Missing 39C 預設『客戶負擔』'
    return value

def get_mark_up(content):
    """
    Get mark up (45A or 45B). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = "[W] 信用狀溢價: missing 45A"
    if '45A' in content.keys():
        value = content['45A']
    return value

def get_mgmt_mark_up(content):
    """
    Get mgmt mark up (42P). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ''
    if '42P' in content.keys():
        cmLog('[W] 溢價處理: {} (目前沒看到過，有待商確)'.format(content['42P']))
        value = '[W] 溢價處理: {} (目前沒看到過，有待商確)'.format(content['42P'])
    else:
        cmLog('[W] 溢價處理: Missing 42P (目前沒看到過，有待商確)')
        value = '[W] 溢價處理: Missing 42P (目前沒看到過，有待商確)'
    return value

### get shipment infomation
def get_destination(content):
    """
    Get destination (44B and 44F). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = None
    if "44B" in content.keys():
        value = content['44B']
    if '44F' in content.keys():
        if value is None:
            value = content['44F']
        else:
            value += content['44F']
    if value is None:
        cmLog('[W] 目的港: Missing 44B and 44F (預設空值)')
        value = "[W] 目的港: Missing 44B and 44F (預設空值)"
    return value

def get_nominated_loading_port(content):
    """
    Get nominated loading port (44E). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if "44E" in content.keys():
        value = content['44E']
        if not('ANY PORT IN TAIWAN' in value or 'ANY TAIWANESE PORT' in value):
            cmLog('[W] 出口港 : \'{}\' does not match expectation'.format(value))
            value = '[W] 出口港 : \'{}\' does not match expectation'.format(value)
    else:
        cmLog('[W] 出口港: Missing 44E')
        value = "[W] 出口港: Missing 44E"
    return value

def get_partial_shipment(content):
    """
    Get partial shipment loading port (43P). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '43P' in content.keys():
        value = content['43P']
        # ALLOWED/PERMITTED 為 True
        # NOT ALLOWED/FORBIDDEN/PROHIBITED為 False
    else:
        cmLog("[W] 可否分批裝運: Missing 43P, 預設『Allow』")
        value = "[W] 可否分批裝運: Missing 43P, 預設『Allow』"
    return value

def get_transshipment(content):
    """
    Get transshipment (43T). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '43T' in content.keys():
        value = content['43T']
        # ALLOWED/PERMITTED 為 True
        # NOT ALLOWED/FORBIDDEN/PROHIBITED為 False
    else:
        cmLog("[W] 可否轉運: Missing 43T, 預設『Allow』")
        value = "[W] 可否轉運: Missing 43T, 預設『Allow』"
    return value

def get_nominated_shiping_lines(content):
    value = "[W] 指定船公司: 在 47A 中 要在與船公司資料庫比對"
    cmLog("[W] 指定船公司: 在 47A 中 要在與船公司資料庫比對")
    return value

def get_movement(content):
    """
    Get movement (45A). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '45A' in content.keys():
        temp = content['45A']
        if re.findall('contain', temp, re.IGNORECASE):
            value = temp
        else:
            cmLog("[W] 裝船方式: unable to find movement info in 45A (此欄位不需要看？)")
            value = "[W] 裝船方式: unable to find movement info in 45A (此欄位不需要看？)"
    else:        
        cmLog("[W] 裝船方式: Missing 45A (此欄位不需要看？)")
        value = "[W] 裝船方式: Missing 45A (此欄位不需要看？)"
    return value

def get_nominated_agent(content):
    """
    Get nominated agent. 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = "[W] 指定代理商: (此欄位不需要看？)"
    cmLog("[W] 指定代理商: (此欄位不需要看？)")
    return value
    
def find_org_cop(line):
    """
    Get # of original and copies 
    Parameters
    ----------
    line: str
        line that wish to get the information from
    Returns
    ----------
        result # of originals and copies
    """
    def find_val_with_patterns(src, pattern_list):
        final_res = 0
        for pat in pattern_list:
            res = re.findall(pat, src, re.IGNORECASE)
            if len(res) > 0:
                final_res = int(res[0])
                break 
        return final_res

    org_patts = ['IN (\d+) ORIGINAL', '(\d+) ORIGINAL', 'IN (\d+) PLUS \d+']
    cop_patts = ['IN (\d+) (?:NON NEGOTIABLE|NON-NEGOTIABLE|COPY|COPIES)','(\d+) (?:NON NEGOTIABLE|NON-NEGOTIABLE|COPY|COPIES)']    
    gen_patts = ['IN (\d+)']
    org_res = find_val_with_patterns(line, org_patts)
    cop_res = find_val_with_patterns(line, cop_patts)
    gen_res = 0
    if org_res + cop_res == 0:        
        ###
        # Check Folds
        containsCopTerms = 'NON NEGOTIABLE' in line or 'NON-NEGOTIABLE' in line or 'COPY' in line or 'COPIES' in line
        containsOrgTerms = 'ORIGINAL' in line
        fold_patts = ['IN (\d+) FOLD']
        fold_res = find_val_with_patterns(line, fold_patts)
        if containsOrgTerms == containsCopTerms:
            org_res = 1
            cop_res = fold_res - org_res
        elif containsOrgTerms is True and containsCopTerms is False:
            org_res = fold_res
        else:
            gen_res = find_val_with_patterns(line, gen_patts)

        ### 
        # Telex release means at least one copy
        if 'TELEX RELEASE' in line and cop_res < 1:
            cop_res = 1

    return org_res, cop_res, gen_res

def replaceFullset(content, key):
    """
    Replace Fullset with numeric values to simply the evaluation of text. 
    Parameters
    ----------
    content: str
        text that wish to be replaced
    key: str
        document key (Full set has different reprentation in different document)
    Returns
    ----------
        replaced text
    """
    # insurance policy
    if key == 'i_p':
        value = re.sub(r'FULL SET', '2 original', content, re.IGNORECASE)
    # bill of lading
    elif key == 'b_l':
        value = re.sub(r'FULL SET', '3 original', content, re.IGNORECASE) 
    else:
        value = content
    return value

def replaceDuplicates(content):
    """
    Replace text with numeric values to simply the evaluation of text. 
    Parameters
    ----------
    content: str
        text that wish to be replaced
    Returns
    ----------
        replaced text
    """
    text = ['single', 'duplicate', 'triplicate', 'quadruplicate']
    value = content
    for idx, item in enumerate(text):
        if item.upper() in content:
            value = content.replace(item.upper(), '{} ORIGINALS'.format(idx + 1))
            break
    return value

def reformatInParagraphs(content, target_code, pats):
    """
    Reformat given content into paragrahs (newline at the end of each paragraph, 
    default is at each line but each line is not neccessary a sentance). 
    Parameters
    ----------
    target_code: str
        specific swift code used to get the text from content
    pats: str
        pattern used to reformat as paragraphs. 
    Returns
    ----------
        a list of paragraphs
    """
    ### check if content can be groupped in paragraphs
    matched = re.findall('\n\n', content)
    paragraphs = None 

    ###
    # Split into paragraphs with double newline
    if matched is not None and len(matched) > 3:
        tmp_para = re.compile("\n\n").split(content)
        paragraphs = '\n'.join([s.replace('\n', '') for s in tmp_para])
    ###
    # Split into paragraps with special patterns 
    else:
        listOfLines = content.split('\n')
        target_pats = listOfLines[0].startswith
        temp_text = ''
        target_pat = None
        for idx, pat in enumerate(pats):
            matched = re.match(pats[idx], listOfLines[0])
            if matched and matched.start() == 0:
                target_pat = pat
                break

        if target_pat is None:
            cmLog('[W] Unable to detect paragraph prefix. Read content directly')
            paragraphs = content
        else:
            tmp_para = []
            for line in listOfLines:
                if target_pat is not None:
                    matched = re.match(target_pat, line) 
                    if (matched and matched.start() == 0):
                        line = line[matched.end():].strip()           
                        tmp_para.append(line)
                    else:
                        if len(tmp_para) == 0:
                          tmp_para.append(line)
                        else:
                          tmp_para[-1] = tmp_para[-1] + ' ' + line
            paragraphs = '\n'.join(tmp_para)
    return paragraphs

def get_shipping_docs(content, config):
    """
    Evaluate session shipping doc (46A)
    Parameters
    ----------
    config: str
        a dictionary load from general config yaml file.
    Returns
    ----------
        a dictionary containing # of originals and copies of each document. 
    """
    res_req_docs = {}
    req_docs = config['req_docs']['items']
    paragraph_pat = config['req_docs']['paragraph_patterns']
       
    if not ('46A' in content.keys() or '46B' in content.keys()):
        for item in req_docs:
            tmp_key_name = item['name']
            key_list = item['keys']
            tmp_key = key_list[0]
            res_req_docs[tmp_key] = {
                    'original': 0, 
                    'copies': 0, 
                    'unspecified': 0, 
                    'text': "[W] 提單: Missing key: 46A"}
        cmLog("[W] 提單: Missing key: 46A")
    else:
        if '46A' in content.keys(): 
            temp = content['46A']
            temp = reformatInParagraphs(temp, '46A', paragraph_pat)
        else:
            temp = content['46B']
            temp = reformatInParagraphs(temp, '46B', paragraph_pat)
            
        splitted = re.split(r'\n', temp)

        for item in req_docs:
            candidate_line = None
            tmp_key_name = item['name']
            key_list = item['keys']
            tmp_key = key_list[0]
            org_res, cop_res, gen_res = 0, 0, 0

            for idx, line in enumerate(splitted):
                contained = False
                for k in key_list:
                    contained = k.upper() in line
                    if contained:
                        break
                if contained:
                    candidate_line = line
                    splitted.remove(candidate_line)
                    break

            if candidate_line is None:
                res_req_docs[tmp_key] = {
                        'original': 0, 
                        'copies': 0, 
                        'unspecified': 0, 
                        'text': "[W] 提單: Unable to find document about {}".format(tmp_key_name)}
                cmLog("[W] 提單: Unable to find document about {}".format(tmp_key_name))
            else:
                target_line = utils.text2number(candidate_line)
                target_line = replaceFullset(target_line, tmp_key)
                target_line = replaceDuplicates(target_line)
                tmp_org, tmp_cop, tmp_gen = find_org_cop(target_line)
                
                org_res = max(org_res, tmp_org)
                cop_res = max(cop_res, tmp_cop)
                gen_res = max(gen_res, tmp_gen)

                ### if original and copies are both zero but keyword is catched, then it 
                ### is assume to have at least one original
                if org_res <= 0 && cop_res <= 0:
                    org_res = 1
                    cop_res = 0

                res_req_docs[tmp_key] = {
                    'original': org_res, 
                    'copies': cop_res, 
                    'unspecified': gen_res, 
                    'text': candidate_line}
        res_req_docs['remained'] = splitted

    return res_req_docs

def get_other_docs(content):
    """
    Get other doc (47A). 
    Parameters
    ----------
    content: dict
        a dictionary of swift code infomation
    Returns
    ----------
        value for this item
    """
    value = ""
    if '47A' in content.keys():
        temp = content['47A']
        add_docs = {}
        add_docs['original_47A'] = temp
        value = add_docs
    else:
        value = {'original_47A':"[W] 提單: Missing 47A"}
        cmLog("[W] 提單: Missing 47A")

    return value

class CLEvaluator(object):
  def __init__(self, formatted):
    assert isinstance(formatted, reformatter.CLFormatterAbstract), '[E] CLEvaluator only accept CLFormatter instance as input'
    self.formatted = formatted
    self.header = {}
    self.checklist = ''

  def dumpToFile(self, fileptah):
    """
    Write this class into a file with json format
    Parameters
    ----------
    filepath: str
        A path wished to be written
    Returns
    ----------
    """
    result = self.dumpToDict()
    with open(fileptah, 'w') as outfile:
      json.dump(result, outfile, ensure_ascii=False, indent=2, sort_keys=True)

  def dumpToDict(self):
    """
    Return a dictionary representation of this class 
    Parameters
    ----------
    Returns
    ----------
    content: dict
        A dictionary representing the checklist
    """
    result = self.formatted.dumpToDict()
    result.update({'checklist': self.checklist})
    return result

  def get_product_list(self, config, target_div):
    """
    Retrieve product list from a config file. (Different division might have different product list)
    Parameters
    ----------
    config: dict
        a dictionary load from general config yaml file. 
    target_div: str
        target division
    Returns
    ----------
    product_list: 
        a list of product (str)
    """
    product_list = []
    for div in config['divisions']:
        if div['code'] == target_div:
            product_list = div['products']
            break
    return product_list

  def simplifiedContent(self, regex=None):
    """
    Restructure the format of swift code to keep only text infomation for simplicity. 
    Parameters
    ----------
    regex: str
        regex that is used to get extract the content from text.  
    Returns
    ----------
    content: dict
        A dictionary with simplified swift code. 
    """
    content = {}
    for key, item in self.formatted.swifts_info.items():
        splitted = re.compile(regex).split(item['text'])
        value = ''
        for idx, token in enumerate(splitted):
            if idx == 0:
                continue
            else:
                value += token
        if len(value) > 0:
            content[key] = value.strip()
    return content

  def getValueAndError(self, ocr_result, methodSets, keySets, argSets=None):
    if len(keySets) - len(methodSets) != 1:
        print('[E] key sets must be greater than method sets: ', methodSets, keySets)
        return
    tmp = {}
    for idx, m in enumerate(methodSets):
        if argSets is not None:
            arg = argSets[idx]
            if arg is not None:
                value = m(ocr_result, arg)
            else:
                value = m(ocr_result)
        else:
            value = m(ocr_result)
        if keySets[0] not in tmp.keys():
            tmp[keySets[0]] = {keySets[idx+1]: value}
        else:
            tmp[keySets[0]][keySets[idx+1]] = value
    return tmp

  def evaluate_checklist(self, config, gen_config, target_div='0001'):
    """
    Evaluate letter of credit based on Formosa plastic's checklist
    Parameters
    ----------
    config: str
        a dictionary load from bank specific config yaml file. 
    gen_config: str
        a dictionary load from general config yaml file. 
    target_div: str
        target division        
    Returns
    ----------
    """
    product_list = self.get_product_list(gen_config, target_div)
    if len(product_list) == 0:
        cmLog("[E] Unable to get product infomation")
        return '[E] Unable to get product infomation'

    swift_reg = config['swift_content']
    ocr_value = self.simplifiedContent(swift_reg)

    checkLists = {'duration': {}, 'main_part': {}, "trade_terms":{}, 'negociation_amt':{}, 'shipping_argmt':{}, 'shipping_docs':{}}

    ### get deadlines
    method_deadline = [get_latest_shipment, get_latest_negociation, get_expiry_date, get_presented_in_7_days]
    keylist_deadline = ['duration', 'latest_shipment', 'latest_negociation', 'expiry_date', 'presented_in_7_days']
    tmp = self.getValueAndError(ocr_value, method_deadline, keylist_deadline)
    checkLists.update(tmp)
    
    ### get main
    method_main = [get_transferable, get_confirmed, get_beneficiary_name, get_name_correctness, get_UCP660]
    keylist_main = ['main_part', 'transferable', 'confirmed', 'beneficiary', 'accurate_name', 'ucp660']
    tmp = self.getValueAndError(ocr_value, method_main, keylist_main)
    checkLists.update(tmp)
    
    ### get terms
    method_terms = [get_descrption, get_quantity, get_amount, get_terms, get_insurance]
    keylist_terms = ['trade_terms', 'descrption', 'quantity', 'amount', 'terms', 'insurance']
    arglist_terms = [product_list,None,None,None,None]
    tmp = self.getValueAndError(ocr_value, method_terms, keylist_terms, arglist_terms)
    checkLists.update(tmp)
    
    ### get negotication infomations
    method_negociation = [get_nominated_bank, get_at_sight, get_interest, get_mark_up, get_mgmt_mark_up]
    keylist_negociation = ['negociation_amt', 'nominated_bank', 'at_sight', 'interest', 'mark_up', 'mgmt_mark_up']
    tmp = self.getValueAndError(ocr_value, method_negociation, keylist_negociation)
    checkLists.update(tmp)
    
    ### get shipping arrangement infomations
    method_shipment = [get_destination, get_nominated_loading_port, get_partial_shipment, get_transshipment, get_nominated_shiping_lines, get_movement, get_nominated_agent]
    keylist_shipment = ['shipping_argmt', 'destination', 'nominated_loading_port', 'partial_shipment', 'transshipment', 'nominated_shiping_lines', 'movement', 'nominated_agent']
    tmp = self.getValueAndError(ocr_value, method_shipment, keylist_shipment)
    checkLists.update(tmp)
    
    ### get shipping documents
    req_docs = get_shipping_docs(ocr_value, gen_config) 
    checkLists['shipping_docs'] = req_docs

    ### get additional documents
    add_docs = get_other_docs(ocr_value)
    checkLists['additional_docs'] = add_docs

    self.checklist = checkLists
    return checkLists

  def evaluate_header(self, config, gen_config, target_div='0001'):
    print('Not implemented')
    result_info = {}
    for item in header_config:
      field = item['field']
      target_box = item['boundingbox']
      if len(target_box) == 0:
        field_info = {field: {'text':"", 'boundingbox':target_box}}
      else:
        item_info = ''
        objectList = self.visdoc.getObjectInBoundaryInPage(0, target_box, depth=visionapi.VisionObject.DEPTH.WORDS)
        textList, boundList = visionapi.VisionObject.getTextAndBoundingbox(objectList)
        ### extract the field with as a group of subfields
        if 'group' in field:
          field_info = self.__extractGroupFields(textList, boundList, item)
        else:
          field_info = self.__extractFields(textList, boundList, item)
      result_info.update(field_info)
    self.header = result_info
