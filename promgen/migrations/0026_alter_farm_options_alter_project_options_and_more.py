# Generated by Django 4.2.11 on 2025-04-15 06:58

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("promgen", "0025_farm_owner"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="farm",
            options={"default_permissions": ("manage", "edit", "view"), "ordering": ["name"]},
        ),
        migrations.AlterModelOptions(
            name="project",
            options={"default_permissions": ("manage", "edit", "view"), "ordering": ["name"]},
        ),
        migrations.AlterModelOptions(
            name="service",
            options={"default_permissions": ("manage", "edit", "view"), "ordering": ["name"]},
        ),
    ]
