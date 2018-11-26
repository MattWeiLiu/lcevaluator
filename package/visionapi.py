import os, base64, json
import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
from enum import Enum
from collections import namedtuple
from googleapiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

DOC_DETECTION = 'DOCUMENT_TEXT_DETECTION'
LOGO_DETECTION = 'LOGO_DETECTION'

SCOPES = 'https://www.googleapis.com/auth/cloud-platform'
vision_svc = None

def formatFeatures(feature_list):
    features = []
    for f in feature_list:
        features.append({'type': f})
    return features

def set_vision_credential(credential_file='vapi-acct.json'):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        credential_file, SCOPES)
    global vision_svc
    vision_svc = discovery.build('vision', 'v1', credentials=credentials)

def requestProperty(image_file, feature_list, languageHints=['en']):
    assert vision_svc is not None, 'vision api credential not set'

    with open(image_file, "rb") as file:
        encoded_string = base64.b64encode(file.read())
        
    encoded = encoded_string.decode('ascii')
    request_dict = [{
        "image":{
            'content': encoded
        },
        'features': feature_list,
        'imageContext': {
            'languageHints': languageHints
         }
        }]

    request = vision_svc.images().annotate(body={
        'requests': request_dict
    })
    response = request.execute()
    return response

def annotateDocument(image_file, features=[DOC_DETECTION], language_list=['en', 'zh-CN', 'zh-TW']):
    # features = features
    featurelist = formatFeatures(features)
    json_res = requestProperty(image_file, featurelist, language_list)
    json_res = json_res['responses'][0]        
    err = None
    if ('error' in json_res):
        err = '[E] ' + json.dumps(json_res['error'])
    return json_res, err

class VisionObject(object):
    """
    Basic object created from Vision API's result
    """
    class DEPTH (Enum):
        NONE = 0
        PAGES = 1
        BLOCKS = 2
        PARAGRAPHS = 3
        WORDS = 4
        SYMBOLS = 5
        TEXT = 6

    @staticmethod
    def getTextAndBoundingbox(objectList):
        textlist = []
        boundinglist = []
        for item in objectList:
            assert isinstance(item, VisionObject), '[E] item in the list must be instance of VisionObject'
            textlist.append(item.getText())
            boundinglist.append(item.bounding)
        return textlist, boundinglist

    @staticmethod
    def getLinesAndBoundingbox(objectList):
        linelist = []
        boundinglist = []
        tmplines = ''
        tmpboxes = []
        for item in objectList:
            assert isinstance(item, VisionObject), '[E] item in the list must be instance of VisionObject'
            tmplines += item.getText()
            tmpboxes.append(item.bounding)
            if item.detectedLineBreak():
                linelist.append(tmplines)
                boundinglist.append(VisionObject.fuseBoundingBox(tmpboxes))
                tmplines = ''
                tmpboxes = []
        return linelist, boundinglist
    

    @staticmethod
    def fuseBoundingBox(boundinglist):
        if boundinglist is None:
            return []
        if len(boundinglist) > 0 and isinstance(boundinglist[0], int):
            boundinglist = [boundinglist]
        boxes = np.array(boundinglist)
        new_bounds = []

        try:
            new_bounds = [min(boxes[:,0].tolist()), min(boxes[:,1].tolist()), max(boxes[:,2].tolist()), max(boxes[:,3].tolist())]
        except IndexError as err:
            print('[E] Unable to fuse boundingbox ', boundinglist)            
        return new_bounds

    def __init__(self, vis_object = None, contentName=None, contentKey = None):
        try:
            self.depth = self.DEPTH[contentKey.upper()].value - 1
        except KeyError as err:
            self.depth =  self.DEPTH.BLOCKS.value

        self.text = ''
        self.bounding = [0,0,0,0]
        self.confidence = 0
        self.vertices = []
        self.content_list = []
            
        if vis_object is not None and isinstance(vis_object, dict):
            if 'boundingBox' in vis_object.keys():                
                self.vertices = vis_object['boundingBox']['vertices']
                self.bounding = self.__getRectFromBoundingbox(self.vertices)

            if 'confidence' in vis_object.keys():                
                self.confidence = vis_object['confidence'] 
        
        if vis_object is not None and (contentName is not None and contentKey is not None):
            if contentName == VisionObject:
                self.content_list.append(vis_object[contentKey])
            else:
                for tmp in vis_object[contentKey]:
                    self.content_list.append(contentName(tmp))

    def __getRectFromBoundingbox(self, vertices):
        """
        Parsing boundingbox from Vision API result and convert to a rect(x_start, y_start, x_end, y_end)
        """
        b_coord = []
        for b in vertices:
            temp = []
            if 'x' in b.keys():
                temp.append(b['x'])
            else:
                temp.append(0)
                
            if 'y' in b.keys():
                temp.append(b['y'])
            else:
                temp.append(0)
            b_coord.append(temp)

        b_array = np.array(b_coord)
        x_list = b_array[:,0]
        y_list = b_array[:,1]
        rect = [int(min(x_list)), int(min(y_list)), int(max(x_list)), int(max(y_list))]
        return rect

    def checkIntersection(self, rect2):
        """
        Self explaind function. Check if self.bounding is intersect with the given rect
        """
        rect1 = self.bounding
        v1 = rect1[2] < rect2[0]
        v2 = rect1[0] > rect2[2]
        v3 = rect1[3] < rect2[1]
        v4 = rect1[1] > rect2[3]
        return not (v1 or v2 or v3 or v4)

    def getArea(self):
        """
        Self explaind function. Calculates the area of self.bounding.
        """
        return (self.bounding[2] - self.bounding[0]) * (self.bounding[3] - self.bounding[1])

    def getOverlappedArea(self, rect):
        """
        Self explaind function. Calculates the overlapping area between self.bounding and given rect.
        """
        dx = max(0, (min(self.bounding[2], rect[2]) - max(self.bounding[0], rect[0])))
        dy = max(0, (min(self.bounding[3], rect[3]) - max(self.bounding[1], rect[1])))
        return dx*dy     

    def getText(self):
        """
        Recursive function that return the text in the content list 
        Parameters
        ----------
        
        Returns
        -------
        str
            text from content list 
        """
        text = ''
        for tmp in self.content_list:
            if isinstance(tmp, str):
                text += tmp
            elif isinstance(tmp, VisionObject):
                text += tmp.getText()
        return text

    def isOverlapped(self, rect, threshold=0.5):
        contentArea = self.getArea()
        intersects = self.checkIntersection(rect)
        overlapped = self.getOverlappedArea(rect)
        return intersects and (overlapped > contentArea * threshold)

    def getObjectInBoundary(self, boundary, threshold=0.5, depth=DEPTH.WORDS):
        """
        Recusive function that returns the text within specified boundary
        Parameters
        ----------
        boundary : list of int in format of [x_start, y_start, x_end, y_end]
            Boundary of the document that wish to extract the text. 
        threshold : int
            A threshold that indicates the valid area from the folloing fomula:
            valid = intersects and (overlapped > contentArea * threshold): 
        depth : enum
            An integer that indicates the levels of returning boundingbox
        Returns
        -------
        list
            List of vision objects
        """
        assert boundary is not None and len(boundary) == 4, '[E] boundary must be a list of integers with length of 4.'
        valid = True
        for b in boundary:
            valid &= isinstance(b, int)
        assert valid, '[E] boundary must be a list of integers with length of 4.'
        
        if self.depth >= depth.value:
            if self.isOverlapped(boundary, threshold):
                return self.content_list
            else:                
                return []
        else:
            overlap_list = []
            for content in self.content_list:
                if isinstance(content, VisionObject):
                    tmp_list = content.getObjectInBoundary(boundary, threshold, depth);
                    overlap_list.extend(tmp_list)
            return overlap_list

