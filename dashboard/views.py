from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Avg, Max, Min
from django.contrib import messages
import os
from django.conf import settings
from schools.models import School
from participants.models import Participant
from scanner.models import OMRSubmission
from results.models import Result
from answer_keys.models import AnswerKey

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        total_schools = School.objects.count()
        total_participants = Participant.objects.count()
        
        junior_count = Participant.objects.filter(group='JUNIOR').count()
        senior_count = Participant.objects.filter(group='SENIOR').count()
        
        evaluated_count = OMRSubmission.objects.filter(status='EVALUATED').count()
        error_count = OMRSubmission.objects.filter(status='ERROR').count()
        pending_count = total_participants - evaluated_count
        
        progress_pct = 0
        if total_participants > 0:
            progress_pct = int((evaluated_count / total_participants) * 100)
            
        # Score aggregates
        avg_score = Result.objects.aggregate(avg=Avg('score'))['avg'] or 0
        high_score = Result.objects.aggregate(max=Max('score'))['max'] or 0
        low_score = Result.objects.aggregate(min=Min('score'))['min'] or 0
        
        # Recent uploads
        recent_uploads = OMRSubmission.objects.select_related('participant', 'participant__school').order_by('-uploaded_at')[:10]
        
        # Check Answer Keys
        keys_configured = AnswerKey.objects.count()
        keys_ready = (keys_configured == 4)
        
        context = {
            'total_schools': total_schools,
            'total_participants': total_participants,
            'junior_count': junior_count,
            'senior_count': senior_count,
            'evaluated_count': evaluated_count,
            'pending_count': pending_count,
            'error_count': error_count,
            'progress_pct': progress_pct,
            'avg_score': round(avg_score, 1),
            'high_score': high_score,
            'low_score': low_score,
            'recent_uploads': recent_uploads,
            'keys_configured': keys_configured,
            'keys_ready': keys_ready,
        }
        
        return render(request, 'dashboard/home.html', context)

class SettingsView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, 'dashboard/settings.html')

class ResetDataView(LoginRequiredMixin, View):
    def post(self, request):
        # Verify that the user confirmed by typing "RESET" in the form
        confirm_text = request.POST.get('confirm_text', '').strip()
        if confirm_text != "RESET":
            messages.error(request, "Data reset cancelled. You must type 'RESET' to confirm.")
            return redirect('dashboard:settings')

        try:
            with transaction.atomic():
                # 1. Delete OMR image files from disk
                submissions = OMRSubmission.objects.all()
                for sub in submissions:
                    if sub.image and os.path.exists(sub.image.path):
                        try:
                            os.remove(sub.image.path)
                        except OSError:
                            pass
                
                # 2. Delete database records (CASCADE will handle Results and Submissions)
                Result.objects.all().delete()
                OMRSubmission.objects.all().delete()
                Participant.objects.all().delete()
                School.objects.all().delete()
                AnswerKey.objects.all().delete()
                
            messages.success(request, "System database has been successfully reset! All schools, participants, answer keys, and results have been deleted.")
        except Exception as e:
            messages.error(request, f"Error resetting database: {str(e)}")
            
        return redirect('dashboard:home')
