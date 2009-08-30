from django.conf.urls.defaults import *

urlpatterns = patterns('documents.docstore.views',
    (r'^$', 'index'),
    (r'^upload/$', 'document_upload'),
    (r'^confirmation/$', 'upload_confirmation'),
    (r'^download/(\d+)/$', 'document_download'),
    (r'^properties/(\d+)/$', 'document_properties'),
    (r'^search/$', 'document_search'),
)
