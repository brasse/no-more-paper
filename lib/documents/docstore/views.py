from __future__ import with_statement

from documents.docstore.models import Document, NumberSequence

from PythonMagick import Image

from tagging.forms import TagField
from tagging.models import Tag, TaggedItem
from tagging.utils import edit_string_for_tags

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext

import itertools
import os
import time

class SearchForm(forms.Form):
    tags = TagField()

class DocumentUploadForm(forms.Form):
    title_from_file_name = forms.BooleanField(required=False, initial=True)
    title = forms.CharField(required=False)
    tags = TagField(required=False)
    file = forms.FileField()
    archive_numbers = forms.IntegerField(required=False)

class DocumentPropertiesForm(forms.Form):
    title = forms.CharField(max_length=200, required=False)
    tags = TagField(required=False)
    creation_time = forms.DateTimeField()

def prepare_path(document_id, creation_time, user_name):
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
            img.write(str('%s-thumb%03d.png' % (root, i)))
    except RuntimeError:
        # Assume that we have reached the last page and that therefore
        # the Image ctor failed.
        pass
    return i

def store_document(user, uploaded_file, title, tags, archive_numbers):
    # create Document instance
    if archive_numbers is not None:
        archive_numbers_start = user.numbersequence.reserve(archive_numbers)
    else:
        archive_numbers_start = None
    d = Document(user=user, store_path='NOT SET', 
                 archive_numbers_start=archive_numbers_start,
                 archive_numbers_length=archive_numbers, 
                 title=title)
    d.save()
    Tag.objects.update_tags(d, tags)

    # save document in DOCUMENTSTORE_PATH
    relative_path =  prepare_path(d.id, d.creation_time.timetuple(), 
                                  user.username)
    full_path = os.path.join(settings.DOCUMENTSTORE_PATH, relative_path)
    with open(full_path, 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    d.store_path = relative_path
    d.save()

    generate_thumbs(full_path, settings.THUMB_WIDTH)

def number_sequence(user):
    try:
        seq = user.numbersequence
    except ObjectDoesNotExist:
        seq = NumberSequence()
        seq.user = user
        seq.save()

def _render_index_page(request, document_list, form):
    paginator = Paginator(document_list, 
                          settings.THUMB_COLUMNS * settings.THUMB_ROWS)

    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', 1))
    except ValueError:
        page = 1

    # If page request is out of range, deliver last page of results.
    if page > paginator.num_pages:
        page = paginator.num_pages

    documents = paginator.page(page)

    use_thumbs = 'thumbs' in request.GET
    return render_to_response('index.html', 
                              dict(documents=documents, 
                                   form=form, use_thumbs=use_thumbs,
                                   columns=settings.THUMB_COLUMNS),
                              context_instance=RequestContext(request))

@login_required
def index(request):
    documents = Document.objects.filter(user=request.user)
    form = SearchForm()
    return _render_index_page(request, documents, form)

@login_required
def document_search(request):
    form = SearchForm(request.GET)
    if form.is_valid():
        all_documents = Document.objects.filter(user=request.user)
        documents = TaggedItem.objects.get_by_model(all_documents, 
                                                    form.cleaned_data['tags'])
    else:
        documents = []
    return _render_index_page(request, documents, form)

@login_required
def upload_confirmation(request):
    return render_to_response('confirmation.html',
                              context_instance=RequestContext(request))

@login_required
def document_upload(request):
    if request.method == 'POST':
        # Make sure that this user has a NumberSequence instance.
        number_sequence(request.user)
        form = DocumentUploadForm(request.POST, request.FILES)
        if (form.is_valid()):
            file = request.FILES['file']
            if file.content_type == 'application/pdf':
                user = request.user
                archive_numbers = form.cleaned_data['archive_numbers']
                if form.cleaned_data['title_from_file_name']:
                    title = os.path.splitext(file.name)[0]
                elif form.cleaned_data['title'] != '':
                    title = form.cleaned_data['title']
                else:
                    title = None
                store_document(user, file, title, form.cleaned_data['tags'], 
                               archive_numbers)
                return redirect(reverse(upload_confirmation))
            else:
                form.errors['file'] = ['File must be a PDF document.']
    else:
        form = DocumentUploadForm()
    return render_to_response('upload.html', dict(form=form),
                              context_instance=RequestContext(request))

@login_required
def document_download(request, id, name=None):
    document = get_object_or_404(Document, user=request.user, id=id)
    if name is None:
        # Redirect this to an url with a decent file name.
        if document.title is None:
            file_name = os.path.basename(document.store_path)
        else:
            # Translate document title to a safe(?) file name.
            # This need more thought. How can we derive a portable file
            # name from the document title?
            table = {ord(' ') : u'_', ord("'") : u'_'}
            file_name = '%s.pdf' % document.title.translate(table).lower()
        return redirect(reverse('download-named', args=[id, file_name]))
    else:
        with open(os.path.join(settings.DOCUMENTSTORE_PATH, 
                               document.store_path)) as f:
            return HttpResponse(f.read(), mimetype='application/pdf')

@login_required
def document_properties(request, id):
    document = get_object_or_404(Document, user=request.user, id=id)
    if request.method == 'POST':
        form = DocumentPropertiesForm(request.POST)
        if form.is_valid():
            document.title = form.cleaned_data['title']
            document.creation_time = form.cleaned_data['creation_time']
            document.save()
            Tag.objects.update_tags(document, form.cleaned_data['tags'])
            request.user.message_set.create(message='Updated properties.')
            return redirect(reverse(document_properties, args=[id]))
    else:
        tag_string = edit_string_for_tags(Tag.objects.get_for_object(document))
        form = DocumentPropertiesForm(dict(title=document.title, 
                                           tags=tag_string,
                                           creation_time=document.creation_time))
    return render_to_response('properties.html', 
                              dict(document=document,
                                   form=form),
                              context_instance=RequestContext(request))

@login_required
def document_thumbnail(request, id):
    document = get_object_or_404(Document, user=request.user, id=id)
    try:
        n = int(request.GET.get('n', 0))
    except:
        n = 0
    root, ext = os.path.splitext(document.store_path)
    thumb_path = os.path.join(settings.DOCUMENTSTORE_PATH, 
                              '%s-thumb%03d.png' % (root, n))
    if not os.path.exists(thumb_path):
        raise Http404
    with open(thumb_path) as f:
        return HttpResponse(f.read(), mimetype='image/png')
