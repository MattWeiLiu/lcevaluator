import os, json, time
import service 
import package.utils as utils
import package.visionapi as visionapi
import package.reformatter as formatter
import package.evaluator as evaluator

class CLTestCases(object):
  @staticmethod
  def runTestWithService(credential, directory, target_bank=None, target_doc=None, save=True, iteration = 10):
    file_gen = utils.traverseDirectories(directory)
    for root, jpg_list in file_gen:
      jpg_list = list(map(lambda x: os.path.join(root, x), jpg_list))
      res_root = root
      if target_bank is not None:
        if not target_bank in root: continue     
      if target_doc is not None:
        if not target_doc in root: continue
      result_info = service.annotateCreditLetter(credential, '0001', jpg_list, root, target_bank)
      

  @staticmethod
  def runTestWithDir(directory, target_bank=None, target_doc=None, save=True, iteration = -1):
    file_gen = utils.traverseDirectories(directory)
    count_docs = 0
    count_bl = 0
    count_inv = 0
    count_pl = 0
    count_other = 0
    count_failed = 0
    checklistpath = None
    tmp_test_result = {}
    test_summary = []
    for root, jpg_list in file_gen:
      jpg_list = list(map(lambda x: os.path.join(root, x), jpg_list))
      res_root = root
      result_str = '[I] Evaluaing document for {}\n'.format(res_root)
      ###
      # , test specified bank or doc. 
      if target_bank is not None:
        if not target_bank in root: continue     
      if target_doc is not None:
        if not target_doc in root: continue
      vis_res_path = os.path.join(root,'vision_result.json')
      tester = CLTestCases(vis_res_path)
      if save:
        checklistpath = os.path.join(root, 'checklist.json')
      
      try:
        count_docs += 1
        tester.runTests(checklistpath)
        tester.assertFinalJsonStructure()
      except AssertionError as e:
        count_failed += 1
        error_str = e.args[0]
        if '46A' in error_str:
          if '46A bl' in error_str:
            count_bl += 1
          if '46A inv' in error_str:
            count_inv += 1
          if '46A pl' in error_str:
            count_pl += 1
        else:
          count_other += 1

        result_str += error_str

      tmp_test_result = {
        'status': '[E]' not in result_str, 
        'message': result_str
      }
      test_summary.append(tmp_test_result)
      if iteration >= 0:
        iteration -= 1
        if iteration == 0:
          break

    if count_docs == 0:
      count_docs = -1
      
    test_report = {
      'Total docs': count_docs,
      'Bill of lading': "{}/{} = {}%".format(count_bl, count_docs, (1-count_bl/count_docs) * 100),
      'Commercial invoice': "{}/{} = {}%".format(count_inv, count_docs, (1-count_inv/count_docs) * 100),
      'Packing list': "{}/{} = {}%".format(count_pl, count_docs, (1-count_pl/count_docs) * 100),
      'Other errors': "{}/{} = {}%".format(count_other, count_docs, (1-count_other/count_docs) * 100),
      'Failed documents': "{}".format(count_failed)
    }
    print(json.dumps(test_report, indent=2))
    # print(test_summary)

    with open('./report.json', 'w') as outfile:
        json.dump(test_summary, outfile, ensure_ascii=False, indent=2, sort_keys=True)



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

  def assertFinalJsonStructure(self):
    assert 'header' in self.checklist.keys(), '[E] Missing header info in checklist\n'
    assert 'swifts' in self.checklist.keys(), '[E] Missing swifts info in checklist\n'
    assert 'checklist' in self.checklist.keys(), '[E] Missing checklist info in checklist\n'

    
  def testFormattor(self):
    self.formatted = formatter.GeneralCLFormatter(self.visdoc)
    general_path = os.path.join('./configs', 'general.yaml')
    self.general = utils.loadFileIfExisted(general_path)
    assert self.general is not None, '[E] Unable to read general config at path {}'.format(general_path)
    bank_name = self.formatted.identifyBankName(self.general)
    config_path = os.path.join('./configs', bank_name + '_config.yaml')
    self.config = utils.loadFileIfExisted(config_path)
    assert self.config is not None, '[E] Unable to read bank config at path {}'.format(config_path)
    self.formatted.extractHeaderInfo(self.config)
    self.formatted.extractSwiftsInfo(self.config, self.general)
    # if len(self.formatted.header_info['lc_no']['text']) == 0:
    #   self.formatted.updateHeaderWithSwiftCode(self.config)

    
  def testEvaluator(self):
    self.testFormattor()
    self.evaluatted = evaluator.CLEvaluator(self.formatted)      
    self.evaluatted.evaluate_checklist(self.config, self.general)
    self.checklist = self.evaluatted.dumpToDict()


  def testRequirementDocument(self):
    assert self.checklist is not None, '[E] "Please run testFormattor and testEvaluator first.'
    shipping_docs = self.checklist['checklist']['shipping_docs']

    def varify(target):
      original = target['original']
      copies = target['copies']
      unspecified = target['unspecified']
      if (original + copies == 0) or unspecified > 0:
        return [-1, original, copies, unspecified, target['text']]
      else:
        return [0, original, copies, unspecified, target['text']]

    assert 'b_l' in shipping_docs.keys(), 'b_l is not in the key list {}'.format(shipping_docs.keys())
    assert 'inv' in shipping_docs.keys(), 'inv is not in the key list {}'.format(shipping_docs.keys())
    assert 'p_l' in shipping_docs.keys(), 'p_l is not in the key list {}'.format(shipping_docs.keys())

    result = {
      'bl': varify(shipping_docs['b_l']),
      'inv': varify(shipping_docs['inv']),
      'pl': varify(shipping_docs['p_l']),
    }
    return result

  def runTests(self, save_path=None):
    self.testEvaluator()
    result = self.testRequirementDocument()
    result_str = ''
    for key, item in result.items():
      if item[0] < 0:
        result_str += '\n[E] 46A {} reuslt: {}'.format(key, item)

    if save_path is not None:
      final = self.evaluatted.dumpToDict()
      with open(save_path, 'w') as outfile:
          json.dump(final, outfile, ensure_ascii=False, indent=2)
    assert '[E]' not in result_str, result_str
    
    