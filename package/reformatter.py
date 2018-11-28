import io, os, json, base64, pathlib, re, math
import package.utils as utils
import package.visionapi as visionapi
import numpy as np
import pandas as pd
from collections import OrderedDict
from datetime import datetime


def checkIfKeyExists(content, target_key):
  assert isinstance(content, dict), '[E] content must be an instance of dict'
  assert target_key in content.keys(), '[E] Missing key "{}" in keylist: {}'.format(target_key, content.keys())

def groupbyLines(dataframe, threshold = 15):
    dataframe = dataframe.sort_values(['ys', 'xs'], ascending=[True, True])
    pre_row = None
    df_list = [pd.DataFrame()]
    text = ''
    
    ### group all text with as individual lines. 
    for index, row in dataframe.iterrows():
        temp_line = pd.DataFrame()
        if pre_row is None:
            pre_row = row
        dif_ys = row['ys'] - pre_row['ys']
        ### if difference bettwen two symbol is greater than 15 then consider it as a new line
        if dif_ys > threshold:
            pre_row = row
            df_list.append(pd.DataFrame())
        df_list[-1] = df_list[-1].append(row)
        
    ### make sure all y-axis aligned line are sorted with x-axis
    for idx, line in enumerate(df_list):
        df_list[idx] = line.sort_values(['xs'], ascending=[True])

    ### simplify the response into list of text and its boundingboxes
    line_list = []
    for linedf in df_list:
        tmp_text_list = []
        tmp_bound_list = []
        for index, row in linedf.iterrows():
            tmp_text_list.append(row['text'])
            tmp_bound_list.append(row[['xs', 'ys', 'xe', 'ye']].tolist())
        texts = ''.join(tmp_text_list).replace('\n', ' ').replace(':', '')
        bounds = utils.fuseBoundingBox(tmp_bound_list)
        line_list.append([texts, bounds])
    return line_list

def mergeLinesWithFields(line_list, field_list):
    found_field = ''
    result = {}
    for idx, line in enumerate(line_list):
        tmp_line_text = line[0]
        tmp_bound_list =line [1]
        for item in field_list:
            label = item['label']
            field = item['field']
            if label in tmp_line_text:
                found_field = field
                tmp_line_text = tmp_line_text.replace(label, '').strip()

        if found_field in result.keys():
            newText = result[found_field]['text'] + ' ' + tmp_line_text
            result[found_field]['text'] = newText.strip()
            newbox = utils.fuseBoundingBox([result[found_field]['boundingbox'], tmp_bound_list])
            result[found_field]['boundingbox'] = newbox
        else:
            result[found_field]={'text':tmp_line_text.strip(), 
                                 'boundingbox': tmp_bound_list}  
    return result

