from django.conf import settings

from promgen.models import FARM_DEFAULT


def settings_in_view(request):
    return {
        'FARM_DEFAULT': FARM_DEFAULT,
        'EXTERNAL_LINKS': settings.PROMGEN.get('links', {})
    }
