# Generated by Django 2.2.8 on 2020-02-21 06:03

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('promgen', '0015_internal'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlertLabel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
                ('value', models.CharField(max_length=128)),
                ('alert', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='promgen.Alert')),
            ],
        ),
    ]
