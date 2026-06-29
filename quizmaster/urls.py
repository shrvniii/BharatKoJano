from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('dashboard:home')), # Redirect root URL to dashboard
    path('accounts/', include('accounts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('schools/', include('schools.urls')),
    path('participants/', include('participants.urls')),
    path('answer-keys/', include('answer_keys.urls')),
    path('scanner/', include('scanner.urls')),
    path('results/', include('results.urls')),
    path('reports/', include('reports.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
