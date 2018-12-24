from __future__ import print_function
import io, os, json, base64, pathlib, re, yaml
import pandas as pd
import numpy as np
import cv2
from collections import OrderedDict
from PIL import Image, ImageDraw
from numbers import Number

def createDirIfNotExist(path):
    """
    Create a directory of given path does not exist
    Parameters
    ----------
    path: str
        path of directory
    """
    if isinstance(path, str):
        if not os.path.exists(path):
            os.makedirs(path)
            return True
    elif isinstance(path, list) or isinstance(path, tuple):
        res = False
        for p in path:
            res |= createDirIfNotExist(p)
        return res
    return False

def traverseDirectories(root_dir, exts=['jpg', 'png']):
    """
    Iterable functions that traverse a given directory and find files with specified extension names
    Parameters
    ----------
    root_dir: str
        path of directory
    exts: list
        list of extenstions that with to be filtered. 
    Return
    ----------
        directory and its files. whoever is calling this functin shall use a loop to iterate the result. 
    """
    assert os.path.isdir(root_dir), '{} has to be a valid directory'.format(root_dir)
    assert isinstance(exts, str) or isinstance(exts, list), 'parameter "exts" must be instance of str or list but get {}'.format(type(exts))
    if isinstance(exts, str): exts = [exts] # convert string to array
    def validateSuffix(path, extension_list):
        suffix = pathlib.Path(path).suffix
        suffix = suffix.replace('.','')
        found = suffix.lower() in extension_list 
        return found

    for root, dirs, files in os.walk(root_dir):
        if root == root_dir and len(files) == 0:
            continue
        files = [f for f in files if not f[0] == '.' and validateSuffix(f, exts)]
        if len(files) == 0:
            print("[W] No image found in '" + root + "'")
            continue
        yield root, files

def loadFileIfExisted(dstPath):
    """
    Load file from the path with known file extension (json, yaml, csv)
    Parameters
    ----------
    path: str
        path of file
    Return
    ----------
        the content in the file 
    """
    assert isinstance(dstPath, str), '[E] parameter \"dstPath\" must be a string'
    content = None
    try:
        with open(dstPath, 'r') as the_file:
            if dstPath.endswith('.csv'):
                content = pd.read_csv(the_file)
            elif dstPath.endswith('.json'):
                content = json.load(the_file)
            elif dstPath.endswith('.yaml'):
                content = yaml.load(the_file)
            else:
                content = the_file.read()
    except (FileNotFoundError, ValueError)  as e:
        print('[E] While opening file at {}. error:{}'.format(dstPath, e))
    return content

def draw_boxes(draw, bounds, color='red', width = 3):
    """Draw a border around the image using the hints in the vector list."""
    if len(bounds) > 0 and isinstance(bounds[0], Number):
        bounds = [bounds]

    # draw = ImageDraw.Draw(image)
    for bound in bounds:
        for i in range(width):
            rect_start = (bound[0] - i, bound[1] - i)
            rect_end = (bound[2] + i, bound[3] + i)
            draw.rectangle((rect_start, rect_end), None, color)
    # return image

def fuseBoundingBox(boundinglist):
    if boundinglist is None:
        return None
    boxes = np.array(boundinglist)
    if boxes.shape[0] == 0 or boxes.shape[1] != 4:
        return None
    new_bounds = [min(boxes[:,0].tolist()), min(boxes[:,1].tolist()), max(boxes[:,2].tolist()), max(boxes[:,3].tolist())]
    return new_bounds

### Conversion
def convertPdfsToJpegs(pdf_root, jpg_root='./jpg_root'):
    """
    Convert all PDFs in a diretcory to JPG. All PDF shall be scanned documents
    Parameters
    ----------
    pdf_root: str
        A directory path which contains multiple pdf files
    jpg_root: str
        A directory path to store converted jpeg files
    Returns
    ----------
    """
    createDirIfNotExist(jpg_root)
    file_gen = traverseDirectories(pdf_root, 'pdf')
    for root, files in file_gen:
        for file in files:
            path_dirs = root.replace(pdf_root, '').replace('/', '')
            dirname = os.path.basename(file).split('.')[0]
            jpg_dir = os.path.join(jpg_root, path_dirs)
            jpg_dir = os.path.join(jpg_dir, dirname)
            file_path = os.path.join(root, file)
            pdf2Jpg(file_path, jpg_dir)

def pdf2Jpg(pdf_path, target_dir):
    """
    Convert PDFs to JPG. All PDF shall be scanned documents
    Parameters
    ----------
    pdf_path: str
        File path of a pdf file
    jpg_root: str
        A directory path to store converted jpeg files
    Returns
    ----------
    """
    jpg_paths =[]
    dir_name = target_dir #os.path.dirname(target_dir)
    for root, dirs, files in os.walk(dir_name):
        for file in files:
            if file.endswith(".jpg"):
                jpg_paths.append(os.path.join(root, file)) 
    
            
    if len(jpg_paths) == 0:
        pdf_file = open(pdf_path, "rb")
        pdf = pdf_file.read()
        startmark = "\xff\xd8"
        startfix = 0
        endmark = "\xff\xd9"
        endfix = 2
        i = 0

        njpg = 0
        while True:
            istream = pdf.find(b"stream", i)
            if istream < 0:
                break
            istart = pdf.find(b"\xff\xd8", istream, istream+20)
            if istart < 0:
                i = istream+20
                continue
            iend = pdf.find(b"endstream", istart)
            if iend < 0:
                raise Exception("Didn't find end of stream!")
            iend = pdf.find(b"\xff\xd9", iend-20)
            if iend < 0:
                raise Exception("Didn't find end of JPG!")
            
            # jpgPath = re.sub(r'(?i)\.pdf', '_{}.jpg'.format(njpg), pdf_path)
            createDirIfNotExist(target_dir)
            jpgPath = os.path.join(target_dir, 'page_{}.jpg'.format(njpg+1))
            istart += startfix
            iend += endfix
            jpg = pdf[istart:iend]
            jpgfile = open(jpgPath, "wb")
            jpgfile.write(jpg)
            jpgfile.close()
            jpg_paths.append(jpgPath)
            njpg += 1
            i = iend
        pdf_file.close()
    return jpg_paths

def text2number(content):
    """
    Convert text to numeric values
    Parameters
    ----------
    content: str
        Text that wish to convert digits. 
    Returns
    ----------
    """
    num_text = ['one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']

    temp = content
    for idx, item in enumerate(num_text):
        temp = temp.replace(item.upper(), str(idx + 1))

    return temp

def removeInvalidChars(content):
    value = content.replace('\x08', '')
    value = value.replace('\b', '')
    return value
