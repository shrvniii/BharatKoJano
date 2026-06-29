from django.conf import settings

def competition_info(request):
    return {
        'COMPETITION_NAME': 'QuizMaster OMR System',
        'CURRENT_YEAR': 2026,
    }
