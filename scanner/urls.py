from django.urls import path
from .views import (
    OMRUploadView, 
    OMRSubmissionDeleteView,
    OMRDuplicateWarningView,
    OMROverrideDuplicateView,
    SetEvaluatorView,
    OMRConfirmResultView,
    OMRAcceptResultView,
    OMRRescanDeleteView
)

app_name = 'scanner'

urlpatterns = [
    path('upload/', OMRUploadView.as_view(), name='upload'),
    path('delete/<int:pk>/', OMRSubmissionDeleteView.as_view(), name='delete_submission'),
    path('duplicate/<int:pk>/', OMRDuplicateWarningView.as_view(), name='duplicate_warning'),
    path('override-duplicate/<int:new_submission_id>/', OMROverrideDuplicateView.as_view(), name='override_duplicate'),
    path('set-evaluator/', SetEvaluatorView.as_view(), name='set_evaluator'),
    path('confirm/<int:pk>/', OMRConfirmResultView.as_view(), name='confirm_result'),
    path('accept/<int:pk>/', OMRAcceptResultView.as_view(), name='accept_result'),
    path('rescan-delete/<int:pk>/', OMRRescanDeleteView.as_view(), name='rescan_delete'),
]
