import csv
import io
from django.shortcuts import render, redirect
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from .models import Participant
from .forms import ParticipantForm
from schools.models import School

class ParticipantListView(LoginRequiredMixin, ListView):
    model = Participant
    template_name = 'participants/participant_list.html'
    context_object_name = 'participants'
    paginate_by = 50

    def get_queryset(self):
        queryset = Participant.objects.select_related('school', 'omr_submission').order_by('roll_number')
        
        # Search
        q = self.request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(roll_number__icontains=q)
            
        # Filters
        school_id = self.request.GET.get('school', '')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
            
        group = self.request.GET.get('group', '')
        if group:
            queryset = queryset.filter(group=group)
            
        paper_set = self.request.GET.get('set', '')
        if paper_set:
            queryset = queryset.filter(paper_set=paper_set)
            
        status = self.request.GET.get('status', '')
        if status:
            if status == 'PENDING':
                queryset = queryset.filter(omr_submission__isnull=True)
            else:
                queryset = queryset.filter(omr_submission__status=status)
                
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schools'] = School.objects.all().order_by('name')
        # Preserve query parameters for pagination
        query_params = self.request.GET.copy()
        if 'page' in query_params:
            query_params.pop('page')
        context['query_params'] = query_params.urlencode()
        return context

class ParticipantUpdateView(LoginRequiredMixin, UpdateView):
    model = Participant
    form_class = ParticipantForm
    template_name = 'participants/participant_form.html'
    success_url = reverse_lazy('participants:list')

    def form_valid(self, form):
        messages.success(self.request, f"Participant '{form.instance.roll_number}' updated successfully.")
        return super().form_valid(form)

class ParticipantDeleteView(LoginRequiredMixin, DeleteView):
    model = Participant
    template_name = 'participants/participant_confirm_delete.html'
    success_url = reverse_lazy('participants:list')

    def form_valid(self, form):
        participant = self.get_object()
        if hasattr(participant, 'omr_submission'):
            messages.error(self.request, f"Cannot delete '{participant.roll_number}' because an OMR sheet has already been uploaded.")
            return redirect('participants:list')
            
        messages.success(self.request, f"Participant '{participant.roll_number}' deleted successfully.")
        return super().form_valid(form)