class CLFormatterAbstract(object):
  def __init__(self, visdoc):
    assert isinstance(visdoc, visionapi.VisionDocument), '[E] CLFormatter only accept VisionDocument instance as input'
    self.visdoc = visdoc
    self.header_info = {}
    self.swifts_info = {}

  def extractHeaderInfo(self, config):
    checkIfKeyExists(config, 'header')

  def extractSwiftsInfo(self, config):
    checkIfKeyExists(config, 'main_body')

  def extract_with_pattern(self, content, pattern):
    text_res = re.findall(pattern, content, re.IGNORECASE)
    if len(text_res) > 0 and len(text_res[0]) > 0:
      return text_res[0]
    else:
      return None

  def extract_with_format(self, content, format_type, format_regex_list):
    res = ''
    err = ''
    if content is not None and content != '':
      if format_type == 'DATE':
        def try_parsing_date(text, format_regex_list):
          for fmt in format_regex_list:
            try:
              return datetime.strptime(text, fmt)
            except ValueError:
              pass
          return None
        content = content.replace('\n', '').strip()
        datetime_object = try_parsing_date(content, format_regex_list)
        if datetime_object is None:
          res = '[E] Unrecognized date {} with formats: {}\n'.format(content, format_regex_list)
        else:
          res = datetime_object.strftime('%m/%d/%Y')
      else:
        err = '[W] Unrecognized format type: {}\n'.format(format_type)

    return res, err

  def orderByLines(self, textList, boundList, threshold=15):
    newdf = pd.DataFrame(boundList, columns=['xs', 'ys', 'xe', 'ye'])
    newdf['text'] = textList
    newdf = newdf.sort_values(['ys', 'xs'], ascending=[True, True])
    lines = []
    boxes = []
    for index, row in newdf.iterrows():
        line = row['text']
        box = row['xs']
        if len(lines) == 0:
            lines.append(row['text'])
            boxes.append(row[['xs', 'ys', 'xe', 'ye']].tolist())
        else:
            dif_ys = row['ys'] - boxes[-1][1]
            if dif_ys > threshold:
                lines.append(row['text'])
                boxes.append(row[['xs', 'ys', 'xe', 'ye']].tolist())
            else:
                dif_xs = row['xs'] - boxes[-1][0]
                if dif_xs < 0:
                    lines[-1] = row['text'] + lines[-1]
                    boxes[-1] = utils.fuseBoundingBox([boxes[-1], row[['xs', 'ys', 'xe', 'ye']].tolist()])
    return lines, boxes

  def dumpToFile(self, fileptah):
    result = self.dumpToDict()
    with open(fileptah, 'w') as outfile:
      json.dump(result, outfile, ensure_ascii=False, indent=2, sort_keys=True)

  def dumpToDict(self):
    result = {'header': self.header_info, 'swifts': self.swifts_info}
    return result
        
