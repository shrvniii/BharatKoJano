from django.urls import path
from .views import SchoolListView, SchoolCreateView, SchoolUpdateView, SchoolDeleteView

app_name = 'schools'

urlpatterns = [
    path('', SchoolListView.as_view(), name='list'),
    path('add/', SchoolCreateView.as_view(), name='add'),
    path('edit/<int:pk>/', SchoolUpdateView.as_view(), name='edit'),
    path('delete/<int:pk>/', SchoolDeleteView.as_view(), name='delete'),
]
