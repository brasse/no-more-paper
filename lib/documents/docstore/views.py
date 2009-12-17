from __future__ import with_statement

from documents.docstore.models import Document, NumberSequence
from documents.docstore import docstore

from tagging.forms import TagField
from tagging.models import Tag, TaggedItem
from tagging.utils import edit_string_for_tags

from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render_to_response
from django.template import RequestContext

import os

class SearchForm(forms.Form):
    tags = TagField(required=False)
    start_date = forms.DateField(required=False, help_text="YYYY-MM-DD")
    end_date = forms.DateField(required=False, help_text="YYYY-MM-DD")

class DocumentUploadForm(forms.Form):
    title_from_file_name = forms.BooleanField(required=False, initial=False)
    title = forms.CharField(required=False)
    tags = TagField(required=False)
    file = forms.FileField()
    archive_numbers = forms.IntegerField(required=False)

class DocumentPropertiesForm(forms.Form):
    title = forms.CharField(max_length=200, required=False)
    tags = TagField(required=False)
    creation_time = forms.DateTimeField()

def create_document(user, uploaded_file, title, tags, archive_numbers):
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

    relative_path = docstore.store(uploaded_file, user.username, d.id,  
                                   d.creation_time.timetuple())

    d.store_path = relative_path
    d.save()

@login_required
def delete_confirmation(request):
    return render_to_response('deleted.html', 
                              context_instance=RequestContext(request))

@login_required
def document_delete(request, id):
    document = get_object_or_404(Document, user=request.user, id=id)
    docstore.delete(document.store_path)
    document.delete()
    return redirect(reverse(delete_confirmation))

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
        filter = dict(user=request.user)
        start_date = form.cleaned_data['start_date']
        if not start_date is None:
            filter['creation_time__gte'] = start_date
        end_date = form.cleaned_data['end_date']
        if not end_date is None:
            filter['creation_time__lte'] = end_date
        documents = Document.objects.filter(**filter)
        tags = form.cleaned_data['tags']
        if tags:
            documents = TaggedItem.objects.get_by_model(documents, tags)
    else:
        documents = []
    return _render_index_page(request, documents, form)

@login_required
def upload_confirmation(request):
    return render_to_response('confirmation.html',
                              context_instance=RequestContext(request))

@login_required
@transaction.commit_manually
def document_upload(request):
    if request.method == 'POST':
        # Make sure that this user has a NumberSequence instance.
        number_sequence(request.user)

        form = DocumentUploadForm(request.POST, request.FILES)
        if (form.is_valid()):
            file = request.FILES['file']
            archive_numbers = form.cleaned_data['archive_numbers']
            if form.cleaned_data['title_from_file_name']:
                title = os.path.splitext(file.name)[0]
            elif form.cleaned_data['title'] != '':
                title = form.cleaned_data['title']
            else:
                title = None
            try:
                create_document(request.user, file, title, 
                                form.cleaned_data['tags'], archive_numbers)
                transaction.commit()
                return redirect(reverse(upload_confirmation))
            except docstore.NotAPdf:
                transaction.rollback()
                form.errors['file'] = ['File must be a PDF document.']
            except:
                transaction.rollback()
                raise
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
        doc = docstore.get(document.store_path)
        if doc is None:
            raise Http404
        with doc:
            return HttpResponse(doc.read(), mimetype='application/pdf')

@login_required
def document_properties(request, id):
    document = get_object_or_404(Document, user=request.user, id=id)
    if request.method == 'POST':
        form = DocumentPropertiesForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['title'] != '':
                document.title = form.cleaned_data['title']
            else:
                document.title = None
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
    thumb = docstore.get_thumb(document.store_path, n)
    if thumb is None:
        raise Http404
    with thumb:
        return HttpResponse(thumb.read(), mimetype='image/png')
