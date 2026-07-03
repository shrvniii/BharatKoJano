from django import forms
from .models import Participant

class ParticipantForm(forms.ModelForm):
    class Meta:
        model = Participant
        fields = ['roll_number', 'student_name', 'school', 'group', 'paper_set']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Apply standard form-control styling to all fields
        for name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
        
        # If editing, disable all fields except student_name
        if self.instance and self.instance.pk:
            self.fields['roll_number'].disabled = True
            self.fields['school'].disabled = True
            self.fields['group'].disabled = True
            self.fields['paper_set'].disabled = True
            self.fields['roll_number'].help_text = "Generated from pre-printed OMR sheet. Cannot be modified."
