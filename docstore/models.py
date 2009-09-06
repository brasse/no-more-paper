from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    file_name = models.CharField(max_length=200)
    scan_date = models.DateTimeField(auto_now_add=True)
    content_type = models.CharField(max_length=200)

    def __unicode__(self):
        return self.file_name

class NumberSequence(models.Model):
    user = models.OneToOneField(User)
    next_free_number = models.IntegerField()

    def __unicode__(self):
        return 'next: %d' % self.next_free_number
