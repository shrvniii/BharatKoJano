from django import forms
from .models import Participant

class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['roll_number', 'school', 'group', 'paper_set']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply standard form-control styling to all fields
        for name, field in self.fields.items():
            if name in ['group', 'paper_set']:
                # Select fields get the same styling
                field.widget.attrs.update({'class': 'form-control'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        
        # If editing and an OMR submission already exists, disable the roll number field
        if self.instance and self.instance.pk:
            if hasattr(self.instance, 'omr_submission'):
                self.fields['roll_number'].disabled = True
                self.fields['roll_number'].help_text = "Roll number cannot be changed because an OMR sheet is already uploaded."
