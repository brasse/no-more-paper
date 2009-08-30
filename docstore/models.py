from django.db import models

class Document(models.Model):
    file_name = models.CharField(max_length=200)
    scan_date = models.DateTimeField(auto_now_add=True)
    content_type = models.CharField(max_length=200)

    def __unicode__(self):
        return self.file_name
