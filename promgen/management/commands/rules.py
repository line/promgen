import logging

from django.core.management.base import BaseCommand

from promgen import models
from promgen import prometheus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, **kwargs):
        prometheus.check_rules(models.Rule.objects.all())
        print(prometheus.render_rules())
