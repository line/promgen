# Generated by Django 3.2.4 on 2021-07-06 06:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('promgen', '0020_fix_exporter_constraints'),
    ]

    operations = [
        migrations.AddField(
            model_name='shard',
            name='samples',
            field=models.PositiveBigIntegerField(default=5000000, help_text='Estimated Sample Count'),
        ),
        migrations.AddField(
            model_name='shard',
            name='targets',
            field=models.PositiveBigIntegerField(default=10000, help_text='Estimated Target Count'),
        ),
    ]
