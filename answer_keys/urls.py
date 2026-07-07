from django.urls import path
from .views import AnswerKeyStatusView, AnswerKeyConfigureView, AnswerKeyUnlockView

app_name = 'answer_keys'

urlpatterns = [
    path('', AnswerKeyStatusView.as_view(), name='status'),
    path('configure/<str:group>/<str:paper_set>/', AnswerKeyConfigureView.as_view(), name='configure'),
    path('unlock/', AnswerKeyUnlockView.as_view(), name='unlock'),
]

