import os, json
import package.reformatter as formatter
import package.evaluator as evaluator
import package.utils as utils
import package.augmentation as augm
import package.visionapi as visionapi
from package.logger import cmLog
import falcon
from falcon_cors import CORS
from PIL import Image
import glob
from pdf2image import convert_from_path
import shutil

cors = CORS(allow_origins_list=['http://127.0.0.1:8080'])
public_cors = CORS(allow_all_origins=True)

def requestOCR(credential, jpg_paths):
    '''
    功能 : 呼叫vision api 
    輸入 : 1. gcp金鑰 2. 信用狀JPEG圖檔 
    輸出 : vision api 分析結果
    注意 : 確保每張圖都有不同的tmp_key，否則會覆蓋
    '''
    visionapi.set_vision_credential(credential)
    vision_results = {}
    for path in jpg_paths:
        vis_response, error = visionapi.annotateDocument(path)
        tmp_key = os.path.basename(path)
        vision_results[tmp_key] = vis_response
        if error is not None:
            cmLog('[E] Vision API Error: {}'.format(error))
            # print('[E] Vision API Error: {}'.format(error))
    return vision_results

def retrieveVisionResponse(credential, jpg_paths, result_root=None):
    '''
    功能 : requestOCR的前導程式，用來寫log檔、回傳錯誤訊息
    輸入 : 1. gcp金鑰 2. 信用狀JPEG圖檔 
    輸出 : vision api 分析結果
    '''
    assert isinstance(jpg_paths, list), '[E] "jpg_paths" must be instance of list'
    vision_results = None
    response_path = None
    if result_root is not None:
        assert isinstance(result_root, str), '[E] "response_path" must be instance of string'
        response_file = 'vision_result.json'
        response_path = os.path.join(result_root, response_file)
        cmLog('[I] Reading existed ocr response from {} ...'.format(response_path))
        if os.path.exists(response_path):
            vision_results = utils.loadFileIfExisted(response_path)
    if vision_results is None:
        cmLog('[I] Sending ocr request to Google Vision API...')
        vision_results = requestOCR(credential, jpg_paths)
        cmLog('[I] Saving Google Vision API ocr response to {} ...'.format(response_path))
        if response_path is not None:
            with open(response_path, 'w') as outfile:
                json.dump(vision_results, outfile, ensure_ascii=False, indent=2, sort_keys=True)
    return vision_results

def validateAllParameters(credential, general_path, jpg_path_list, result_root):
    '''
    功能 : 影像處理之前檢查參數
    輸入 : 1.gcp金鑰 2.general.yaml 3.信用狀JPEG圖檔 4.輸出路徑
    輸出 : 
    '''
    assert (isinstance(credential, str) and 
            isinstance(general_path, str) and 
            isinstance(result_root, str)), '[E] All parameters has to be string type'
    assert os.path.exists(credential), '[E] Credential file "{}" not found'.format(credential)
    assert os.path.exists(general_path), '[E] Config file "{}" not found'.format(general_path)
    
    if isinstance(jpg_path_list, str):
        jpg_path_list = [jpg_path_list]
    
    for jpg_path in jpg_path_list:
        assert os.path.exists(jpg_path), '[E] JPG file "{}" not found'.format(jpg_path)

    if not os.path.exists(result_root):
        utils.createDirIfNotExist(result_root)

