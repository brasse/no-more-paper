import os, sys
sys.path.append('/var/lib/django/documents/lib')
os.environ['DJANGO_SETTINGS_MODULE'] = 'documents.settings'

import django.core.handlers.wsgi

application = django.core.handlers.wsgi.WSGIHandler()
