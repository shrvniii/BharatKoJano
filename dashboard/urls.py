from django.urls import path
from .views import DashboardView, SettingsView, ResetDataView, AboutView

app_name = 'dashboard'

urlpatterns = [
    path('', DashboardView.as_view(), name='home'),
    path('about/', AboutView.as_view(), name='about'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('settings/reset/', ResetDataView.as_view(), name='reset_data'),
]
