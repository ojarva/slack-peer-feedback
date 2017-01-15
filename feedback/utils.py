import teams.models
import oauth_handlers.models
import slacker
import hashlib
from django.conf import settings
from django.utils import timezone
import datetime
import urllib


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
        u"recipients": u",".join(map(lambda k: k[0], recipients)),
        u"expires_at": unicode(timezone.now() + datetime.timedelta(hours=2)),
    }
    args["token"] = hash_arguments(args)

    return "%snew_feedback?%s" % (settings.WEB_ROOT, urllib.urlencode(args))
