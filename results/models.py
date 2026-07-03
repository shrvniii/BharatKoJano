from django.db import models
from scanner.models import OMRSubmission
from participants.models import Participant

class Result(models.Model):
    submission = models.OneToOneField(OMRSubmission, on_delete=models.CASCADE, related_name='result')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='results') # Denormalized for convenience
    score = models.IntegerField()  # 0 to 50
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    unanswered_count = models.IntegerField()
    multi_marked_count = models.IntegerField()
    confidence_score = models.IntegerField(default=100)
    question_breakdown = models.JSONField()  # List of 50 dicts: [{"q_no": 1, "detected": 1, "correct": 1, "status": "correct"}]
    evaluated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for {self.participant.roll_number}: {self.score}/50"
