import logging
import subprocess
import tempfile

from django.conf import settings
from django.template.loader import render_to_string

from promgen import models

logger = logging.getLogger(__name__)


def check_rules(rules):
    with tempfile.NamedTemporaryFile() as fp:
        logger.debug('Rendering to %s', fp.name)
        fp.write(render_to_string('promgen/rules.txt', {'rules': rules}))
        fp.flush()

        subprocess.check_call([
            settings.PROMGEN['rule_writer']['promtool_path'],
            'check-rules',
            fp.name
        ])


def render_rules():
    return render_to_string('promgen/rules.txt', {'rules': models.Rule.objects.all()})
