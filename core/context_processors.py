from django.conf import settings

def competition_info(request):
    return {
        'COMPETITION_NAME': 'BKJ-OMS (Bharat Ko Jano)',
        'CURRENT_YEAR': 2026,
    }
