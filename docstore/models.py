from django.db import models
from django.contrib.auth.models import User

class Document(models.Model):
    file_name = models.CharField(max_length=200)
    scan_date = models.DateTimeField(auto_now_add=True)
    content_type = models.CharField(max_length=200)
    archive_numbers_start = models.IntegerField(null=True, blank=True)
    archive_numbers_length = models.IntegerField(null=True, blank=True)

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
        return self.file_name

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
