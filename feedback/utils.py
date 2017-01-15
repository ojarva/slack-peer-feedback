import teams.models
import oauth_handlers.models
import slacker
import hashlib
from django.conf import settings
from django.utils import timezone
import datetime
import urllib


def hash_arguments(args):
    return hashlib.sha256(str(sorted(args.items())) + settings.USER_LINK_SECRET).hexdigest()

def verify_arguments(args, secret):
    return hash_arguments(args) == secret

def get_new_feedback_url(sender, recipients):
    args = {
        "sender_id": sender.user_id,
        "recipients": ",".join(map(lambda k: k[0], recipients)),
        "expires_at": timezone.now() + datetime.timedelta(hours=2),
    }
    args["token"] = hash_arguments(args)

    return "%snew_feedback?%s" % (settings.WEB_ROOT, urllib.urlencode(args))
