import io, os, json, base64, pathlib, re, cv2, math
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

def augmentBatchImages(src_paths, bank_name, dst_paths=None, grayscaled=True, kernel=(5,5), iterations = 1):
    '''
    功能 : augmentation.py的主功能，負責優化信用狀掃描檔，由service/annotateCreditLetter呼叫
    輸入 : 1.信用狀JPEG圖檔, 2.銀行名稱 3.輸出路徑
    輸出 : 優化影像
    附註 : 可以根據不同銀行設計不同的影像優化流程，部分的影像優化策略可以在這份檔案裡面找到，或是參考網路上別人的建議設計新的優化方法
    '''
    if isinstance(src_paths, list):
        tmp_list = []
        for i, path in enumerate(src_paths):
            dst_path = ensureDestinationPath(path, dst_paths)
            tmp_path = path

            if bank_name == 'mega' and i == 0:  # remove blue seal on mega lc
                img1 = cv2.imread(tmp_path)
                # create NumPy arrays from the boundaries
                lower = np.array([140, 0, 0], dtype = "uint8")
                upper = np.array([255, 100, 100], dtype = "uint8")

                # find the colors within the specified boundaries and apply
                # the mask
                mask = cv2.inRange(img1, lower, upper)
                if mask.max() == 255:
                    output = cv2.bitwise_and(img1, img1, mask = mask)
                    imgray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY)

                    # contours
                    contours = cv2.findContours(imgray, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                    contours = contours[-2]

                    boxes = []
                    for c in contours:
                        (x, y, w, h) = cv2.boundingRect(c)
                        boxes.append([x,y, x+w,y+h])

                    boxes = np.asarray(boxes)
                    # need an extra "min/max" for contours outside the frame
                    left = np.min(boxes[:,0])
                    top = np.min(boxes[:,1])
                    right = np.max(boxes[:,2])
                    bottom = np.max(boxes[:,3])
                    # final_img = cv2.rectangle(img1, (left,top), (right,bottom), (0, 255, 0), 2)
                    buffer = 10
                    img = cv2.rectangle(img1, (left-buffer,top-buffer), (right+buffer,bottom+buffer), (255,255,255), -1) # blocking by white block
                    img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                else:
                    if grayscaled:
                        img = cv2.imread(tmp_path, 0)
                    else:
                        img = cv2.imread(tmp_path)
            else:
                if grayscaled:
                    img = cv2.imread(tmp_path, 0)
                else:
                    img = cv2.imread(tmp_path)

            tmp_img = img
            # tmp_img = skrewImage(tmp_img)
            # tmp_img = denoiseImage(tmp_img)
            if bank_name == 'bktw' or bank_name == 'huanan':   # Cause Dot matrix printer
                tmp_img = cv2.pyrDown(tmp_img)
                tmp_img = cv2.pyrUp(tmp_img)
                tmp_img = cv2.erode(tmp_img, (10, 10), iterations=1)
                tmp_img = cv2.dilate(tmp_img, (6, 6), iterations=1)
            else:
                tmp_img = denoiseImage(tmp_img)
                tmp_img = erodeImage(tmp_img, kernel, iterations)
            # tmp_img = cv2.bitwise_not(tmp_img) 
            # tmp_img = morphologyImage(tmp_img)
            # tmp_img = thresholdImage(tmp_img, 60, 255) 
            # tmp_img = cv2.bitwise_not(tmp_img)
            
            image = Image.fromarray(tmp_img)
            image.save(dst_path, "JPEG", quality=110)

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

def denoiseImage(image):
    small = cv2.pyrDown(image)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    grad = cv2.morphologyEx(small, cv2.MORPH_GRADIENT, kernel)

    _, bw = cv2.threshold(grad, 0.0, 255.0, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 1))
    connected = cv2.morphologyEx(bw, cv2.MORPH_CLOSE, kernel)
    # using RETR_EXTERNAL instead of RETR_CCOMP
    # im2, contours, hierarchy = cv2.findContours(connected.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = cv2.findContours(connected.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    contours = contours[-2]

    mask = np.zeros(bw.shape, dtype=np.uint8)
    for idx in range(len(contours)):
        x, y, w, h = cv2.boundingRect(contours[idx])
        # mask[y:y+h, x:x+w] = 0
        if w > 4 and h > 4:
            cv2.rectangle(mask, (x, y), (x+w-1, y+h-1), (255, 255, 255), -1)

    masked = image
    mask = cv2.pyrUp(mask, dstsize=(masked.shape[1], masked.shape[0]))
    masked = cv2.bitwise_not(masked)
    masked = cv2.bitwise_and(masked, mask)
    masked = cv2.bitwise_not(masked)
    return masked