class GeneralCLFormatter(CLFormatterAbstract):
  def __init__(self, visdoc):
    super().__init__(visdoc)

  def __extractGroupFields(self, text_list, bound_list, config):
    readBy = config['readby']
    height = config['line_height']
    subfield_list = config['item_list']
    newdf = pd.DataFrame(bound_list, columns=['xs', 'ys', 'xe', 'ye'])
    newdf['text'] = text_list
    if readBy == 'byline':
      line_list = groupbyLines(newdf, height / 2)
      result = mergeLinesWithFields(line_list, subfield_list)
    else:
      result = {}
    return result


  def __extractFields(self, text_list, bound_list, config):
    field = config['field']
    result_info = {field:{'error': ''}}
    tmp_info = {}
    text = ''.join(text_list)
    ### Extract text based on pattern if specified in config yaml
    if 'pattern' in config.keys():
      pattern = config['pattern']
      text_res = self.extract_with_pattern(text, pattern)
      if text_res is not None:
        text = text_res

    ### Extract text based on format if specified in config yaml
    if 'format' in config.keys():
      format_type = config['format']['type']
      format_regex = config['format']['regex']
      result, err = self.extract_with_format(text, format_type, format_regex)
      text = result
      if err is not None and len(err) > 0:
        if 'error' in tmp_info.keys():
          tmp_info['error'] += err
        else:
          tmp_info['error'] = err

    tmp_info.update({
                'text': text,
                'boundingbox': utils.fuseBoundingBox(bound_list)
            })
    result_info[field] = tmp_info
    return result_info

  def identifyBankName(self, config):
    assert isinstance(self.visdoc, visionapi.VisionDocument), '[E] VisionDocument instance as input'
    titles = config['bank_titles']
    bank = 'unknown'
    for item in titles:
        name = item['name']
        box = item['boundingbox']
        expect = item['text'].upper()

        objectList = self.visdoc.getObjectInBoundaryInPage(0, box, depth=visionapi.VisionObject.DEPTH.WORDS)
        textList, boundList = visionapi.VisionObject.getTextAndBoundingbox(objectList)
        extracted = ''.join(textList)
        if expect in extracted.upper():
            bank = name
            break
    return bank

  def extractHeaderInfo(self, config):
    super().extractHeaderInfo(config)
    header_config = config['header']
    # print(json.dumps(header_config, indent=2))
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
    self.header_info = result_info
    return result_info

  def extractSwiftsInfo(self, config, swifts_config, detail=True):
    super().extractSwiftsInfo(config)

    body_config = config['main_body']
    line_height = config['line_height']
    swift_regex = config['swift_regex']
    swifts = swifts_config['swift_codes']

    ### Initialize swift code dictionary
    swifts_result = {}
    for item in swifts:
      swifts_result[item['code']] = {'text':'', 'boundingbox':[], 'page':[]}
      if 'code2' in item.keys():
        swifts_result[item['code2']] = {'text':'', 'boundingbox':[], 'page':[]}
    
    p_index_list = [page['index'] for page in body_config]
    number_pages = self.visdoc.getNumberOfPages()
    last_found = None
    for p in range(0,number_pages):
      ### Get the boundingbox for specific page index
      target_box = None
      if p in p_index_list:
        tmp_idx = p_index_list.index(p)
      else:
        tmp_idx = p_index_list.index('n')
      target_box = body_config[tmp_idx]['boundingbox']

      ### Get line list and boundingbox list
      objectList = self.visdoc.getObjectInBoundaryInPage(p, target_box, depth=visionapi.VisionObject.DEPTH.WORDS)

      ### Extract swift code infomation from line list
      tmp_result, last_found = self.reformatSwiftInfo(objectList, swifts_result.keys(), swift_regex, last_found, line_height=line_height)

      ### Merge and clean up extracted infomation
      for key, value in tmp_result.items():
        texts = tmp_result[key]['text'].strip() + '\b'
        boxes = visionapi.VisionObject.fuseBoundingBox(tmp_result[key]['boundingbox'])
        try:
          swifts_result[key]['text'] += texts
          swifts_result[key]['boundingbox'].append(boxes)
          swifts_result[key]['page'].append(p)
        except KeyError as e:
          print('[W] Swift code {} is not in the config file. Content: {}'.format(key,texts))

    if not detail:
      final_result = {}
      for key, value in swifts_result.items():
        if len(value['text']) != 0:
          final_result[key] = value
      self.swifts_info = final_result
    else:
      self.swifts_info = swifts_result

    return swifts_result

  def reformatSwiftInfo(self, objectList, codeList, codeRegex, initial_key = None, line_height=30):
    line_list, bound_list = [], []
    if len(objectList) > 0:
      line_list, bound_list = visionapi.VisionObject.getLinesAndBoundingbox(objectList)
      line_list, bound_list = self.orderByLines(line_list, bound_list, line_height / 2)

    last_found = initial_key
    result = {}
    ### Extract swift code infomation from line list
    for idx, line in enumerate(line_list):
      key_regex = codeRegex
      searched = re.search(key_regex, line)  

      if searched is not None:
        last_found = searched.group(1)
        last_found = last_found.replace(' ', '')
        last_found = re.sub('[^0-9a-zA-Z]+', '', last_found)

      if last_found:
        clenedline = line
        boxes = bound_list[idx]
        if last_found in result.keys():
          if '46' in last_found or '47' in last_found:
            cur_line_height = boxes[3] - boxes[1]
            last_box = result[last_found]['boundingbox'][-1]
            last_line_height = last_box[3] - last_box[1]
            line_space = boxes[1] - last_box[3]
            if line_space > ((cur_line_height + last_line_height) / 2) * 0.6:
              new_box = [boxes[0], last_box[3], boxes[0]+20, boxes[1]]
              result[last_found]['text'] += '\n'
              result[last_found]['boundingbox'].append(new_box)
            
          result[last_found]['text'] += clenedline
          result[last_found]['boundingbox'].append(boxes)
        else:
          result[last_found] = {
              'text': clenedline,
              'boundingbox': [boxes]
          }

    return result, last_found
