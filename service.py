import os, json
import package.reformatter as formatter
import package.evaluator as evaluator
import package.utils as utils
import package.visionapi as visionapi
import falcon
from falcon_cors import CORS

cors = CORS(allow_origins_list=['http://127.0.0.1:8080'])
public_cors = CORS(allow_all_origins=True)


def requestOCR(credential, jpg_paths):
    visionapi.set_vision_credential(credential)
    vision_results = {}
    for path in jpg_paths:
        vis_response, error = visionapi.annotateDocument(path)
        tmp_key = os.path.basename(path)
        vision_results[tmp_key] = vis_response
        if error is not None:
            print('[E] Vision API Error: {}'.format(error))
    return vision_results

def retrieveVisionResponse(credential, jpg_paths, result_root=None):
    assert isinstance(jpg_paths, list), '[E] "jpg_paths" must be instinace of list'
    vision_results = None
    response_path = None
    if result_root is not None:
        assert isinstance(result_root, str), '[E] "response_path" must be instinace of string'
        response_file = 'vision_result.json'
        response_path = os.path.join(result_root, response_file)
        if os.path.exists(response_path):
            print('[I] Reading existed ocr response from {} ...'.format(response_path))
            vision_results = utils.loadFileIfExisted(response_path)

    if vision_results is None:
        print('[I] Sending ocr request to Google Vision API...')
        vision_results = requestOCR(credential, jpg_paths)
        print('[I] Saving ocr response to {} ...'.format(response_path))
        if response_path is not None:
            with open(response_path, 'w') as outfile:
                json.dump(vision_results, outfile, ensure_ascii=False, indent=2, sort_keys=True)

    return vision_results

def validateAllParameters(credential, general_path, jpg_path_list, result_root):
    assert (isinstance(credential, str) and 
            isinstance(general_path, str) and 
            isinstance(result_root, str)), '[E] All paramters has to be string type'
    assert os.path.exists(credential), '[E] Credential file "{}" not found'.format(credential)
    assert os.path.exists(general_path), '[E] Config file "{}" not found'.format(general_path)
    
    if isinstance(jpg_path_list, str):
        jpg_path_list = [jpg_path_list]
    
    for jpg_path in jpg_path_list:
        assert os.path.exists(jpg_path), '[E] JPG file "{}" not found'.format(jpg_path)

    if not os.path.exists(result_root):
        createDirIfNotExist(result_root)

def annotateCreditLetter(credential, division_code, jpg_path_list, result_root, bank_name=None):
    # Validate all parameters
    general_path = os.path.join('./configs', 'general.yaml')
    validateAllParameters(credential, general_path, jpg_path_list, result_root)
    
    ### FIRST 
    # . Sending image to Google Vision API and save the response
    vision_results = retrieveVisionResponse(credential, jpg_path_list, result_root)

    ### SECOND 
    # . Preparing and organizing vision api's result with config file
    vision_doc = visionapi.VisionDocument.createWithVisionResponse(vision_results)
    general = utils.loadFileIfExisted(general_path)
    final_result = {}

    ### THIRD 
    if bank_name is None:
        bank_name = identifyBankName(vision_doc, general)
    print('[I] evaluate letter of credit with {} config'.format(bank_name))
    config_path = os.path.join('./configs', bank_name + '_config.yaml')
    config = utils.loadFileIfExisted(config_path)
    
    if config is None:
        final_result = {
                'error':'[E] Unable to find config file with bank: {}'.format(bank_name)
                }
    else:
    ### FORTH
    # . Reformat vision response and then evaluate it.     
        clfomatted = formatter.GeneralCLFormatter(vision_doc)
        header_info = clfomatted.extractHeaderInfo(config)
        swifts_info = clfomatted.extractSwiftsInfo(config, general)
        info_text = clfomatted.dumpToDict()
        
        evaluatted = evaluator.CLEvaluator(clfomatted)
        checklist = evaluatted.evaluate_checklist(config, general)

        ### 
        # adding prefix for C# aaplication (C# cannot read key starting with _ or numeric value)
        newswift = {}
        for key, value in info_text['swifts'].items():
            newswift['code_'+key] = info_text['swifts'][key]
        info_text['swifts'] = newswift

        final_result.update(info_text)
        final_result.update(checklist)

    if result_root is not None:
        result_path = os.path.join(result_root, 'checklist.json')
        with open(result_path, 'w') as outfile:
            json.dump(final_result, outfile, ensure_ascii=False, indent=2)

    return final_result


def checkIfKeyExists(content, target_key):
    if not isinstance(content, dict):
        return False
    if not (target_key in content.keys()):
        return False
    return True

class RequestCloudMile:
    cors = public_cors
    def on_post(self, req, resp):
        req_str = req.stream.read()
        status = falcon.HTTP_200
        output = '[INFO] Request Received.'
        if (len(str(req_str)) == 0):
            status = falcon.HTTP_501
            output = '[ERROR] Invalid Reqeust Found.'
        else:
            data = json.loads(req_str.decode('utf8'))
            if not checkIfKeyExists(data, 'jpg_path_list'):
                output = '[ERROR] No jpg_path_list found.'
            else:
                jpg_path_list = data['jpg_path_list']

                if checkIfKeyExists(data, 'credential'):
                    credential = data['credential']
                else:
                    credential = './service_acc.json'

                if checkIfKeyExists(data, 'division_code'):
                    division_code = data['division_code']
                else:
                    division_code = '0001'

                if checkIfKeyExists(data, 'bank_name'):
                    bank_name = data['bank_name']
                else:
                    bank_name = None

                if checkIfKeyExists(data, 'result_root'):
                    result_root = data['result_root']
                else:
                    result_root = None
                output = annotateCreditLetter(credential, division_code, jpg_path_list, result_root, bank_name)

        resp.status = status
        resp.body = json.dumps(output)


class RequestPdfToJpg:
    cors = public_cors
    def on_post(self, req, resp):
        req_str = req.stream.read()
        status = falcon.HTTP_200
        output = '[INFO] Request Received.'
        if (len(str(req_str)) == 0):
            status = falcon.HTTP_501
            output = '[ERROR] Invalid Reqeust Found.'
        else:
            data = json.loads(req_str.decode('utf8'))
            if not checkIfKeyExists(data, 'pdf_path'):
                output = '[ERROR] No pdf_path found.'
            else:

                if checkIfKeyExists(data, 'dst_dir'):
                    dst_dir = data['dst_dir']
                else:
                    dst_dir = 'tmp'

                pdf_path = data['pdf_path']
                paths = utils.pdf2Jpg(pdf_path, dst_dir)
                output = {'jpg_files':paths}

        resp.status = status
        resp.body = json.dumps(output)


app = falcon.API(middleware=[cors.middleware])
app.add_route('/cloudmile/clevaluator', RequestCloudMile())
app.add_route('/cloudmile/pdfToJpg', RequestPdfToJpg())
