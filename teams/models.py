from __future__ import unicode_literals

from django.db import models
import uuid

class Team(models.Model):
    name = models.CharField(max_length=50)
    slack_team = models.ForeignKey("SlackTeam")
    owner = models.ForeignKey("SlackUser")

    class Meta:
        unique_together = (("name", "slack_team"), )

    def __unicode__(self):
        return u"%s (@%s)" % (self.name, self.owner.name)

class SlackTeam(models.Model):
    team_id = models.CharField(max_length=50)
    team_name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.team_name

class SlackUser(models.Model):
    PUBLIC_ATTRIBUTES = ("name", "real_name", "tz", "user_id", "image_192", "image_24")
    is_admin = models.BooleanField(blank=True)
    is_bot = models.BooleanField(blank=True, default=False)
    deleted = models.BooleanField(blank=True, default=False)
    name = models.CharField(max_length=50)
    real_name = models.CharField(max_length=50, null=True, blank=True)
    slack_team = models.ForeignKey("SlackTeam")
    tz = models.CharField(max_length=50, null=True, blank=True)
    tz_offset = models.IntegerField(null=True)
    user_id = models.CharField(primary_key=True, max_length=50)
    email = models.CharField(max_length=255, null=True, blank=True)
    image_192 = models.CharField(max_length=1024, null=True, blank=True)
    image_24 = models.CharField(max_length=1024, null=True, blank=True)

    def __unicode__(self):
        return u"%s (@%s)" % (self.real_name, self.name)

    def to_public_json(self):
        data = {}
        for attr in self.PUBLIC_ATTRIBUTES:
            data[attr] = getattr(self, attr)
        return data

    def get_full_name(self):
        return u"%s (@%s)" % (self.real_name, self.name)

    class Meta:
        ordering = (("real_name", "name"))

class TeamMember(models.Model):
    team = models.ForeignKey("Team")
    user = models.ForeignKey("SlackUser")

    can_see_feedbacks = models.BooleanField(blank=True, default=False)

    def __unicode__(self):
        return u"@%s in %s" % (self.user, self.team)


class Feedback(models.Model):
    feedback_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feedback_group_id = models.UUIDField(default=uuid.uuid4, editable=False)

    cancelled = models.BooleanField(default=False, blank=True)

    recipient = models.ForeignKey("SlackUser", related_name="recipient_user")
    recipient_team = models.ForeignKey("Team", null=True, blank=True)

    sender = models.ForeignKey("SlackUser", related_name="sender_user")
    anonymous = models.BooleanField(blank=True, default=True)

    feedback = models.TextField()

    reply_to = models.ForeignKey("Feedback", null=True, blank=True, related_name="feedback_response")

    given = models.DateTimeField(auto_now_add=True)
    delivered = models.DateTimeField(null=True, blank=True)

    flagged_helpful = models.BooleanField(blank=True, default=False)
    flagged_difficult_to_understand = models.BooleanField(blank=True, default=False)

    response_url = models.CharField(max_length=1024, null=True, blank=True)
    response_url_valid_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-given", )

    def __unicode__(self):
        return u"Feedback for %s by %s" % (self.recipient, self.get_author_name())

    def get_author_name(self):
        if self.anonymous:
            return u"Anonymous colleague"
        return u"%s (@%s)" % (self.sender.real_name, self.sender.name)

    def get_author_icon(self):
        if self.anonymous:
            return None
        return self.sender.image_24
