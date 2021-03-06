from django.core.management.base import BaseCommand, CommandError
import datetime
from teams.models import Feedback
from oauth_handlers.models import AuthorizationData
from django.utils import timezone
from django.core.urlresolvers import reverse
from django.conf import settings
import datetime
import requests
import slacker
import uuid


class Command(BaseCommand):
    help = "Send feedbacks"

    def handle(self, *args, **kwargs):
        now = timezone.now()
        per_recipient_feedbacks = {}

        for feedback in Feedback.objects.filter(delivered_at=None).filter(cancelled=False):
            if now - feedback.given_at > datetime.timedelta(minutes=settings.FEEDBACK_DELAY_MINUTES):
                recipient_id = feedback.recipient.user_id
                if recipient_id not in per_recipient_feedbacks:
                    authorization_data = AuthorizationData.objects.get(team_id=feedback.recipient.slack_team.team_id)
                    per_recipient_feedbacks[recipient_id] = {"recipient": feedback.recipient, "authorization_data": authorization_data, "items": []}
                per_recipient_feedbacks[recipient_id]["items"].append(feedback.get_slack_notification())
                feedback.delivered_at = now
                feedback.save()
                if feedback.response_url:
                    requests.post(feedback.response_url, json={"replace_original": True, "response_type": "ephemeral", "text": "Your feedback has been delivered."})

        for user, user_data in per_recipient_feedbacks.items():
            slack = slacker.Slacker(user_data["authorization_data"].bot_access_token)
            if user_data["recipient"].show_slash_prompt_hint:
                user_data["items"].append({
                    "text": "You can use `/peer_feedback @username Your feedback message` to send anonymous feedback to your colleagues.",
                    "attachment_type": "default",
                    "color": "#D5D5D5",
                    "response_type": "ephemeral",
                    "fallback": "Try /peer_feedback help",
                    "callback_id": "feedback-hint-%s" % uuid.uuid4(),
                    "mrkdwn_in": ["text"],
                    "actions": [
                        {
                            "name": "do_not_show_slash_hint",
                            "text": "Got it",
                            "type": "button",
                            "value": "do_not_show_slash_hint"
                        }
                    ],
                })
                print "Add hint prompt to %s" % user

            if len(settings.ONLY_MESSAGES_TO) == 0 or user in settings.ONLY_MESSAGES_TO:
                print "Sending notification to %s" % user
                slack.chat.post_message(user, "You have new feedback", attachments=user_data["items"], icon_emoji=":blue_heart:")
