# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-14 20:51
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0003_auto_20170114_2001'),
    ]

    operations = [
        migrations.AddField(
            model_name='feedback',
            name='response_url',
            field=models.CharField(blank=True, max_length=1024, null=True),
        ),
    ]
