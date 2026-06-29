from django.urls import path
from .views import ResultListView, ResultDetailView, RankingsView

app_name = 'results'

urlpatterns = [
    path('', ResultListView.as_view(), name='list'),
    path('detail/<int:pk>/', ResultDetailView.as_view(), name='detail'),
    path('rankings/', RankingsView.as_view(), name='rankings'),
]
