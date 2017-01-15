from django.shortcuts import render
from django.conf import settings
import json
import pprint
import uuid
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.exceptions import PermissionDenied
import re
from teams.models import Feedback, SlackUser
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from teams.utils import update_user


def parse_new_feedback_input(text):
    user_re = re.compile(r"^(<@(?P<user_id>[A-Za-z0-9]+)\|(?P<user_name>[A-Za-z0-9-_]+)>)(?P<feedback>.*)")
    recipients = []
    feedback = text
    while True:
        match = user_re.match(feedback)
        if match:
            recipients.append((match.group("user_id"), match.group("user_name")))
            text = text.replace(match.group(1), "")
            feedback = match.group("feedback").strip()
        else:
            break
    return recipients, feedback


@csrf_exempt
def incoming_slack_event(request):
    data = json.loads(request.body)

    if not isinstance(data, dict):
        return HttpResponseBadRequest("Expected application/json body, got something else.")

    if data.get("token") != settings.VERIFICATION_TOKEN:
        raise PermissionDenied
    event_type = data.get("type")
    if event_type == "url_verification":
        return HttpResponse(json.dumps({"challenge": data.get("challenge")}), content_type="application/json")
    if event_type == "event_callback":
        event = data.get("event")
        if event["type"] == "user_change":
            user = event["user"]
            update_user(user)
        return HttpResponse()


@csrf_exempt
def peer_feedback_handler(request):
    pprint.pprint(request.POST)
    if request.POST.get("token") != settings.VERIFICATION_TOKEN:
        raise PermissionDenied

    feedback_sender = SlackUser.objects.get(user_id=request.POST.get("user_id"))

    text = request.POST.get("text")
    if text == "list":
        feedbacks = Feedback.objects.filter(recipient=feedback_sender).filter(cancelled=False).exclude(delivered=None).order_by("delivered")[:20]
        attachments = []
        for feedback in feedbacks:
            attachments.append({
                "text": feedback.feedback,
                "author_name": feedback.get_author_name(),
                "author_icon": feedback.get_author_icon(),
            })
        return HttpResponse(json.dumps({"attachments": attachments, "response_type": "ephemeral"}), content_type="application/json")

    recipients, feedback = parse_new_feedback_input(text)
    if len(text) > 0 and len(recipients) == 0:
        return HttpResponse(json.dumps({"text": """Hmm, I couldn't parse the feedback. Use any of these:
`/peer_feedback @username Your feedback` - directly sends anonymous feedback
`/peer_feedback @username` - gives a link for more complex feedback
`/peer_feedback` - gives options for giving more complex feedback for anyone
`/peer_feedback list` - shows recent feedback you have received.""", "response_type": "ephemeral"}), content_type="application/json")

    callback_id = None
    feedback_group_id = uuid.uuid4()
    if len(recipients) > 1:
        callback_id = "group-" + str(feedback_group_id)

    for recipient in recipients:
        slack_user = SlackUser.objects.get(user_id=recipient[0])
        user_feedback = Feedback(recipient=slack_user, sender=feedback_sender, feedback=feedback, feedback_group_id=feedback_group_id, response_url=request.POST.get("response_url"))
        user_feedback.save()
        if not callback_id:
            callback_id = "item-" + str(user_feedback.feedback_id)

    if len(recipients) == 1:
        recipients_text = "one recipient"
    else:
        recipients_text = "%s recipients"
    if len(feedback) > 0 and len(recipients) > 0:
        return HttpResponse(json.dumps({"text": "Got it. Your feedback will be delivered anonymously to %s" % recipients_text, "attachments": [{
            "text": "%s\n\nThis feedback will be delivered anonymously to %s. Do you want to take any other actions?" % (feedback, recipients_text),
            "fallback": "Edit your feedback.",
            "callback_id": callback_id,
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [
                {
                    "name": "add_name",
                    "text": "Add my name",
                    "type": "button",
					"style": "danger",
                    "value": "add_name",
					"confirm": {
                        "title": "Are you sure?",
                        "text": "Do you want to convert this anonymous feedback to non-anonymous?",
                        "ok_text": "Yes",
                        "dismiss_text": "No"
                    }
				},
                {
                    "name": "cancel",
                    "text": "Cancel this feedback",
					"style": "danger",
                    "type": "button",
                    "value": "maze"
                },
                {
                    "name": "done",
                    "text": "I'm done with this",
                    "style": "primary",
                    "type": "button",
                    "value": "done"
                }
            ]
        }]}), content_type="application/json")
