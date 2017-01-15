from django.core.management.base import BaseCommand, CommandError
import datetime
from teams.models import SlackUser
from oauth_handlers.models import AuthorizationData
from django.utils import timezone
import datetime
import requests
import slacker
from teams.utils import refresh_slack_users

class Command(BaseCommand):
    help = "Refresh all members of all teams"

    def handle(self, *args, **kwargs):
        for authorization_data in AuthorizationData.objects.all():
            refresh_slack_users(authorization_data.team_id)
