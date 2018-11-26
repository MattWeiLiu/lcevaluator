import os, json, time
import package.utils as utils
import package.visionapi as visionapi
import package.reformatter as formatter
import package.evaluator as evaluator

class CLTestCases(object):

  @staticmethod
  def runTestWithDir(directory, target_bank=None, target_doc=None, save=True, iteration = 10):
    file_gen = utils.traverseDirectories(directory)
    count_docs = 0
    count_bl = 0
    count_inv = 0
    count_pl = 0
    count_other = 0
    checklistpath = None
    for root, jpg_list in file_gen:
        jpg_list = list(map(lambda x: os.path.join(root, x), jpg_list))
        res_root = root   
        if target_bank is not None:
          if not target_bank in root: continue     
        if target_doc is not None:
          if not target_doc in root: continue
        vis_res_path = os.path.join(root,'vision_result.json')
        tester = CLTestCases(vis_res_path)
        if save:
          checklistpath = os.path.join(root, 'checklist.json')
        result_str = tester.runTests(checklistpath)
        count_docs += 1
        if '46A bl' in result_str:
          count_bl += 1
        if '46A inv' in result_str:
          count_inv += 1
        if '46A pl' in result_str:
          count_pl += 1
        if '[E]' in result_str and '46A' not in result_str:
          count_other += 1
        if '[E]' in result_str:
          print(result_str)
        iteration -= 1
        if iteration == 0:
          break
    test_result = {
      'Total docs': count_docs,
      'Bill of lading': "{}/{} = {}".format(count_bl, count_docs, count_bl/count_docs),
      'Commercial invoice': "{}/{} = {}".format(count_inv, count_docs, count_inv/count_docs),
      'Packing list': "{}/{} = {}".format(count_pl, count_docs, count_pl/count_docs),
      'Other errors': "{}/{} = {}".format(count_other, count_docs, count_other/count_docs)
    }
    print(json.dumps(test_result, indent=2))


  def __init__(self, visdoc_path):
    vision_results = utils.loadFileIfExisted(visdoc_path)
    visdoc = visionapi.VisionDocument.createWithVisionResponse(vision_results)
    self.doc_path = visdoc_path
    self.visdoc = visdoc
    self.formatted = None
    self.evaluatted = None
    self.general = None  
    self.config = None  
    self.checklist = None
    
  def testFormattor(self):
    self.formatted = formatter.GeneralCLFormatter(self.visdoc)
    general_path = os.path.join('./configs', 'general.yaml')
    self.general = utils.loadFileIfExisted(general_path)
    assert self.general is not None, 'Unable to read general config at path {}'.format(general_path)
    bank_name = self.formatted.identifyBankName(self.general)
    config_path = os.path.join('./configs', bank_name + '_config.yaml')
    self.config = utils.loadFileIfExisted(config_path)
    assert self.config is not None, 'Unable to read bank config at path {}'.format(config_path)
    header_info = self.formatted.extractHeaderInfo(self.config)
    swifts_info = self.formatted.extractSwiftsInfo(self.config, self.general)

    
  def testEvaluator(self, save_path=None):
    self.testFormattor()
    self.evaluatted = evaluator.CLEvaluator(self.formatted)      
    self.checklist = self.evaluatted.evaluate_checklist(self.config, self.general)

    if save_path is not None:
      print(save_path)
      with open(save_path, 'w') as outfile:
          json.dump(self.checklist, outfile, ensure_ascii=False, indent=2)

  def testRequirementDocument(self):
    assert self.checklist is not None, '[E] "Please run testFormattor and testEvaluator first.'
    shipping_docs = self.checklist['shipping_docs']

    def varify(target):
      original = target['original']
      copies = target['copies']
      unspecified = target['unspecified']
      if (original + copies == 0) or unspecified > 0:
        return [-1, original, copies, unspecified, target['text']]
      else:
        return [0, original, copies, unspecified, target['text']]

    result = {
      'bl': varify(shipping_docs['b_l']),
      'inv': varify(shipping_docs['inv']),
      'pl': varify(shipping_docs['p_l']),
    }
    return result

  def runTests(self, save_path=None):
    # starts = time.time()
    result_str = '[I] Check documenat {}'.format(self.doc_path)

    # print('[I] Check documenat {}'.format(self.doc_path))
    # try:
    self.testFormattor()
    self.testEvaluator(save_path)
    result = self.testRequirementDocument()
    # ends = time.time()
    for key, item in result.items():
      if item[0] < 0:
        result_str += '\n[E] 46A {} reuslt: {}'.format(key, item)
        # print('[I] 46A {} reuslt: {}'.format(key, item))
    # except Exception as e:
    #   result_str += '\n[E] {}'.format(e)
        # print('[E] {}'.format(e))
    return result_str

    