# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-14 22:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0006_auto_20170114_2159'),
    ]

    operations = [
        migrations.AddField(
            model_name='slackuser',
            name='image_24',
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
    ]
