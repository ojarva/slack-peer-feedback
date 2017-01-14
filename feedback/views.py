from django.shortcuts import render
import pprint
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.exceptions import PermissionDenied
from teams.models import SlackUser, Feedback
import json

@csrf_exempt
def receive_interactive_command(request):
    pprint.pprint(request.POST)
    payload_data = request.POST.get("payload", [])
    action = json.loads(payload_data)
    if action["token"] != settings.VERIFICATION_TOKEN:
        raise PermissionDenied
    callback_id = action["callback_id"]
    if callback_id.startswith("group-"):
        feedback = Feedback.objects.filter(feedback_group_id=callback_id.replace("group-", ""))
    else:
        feedback = Feedback.objects.filter(feedback_id=callback_id.replace("item-", ""))
    feedback.update(response_url=action["response_url"])
    requested_action = action["actions"][0]["name"]
    response = {"replace_original": True, "response_type": "ephemeral"}
    if requested_action == "add_name":
        feedback.update(anonymous=False)
        response["attachments"] = [{
            "fallback": "Sorry, can't - something went wrong.",
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
            "fallback": "Sorry, can't - something went wrong.",
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
            "fallback": "Sorry, can't - something went wrong.",
            "callback_id": callback_id,
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": actions,
        }]
    elif requested_action == "done":
        response["text"] = "Ok, thanks!"
    return HttpResponse(json.dumps(response), content_type="application/json")
