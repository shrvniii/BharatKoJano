from django.db import models
from django.conf import settings
from participants.models import Participant
from answer_keys.models import AnswerKey

class OMRSubmission(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('EVALUATED', 'Evaluated'),
        ('ERROR', 'Error'),
    ]

    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='omr_submission', blank=True, null=True)
    image = models.ImageField(upload_to='omr_sheets/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    error_message = models.TextField(blank=True, null=True)
    detected_answers = models.JSONField(blank=True, null=True)  # List of 50 detected values (0=unanswered, 1-4=A-D, 5=multi-marked)
    answer_key = models.ForeignKey(AnswerKey, on_delete=models.PROTECT, related_name='submissions', blank=True, null=True)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True, related_name='submissions')
    evaluator_name = models.CharField(max_length=100, blank=True, null=True)
    is_accepted = models.BooleanField(default=False)

    def __str__(self):
        roll_num = self.participant.roll_number if self.participant else "No Participant"
        return f"Submission for {roll_num} ({self.status})"

class BatchProcess(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    batch_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    total = models.IntegerField(default=0)
    processed = models.IntegerField(default=0)
    success = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    percentage = models.IntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    failed_files = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Batch {self.batch_id} ({self.status})"

