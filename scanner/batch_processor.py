import os
import cv2
import shutil
import logging
import zipfile
import threading
from django.db import connections
from django.core.files import File
from .models import BatchProcess, OMRSubmission
from .evaluator import evaluate_and_grade_submission

logger = logging.getLogger(__name__)

def safe_extract_zip(zip_path, extract_to):
    """
    Extracts a ZIP file to extract_to path while guarding against path traversal attacks.
    """
    if not zipfile.is_zipfile(zip_path):
        raise ValueError("Invalid ZIP file or corrupted ZIP archive.")
        
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        # Check if zip is empty
        infolist = zip_ref.infolist()
        if not infolist:
            raise ValueError("The uploaded ZIP file is empty.")
            
        for member in zip_ref.infolist():
            # Get target path and resolve it
            target_path = os.path.abspath(os.path.join(extract_to, member.filename))
            # Check for path traversal
            if not target_path.startswith(os.path.abspath(extract_to)):
                raise ValueError("Potential path traversal attack detected in ZIP file.")
            
            # If it's a directory, create it
            if member.is_dir():
                os.makedirs(target_path, exist_ok=True)
            else:
                # Ensure parent directory exists
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                with zip_ref.open(member) as source, open(target_path, "wb") as target:
                    shutil.copyfileobj(source, target)

def process_batch_async(batch_id, extract_path, file_list):
    """
    Sequentially processes extracted OMR sheets in a background daemon thread.
    Updates the BatchProcess model status and metrics.
    Cleans up the extracted directory and temporary zip file (if applicable).
    """
    # Close any open connections to ensure thread gets fresh connection pools
    connections.close_all()
    
    total = len(file_list)
    success_count = 0
    failed_count = 0
    failed_files = []
    
    try:
        # Fetch the batch process object
        batch = BatchProcess.objects.get(batch_id=batch_id)
        batch.status = 'processing'
        batch.total = total
        batch.processed = 0
        batch.success = 0
        batch.failed = 0
        batch.percentage = 0
        batch.save()
        
        for idx, rel_path in enumerate(file_list):
            full_path = os.path.join(extract_path, rel_path)
            filename = os.path.basename(rel_path)
            
            # Double check existence
            if not os.path.exists(full_path):
                failed_count += 1
                failed_files.append({
                    "filename": filename,
                    "reason": "File not found during extraction."
                })
                # Update status
                batch.processed = idx + 1
                batch.failed = failed_count
                batch.percentage = int((batch.processed / total) * 100)
                batch.failed_files = failed_files
                batch.save()
                continue
                
            # Verify file with OpenCV to ensure it's not corrupt or unreadable
            try:
                img = cv2.imread(full_path)
                if img is None:
                    raise Exception("Unreadable or corrupted image file")
            except Exception as img_err:
                failed_count += 1
                failed_files.append({
                    "filename": filename,
                    "reason": f"Corrupted file or invalid format: {str(img_err)}"
                })
                batch.processed = idx + 1
                batch.failed = failed_count
                batch.percentage = int((batch.processed / total) * 100)
                batch.failed_files = failed_files
                batch.save()
                continue
                
            # Save the OMR submission and run grading
            submission = None
            try:
                with open(full_path, 'rb') as f:
                    django_file = File(f, name=filename)
                    # We create the submission with PENDING status.
                    # Under Django, saving a file will save/upload it to media/omr_sheets/
                    submission = OMRSubmission.objects.create(status='PENDING')
                    submission.image.save(filename, django_file, save=True)
                
                # Execute standard OMR evaluation
                success, msg = evaluate_and_grade_submission(submission.pk)
                if success:
                    success_count += 1
                else:
                    failed_count += 1
                    failed_files.append({
                        "filename": filename,
                        "reason": msg
                    })
            except Exception as e:
                failed_count += 1
                failed_files.append({
                    "filename": filename,
                    "reason": f"Processing error: {str(e)}"
                })
                # Rollback or cleanup submission if necessary
                if submission and not submission.participant:
                    try:
                        submission.delete()
                    except Exception:
                        pass
                        
            # Update progress metrics
            batch.processed = idx + 1
            batch.success = success_count
            batch.failed = failed_count
            batch.percentage = int((batch.processed / total) * 100)
            batch.failed_files = failed_files
            batch.save()
            
        # Update completion status
        batch.status = 'completed'
        batch.save()
        
    except Exception as fatal_err:
        logger.exception("Fatal error during batch processing.")
        try:
            batch = BatchProcess.objects.get(batch_id=batch_id)
            batch.status = 'failed'
            batch.error_message = str(fatal_err)
            batch.save()
        except Exception:
            pass
            
    finally:
        # Clean up temporary extracted directory
        try:
            if os.path.exists(extract_path):
                shutil.rmtree(extract_path)
        except Exception as cleanup_err:
            logger.error(f"Failed to clean up extract path {extract_path}: {cleanup_err}")
            
        # Close all connections at thread end
        connections.close_all()

def start_batch_processing(batch_id, extract_path, file_list):
    """
    Spawns the background processor in a daemon thread.
    """
    thread = threading.Thread(target=process_batch_async, args=(batch_id, extract_path, file_list))
    thread.daemon = True
    thread.start()
