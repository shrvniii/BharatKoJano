from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
import json
import logging
from .models import AnswerKey
from .forms import AnswerKeyForm

logger = logging.getLogger(__name__)

def is_module_locked():
    # Return True if all 4 categories exist in the database
    count = AnswerKey.objects.filter(
        group__in=['JUNIOR', 'SENIOR'],
        paper_set__in=['SET_A', 'SET_B']
    ).count()
    return count >= 4

def is_key_locked(key):
    if not key:
        return False
    if key.is_locked:
        return True
    return is_module_locked()

class AnswerKeyStatusView(LoginRequiredMixin, View):
    def get(self, request):
        # Automatically lock the module when user exits the configure page to return to status
        if 'answer_keys_unlocked' in request.session:
            del request.session['answer_keys_unlocked']

        combinations = [
            {'group': 'JUNIOR', 'group_name': 'Junior', 'set': 'SET_A', 'set_name': 'Set A'},
            {'group': 'JUNIOR', 'group_name': 'Junior', 'set': 'SET_B', 'set_name': 'Set B'},
            {'group': 'SENIOR', 'group_name': 'Senior', 'set': 'SET_A', 'set_name': 'Set A'},
            {'group': 'SENIOR', 'group_name': 'Senior', 'set': 'SET_B', 'set_name': 'Set B'},
        ]
        
        status_list = []
        module_locked = is_module_locked()
        for combo in combinations:
            try:
                key = AnswerKey.objects.get(group=combo['group'], paper_set=combo['set'])
                combo['configured'] = True
                combo['is_locked'] = key.is_locked or module_locked
                combo['key_id'] = key.pk
            except AnswerKey.DoesNotExist:
                combo['configured'] = False
                combo['is_locked'] = False
                combo['key_id'] = None
            status_list.append(combo)
            
        return render(request, 'answer_keys/key_status.html', {
            'status_list': status_list,
            'module_locked': module_locked
        })

class AnswerKeyConfigureView(LoginRequiredMixin, View):
    def get(self, request, group, paper_set):
        # Validate parameters
        if group not in ['JUNIOR', 'SENIOR'] or paper_set not in ['SET_A', 'SET_B']:
            messages.error(request, "Invalid group or paper set.")
            return redirect('answer_keys:status')
            
        key = AnswerKey.objects.filter(group=group, paper_set=paper_set).first()
        answers_data = key.answers if key else None
        
        is_locked = is_key_locked(key)
        session_unlocked = request.session.get('answer_keys_unlocked', False)
        
        form = AnswerKeyForm(answers_data=answers_data)
        
        # If locked and not unlocked by session, disable all fields
        if is_locked and not session_unlocked:
            for field in form.fields.values():
                field.disabled = True
                
        context = {
            'group': group,
            'group_name': 'Junior' if group == 'JUNIOR' else 'Senior',
            'paper_set': paper_set,
            'set_name': 'Set A' if paper_set == 'SET_A' else 'Set B',
            'form': form,
            'is_locked': is_locked,
            'session_unlocked': session_unlocked,
            'key': key
        }
        return render(request, 'answer_keys/key_form.html', context)

    def post(self, request, group, paper_set):
        if group not in ['JUNIOR', 'SENIOR'] or paper_set not in ['SET_A', 'SET_B']:
            messages.error(request, "Invalid group or paper set.")
            return redirect('answer_keys:status')
            
        key = AnswerKey.objects.filter(group=group, paper_set=paper_set).first()
        
        is_locked = is_key_locked(key)
        session_unlocked = request.session.get('answer_keys_unlocked', False)
        
        if is_locked and not session_unlocked:
            messages.error(request, "This answer key is locked. Please unlock it using the password first.")
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
            
            # Automatically lock again after saving
            if 'answer_keys_unlocked' in request.session:
                del request.session['answer_keys_unlocked']
            
            messages.success(request, f"Answer Key for {group.title()} {paper_set.replace('_', ' ').title()} saved successfully.")
            return redirect('answer_keys:status')
            
        context = {
            'group': group,
            'group_name': 'Junior' if group == 'JUNIOR' else 'Senior',
            'paper_set': paper_set,
            'set_name': 'Set A' if paper_set == 'SET_A' else 'Set B',
            'form': form,
            'is_locked': is_locked,
            'session_unlocked': session_unlocked,
            'key': key
        }
        return render(request, 'answer_keys/key_form.html', context)

class AnswerKeyUnlockView(LoginRequiredMixin, View):
    def post(self, request):
        try:
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                password = data.get('password', '')
            else:
                password = request.POST.get('password', '')
            
            if password == settings.ANSWER_KEY_PASSWORD:
                request.session['answer_keys_unlocked'] = True
                return JsonResponse({'success': True})
            else:
                logger.warning(
                    f"Failed answer key unlock attempt by user '{request.user.username}' from IP '{request.META.get('REMOTE_ADDR')}'"
                )
                return JsonResponse({
                    'success': False,
                    'error': 'Incorrect password. Please try again.'
                })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

