from __future__ import with_statement

from PythonMagick import Image

from django.conf import settings

import itertools
import os
import time

THUMB_NAME_FORMAT = '%s-thumb%03d.png'

class Error(Exception):
    pass

class NotAPdf(Error):
    pass

def _prepare_path(document_id, creation_time, user_name):
    date_str = time.strftime('%Y%m%d', creation_time)
    time_str = time.strftime('%H%M%S', creation_time)
    relative_path = os.path.join(user_name, date_str)
    dir = os.path.join(settings.DOCUMENTSTORE_PATH, relative_path)
    if not os.path.exists(dir):
        os.makedirs(dir)
    return os.path.join(relative_path, 
                        '%s%s-%d.pdf' % (date_str, time_str, document_id))

def generate_thumbs(pdf, thumb_width):
    '''
    Genrate thumbnails of pdf and return the number of thumbnails created.
    '''
    root, ext = os.path.splitext(pdf)
    if ext != '.pdf':
        return 0
    try:
        for i in itertools.count():
            # If root (wich is unicode) contains any characters that can't
            # be converted by str() we will crash and burn. This needs to
            # become more robust.
            img = Image(str('%s.pdf[%d]' % (root, i)))
            img.scale('%d' % thumb_width)
            img.write(str(THUMB_NAME_FORMAT % (root, i)))
    except RuntimeError:
        # Assume that we have reached the last page and that therefore
        # the Image ctor failed.
        pass
    return i

def is_pdf(pdf):
    PDF_MAGIC = '%PDF'
    with open(pdf) as f:
        magic = f.read(len(PDF_MAGIC))
        return magic == PDF_MAGIC

def store(file, user_name, document_id, creation_time, 
          thumb_width=None, store_path=None):
    '''
    Store document contained in file and return its relative path. If the 
    document in file is not a PDF this function will raise an error.
    '''
    if thumb_width is None:
        thumb_width = settings.THUMB_WIDTH
    if store_path is None:
        store_path = settings.DOCUMENTSTORE_PATH

    relative_path = _prepare_path(document_id, creation_time, user_name)
    full_path = os.path.join(store_path, relative_path)
    with open(full_path, 'wb') as f:
        for chunk in file.chunks():
            f.write(chunk)

    if not is_pdf(full_path):
        os.remove(full_path)
        raise NotAPdf

    generate_thumbs(full_path, thumb_width)

    return relative_path

def get(path, store_path=None):
    '''
    Returns a file like object containing the document at path.
    '''    
    if store_path is None:
        store_path = settings.DOCUMENTSTORE_PATH

    full_path = os.path.join(store_path, path)
    if not os.path.exists(full_path):
        return None
    return open(full_path)

def get_thumb(path, n=0, store_path=None):
    '''
    Returns a file like object containing thumb number n from document
    at path.
    '''
    if store_path is None:
        store_path = settings.DOCUMENTSTORE_PATH

    root, ext = os.path.splitext(path)
    thumb_path = os.path.join(store_path, 
                              THUMB_NAME_FORMAT % (root, n))
    if not os.path.exists(thumb_path):
        return None
    return open(thumb_path)
