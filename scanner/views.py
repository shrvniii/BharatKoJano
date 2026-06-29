from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from .models import OMRSubmission
from .forms import OMRUploadForm
from .evaluator import evaluate_and_grade_submission
from answer_keys.models import AnswerKey

class OMRUploadView(LoginRequiredMixin, View):
    def get(self, request):
        form = OMRUploadForm()
        return render(request, 'scanner/upload.html', {'form': form})

    def post(self, request):
        form = OMRUploadForm(request.POST, request.FILES)
        if form.is_valid():
            participant = form.cleaned_data['participant']
            
            # Resolve the correct AnswerKey
            try:
                answer_key = AnswerKey.objects.get(
                    group=participant.group,
                    paper_set=participant.paper_set
                )
            except AnswerKey.DoesNotExist:
                messages.error(
                    request, 
                    f"Cannot evaluate sheet: The Answer Key for "
                    f"'{participant.get_group_display()} - {participant.get_paper_set_display()}' "
                    f"has not been configured yet."
                )
                return render(request, 'scanner/upload.html', {'form': form})
            
            # Save the submission
            submission = form.save(commit=False)
            submission.answer_key = answer_key
            submission.status = 'PENDING'
            submission.save()
            
            # Trigger OMR evaluation
            success, msg = evaluate_and_grade_submission(submission.pk)
            
            if success:
                messages.success(request, f"OMR Sheet for {participant.full_name} evaluated successfully!")
                # Redirect to the result detail view
                return redirect('results:detail', pk=submission.result.pk)
            else:
                messages.error(request, f"OMR Evaluation failed: {msg}")
                # Render the upload page again
                return redirect('scanner:upload')
                
        return render(request, 'scanner/upload.html', {'form': form})

class OMRSubmissionDeleteView(LoginRequiredMixin, DeleteView):
    model = OMRSubmission
    template_name = 'scanner/submission_confirm_delete.html'
    success_url = reverse_lazy('results:list')

    def form_valid(self, form):
        submission = self.get_object()
        participant_name = submission.participant.full_name
        
        # Check if this was the last submission using its answer key
        # If so, we might want to unlock the answer key in the future, but let's keep it simple:
        # We can check if any other evaluated submissions exist for this key. If not, unlock it!
        answer_key = submission.answer_key
        
        response = super().form_valid(form)
        
        # Check if other submissions still use this answer key
        other_submissions_exist = OMRSubmission.objects.filter(answer_key=answer_key).exclude(pk=submission.pk).exists()
        if not other_submissions_exist:
            answer_key.is_locked = False
            answer_key.save()
            
        messages.success(self.request, f"OMR submission and result for '{participant_name}' have been reset.")
        return response
