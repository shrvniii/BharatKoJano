from django.shortcuts import render, redirect
import os
import shutil
from django.conf import settings
from django.views import View
from django.views.generic import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from .models import OMRSubmission, BatchProcess
from .forms import OMRUploadForm
from .evaluator import evaluate_and_grade_submission
from .batch_processor import safe_extract_zip, start_batch_processing
from answer_keys.models import AnswerKey

class OMRUploadView(LoginRequiredMixin, View):
    def get(self, request):
        form = OMRUploadForm()
        return render(request, 'scanner/upload.html', {'form': form})

    def post(self, request):
        form = OMRUploadForm(request.POST, request.FILES)
        if form.is_valid():
            participant = form.cleaned_data.get('participant')
            
            # Save the submission
            submission = form.save(commit=False)
            
            if participant:
                # Resolve the correct AnswerKey (manual override)
                try:
                    answer_key = AnswerKey.objects.get(
                        group=participant.group,
                        paper_set=participant.paper_set
                    )
                    submission.answer_key = answer_key
                except AnswerKey.DoesNotExist:
                    messages.error(
                        request, 
                        f"Cannot evaluate sheet: The Answer Key for "
                        f"'{participant.get_group_display()} - {participant.get_paper_set_display()}' "
                        f"has not been configured yet."
                    )
                    return render(request, 'scanner/upload.html', {'form': form})
            
            submission.status = 'PENDING'
            submission.save()
            
            # Trigger OMR evaluation (which handles auto-detecting roll number and linking)
            success, msg = evaluate_and_grade_submission(submission.pk)
            
            if success:
                submission.refresh_from_db()
                messages.success(request, f"OMR Sheet for {submission.participant.roll_number} evaluated successfully!")
                return redirect('results:detail', pk=submission.result.pk)
            else:
                messages.error(request, f"OMR Evaluation failed: {msg}")
                # Clean up the submission if it failed and has no participant linked
                if not submission.participant:
                    submission.delete()
                return redirect('scanner:upload')
                
        return render(request, 'scanner/upload.html', {'form': form})

from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class BulkUploadView(LoginRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return JsonResponse({"error": "No file uploaded"}, status=400)
            
        # Check file extension (accept both .zip and .pdf)
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in ['.zip', '.pdf']:
            return JsonResponse({"error": "Only ZIP and PDF files are supported"}, status=400)
            
        # Max size limit 100MB
        if uploaded_file.size > 100 * 1024 * 1024:
            return JsonResponse({"error": "File exceeds maximum size limit (100MB)"}, status=400)
            
        # Generate batch ID
        import uuid
        batch_id = uuid.uuid4().hex[:12]
        
        # Save file temporarily and extract
        
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_batches', batch_id)
        extract_path = os.path.join(temp_dir, 'extracted')
        os.makedirs(extract_path, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, f'batch{file_ext}')
        try:
            with open(temp_file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
                    
            if file_ext == '.zip':
                # Extract ZIP
                safe_extract_zip(temp_file_path, extract_path)
            else:
                # Process PDF: Extract pages as PNG images
                import fitz
                doc = fitz.open(temp_file_path)
                if len(doc) == 0:
                    raise ValueError("The uploaded PDF file is empty.")
                    
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    # Render page to a high-resolution pixmap (150 DPI is ideal)
                    pix = page.get_pixmap(dpi=150)
                    img_name = f"page_{page_num+1:03d}.png"
                    img_path = os.path.join(extract_path, img_name)
                    pix.save(img_path)
                doc.close()
        except ValueError as val_err:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({"error": str(val_err)}, status=400)
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({"error": f"Invalid file format: {str(e)}"}, status=400)
            
        # Clean up temporary file immediately after extraction
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception:
                pass
                
        # Scan extracted files for supported image formats
        valid_files = []
        for root, _, files in os.walk(extract_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png']:
                    rel_path = os.path.relpath(os.path.join(root, file), extract_path)
                    valid_files.append(rel_path)
                    
        valid_files.sort()
        
        if not valid_files:
            shutil.rmtree(temp_dir, ignore_errors=True)
            return JsonResponse({"error": "No supported images found"}, status=400)
            
        # Create BatchProcess record
        batch = BatchProcess.objects.create(
            batch_id=batch_id,
            status='queued',
            total=len(valid_files),
            processed=0,
            success=0,
            failed=0,
            percentage=0
        )
        
        # Start background processor thread
        start_batch_processing(batch_id, extract_path, valid_files)
        
        return JsonResponse({"batchId": batch_id}, status=200)

class BatchProgressView(LoginRequiredMixin, View):
    def get(self, request, batch_id):
        from .models import BatchProcess
        try:
            batch = BatchProcess.objects.get(batch_id=batch_id)
            return JsonResponse({
                "status": batch.status,
                "processed": batch.processed,
                "total": batch.total,
                "success": batch.success,
                "failed": batch.failed,
                "percentage": batch.percentage
            })
        except BatchProcess.DoesNotExist:
            return JsonResponse({"error": "Batch not found"}, status=404)

class BatchResultsView(LoginRequiredMixin, View):
    def get(self, request, batch_id):
        from .models import BatchProcess
        try:
            batch = BatchProcess.objects.get(batch_id=batch_id)
            return JsonResponse({
                "total": batch.total,
                "success": batch.success,
                "failed": batch.failed,
                "failedFiles": batch.failed_files,
                "errorMessage": batch.error_message
            })
        except BatchProcess.DoesNotExist:
            return JsonResponse({"error": "Batch not found"}, status=404)


class OMRSubmissionDeleteView(LoginRequiredMixin, DeleteView):
    model = OMRSubmission
    template_name = 'scanner/submission_confirm_delete.html'
    success_url = reverse_lazy('results:list')

    def form_valid(self, form):
        submission = self.get_object()
        participant_name = submission.participant.roll_number
        
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
