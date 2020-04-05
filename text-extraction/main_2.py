import firebase_admin
import json
import uuid
import cv2
import numpy as np
import pytesseract
import imutils
import functools
import os
import shutil
import functools

from imutils.perspective import four_point_transform
from imutils import contours
from pathlib import Path
from os import listdir
from imutils.object_detection import non_max_suppression
from pathlib import Path
from os import listdir
from matplotlib import pyplot as plt
from skimage.filters import threshold_local
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import storage
from google.cloud import storage
from pytesseract import Output

COLLECTION = u'testCollection'
BUCKET_NAME = u'versusvirus-output'



def detect_document(path):
    """Detects document features in an image."""
    from google.cloud import vision
    import io
    client = vision.ImageAnnotatorClient()

    with io.open(path, 'rb') as image_file:
        content = image_file.read()

    image = vision.types.Image(content=content)

    response = client.document_text_detection(image=image)

    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            print('\nBlock confidence: {}\n'.format(block.confidence))

            for paragraph in block.paragraphs:
                print('Paragraph confidence: {}'.format(
                    paragraph.confidence))

                for word in paragraph.words:
                    word_text = ''.join([
                        symbol.text for symbol in word.symbols
                    ])
                    print('Word text: {} (confidence: {})'.format(
                        word_text, word.confidence))

                    for symbol in word.symbols:
                        print('\tSymbol: {} (confidence: {})'.format(
                            symbol.text, symbol.confidence))

    if response.error.message:
        raise Exception(
            '{}\nFor more info on error messages, check: '
            'https://cloud.google.com/apis/design/errors'.format(
                response.error.message))



def get_bw(tuple):
    return (tuple[0] + tuple[1] + tuple[2])/3



def setup():
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred, {
    'projectId': "versusvirus-273113",
    'storageBucket': BUCKET_NAME
    })


def loadFileMock(fileName):
    print("Start loading file MOCK")
    with open(fileName) as json_data_string:
        json_data = json.load(json_data_string)
    print(json_data)
    return json_data    

def loadFile(fileName):

def writeToDB(collection, doc_name, document):
    setup()
    db = firestore.client()
    doc_ref = db.collection(collection).document(doc_name)
    doc_ref.set({
        u'bemerkungen': "Patient befindet sich in gutem Zustand.",
        u'exposition': {
            "ausland": True
        }
    })

def loadFile():
    print("Start loading file")
    bucket = storage.bucket(BUCKET_NAME)
    blob = bucket.get_blob(fileName);
    print("File content type:" + blob.content_type)
    json_data_string = blob.download_as_string()
    json_data = json.loads(json_data_string)
    print(json_data)
    return json_data

def createEntry(id, jsonEntry):
    print("Start creation of new entry")
    db = firestore.client()
    doc_ref = db.collection(COLLECTION).document(str(id))
    doc_ref.set(jsonEntry)


def getBlobFromBucket(bucket_name, filename):
    client = storage.Client()
 
    bucket = client.get_bucket(bucket_name)
    blob = bucket.blob(filename)
    my_blob = bucket.get_blob(filename)
    total_filename = "/tmp/"+str(filename)
    blob.download_to_filename(total_filename)
    return total_filename

def getImage(filename):
    bucket = storage.bucket(BUCKET_NAME)
    myImage = bucket.get_blob(filename);
    print("Blob downloaded:", myImage.content_type);
    with open("/tmp/" + filename, "wb") as file_obj:
        myImage.download_to_file(file_obj)

def extract(data, context):
    setup()
    #jsonObject = loadFileMock(data['name'])
    jsonObject = loadFile(data['name'])
    createEntry(uuid.uuid1(), jsonObject)

    print("I am being executed by the cloud function trigger")

    filename = getBlobFromBucket(BUCKET_NAME, data['name'])
    image = cv2.imread(filename)
    print("got the image from the blob")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    # Find contours, filter using contour approximation, aspect ratio, and contour area
    threshold_max_area = 3000
    threshold_min_area = 500
    cnts = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    for c in cnts:
     
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.035 * peri, True)
        x,y,w,h = cv2.boundingRect(approx)
        aspect_ratio = w / float(h)
        area = cv2.contourArea(c) 
        if len(approx) == 4 and area < threshold_max_area and area > threshold_min_area and (aspect_ratio >= 0.9 and aspect_ratio <= 1.1):
            
            crop_img = image[y:y+h, x:x+w]
            
            mean_val = get_bw(cv2.mean(crop_img))
     
            
            if mean_val > 165:
                myRectangle = cv2.rectangle(image, (x, y), (x + w, y + h), (255,255,12), 2)
            else:
                myRectangle = cv2.rectangle(image, (x-5, y-5), (x + w + 200, y + h + 10), (36,255,12), 2)

                # TODO: Make tesseract work
                # text = pytesseract.image_to_string(image[y-10:y+h+15, x-10:x+w+130],config='--psm 6',lang='deu')
                # print(text)
                # cv2.imshow("Outline", image[y-10:y+h+15, x-10:x+w+130])
                # cv2.waitKey(0)
                # cv2.destroyAllWindows()



    detect_document(filename)
    print("Now create the document and insert in DB")

    writeToDB(COLLECTION, "ahv.nr.here", None)

