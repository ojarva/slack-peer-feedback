from django.core.management.base import BaseCommand, CommandError
import datetime
from teams.models import Feedback
from oauth_handlers.models import AuthorizationData
from django.utils import timezone
import datetime
import requests
import slacker


class Command(BaseCommand):
    help = "Send feedbacks"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        for feedback in Feedback.objects.filter(delivered=None).filter(cancelled=False):
            if now - feedback.given > datetime.timedelta(minutes=8):
                authorization_data = AuthorizationData.objects.get(team_id=feedback.recipient.slack_team.team_id)
                slack = slacker.Slacker(authorization_data.bot_access_token)
                title = None
                if not feedback.anonymous:
                    title = "Feedback from %s (%s)" % (feedback.sender.real_name, feedback.sender.name)
                slack.chat.post_message(feedback.recipient.user_id, "You have new feedback", attachments=[
                    {
                        "title": title,
                        "text": feedback.feedback
                    }
                ])
                feedback.delivered = now
                feedback.save()

                if feedback.response_url:
                    requests.post(feedback.response_url, json={"replace_original": True, "response_type": "ephemeral", "text": "Your feedback has been delivered."})
