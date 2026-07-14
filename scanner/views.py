from django.shortcuts import render, redirect, get_object_or_404
import os
import shutil
from django.conf import settings
from django.views import View
from django.views.generic import DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.db import transaction
from .models import OMRSubmission, BatchProcess
from .forms import OMRUploadForm
from .evaluator import evaluate_and_grade_submission
from .batch_processor import safe_extract_zip, start_batch_processing
from answer_keys.models import AnswerKey
from participants.models import Participant

class OMRUploadView(LoginRequiredMixin, View):
    def get(self, request):
        # 1. Enforce evaluator name in session
        evaluator_name = request.session.get('evaluator_name')
        if not evaluator_name:
            return render(request, 'scanner/enter_evaluator.html', {'next_url': request.path})
            
        # 2. Redirect to pending unaccepted scan confirmation page (using session storage for concurrency safety)
        pending_id = request.session.get('pending_submission_id')
        if pending_id:
            pending_sub = OMRSubmission.objects.filter(
                pk=pending_id,
                status='EVALUATED', 
                is_accepted=False
            ).first()
            if pending_sub:
                messages.error(request, "Error: Current scan was not saved. Please click 'Accept Result' to save it, or 'Rescan' to discard.")
                return redirect('scanner:confirm_result', pk=pending_sub.pk)
            else:
                # Clean up stale session ID
                if 'pending_submission_id' in request.session:
                    del request.session['pending_submission_id']
            
        form = OMRUploadForm()
        return render(request, 'scanner/upload.html', {'form': form})

    def post(self, request):
        evaluator_name = request.session.get('evaluator_name')
        if not evaluator_name:
            return render(request, 'scanner/enter_evaluator.html', {'next_url': request.path})
            
        form = OMRUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the submission
            submission = form.save(commit=False)
            submission.operator = request.user
            submission.evaluator_name = evaluator_name
            submission.status = 'PENDING'
            submission.save()
            
            # Store ID in session for concurrency tracking
            request.session['pending_submission_id'] = submission.id
            
            # Trigger OMR evaluation (which handles auto-detecting roll number and linking)
            success, msg = evaluate_and_grade_submission(submission.pk)
            
            submission.refresh_from_db()
            if success:
                # Redirect to confirmation page instead of results page
                return redirect('scanner:confirm_result', pk=submission.pk)
            else:
                # Clean up pending scan session if evaluation failed
                if 'pending_submission_id' in request.session:
                    del request.session['pending_submission_id']
                    
                if submission.status == 'ERROR' and submission.error_message and submission.error_message.startswith("DUPLICATE_SCAN"):
                    return redirect('scanner:duplicate_warning', pk=submission.pk)
                    
                messages.error(request, f"OMR Evaluation failed: {msg}")
                # Clean up the submission if it failed and has no participant linked
                if not submission.participant:
                    submission.delete()
                return redirect('scanner:upload')
                
        return render(request, 'scanner/upload.html', {'form': form})

class OMRDuplicateWarningView(LoginRequiredMixin, View):
    def get(self, request, pk):
        new_submission = get_object_or_404(OMRSubmission, pk=pk)
        
        # Error message is format: DUPLICATE_SCAN:roll_number:group:scan_time:operator_name
        parts = new_submission.error_message.split(':') if new_submission.error_message else []
        if len(parts) >= 6:
            roll_number = parts[1]
            group = parts[2]
            scan_time = f"{parts[3]}:{parts[4]}:{parts[5]}"
            operator_name = parts[6] if len(parts) > 6 else "Unknown"
        else:
            roll_number = "Unknown"
            group = "Unknown"
            scan_time = "Unknown"
            operator_name = "Unknown"
            if new_submission.participant:
                roll_number = new_submission.participant.roll_number
                group = new_submission.participant.group
                existing_eval = OMRSubmission.objects.filter(
                    participant=new_submission.participant,
                    status='EVALUATED'
                ).exclude(pk=new_submission.pk).first()
                if existing_eval:
                    from django.utils import timezone
                    local_uploaded_at = timezone.localtime(existing_eval.uploaded_at)
                    scan_time = local_uploaded_at.strftime("%Y-%m-%d %H:%M:%S")
                    operator_name = existing_eval.operator.username if existing_eval.operator else "Unknown"

        context = {
            'new_submission': new_submission,
            'roll_number': roll_number,
            'group': group.title(),
            'scan_time': scan_time,
            'operator_name': operator_name,
            'is_admin': request.user.is_staff or request.user.is_superuser
        }
        return render(request, 'scanner/duplicate_warning.html', context)

