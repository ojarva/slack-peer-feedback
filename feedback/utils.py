import teams.models
import oauth_handlers.models
import slacker
import hashlib
from django.conf import settings
from django.utils import timezone
import datetime
import urllib
import random


def hash_arguments(args):
    hash_string = str(sorted(args.items()))
    return hashlib.sha256(hash_string + settings.USER_LINK_SECRET).hexdigest()

def verify_arguments(args, token):
    if "token" in args:
        del args["token"]
    return hash_arguments(args) == token

def get_new_feedback_url(sender, recipients):
    args = {
        u"sender_id": sender.user_id,
        u"sender_team_id": sender.slack_team.team_id,
        u"recipients": u",".join(map(lambda k: k[0], recipients)),
        u"expires_at": unicode(timezone.now() + datetime.timedelta(hours=2)),
    }
    args["token"] = hash_arguments(args)

    return "%snew_feedback?%s" % (settings.WEB_ROOT, urllib.urlencode(args))

def get_random_question():
    return random.choice([
        "How was the last encounter with this person?",
        "Do you know what this person is doing?",
        "Would you like to work with this person? Why and why not?",
        "What is the best thing about this person?",
        "What would you like to learn from this person?",
    ])

def get_random_recipient(team_id):
    slack_team = teams.models.SlackTeam.objects.get(team_id=team_id)
    active_members = teams.models.SlackUser.objects.filter(slack_team=slack_team).filter(deleted=False).filter(is_bot=False)
    return active_members[random.randint(0, len(active_members))]
