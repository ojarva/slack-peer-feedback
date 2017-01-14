from __future__ import unicode_literals

from django.db import models

class AuthorizationData(models.Model):
    team_id = models.CharField(max_length=30, primary_key=True)

    user_id = models.CharField(max_length=30)
    access_token = models.CharField(max_length=150)
    bot_access_token = models.CharField(max_length=150)
    bot_user_id = models.CharField(max_length=30)
    incoming_webhook_url = models.CharField(max_length=250)
    incoming_webhook_channel_id = models.CharField(max_length=30)
    incoming_webhook_channel = models.CharField(max_length=250)
    incoming_webhook_configuration_url = models.CharField(max_length=250)
    scopes = models.CharField(max_length=150)
    team_name = models.CharField(max_length=150)
