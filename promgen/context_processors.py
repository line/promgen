from django.conf import settings


def settings_in_view(request):
    return {'EXTERNAL_LINKS': settings.PROMGEN.get('links', {})}
