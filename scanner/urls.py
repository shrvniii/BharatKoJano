from django.urls import path
from .views import OMRUploadView, OMRSubmissionDeleteView

app_name = 'scanner'

urlpatterns = [
    path('upload/', OMRUploadView.as_view(), name='upload'),
    path('delete/<int:pk>/', OMRSubmissionDeleteView.as_view(), name='delete_submission'),
]
