import io, os, json, base64, pathlib, re, cv2
from package.logger import cmLog
import numpy as np
from PIL import Image

def ensureKernelSize(kernel):
    if kernel is None or not isinstance(kernel, (list, tuple)):
        cmLog('[E] Kernel has to be list type, default to (2, 2)')
        kernel = (2, 2)
    else:
        if len(kernel) != 2:
            cmLog('[E] Kernel has to have length of 2, default to (2, 2)')
            kernel = (2, 2)
        else:
            if not (isinstance(kernel[0], int) and isinstance(kernel[1], int)):
                cmLog('[E] Kernel has to contain only integers, default to (2, 2)')
                kernel = (2, 2)    
    return kernel

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

            tmp_img = img
            # tmp_img = skrewImage(tmp_img)
            tmp_img = erodeImage(tmp_img, kernel)
            # tmp_img = cv2.bitwise_not(tmp_img) 
            # tmp_img = morphologyImage(tmp_img)
            # tmp_img = thresholdImage(tmp_img, 60, 255) 
            # tmp_img = cv2.bitwise_not(tmp_img) 
            
            image = Image.fromarray(tmp_img)
            image.save(dst_path, "JPEG", quality=90)

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

###
# Image augmentation methods
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

def dilateImage(image, kernel, iterations = 1):    
    kernel = ensureKernelSize(kernel)
    kernel = np.ones(kernel, np.uint8)
    dilation = cv2.dilate(image, kernel, iterations=iterations)
    return dilation

def erodeImage(image, kernel, iterations = 1):    
    kernel = ensureKernelSize(kernel)
    kernel = np.ones(kernel, np.uint8)
    erosion = cv2.erode(image, kernel, iterations=iterations)
    return erosion

def thresholdImage(image, low=127, high=255, th_type = cv2.THRESH_BINARY):
    ret, th = cv2.threshold(image,low,high,th_type)
    # th = cv2.bitwise_not(th)
    # ret, th = cv2.threshold(image, low, high, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    # th = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2)
    return th

def morphologyImage(image, morph_type=cv2.MORPH_CLOSE, kernel=(2,2)):
    """
        Open is used to remove noises outside the object (white area)
        Close is used to remove noises inside the object (white area)
        cv2.MORPH_CLOSE = Dilation followed by Erosion
        cv2.MORPH_OPEN = Erosion followed by Dilation
    """
    kernel = ensureKernelSize(kernel)
    augmented = image
    augmented = cv2.morphologyEx(augmented, morph_type, kernel)
    return augmented
