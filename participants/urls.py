from django.urls import path
from .views import (
    ParticipantListView, 
    ParticipantUpdateView, 
    ParticipantDeleteView,
    ParticipantImportView,
    DownloadSampleCSVView
)

app_name = 'participants'

urlpatterns = [
    path('', ParticipantListView.as_view(), name='list'),
    path('edit/<int:pk>/', ParticipantUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', ParticipantDeleteView.as_view(), name='delete'),
    path('import/', ParticipantImportView.as_view(), name='import'),
    path('download-sample-csv/', DownloadSampleCSVView.as_view(), name='download_sample_csv'),
]
