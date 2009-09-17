from django.conf.urls.defaults import *
from django.conf import settings

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

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'site_media/(?P<path>.*)$', 'django.views.static.serve', 
         {'document_root': settings.DEBUG_SITE_MEDIA}),
    )