class VisionSymbol(VisionObject):
    def __init__(self, symbol):
        super().__init__(symbol, contentName=VisionObject, contentKey='text')
        self.languageCodes = ['en']
        if 'property' in symbol and 'detectedLanguages' in symbol['property']: 
            self.languageCodes.pop(0)
            for code in symbol['property']['detectedLanguages']:
                self.languageCodes.append(code['languageCode'])
        
        self.detectedBreak = ''
        if 'property' in symbol and 'detectedBreak' in symbol['property']: 
            if symbol['property']['detectedBreak']['type'] == 'SPACE':
                self.detectedBreak = ' '        
            else:
                self.detectedBreak = '\n'
            self.content_list.append(self.detectedBreak)
    
    def detectedLineBreak(self):
        return self.detectedBreak == '\n'

class VisionWord(VisionObject):
    def __init__(self, word):
        super().__init__(word, contentName=VisionSymbol, contentKey='symbols')

class VisionParagraph(VisionObject):
    def __init__(self, para):
        super().__init__(para, contentName=VisionWord, contentKey='words')

class VisionBlock(VisionObject):
    def __init__(self, block):
        super().__init__(block, contentName=VisionParagraph, contentKey='paragraphs')

class VisionPage(VisionObject):
    def __init__(self, page=None):
        super().__init__(page, contentName=VisionBlock, contentKey='blocks')
        if page is not None:
            if 'width' in page.keys() and 'height' in page.keys() :
                self.bounding = [0, 0, page["width"], page["height"]]
            if 'property' in page.keys():
                self.property = page['property']

class VisionDocument(VisionObject):
    @staticmethod
    def createWithVisionResponse(response):
        vision_doc = None
        for idx, (key, res) in enumerate(response.items()):
            if vision_doc is None:
                vision_doc = VisionDocument(res)
            else:
                vision_doc.addPage(res)
        return vision_doc

    def __init__(self, response):
        if 'fullTextAnnotation' not in response.keys():
            print('[E] Response is missing key "fullTextAnnotation":{}'.format(response))
            super().__init__(None, contentName=VisionPage, contentKey=None)        
        else:
            super().__init__(response['fullTextAnnotation'], contentName=VisionPage, contentKey='pages')        
            

    def getNumberOfPages(self):
        return len(self.content_list)

    def addPage(self, response):
        ### Some page in the PDF is completely empty, therefore create an empty page.
        if 'fullTextAnnotation' not in response.keys():
            print('[W] Response is missing key "fullTextAnnotation":{}'.format(response))
            self.content_list.append(VisionPage())
        else:
            if 'pages' not in response['fullTextAnnotation'].keys():
                print('[W] fullTextAnnotation is missing key "page":{}'.format(response))
                self.content_list.append(VisionPage())
            else:
                pages = response['fullTextAnnotation']['pages']
                for p in pages:
                    self.content_list.append(VisionPage(p))                      
    
    def getObjectInBoundaryInPage(self, page_idx, boundary, threshold=0.5, depth=VisionObject.DEPTH.WORDS):
        return self.content_list[page_idx].getObjectInBoundary(boundary, threshold=threshold, depth=depth)


### PageTable
#   PageID | witdh | height | properties | text

### BlockTable
#   BlockID | PageID | boundingbox | confidence | paragraph_count | block_type 

### ParagraphTable
#   ParagraphID | BlockID | boundingbox | confidence | word_count

### WordTable
#   WordID | ParagraphID | boundingbox | confidence | symbol_count | property

### SymbolTable
#   SymbolID | WordID | boundingbox | confidence | property | text
