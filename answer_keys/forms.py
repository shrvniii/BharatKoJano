from django import forms

class AnswerKeyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        answers_data = kwargs.pop('answers_data', None)
        super().__init__(*args, **kwargs)
        
        # Options corresponding to A, B, C, D (stored as integers 1, 2, 3, 4)
        CHOICES = [
            ('', '—'),
            (1, 'A'),
            (2, 'B'),
            (3, 'C'),
            (4, 'D'),
        ]
        
        for i in range(1, 51):
            initial_val = None
            if answers_data and len(answers_data) >= i:
                initial_val = answers_data[i-1]
                
            self.fields[f'q_{i}'] = forms.TypedChoiceField(
                choices=CHOICES,
                coerce=int,
                label=f"Q{i}",
                required=True,
                initial=initial_val,
                widget=forms.Select(attrs={'class': 'form-control', 'style': 'padding: 6px 12px;'})
            )
