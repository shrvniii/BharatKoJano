from django.urls import path
from .views import (
    OMRUploadView, 
    OMRSubmissionDeleteView,
    OMRDuplicateWarningView,
    OMROverrideDuplicateView
)

app_name = 'scanner'

urlpatterns = [
    path('upload/', OMRUploadView.as_view(), name='upload'),
    path('delete/<int:pk>/', OMRSubmissionDeleteView.as_view(), name='delete_submission'),
    path('duplicate/<int:pk>/', OMRDuplicateWarningView.as_view(), name='duplicate_warning'),
    path('override-duplicate/<int:new_submission_id>/', OMROverrideDuplicateView.as_view(), name='override_duplicate'),
]
