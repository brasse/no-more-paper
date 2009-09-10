from django.conf.urls.defaults import *

urlpatterns = patterns('django.contrib.auth.views',
    (r'^login/$', 'login', 
     {'template_name': 'login.html'}),
    (r'^logout/$', 'logout', 
     {'template_name': 'logout.html'}),
)

urlpatterns += patterns('documents.docstore.views',
    (r'^$', 'index'),
    (r'^upload/$', 'document_upload'),
    (r'^confirmation/$', 'upload_confirmation'),
    url(r'^download/(\d+)/$', 'document_download', name='download'),
    url(r'^download/(\d+)/(.+)$', 'document_download', name='download-named'),
    (r'^properties/(\d+)/$', 'document_properties'),
    (r'^thumb/(\d+)/$', 'document_thumbnail'),
    (r'^search/$', 'document_search'),
)
