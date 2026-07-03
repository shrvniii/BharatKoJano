from django.urls import path
from .views import (
    ParticipantListView, 
    ParticipantUpdateView, 
    ParticipantDeleteView
)

app_name = 'participants'

urlpatterns = [
    path('', ParticipantListView.as_view(), name='list'),
    path('edit/<int:pk>/', ParticipantUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', ParticipantDeleteView.as_view(), name='delete'),
]