def annotateCreditLetter(credential, division_code, jpg_path_list, result_root, bank_name=None):
    '''
    功能 : 信用狀分析流程的主幹，所有的sub function都是由這裡呼叫再將資料回傳
    輸入 : 1.gcp金鑰 2.general.yaml 3.信用狀JPEG圖檔 4.輸出路徑
    輸出 : 最終分析結果
    注意 : 分析流程可以參考“台塑信用狀辨識流程圖”
    '''
    # Validate all parameters
    general_path = os.path.join('./configs', 'general.yaml')
    validateAllParameters(credential, general_path, jpg_path_list, result_root)

    general = utils.loadFileIfExisted(general_path)

    ### 
    # . Auto-identified bank name
    if bank_name is None:
        jpg_path_list_n = augm.augmentBatchImages([jpg_path_list[0]], bank_name)
        os.mkdir(result_root+'/tmp')
        vision_results = retrieveVisionResponse(credential, jpg_path_list_n, result_root+'/tmp')
        vision_doc = visionapi.VisionDocument.createWithVisionResponse(vision_results)
        clformatted = formatter.GeneralCLFormatter(vision_doc)
        bank_name = clformatted.identifyBankName(general)  ## 參考general.yaml預設的銀行bounding box擷取銀行名稱
        [os.remove(path) for path in jpg_path_list_n]
        shutil.rmtree(result_root+'/tmp') 
        cmLog('[I] Auto-identified bank name: {}'.format(bank_name))
    
    ### 
    # . Preprocessing the image for enhancement
    cmLog('[I] Preprocessing image for enhencement ...')
    jpg_path_list = augm.augmentBatchImages(jpg_path_list, bank_name)

    ###  
    # . Sending image to Google Vision API and save the response
    vision_results = retrieveVisionResponse(credential, jpg_path_list, result_root)

    ###  
    # . Preparing and organizing vision api's result with config file
    cmLog('[I] Preparing and organizing ocr response ...')
    vision_doc = visionapi.VisionDocument.createWithVisionResponse(vision_results)
    
    ###   
    # . Initialize a formatter
    final_result = {}
    clformatted = formatter.GeneralCLFormatter(vision_doc)
    
    ###
    # . General config must exist
    if general is None:
        cmLog('[C] Unable to find general config file at: {}'.format(general))
        final_result = {
            'error':'[E] Unable to find config file with bank: {} for document at: {}'.format(bank_name, jpg_path_list[0])
            }
    else:
        if 'bank_titles' not in general:
            print('bank_titles')
        bank_list = [b['name'] for b in general['bank_titles']]
        if bank_name.lower() not in bank_list:
            bank_name = clformatted.identifyBankName(general)
            cmLog('[I] Auto-identified bank name: {}'.format(bank_name))
        
        config_path = os.path.join('./configs', bank_name + '_config.yaml')
        config = utils.loadFileIfExisted(config_path)

        ###
        # . Bank config must exist
        if config is None:
            cmLog('[C] Unable to find config file with bank: {} for document at: {}'.format(bank_name, jpg_path_list[0]))
            final_result = {
                'error':'[E] Unable to find config file with bank: {} for document at: {}'.format(bank_name, jpg_path_list[0])
                }
        else:
            cmLog('[I] Extracting Header and Swift codes for bank {} ...'.format(bank_name))
            clformatted.extractHeaderInfo(config)   ## 呼叫reformatter.py分析header的內容
            clformatted.extractSwiftsInfo(config, general)  ## 呼叫reformatter.py分析Swift的內容
            
            cmLog('[I] Evaluating letter of credit ...')
            evaluated = evaluator.CLEvaluator(clformatted)
            evaluated.evaluate_checklist(config, general)
            final_result = evaluated.dumpToDict()

            ### 
            # adding prefix for C# application (C# cannot read key starting with _ or numeric value)
            newswift = {}
            for key, value in final_result['swifts'].items():
                newswift['code_'+key] = final_result['swifts'][key]
            final_result['swifts'] = newswift

        '''
        
        針對回傳的結果做Rule Based的修飾

        '''
        ###
        # 0 replace O
        if 'O' in final_result['header']['lc_no']['text']:
            final_result['header']['lc_no']['text'] = '0'.join(final_result['header']['lc_no']['text'].split('O'))

        ###
        # if applicant is empty replace by code_50
        if final_result['header']['applicant']['text'] == '':
            final_result['header']['applicant']['text'] = final_result['swifts']['code_50']['text']

        ###
        # specialized for mega bank
        if bank_name == 'mega':
            final_result['header']['advising_no_of_bank']['boundingbox'] = [1634, 470, 2520, 660]


        ###
        # if lc_no is empty replace by code_20 or code_21 ，only for mega
        if final_result['header']['lc_no']['text'] == '':
            if 'DOCUMENTARYCREDITN' in final_result['swifts']['code_20']['text'].upper().replace(" ",""):
                code_20_text = final_result['swifts']['code_20']['text'].replace(':', '\n').split('\n')
                for i, _ in enumerate(code_20_text):
                    if 'DOCUMENTARYCREDITN' in _.upper().replace(" ",""):
                        final_result['header']['lc_no']['text'] = code_20_text[i+1].strip()
                        break

            elif 'DOCUMENTARYCREDITN' in final_result['swifts']['code_21']['text'].upper().replace(" ",""):
                code_20_text = final_result['swifts']['code_21']['text'].replace(':', '\n').split('\n')
                for i, _ in enumerate(code_20_text):
                    if 'DOCUMENTARY CREDIT N' in _.upper().replace(" ",""):
                        final_result['header']['lc_no']['text'] = code_20_text[i+1].strip()
                        break


        ###
        # saving checklist.json
        if result_root is not None:
            result_path = os.path.join(result_root, 'checklist.json')
            cmLog('[I] Saving evaluation result in {} ...'.format(result_path))
            with open(result_path, 'w') as outfile:
                json.dump(final_result, outfile, ensure_ascii=False, indent=2)

    return final_result


def checkIfKeyExists(content, target_key):
    '''
    功能 : 檢查post data是否正確
    輸入 : 1.post info 2.target_key
    輸出 : Boolean
    '''
    if not isinstance(content, dict):
        return False
    if not (target_key in content.keys()):
        return False
    return True

