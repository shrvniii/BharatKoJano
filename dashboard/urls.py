from django.urls import path
from .views import DashboardView, SettingsView, ResetDataView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='home'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('settings/reset/', ResetDataView.as_view(), name='reset_data'),
]
