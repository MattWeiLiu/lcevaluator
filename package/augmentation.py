import io, os, json, base64, pathlib, re, cv2
from package.logger import cmLog
import numpy as np
from PIL import Image

def ensureDestinationPath(src_path, dst_path):
    assert src_path is not None or not os.path.exists(src_path), '[C] Failed to load image from source: {}'.format(src_path)
    if dst_path is None:
        tmp_dir = os.path.dirname(src_path)
        tmp_file = os.path.basename(src_path)
        if not '_aug.jpg' in src_path:
            dst_path = os.path.join(tmp_dir, tmp_file.split('.')[0]+'_aug.jpg')
        else:
            print('[W] augmentated image path already existed will override the existing file')
            cmLog('[W] augmentated image path already existed will override the existing file')
            dst_path = src_path
    return dst_path

def augmentBatchImages(src_paths, dst_paths=None, grayscaled=True, kernel=(2,2), iterations = 1):
    if isinstance(src_paths, list):
        tmp_list = []
        for path in src_paths:
            dst_path = ensureDestinationPath(path, dst_paths)
            tmp_path = path

            if grayscaled:
                img = cv2.imread(tmp_path, 0)
            else:
                img = cv2.imread(tmp_path)

            tmp_img = skrewImage(img)
            tmp_img = erodeImage(tmp_img, kernel)

            image = Image.fromarray(tmp_img)
            image.save(dst_path, "JPEG")

            # tmp_path = skrewImagePath(path, dst_path, grayscaled)
            # tmp_path = erodeImagePath(tmp_path, dst_path, grayscaled, kernel, iterations)
            tmp_list.append(dst_path)
        return tmp_list
    elif isinstance(src_paths, str):
        return [erodeImagePath(src_paths, dst_path, grayscaled, kernel, iterations)]
    else:
        cmLog('[E] Failed to interpret paramter: {}'.format(src_paths))
 

def erodeBatchImages(src_paths, dst_paths=None, grayscaled=True, kernel=(2,2), iterations = 1):
    if isinstance(src_paths, list):
        tmp_list = []
        for paths in src_paths:
            tmp_list.append(erodeImagePath(paths, dst_paths, grayscaled, kernel, iterations))
        return tmp_list
    elif isinstance(src_paths, str):
        return [erodeImagePath(src_paths, dst_paths, grayscaled, kernel, iterations)]
    else:
        cmLog('[E] Failed to interpret paramter: {}'.format(src_paths))

def thresholdImage(image):
    ret, th = cv2.threshold(image,127,255,cv2.THRESH_BINARY)

    return th

def erodeImagePath(src_path, dst_path=None, grayscaled=True, kernel=(2,2), iterations = 1):
    dst_path = ensureDestinationPath(src_path, dst_path)
    if grayscaled:
        img = cv2.imread(src_path, 0)
    else:
        img = cv2.imread(src_path)

    tmp = erodeImage(img, kernel)
    image = Image.fromarray(tmp)
    image.save(dst_path, "JPEG")
    return dst_path

def erodeImage(image, kernel):    
    if kernel is None or not isinstance(kernel, (list, tuple)):
        cmLog('[E] Kernel has to be list type, default to (2, 2)')
        kernel = (1, 1)
    else:
        if len(kernel) != 2:
            cmLog('[E] Kernel has to have length of 2, default to (2, 2)')
            kernel = (1, 1)
        else:
            if not (isinstance(kernel[0], int) and isinstance(kernel[1], int)):
                cmLog('[E] Kernel has to contain only integers, default to (2, 2)')
                kernel = (1, 1)

    kernel = np.ones(kernel, np.uint8)
    erosion = cv2.erode(image, kernel, iterations = 1)
    return erosion

def skrewBatchImages(src_paths, dst_path=None, grayscaled=True, kernel=(2,2), iterations = 1):
    if isinstance(src_paths, list):
        tmp_list = []
        for paths in src_paths:
            tmp_list.append(skrewImagePath(paths, dst_path, grayscaled))
        return tmp_list
    elif isinstance(src_paths, str):
        return [erodeImagePath(src_paths, dst_path, grayscaled)]
    else:
        cmLog('[E] Failed to interpret paramter: {}'.format(src_paths))

def skrewImagePath(src_path, dst_path=None, grayscaled=True):
    dst_path = ensureDestinationPath(src_path, dst_path)
    if grayscaled:
        img = cv2.imread(src_path, 0)
    else:
        img = cv2.imread(src_path)
    rotated = skrewImage(img)
    image = Image.fromarray(rotated)
    image.save(dst_path, "JPEG")
    return dst_path
    
def skrewImage(image):
    img = cv2.bitwise_not(image)
    thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h), 
                             flags=cv2.INTER_CUBIC, 
                             borderMode=cv2.BORDER_REPLICATE) 
    rotated = cv2.bitwise_not(rotated)
    return rotated

