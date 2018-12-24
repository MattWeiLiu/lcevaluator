import io, os, json, base64, pathlib, re, cv2
from package.logger import cmLog
import numpy as np
from PIL import Image

def erodeBatchImages(src_paths, dst_path=None, grayscaled=True, kernel=(2,2), iterations = 1):
    if isinstance(src_paths, list):
        tmp_list = []
        for paths in src_paths:
            tmp_list.append(erodeImage(paths, dst_path, grayscaled, kernel, iterations))
        return tmp_list
    elif isinstance(src_paths, str):
        return [erodeImage(src_paths, dst_path, grayscaled, kernel, iterations)]
    else:
        cmLog('[E] Failed to interpret paramter: {}'.format(src_paths))



def erodeImage(src_path, dst_path=None, grayscaled=True, kernel=(2,2), iterations = 1):
    assert src_path is not None or not os.path.exists(src_path), '[C] Failed to load image from source: {}'.format(src_path)
    
    if dst_path is None:
        tmp_dir = os.path.dirname(src_path)
        tmp_file = os.path.basename(src_path)
        if not '_aug.jpg' in src_path:
            dst_path = os.path.join(tmp_dir, tmp_file.split('.')[0]+'_aug.jpg')
        else:
            cmLog('[W] augmentated image path already existed will override the existing ')
            dst_path = src_path
    
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

    if grayscaled:
        img = cv2.imread(src_path, 0)
    else:
        img = cv2.imread(src_path)

    kernel = np.ones(kernel, np.uint8)
    erosion = cv2.erode(img, kernel, iterations = 1)
    image = Image.fromarray(erosion)
    image.save(dst_path, "JPEG")
    return dst_path