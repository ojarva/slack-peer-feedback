from __future__ import unicode_literals

from django.conf import settings
from django.db import models
import uuid
from django.core.urlresolvers import reverse
from django.utils import timezone
from oauth_handlers.models import AuthorizationData
import slacker
import random


class Team(models.Model):
    name = models.CharField(max_length=50)
    slack_team = models.ForeignKey("SlackTeam")
    owner = models.ForeignKey("SlackUser")

    class Meta:
        unique_together = (("name", "slack_team"), )

    def __str__(self):
        return f"{self.name} (@{self.owner.name})"

class SlackTeam(models.Model):
    team_id = models.CharField(max_length=50)
    team_name = models.CharField(max_length=50)

    def __str__(self):
        return self.team_name

class SlackUser(models.Model):
    PUBLIC_ATTRIBUTES = ("name", "real_name", "tz", "user_id", "image_192", "image_24")
    is_admin = models.BooleanField(blank=True)
    is_bot = models.BooleanField(blank=True, default=False)
    is_restricted = models.BooleanField(blank=True, default=False)
    deleted = models.BooleanField(blank=True, default=False)
    name = models.CharField(max_length=50)
    real_name = models.CharField(max_length=500, null=True, blank=True)
    first_name = models.CharField(max_length=250, null=True, blank=True)
    last_name = models.CharField(max_length=250, null=True, blank=True)
    slack_team = models.ForeignKey("SlackTeam")
    tz = models.CharField(max_length=50, null=True, blank=True)
    tz_offset = models.IntegerField(null=True)
    user_id = models.CharField(primary_key=True, max_length=50, editable=False)
    email = models.CharField(max_length=255, null=True, blank=True)
    image_192 = models.CharField(max_length=1024, null=True, blank=True)
    image_24 = models.CharField(max_length=1024, null=True, blank=True)

    show_slash_prompt_hint = models.BooleanField(blank=True, default=False)

    def __str__(self):
        return f"{self.real_name} (@{self.name})"

    def to_public_json(self):
        data = {}
        for attr in self.PUBLIC_ATTRIBUTES:
            data[attr] = getattr(self, attr)
        return data

    def get_full_name(self):
        return f"{self.real_name} (@{self.name})"

    class Meta:
        ordering = (("real_name", "name"))

class TeamMember(models.Model):
    team = models.ForeignKey("Team")
    user = models.ForeignKey("SlackUser")

    can_see_feedbacks = models.BooleanField(blank=True, default=False)
    active = models.BooleanField(blank=True, default=True)

    def __str__(self):
        return f"@{self.user} in {self.team}"


class Feedback(models.Model):
    feedback_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feedback_group_id = models.UUIDField(default=uuid.uuid4, editable=False)

    cancelled = models.BooleanField(default=False, blank=True)

    recipient = models.ForeignKey("SlackUser", related_name="recipient_user")
    recipient_team = models.ForeignKey("Team", null=True, blank=True)

    sender = models.ForeignKey("SlackUser", related_name="sender_user")
    anonymous = models.BooleanField(blank=True, default=True)

    question = models.CharField(max_length=250, null=True, blank=True)
    feedback = models.TextField()

    reply_to = models.ForeignKey("Feedback", null=True, blank=True, related_name="feedback_response")

    given_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    flagged_helpful = models.BooleanField(blank=True, default=False)
    flagged_difficult_to_understand = models.BooleanField(blank=True, default=False)

    response_url = models.CharField(max_length=1024, null=True, blank=True)
    response_url_valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-given_at", )

    def __str__(self):
        return f"Feedback for {self.recipient} by {self.get_author_name()}"

    def get_replies_count(self):
        return Feedback.objects.filter(feedback_id=self.reply_to).count()

    def get_author_name(self):
        if self.anonymous:
            return "Anonymous colleague"
        return f"{self.sender.real_name} (@{self.sender.name})"

    def get_author_icon(self):
        if self.anonymous:
            return None
        return self.sender.image_24

    def get_feedback_url(self):
        if self.reply_to:
            parent_feedback = self.reply_to
        else:
            parent_feedback = self
        return "%s%s" % (settings.WEB_ROOT, reverse("single_feedback", args=(parent_feedback.feedback_id,)).strip("/"))


    def get_slack_notification(self):
        pre_text = ""
        if self.reply_to:
            pre_text = "%s replied to your feedback:\n" % self.get_author_name()
        feedback_url = self.get_feedback_url()

        return {
            "author_name": self.get_author_name(),
            "author_icon": self.get_author_icon(),
            "text": "%s%s\n\n<%s|View or reply to feedback>" % (pre_text, self.feedback, feedback_url),
            "fallback": "Respond to your feedback.",
            "callback_id": "reply-%s" % self.feedback_id,
            "color": "#3AA3E3",
            "mrkdwn_in": ["text", "fields"],
            "attachment_type": "default",
            "actions": [
                {
                    "name": "flag_helpful",
                    "text": "Send thanks :heart:",
                    "type": "button",
                    "value": "flag_helpful"
                },
                {
                    "name": "didnt_understand",
                    "text": "Didn't understand :confused:",
                    "type": "button",
                    "value": "didnt_understand"
                },
                {
                    "name": "feedback_received",
                    "text": "Ok, dismiss. :ok_hand:",
                    "type": "button",
                    "value": "feedback_received"
                }
            ]
        }

    def send_notification(self):
        if self.delivered_at:
            return False
        self.delivered_at = timezone.now()
        self.save()
        authorization_data = AuthorizationData.objects.get(team_id=self.recipient.slack_team.team_id)
        slack = slacker.Slacker(authorization_data.bot_access_token)
        message_text = "You have new feedback"
        icon_emoji = ":blue_heart:"
        if self.reply_to:
            message_text = "You have a reply to your feedback"
            icon_emoji = ":leftwards_arrow_with_hook:"
        if len(settings.ONLY_MESSAGES_TO) == 0 or self.recipient.user_id in settings.ONLY_MESSAGES_TO:
            slack.chat.post_message(self.recipient.user_id, message_text, attachments=[self.get_slack_notification()], icon_emoji=icon_emoji)

    def get_anonymized_recipient_first_name(self):
        if self.anonymous:
            return "Recipient"
        return self.recipient.first_name


class SentQuestion(models.Model):
    sent_question_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feedback_sender = models.ForeignKey("SlackUser", related_name="feedback_sender")
    feedback_receiver = models.ForeignKey("SlackUser", related_name="feedback_receiver")
    question = models.CharField(max_length=250, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    answered_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp for answering to this feedback prompt.")
    dismissed_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp for dismissing this feedback prompt.")
    feedback = models.ForeignKey("Feedback", null=True)

    def __str__(self):
        return f"{self.feedback_sender} to {self.feedback_receiver} at {self.sent_at}"

    class Meta:
        ordering = ("-sent_at",)

    def get_random_prompt(self):
        return random.choice(("Could you give feedback to",
                              "Please give feedback to",
                              "You can help"))

class FeedbackQuestion(models.Model):
    question_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question_text = models.CharField(max_length=250)

    generic_question = models.BooleanField(default=True)
    team_question = models.BooleanField(default=False)

    team = models.ForeignKey("Team", null=True, blank=True)

    def __str__(self):
        return self.question_text
