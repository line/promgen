import logging
import subprocess
import tempfile

from django.conf import settings
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from promgen import models

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, **kwargs):
        context = {
            'rules': models.Rule.objects.all()
        }
        with tempfile.NamedTemporaryFile() as fp:
            logger.debug('Rendering to %s', fp.name)
            fp.write(render_to_string('promgen/rules.txt', context))
            fp.flush()

            subprocess.check_call([
                settings.PROMGEN['rule_writer']['promtool_path'],
                'check-rules',
                fp.name
            ])
