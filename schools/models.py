from django.db import models

class School(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()
        if self.code:
            if not self.code.isdigit() or len(self.code) != 2:
                from django.core.exceptions import ValidationError
                raise ValidationError({'code': 'School code must be exactly 2 digits (e.g., 01, 02, ..., 38).'})

    def __str__(self):
        return self.name