class RequestCloudMile:
    '''
    功能 : 信用狀分析API
    輸入 : credential, jpg_path_list, result_root
    輸出 : 分析結果
    '''
    cors = public_cors
    def on_post(self, req, resp):
        req_str = req.stream.read()
        status = falcon.HTTP_200
        output = '[INFO] Request Received.'
        if (len(str(req_str)) == 0):
            status = falcon.HTTP_501
            output = '[ERROR] Invalid Request Found.'
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
    '''
    功能 : PDF轉JEPG
    輸入 : pdf_path, dst_dir
    輸出 : JEPG路徑
    '''
    cors = public_cors
    def on_post(self, req, resp):
        req_str = req.stream.read()
        status = falcon.HTTP_200
        output = '[INFO] Request Received.'
        if (len(str(req_str)) == 0):
            status = falcon.HTTP_501
            output = '[ERROR] Invalid Request Found.'
        else:
            data = json.loads(req_str.decode('utf8'))
            if not checkIfKeyExists(data, 'pdf_path'):
                output = '[ERROR] No pdf_path found.'
            else:
                pdf_path = data['pdf_path']
                
                if checkIfKeyExists(data, 'dst_dir'):
                    dst_dir = data['dst_dir']
                else:
                    dst_dir = 'tmp'
                    
                if checkIfKeyExists(data, 'bank_name'):
                    bank_name = data['bank_name']
                else:
                    bank_name = None
                # paths = utils.pdf2Jpg(pdf_path, dst_dir)
                # output = {'jpg_files':paths}
                convert_from_path(pdf_path,
                    dpi = 400,
                    output_folder=dst_dir,
                    output_file='page',
                    fmt='jpg')
                # output = '[INFO] jpg is under dst_dir you given.'
                output = {'jpg_files':sorted(glob.glob(dst_dir + '/*.jpg'))}

        resp.status = status
        resp.body = json.dumps(output)
        
class RequestImaging:
    '''
    功能 : 原圖快照，輔助營業員判斷辨識結果
    輸入 : jpg_path_list, json_path, result_root
    輸出 : JEPG路徑
    '''
    cors = public_cors
    def on_post(self, req, resp):
        req_str = req.stream.read()
        status = falcon.HTTP_200
        output = '[INFO] Request Received.'
        if (len(str(req_str)) == 0):
            status = falcon.HTTP_501
            output = '[ERROR] Invalid Request Found.'
        else:
            data = json.loads(req_str.decode('utf8'))
            if not checkIfKeyExists(data, 'json_path'):
                output = '[ERROR] No json_path found.'
            elif  not checkIfKeyExists(data, 'jpg_path_list'):
                output = '[ERROR] No jpg_path_list found.'
            elif not checkIfKeyExists(data, 'result_root'):
                output = '[ERROR] No result_root found.'
            else:
                json_path     = data['json_path']
                jpg_path_list = data['jpg_path_list']
                result_root   = data['result_root']
 
                with open(json_path , 'r') as reader:
                    jf = json.loads(reader.read())
                
                ## read jpg file
                jpg_list = []
                for _ in jpg_path_list:
                    jpg_list.append(Image.open(_))

                ## Get header image, header image always in page 1
                output = {}
                # empty = []
                for head in jf['header'].keys():
                    if type(jf['header'][head]['boundingbox']) is list:
                        bbox = tuple(jf['header'][head]['boundingbox'])
                        if len(bbox) == 4 and bbox != (-1,-1,-1,-1):
                            jpg_list[0].crop(bbox).save( result_root + '/' +head +'.png' )
                            output[head] = result_root + '/' +head +'.png'
  
                ## Get swift image, swift image maybe cross mutiple page
                for swift in jf['swifts'].keys():
                    for i, page in enumerate(jf['swifts'][swift]['page']):
                        bbox = tuple(jf['swifts'][swift]['boundingbox'][i])
                        if len(bbox) == 4 and bbox != (-1,-1,-1,-1):
                            jpg_list[jf['swifts'][swift]['page'][i]].crop(bbox).save( result_root + '/' + swift +'_'+str(i)+'.png' )
                            if swift not in output:
                                output[swift] = {'page_{}'.format(i):result_root + '/' + swift +'_'+str(i)+'.png'}
                            else:
                                output[swift]['page_{}'.format(i)] = result_root + '/' + swift +'_'+str(i)+'.png'
                # output = ', '.join(str(_) for _ in empty) + ' are empty'
        resp.status = status
        resp.body = json.dumps(output)

app = falcon.API(middleware=[cors.middleware])
app.add_route('/cloudmile/clevaluator', RequestCloudMile())
app.add_route('/cloudmile/pdfToJpg', RequestPdfToJpg())
app.add_route('/cloudmile/imaging', RequestImaging())
