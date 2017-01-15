from django.shortcuts import render
import pprint
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.exceptions import PermissionDenied
from teams.models import SlackUser, Feedback
import json
from utils import verify_arguments, get_random_question, get_random_recipient
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import re
import uuid



def dashboard(request):
    if not request.session.get("user_id") or request.session.get("authenticated_by") != "slack_login":
        return HttpResponseRedirect(reverse("login"))
    slack_user = SlackUser.objects.get(user_id=request.session.get("user_id"))
    feedbacks = Feedback.objects.filter(recipient=slack_user).filter(cancelled=False).exclude(delivered=None)
    context = {
        "slack_user": slack_user,
        "feedbacks": feedbacks,
    }
    return render(request, "dashboard.html", context)


def leave_new_feedback_page(request, **kwargs):
    token = request.GET.get("token")
    context = {}
    if token:
        if not verify_arguments(dict(request.GET.iteritems()), token):
            raise PermissionDenied
        expires_at = parse_datetime(request.GET.get("expires_at"))
        if expires_at < timezone.now():
            raise PermissionDenied

        if "user_id" not in request.session:
            request.session["user_id"] = request.GET.get("sender_id")
            request.session["team_id"] = request.GET.get("sender_team_id")
            request.session["authenticated_by"] = "link_auth"
        context["expires_at"] = expires_at
        recipient_ids = request.GET.get("recipients", "")
        context["recipients"] = SlackUser.objects.filter(user_id__in=recipient_ids.split(","))
        context["recipient_ids"] = recipient_ids

    if not request.session.get("user_id") or not request.session.get("team_id"):
        return HttpResponseRedirect(reverse("login"))

    sender = SlackUser.objects.get(user_id=request.session.get("user_id"))
    context["sender"] = sender

    if request.method == "POST":
        recipient_ids = request.POST.get("recipient_ids")
        if recipient_ids:
            recipients = recipient_ids.split(",")
            recipients = SlackUser.objects.filter(user_id__in=recipient_ids)
        else:
            recipients = request.POST.get("recipient")
            print recipients
            components = re.match(r"^(?P<real_name>(.*)) \(@(?P<name>([A-Za-z0-9-_]+))\)$", recipients)
            if not components:
                return HttpResponseBadRequest("Invalid recipient data")
            recipients = SlackUser.objects.filter(name=components.group("name")).filter(real_name=components.group("real_name"))
            if len(recipients) == 0:
                return HttpResponseBadRequest("No recipients found")

        feedback_group_id = uuid.uuid4()
        for recipient in recipients:
            feedback = Feedback(feedback_group_id=feedback_group_id, recipient=recipient, sender=sender, feedback=request.POST.get("feedback_text"))
            feedback.save()
        return HttpResponseRedirect(reverse("feedback_received"))

    if kwargs.get("random"):
        context["question"] = get_random_question()
        context["recipients"] = [get_random_recipient(request.session.get("team_id"))]
        context["recipient_ids"] = ",".join(map(lambda k: k.user_id, context["recipients"]))
    return render(request, "new_feedback.html", context)


def feedback_received(request):
    context = {}
    return render(request, "feedback_received.html", context)


@csrf_exempt
def receive_interactive_command(request):
    pprint.pprint(request.POST)
    payload_data = request.POST.get("payload", {})
    action = json.loads(payload_data)
    if action["token"] != settings.VERIFICATION_TOKEN:
        raise PermissionDenied
    callback_id = action["callback_id"]

    if callback_id.startswith("reply-"):
        feedback = Feedback.objects.filter(feedback_id=callback_id.replace("reply-", ""))
    elif callback_id.startswith("feedback-hint"):
        pass
    else:
        if callback_id.startswith("group-"):
            feedback = Feedback.objects.filter(feedback_group_id=callback_id.replace("group-", ""))
        elif callback_id.startswith("item-"):
            feedback = Feedback.objects.filter(feedback_id=callback_id.replace("item-", ""))
        feedback.update(response_url=action["response_url"])

    requested_action = action["actions"][0]["name"]
    response = {"replace_original": True, "response_type": "ephemeral"}
    if requested_action == "do_not_show_slash_hint":
        SlackUser.objects.filter(user_id=payload_data["user"]["id"]).update(show_slash_prompt_hint=False)
        response["text"] = "You won't see this hint again."
    elif requested_action == "flag_helpful":
        feedback.update(flagged_helpful=True)
        response["text"] = "Ok, thanks! This information will be available for the person who gave the feedback to you."
    elif requested_action == "didnt_understand":
        feedback.update(flagged_difficult_to_understand=True)
        response["text"] = "Ok, thanks for the information! This will be available for the person who gave the feedback for you - hopefully they will clarify what they meant."
    elif requested_action == "feedback_received":
        response["text"] = "You can view feedbacks you have received with /peer_feedback list"
    elif requested_action == "add_name":
        feedback.update(anonymous=False)
        response["attachments"] = [{
            "fallback": "Edit your feedback.",
            "callback_id": callback_id,
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [
                {
                    "name": "cancel",
                    "text": "Cancel this feedback",
                    "style": "danger",
                    "type": "button",
                    "value": "cancel"
                },
                {
                    "name": "done",
                    "text": "I'm done with this",
                    "style": "primary",
                    "type": "button",
                    "value": "done"
                }
            ]
        }]
    elif requested_action == "cancel":
        feedback.update(cancelled=True)
        response["text"] = "Ok, your feedback has been cancelled."
        response["attachments"] = [{
            "fallback": "Edit your feedback.",
            "callback_id": callback_id,
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [{
                "name": "undo_cancel",
                "text": "Undo - show this feedback",
                "type": "button",
                "value": "undo_cancel",
            }],
        }]

    elif requested_action == "undo_cancel":
        feedback.update(cancelled=False)
        response["text"] = "Ok, undo done - feedback will be delivered soon."
        actions = [
            {
                "name": "cancel",
                "text": "Cancel this feedback",
                "style": "danger",
                "type": "button",
                "value": "cancel"
            },
            {
                "name": "done",
                "text": "I'm done with this",
                "style": "primary",
                "type": "button",
                "value": "done"
        }]
        if feedback[0].anonymous:
            actions.append({
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
            })
        response["attachments"] = [{
            "fallback": "Edit your feedback.",
            "callback_id": callback_id,
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": actions,
        }]
    elif requested_action == "done":
        response["text"] = "Ok, thanks!"
    return HttpResponse(json.dumps(response), content_type="application/json")
