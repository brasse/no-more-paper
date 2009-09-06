from __future__ import with_statement

import documents.settings as settings
from documents.docstore.models import Document, NumberSequence

from tagging.forms import TagField
from tagging.models import Tag, TaggedItem
from tagging.utils import edit_string_for_tags

from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext

import os

class SearchForm(forms.Form):
    tags = TagField()

class DocumentUploadForm(forms.Form):
    tags = TagField(required=False)
    file = forms.FileField()
    archive_numbers = forms.IntegerField(required=False)

class DocumentPropertiesForm(forms.Form):
    tags = TagField(required=False)
    scan_date = forms.DateTimeField()
    content_type = forms.CharField(max_length=200)

def store_document(user, uploaded_file, tags, archive_numbers):
    # save document in DOCUMENTSTORE_PATH
    with open(os.path.join(settings.DOCUMENTSTORE_PATH, 
                           uploaded_file.name), 'wb') as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    # create Document instance
    if archive_numbers is not None:
        archive_numbers_start = user.numbersequence.reserve(archive_numbers)
    else:
        archive_numbers_start = None
    d = Document(file_name=uploaded_file.name, 
                 content_type=uploaded_file.content_type,
                 archive_numbers_start=archive_numbers_start,
                 archive_numbers_length=archive_numbers)
    d.save()
    Tag.objects.update_tags(d, tags)
    
    return d.id

def number_sequence(user):
    try:
        seq = user.numbersequence
    except ObjectDoesNotExist:
        seq = NumberSequence()
        seq.user = user
        seq.save()

def _render_index_page(request, documents, form):
    tagged_documents = ((d, Tag.objects.get_for_object(d)) 
                        for d in documents)
    return render_to_response('index.html', 
                              dict(tagged_documents=tagged_documents,
                                   form=form),
                              context_instance=RequestContext(request))

def index(request):
    documents = Document.objects.all()
    form = SearchForm()
    return _render_index_page(request, documents, form)

def document_search(request):
    form = SearchForm(request.GET)
    if form.is_valid():
        documents = TaggedItem.objects.get_by_model(Document, 
                                                    form.cleaned_data['tags'])
    else:
        documents = []
    return _render_index_page(request, documents, form)

def upload_confirmation(request):
    return render_to_response('confirmation.html',
                              context_instance=RequestContext(request))

def document_upload(request):
    if request.method == 'POST':
        # Make sure that this user has a NumberSequence instance.
        number_sequence(request.user)
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            user = request.user
            archive_numbers = form.cleaned_data['archive_numbers']
            store_document(user, request.FILES['file'], 
                           form.cleaned_data['tags'],
                           archive_numbers)
            return redirect(reverse(upload_confirmation))
    else:
        form = DocumentUploadForm()
    return render_to_response('upload.html', dict(form=form),
                              context_instance=RequestContext(request))

def document_download(request, id):
    document = get_object_or_404(Document, id=id)
    with open(os.path.join(settings.DOCUMENTSTORE_PATH, 
                           document.file_name)) as f:
        content_type = document.content_type
        if not content_type:
            content_type = 'application/octet-stream'
        return HttpResponse(f.read(), mimetype=content_type)
              
def document_properties(request, id):
    document = get_object_or_404(Document, id=id)
    if request.method == 'POST':
        form = DocumentPropertiesForm(request.POST)
        if form.is_valid():
            document.scan_date = form.cleaned_data['scan_date']
            document.content_type = form.cleaned_data['content_type']
            document.save()
            Tag.objects.update_tags(document, form.cleaned_data['tags'])
            request.user.message_set.create(message='Updated properties.')
            return redirect(reverse(document_properties, args=[id]))
    else:
        tag_string = edit_string_for_tags(Tag.objects.get_for_object(document))
        form = DocumentPropertiesForm(dict(tags=tag_string,
                                           scan_date=document.scan_date,
                                           content_type=document.content_type))
    return render_to_response('properties.html', 
                              dict(document=document,
                                   form=form),
                              context_instance=RequestContext(request))
