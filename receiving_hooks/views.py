from django.shortcuts import render
from django.conf import settings
import json
import uuid
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.exceptions import PermissionDenied
import re
from teams.models import Feedback, SlackUser
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from teams.utils import update_user
from feedback.utils import get_new_feedback_url


def parse_new_feedback_input(text):
    user_re = re.compile(r"^(<@(?P<user_id>[A-Za-z0-9]+)\|(?P<user_name>[A-Za-z0-9-_\.]+)>)(?P<feedback>.*)$", re.DOTALL)
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


def get_help_text():
    return """Use any of these:
`/peer_feedback @username Your feedback` - directly sends anonymous feedback :star:
`/peer_feedback @username` - link to feedback form with specific user :link:
`/peer_feedback` - link to feedback form :link:
`/peer_feedback list` - shows recent feedback you have received :book:."""


@csrf_exempt
def peer_feedback_handler(request):
    if request.POST.get("token") != settings.VERIFICATION_TOKEN:
        raise PermissionDenied

    feedback_sender = SlackUser.objects.get(user_id=request.POST.get("user_id"))
    if feedback_sender.show_slash_prompt_hint:
        feedback_sender.show_slash_prompt_hint = False
        feedback_sender.save()

    text = request.POST.get("text").strip()
    if text == "list":
        feedbacks = Feedback.objects.filter(recipient=feedback_sender).filter(reply_to=None).filter(cancelled=False).exclude(delivered_at=None).order_by("delivered_at")[:20]
        attachments = []
        for feedback in feedbacks:
            attachments.append({
                "text": """%s\n\n<%s|View or reply>""" % (feedback.feedback, feedback.get_feedback_url()),
                "author_name": feedback.get_author_name(),
                "author_icon": feedback.get_author_icon(),
                "mrkdwn_in": ["text"],
            })
        feedback_list_text = None
        if len(attachments) == 0:
            feedback_list_text = "You don't have any feedback - yet."
        response = {"attachments": attachments, "text": feedback_list_text, "response_type": "ephemeral", "icon_emoji": ":book:"}
        return HttpResponse(json.dumps(response), content_type="application/json")
    if text == "list sent":
        feedbacks = Feedback.objects.filter(sender=feedback_sender).filter(reply_to=None).order_by("given_at")[:20]
        attachments = []
        for feedback in feedbacks:
            attachments.append({
                "text": """%s\n\nTo %s. <%s|View or reply>""" % (feedback.feedback, feedback.recipient, feedback.get_feedback_url()),
                "author_name": feedback.get_author_name(),
                "author_icon": feedback.get_author_icon(),
                "mrkdwn_in": ["text"],
            })
        feedback_list_text = None
        if len(attachments) == 0:
            feedback_list_text = "You haven't sent any feedback - yet :unamused:. Check out `/peer_feedback help` to get started."
        response = {"attachments": attachments, "text": feedback_list_text, "response_type": "ephemeral", "icon_emoji": ":book:"}
        return HttpResponse(json.dumps(response), content_type="application/json")

    if text == "help" or text == "commands":
        return HttpResponse(json.dumps({"text": get_help_text(), "response_type": "ephemeral", "mrkdwn_in": ["text"]}), content_type="application/json")

    recipients, feedback = parse_new_feedback_input(text)
    if len(text) > 0 and len(recipients) == 0:
        return HttpResponse(json.dumps({"text": "Hmm, I couldn't parse the feedback :tired_face:.\n\n" + get_help_text(), "response_type": "ephemeral", "mrkdwn_in": ["text"]}), content_type="application/json")

    callback_id = None
    feedback_group_id = uuid.uuid4()
    if len(recipients) > 1:
        callback_id = "group-" + str(feedback_group_id)

    if len(recipients) == 1:
        recipients_text = "one recipient"
    else:
        recipients_text = "%s recipients"

    if len(feedback) == 0 and len(recipients) > 0:
        return HttpResponse(json.dumps({"text": "Got it :+1:. <%s|Send feedback to %s>. This link is valid for 2 hours." % (get_new_feedback_url(feedback_sender, recipients), ", ".join(map(lambda k: "@" + k[1], recipients))), "icon_emoji": ":white_check_mark:"}), content_type="application/json")
    if len(text) == 0:
        return HttpResponse(json.dumps({"text": "<%s|Send feedback>. This link is valid for 2 hours." % (get_new_feedback_url(feedback_sender, [])), "icon_emoji": ":white_check_mark:"}), content_type="application/json")


    for recipient in recipients:
        slack_user = SlackUser.objects.get(user_id=recipient[0])
        user_feedback = Feedback(recipient=slack_user, sender=feedback_sender, feedback=feedback, feedback_group_id=feedback_group_id, response_url=request.POST.get("response_url"))
        user_feedback.save()
        if not callback_id:  # TODO: this is not compatible with giving feedback to multiple users at once.
            callback_id = "item-" + str(user_feedback.feedback_id)

    if len(feedback) > 0 and len(recipients) > 0:
        return HttpResponse(json.dumps({"text": "Got it. Your feedback will be delivered anonymously to %s" % recipients_text, "icon_emoji": ":white_check_mark:", "attachments": [{
            "text": "%s\n\nThis feedback will be delivered anonymously to %s :+1:. Do you want to take any other actions? You can also <%s|view or reply to this feedback>" % (feedback, recipients_text, user_feedback.get_feedback_url()),  # TODO: this is not compatible with giving feedback to multiple users at once.
            "fallback": "Edit your feedback.",
            "callback_id": callback_id,
            "color": "#3AA3E3",
            "attachment_type": "default",
            "mrkdwn_in": ["text", "fields"],
            "actions": [
                {
                    "name": "add_name",
                    "text": ":warning: Add my name",
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
                    "text": ":speak_no_evil: Cancel this feedback",
					"style": "danger",
                    "type": "button",
                    "value": "cancel"
                },
                {
                    "name": "done",
                    "text": ":wave: I'm done with this",
                    "style": "primary",
                    "type": "button",
                    "value": "done"
                }
            ]
        }]}), content_type="application/json")
