# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-01-22 16:23
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0015_slackuser_is_restricted'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='feedback',
            options={'ordering': ('-given_at',)},
        ),
        migrations.RenameField(
            model_name='feedback',
            old_name='delivered',
            new_name='delivered_at',
        ),
        migrations.RenameField(
            model_name='feedback',
            old_name='given',
            new_name='given_at',
        ),
    ]