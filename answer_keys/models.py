from django.db import models

class AnswerKey(models.Model):
    GROUP_CHOICES = [
        ('JUNIOR', 'Junior'),
        ('SENIOR', 'Senior'),
    ]
    
    SET_CHOICES = [
        ('SET_A', 'Set A'),
        ('SET_B', 'Set B'),
    ]

    group = models.CharField(max_length=10, choices=GROUP_CHOICES)
    paper_set = models.CharField(max_length=5, choices=SET_CHOICES)
    answers = models.JSONField()  # List of 50 integers (1-4). Index = question number (0-based).
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('group', 'paper_set')

    def __str__(self):
        return f"{self.get_group_display()} - {self.get_paper_set_display()}"
