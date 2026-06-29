from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import AnswerKey
from .forms import AnswerKeyForm

class AnswerKeyStatusView(LoginRequiredMixin, View):
    def get(self, request):
        combinations = [
            {'group': 'JUNIOR', 'group_name': 'Junior', 'set': 'SET_A', 'set_name': 'Set A'},
            {'group': 'JUNIOR', 'group_name': 'Junior', 'set': 'SET_B', 'set_name': 'Set B'},
            {'group': 'SENIOR', 'group_name': 'Senior', 'set': 'SET_A', 'set_name': 'Set A'},
            {'group': 'SENIOR', 'group_name': 'Senior', 'set': 'SET_B', 'set_name': 'Set B'},
        ]
        
        status_list = []
        for combo in combinations:
            try:
                key = AnswerKey.objects.get(group=combo['group'], paper_set=combo['set'])
                combo['configured'] = True
                combo['is_locked'] = key.is_locked
                combo['key_id'] = key.pk
            except AnswerKey.DoesNotExist:
                combo['configured'] = False
                combo['is_locked'] = False
                combo['key_id'] = None
            status_list.append(combo)
            
        return render(request, 'answer_keys/key_status.html', {'status_list': status_list})

class AnswerKeyConfigureView(LoginRequiredMixin, View):
    def get(self, request, group, paper_set):
        # Validate parameters
        if group not in ['JUNIOR', 'SENIOR'] or paper_set not in ['SET_A', 'SET_B']:
            messages.error(request, "Invalid group or paper set.")
            return redirect('answer_keys:status')
            
        key = AnswerKey.objects.filter(group=group, paper_set=paper_set).first()
        answers_data = key.answers if key else None
        is_locked = key.is_locked if key else False
        
        form = AnswerKeyForm(answers_data=answers_data)
        
        # If locked, disable all fields
        if is_locked:
            for field in form.fields.values():
                field.disabled = True
                
        context = {
            'group': group,
            'group_name': 'Junior' if group == 'JUNIOR' else 'Senior',
            'paper_set': paper_set,
            'set_name': 'Set A' if paper_set == 'SET_A' else 'Set B',
            'form': form,
            'is_locked': is_locked,
            'key': key
        }
        return render(request, 'answer_keys/key_form.html', context)

    def post(self, request, group, paper_set):
        if group not in ['JUNIOR', 'SENIOR'] or paper_set not in ['SET_A', 'SET_B']:
            messages.error(request, "Invalid group or paper set.")
            return redirect('answer_keys:status')
            
        key = AnswerKey.objects.filter(group=group, paper_set=paper_set).first()
        
        if key and key.is_locked:
            messages.error(request, "This answer key is locked because OMR sheets have already been evaluated with it.")
            return redirect('answer_keys:status')
            
        form = AnswerKeyForm(request.POST)
        if form.is_valid():
            # Compile answers into a list of 50 integers
            answers = []
            for i in range(1, 51):
                answers.append(form.cleaned_data[f'q_{i}'])
                
            if not key:
                key = AnswerKey(group=group, paper_set=paper_set)
            
            key.answers = answers
            key.save()
            
            messages.success(request, f"Answer Key for {group.title()} {paper_set.replace('_', ' ').title()} saved successfully.")
            return redirect('answer_keys:status')
            
        context = {
            'group': group,
            'group_name': 'Junior' if group == 'JUNIOR' else 'Senior',
            'paper_set': paper_set,
            'set_name': 'Set A' if paper_set == 'SET_A' else 'Set B',
            'form': form,
            'is_locked': False,
            'key': key
        }
        return render(request, 'answer_keys/key_form.html', context)
