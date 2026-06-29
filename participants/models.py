from django.db import models
from schools.models import School

class Participant(models.Model):
    GROUP_CHOICES = [
        ('JUNIOR', 'Junior'),
        ('SENIOR', 'Senior'),
    ]
    
    SET_CHOICES = [
        ('SET_A', 'Set A'),
        ('SET_B', 'Set B'),
    ]

    roll_number = models.CharField(max_length=20, unique=True)
    full_name = models.CharField(max_length=150)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='participants')
    group = models.CharField(max_length=10, choices=GROUP_CHOICES)
    paper_set = models.CharField(max_length=5, choices=SET_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.roll_number} - {self.full_name}"
