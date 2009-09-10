from tagging.models import Tag

from django.db import models
from django.contrib.auth.models import User

import os

class Document(models.Model):
    user = models.ForeignKey(User)
    store_path = models.CharField(max_length=200)
    creation_time = models.DateTimeField(auto_now_add=True)
    archive_numbers_start = models.IntegerField(null=True, blank=True)
    archive_numbers_length = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=200, null=True, blank=True)

    def tags(self):
        return Tag.objects.get_for_object(self)

    def archive_numbers_string(self):
        if (self.archive_numbers_length is None or 
            self.archive_numbers_length == 0):
            return ''
        elif self.archive_numbers_length == 1:
            return '%d' % self.archive_numbers_start
        else:
            return '%d-%d' % (self.archive_numbers_start,
                              self.archive_numbers_start + 
                              self.archive_numbers_length - 1)

    def __unicode__(self):
        if self.title:
            return self.title
        else:
            return os.path.basename(self.store_path)

class NumberSequence(models.Model):
    user = models.OneToOneField(User)
    next_free_number = models.IntegerField(default=1)

    def reserve(self, n):
        next = self.next_free_number
        self.next_free_number += n
        self.save()
        return next

    def __unicode__(self):
        return 'next: %d' % self.next_free_number