class OMROverrideDuplicateView(LoginRequiredMixin, View):
    def post(self, request, new_submission_id):
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(request, "Permission denied: Only administrators can replace scans.")
            return redirect('scanner:upload')
            
        new_submission = get_object_or_404(OMRSubmission, pk=new_submission_id)
        participant = new_submission.participant
        
        if not participant:
            messages.error(request, "Error: No participant linked to this submission.")
            return redirect('scanner:upload')
            
        try:
            with transaction.atomic():
                # Delete previous evaluated submissions for this participant
                OMRSubmission.objects.filter(
                    participant=participant,
                    status='EVALUATED'
                ).exclude(pk=new_submission.pk).delete()
                
                # Mark this submission as pending so it can evaluate cleanly
                new_submission.status = 'PENDING'
                new_submission.error_message = None
                new_submission.operator = request.user
                new_submission.save()
                
            # Run evaluation on the new submission
            success, msg = evaluate_and_grade_submission(new_submission.pk)
            
            if success:
                new_submission.refresh_from_db()
                messages.success(request, f"OMR Sheet for {new_submission.participant.roll_number} evaluated and replaced successfully!")
                return redirect('results:detail', pk=new_submission.result.pk)
            else:
                messages.error(request, f"Evaluation override failed: {msg}")
                return redirect('scanner:upload')
                
        except Exception as e:
            messages.error(request, f"Override transaction failed: {str(e)}")
            return redirect('scanner:upload')

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
    success_url = reverse_lazy('scanner:upload')

    def form_valid(self, form):
        submission = self.get_object()
        participant_name = submission.participant.roll_number if submission.participant else "Unknown Student"
        answer_key = submission.answer_key
        
        if answer_key:
            # Check if other submissions still use this answer key
            other_submissions_exist = OMRSubmission.objects.filter(answer_key=answer_key).exclude(pk=submission.pk).exists()
            if not other_submissions_exist:
                answer_key.is_locked = False
                answer_key.save()
                
        # Clear session ID if this is the pending one
        if self.request.session.get('pending_submission_id') == submission.pk:
            del self.request.session['pending_submission_id']
                
        response = super().form_valid(form)
        messages.success(self.request, f"OMR submission and result for '{participant_name}' have been reset.")
        return response


class SetEvaluatorView(LoginRequiredMixin, View):
    def post(self, request):
        evaluator_name = request.POST.get('evaluator_name', '').strip()
        next_url = request.POST.get('next', '').strip()
        if evaluator_name:
            request.session['evaluator_name'] = evaluator_name
            messages.success(request, f"Session started for evaluator: {evaluator_name}")
        else:
            messages.error(request, "Evaluator name cannot be blank.")
            
        if next_url:
            return redirect(next_url)
        return redirect('dashboard:home')


class OMRConfirmResultView(LoginRequiredMixin, View):
    def get(self, request, pk):
        if not request.session.get('evaluator_name'):
            return render(request, 'scanner/enter_evaluator.html', {'next_url': request.path})
            
        session_pending_id = request.session.get('pending_submission_id')
        if session_pending_id and session_pending_id != pk:
            messages.error(request, "Access denied: This scan is registered to another operator session.")
            return redirect('scanner:upload')
            
        submission = get_object_or_404(OMRSubmission, pk=pk)
        if submission.is_accepted:
            messages.info(request, "This scan has already been accepted.")
            return redirect('scanner:upload')
            
        result = getattr(submission, 'result', None)
        if not result:
            messages.error(request, "No evaluated results found for this scan.")
            return redirect('scanner:upload')
            
        return render(request, 'scanner/confirm_result.html', {
            'submission': submission,
            'result': result,
            'participant': submission.participant,
        })


class OMRAcceptResultView(LoginRequiredMixin, View):
    def post(self, request, pk):
        submission = get_object_or_404(OMRSubmission, pk=pk)
        submission.is_accepted = True
        submission.save()
        
        # Clear session ID
        if 'pending_submission_id' in request.session:
            del request.session['pending_submission_id']
            
        messages.success(request, f"Result for roll number {submission.participant.roll_number} accepted and saved successfully!")
        return redirect('scanner:upload')


class OMRRescanDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        submission = get_object_or_404(OMRSubmission, pk=pk)
        roll_number = submission.participant.roll_number if submission.participant else "Unknown"
        
        # Delete image from disk if it exists
        if submission.image and os.path.exists(submission.image.path):
            try:
                os.remove(submission.image.path)
            except OSError:
                pass
                
        # Clean up database record (CASCADE deletes the result)
        submission.delete()
        
        # Clear session ID
        if 'pending_submission_id' in request.session:
            del request.session['pending_submission_id']
            
        messages.info(request, f"Scan for roll number {roll_number} discarded. Ready for rescan.")
        return redirect('scanner:upload')
