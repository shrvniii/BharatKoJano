from django.urls import path
from .views import (
    ParticipantListView, 
    ParticipantCreateView, 
    ParticipantUpdateView, 
    ParticipantDeleteView,
    ParticipantImportView,
    DownloadSampleCSVView
)

app_name = 'participants'

urlpatterns = [
    path('', ParticipantListView.as_view(), name='list'),
    path('add/', ParticipantCreateView.as_view(), name='add'),
    path('edit/<int:pk>/', ParticipantUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', ParticipantDeleteView.as_view(), name='delete'),
    path('import/', ParticipantImportView.as_view(), name='import'),
    path('sample-csv/', DownloadSampleCSVView.as_view(), name='sample_csv'),
]
