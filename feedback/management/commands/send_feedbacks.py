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
                author_name = "Anonymous colleague"
                if not feedback.anonymous:
                    author_name = "%s (@%s)" % (feedback.sender.real_name, feedback.sender.name)
                    if feedback.sender.image_24:
                        author_icon = feedback.sender.image_24

                slack.chat.post_message(feedback.recipient.user_id, "You have new feedback", attachments=[
                    {
                        "author_name": author_name,
                        "author_icon": author_icon,
                        "text": feedback.feedback,
                        "fallback": "Respond to your feedback.",
                        "callback_id": "reply-%s" % feedback.feedback_id,
                        "color": "#3AA3E3",
                        "attachment_type": "default",
                        "actions": [
                            {
                                "name": "flag_helpful",
                                "text": "Send thanks",
                                "type": "button",
                                "value": "flag_helpful"
                            },
                            {
                                "name": "didnt_understand",
                                "text": "Didn't understand",
                                "type": "button",
                                "value": "didnt_understand"
                            },
                            {
                                "name": "feedback_received",
                                "text": "Ok, thanks.",
                                "type": "button",
                                "value": "feedback_received"
                            }
                        ]
                    }
                ])
                feedback.delivered = now
                feedback.save()

                if feedback.response_url:
                    requests.post(feedback.response_url, json={"replace_original": True, "response_type": "ephemeral", "text": "Your feedback has been delivered."})
