import json
import re

import dj_database_url
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.utils import ConnectionHandler

from promgen import models

# Attemps to match the pattern name="value" for Prometheus labels and annotations
RULE_MATCH = re.compile('((?P<key>\w+)\s*=\s*\"(?P<value>.*?)\")')


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]


def convert_to_json(value):
    if value == '':
        return '{}'

    converted = {}
    value = value.strip().strip('{}')
    for match, key, value in RULE_MATCH.findall(value):
        converted[key] = value
    return json.dumps(converted, ensure_ascii=False)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('db')

    def handle(self, db, **kwargs):
        settings.DATABASES['promgen'] = dj_database_url.parse(db)
        connections = ConnectionHandler(settings.DATABASES)
        with connections['promgen'].cursor() as c:
            services = {}
            c.execute('SELECT * FROM service')
            for row in dictfetchall(c):
                services[row['id']], _ = models.Service.objects.get_or_create(
                    name=row['name']
                )

            projects = {}
            c.execute('SELECT * FROM project')
            for row in dictfetchall(c):
                projects[row['id']], _ = models.Project.objects.get_or_create(
                    name=row['name'],
                    service_id=services[row['service_id']].id
                )
                if row['mail_address']:
                    models.Sender.objects.get_or_create(
                        project=projects[row['id']],
                        sender='promgen.sender.email',
                        value=row['mail_address'],
                    )
                if row['hipchat_channel']:
                    models.Sender.objects.get_or_create(
                        project=projects[row['id']],
                        sender='promgen.sender.ikasan',
                        value=row['hipchat_channel'],
                    )
                if row['line_notify_access_token']:
                    models.Sender.objects.get_or_create(
                        project=projects[row['id']],
                        sender='promgen.sender.linenotify',
                        value=row['line_notify_access_token'],
                        password=True,
                    )

            c.execute('SELECT * FROM rule')
            for row in dictfetchall(c):
                models.Rule.objects.update_or_create(
                    name=row['alert_clause'],
                    service=services[row['service_id']],
                    defaults={
                        'duration': row['for_clause'],
                        'clause': row['if_clause'],
                        'labels': convert_to_json(row['labels_clause'].strip()),
                        'annotations': convert_to_json(row['annotations_clause'].strip()),
                    }
                )
