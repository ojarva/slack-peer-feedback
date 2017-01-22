from django.shortcuts import render
import pprint
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden, HttpResponseServerError
from django.core.urlresolvers import reverse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.exceptions import PermissionDenied
from teams.models import SlackUser, Feedback, SentQuestion
from django.template.loader import render_to_string
import json
from utils import verify_arguments, get_random_question, get_random_recipient
from django.utils import timezone
from django.utils.dateparse import parse_datetime
import re
import uuid


def sent_feedback(request):
    if not request.session.get("user_id") or request.session.get("authenticated_by") != "slack_login":
        return HttpResponseRedirect(reverse("login"))
    slack_user = SlackUser.objects.get(user_id=request.session.get("user_id"))
    feedbacks = Feedback.objects.filter(sender=slack_user).filter(cancelled=False).filter(reply_to=None)
    context = {
        "slack_user": slack_user,
        "feedbacks": feedbacks,
    }
    return render(request, "sent_feedback.html", context)


def dismiss_pending_question(request, question_id):
    if not request.session.get("user_id"):
        return HttpResponseRedirect(reverse("login"))
    slack_user = SlackUser.objects.get(user_id=request.session.get("user_id"))
    try:
        question = SentQuestion.objects.filter(feedback_sender=slack_user).get(sent_question_id=question_id)
    except SentQuestion.DoesNotExist:
        return HttpResponseNotFound("Question does not exist.")
    if not question.answered_at:
        question.dismissed_at = timezone.now()
        question.save()
    return HttpResponseRedirect(reverse("dashboard"))


def dashboard(request):
    if not request.session.get("user_id") or request.session.get("authenticated_by") != "slack_login":
        return HttpResponseRedirect(reverse("login"))
    slack_user = SlackUser.objects.get(user_id=request.session.get("user_id"))
    feedbacks = Feedback.objects.filter(recipient=slack_user).filter(cancelled=False).exclude(delivered_at=None).filter(reply_to=None)
    pending_questions = SentQuestion.objects.filter(feedback_sender=slack_user).filter(dismissed_at=None).filter(answered_at=None)
    context = {
        "slack_user": slack_user,
        "feedbacks": feedbacks,
        "pending_questions": pending_questions,
    }
    return render(request, "dashboard.html", context)


def single_feedback(request, feedback_id):
    if not request.session.get("user_id") or request.session.get("authenticated_by") != "slack_login":
        return HttpResponseRedirect(reverse("login"))

    slack_user = SlackUser.objects.get(user_id=request.session.get("user_id"))
    feedback = Feedback.objects.get(feedback_id=feedback_id)
    context = {
        "slack_user": slack_user
    }
    if feedback.reply_to != None:
        return HttpResponseForbidden("You can only access parent feedback with this method. Request was for a reply.")

    if slack_user == feedback.recipient:
        context["anonymous"] = False
    elif slack_user == feedback.sender:
        context["anonymous"] = feedback.anonymous
    else:
        return HttpResponseForbidden("This is not your feedback.")

    if feedback.cancelled and feedback.sender != slack_user:
        return HttpResponseNotFound("Feedback does not exist.")

    if request.method == "POST":
        print request.POST
        if "feedback-action" in request.POST:
            if not feedback.delivered_at:
                if "make_non_anonymous" in request.POST:
                    feedback.anonymous = False
                elif "make_anonymous" in request.POST:
                    feedback.anonymous = True
                elif "cancel" in request.POST:
                    feedback.cancelled = True
                elif "undo_cancel" in request.POST:
                    feedback.cancelled = False
                else:
                    return HttpResponseServerError("Unhandled feedback action")
                feedback.save()
        else:
            feedback_text = request.POST.get("feedback")
            if slack_user == feedback.recipient:
                feedback_recipient = feedback.sender
            else:
                feedback_recipient = feedback.recipient
            feedback_reply = Feedback(feedback=feedback_text, reply_to=feedback, sender=slack_user, recipient=feedback_recipient, anonymous=context["anonymous"])
            feedback_reply.save()
            feedback_reply.send_notification()
        return HttpResponseRedirect(reverse("single_feedback", args=(feedback_id,)))

    feedbacks = []
    reply_exists = True
    feedbacks.append(feedback)
    feedbacks.extend(Feedback.objects.filter(reply_to=feedback).filter(cancelled=False).exclude(delivered_at=None).order_by("given_at"))

    context["feedbacks"] = feedbacks
    return render(request, "single_feedback.html", context)


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
    context["sender"] = context["slack_user"] = sender


    question_id = kwargs.get("question_id")
    if question_id:
        question = SentQuestion.objects.get(sent_question_id=question_id)
        assert question.feedback_sender == sender
        context["question_id"] = question_id
        if request.GET.get("without_question") != "true":
            context["question"] = question.question
        context["recipients"] = [question.feedback_receiver]
        context["recipient_ids"] = question.feedback_receiver.user_id


    if request.method == "POST":
        recipient_ids = request.POST.get("recipient_ids")
        if recipient_ids:
            recipient_ids = recipient_ids.split(",")
            recipients = SlackUser.objects.filter(user_id__in=recipient_ids)
        else:
            recipients = request.POST.get("recipient")
            components = re.match(r"^(?P<real_name>(.*)) \(@(?P<name>([A-Za-z0-9-_]+))\)$", recipients)
            if not components:
                return HttpResponseBadRequest("Invalid recipient data")
            recipients = SlackUser.objects.filter(name=components.group("name")).filter(real_name=components.group("real_name"))
            if len(recipients) == 0:
                return HttpResponseBadRequest("No recipients found")

        feedback_group_id = uuid.uuid4()
        if len(recipients) == 0:
            return HttpResponseBadRequest("No recipients found :(")
        for recipient in recipients:
            feedback = Feedback(feedback_group_id=feedback_group_id, recipient=recipient, sender=sender, feedback=request.POST.get("feedback_text"), question=request.POST.get("question"))
            feedback.save()
        if question_id and question:
            question.answered_at = timezone.now()
            if question.dismissed_at:
                question.dismissed_at = None
            question.save()
        return HttpResponseRedirect(reverse("feedback_received"))

    if kwargs.get("random"):
        context["recipients"] = [get_random_recipient(request.session.get("team_id"))]
        context["question"] = get_random_question(context["recipients"][0])
        context["recipient_ids"] = ",".join(map(lambda k: k.user_id, context["recipients"]))
    return render(request, "new_feedback.html", context)


def feedback_received(request):
    context = {}
    return render(request, "feedback_received.html", context)


def replace_attachment(attachments, callback_id, replacement):
    for i, item in enumerate(attachments):
        if item.get("callback_id") == callback_id:
            break
    else:
        attachments.append(replacement)
        return attachments
    if replacement:
        attachments[i] = replacement
    else:
        del attachments[i]
    return attachments

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
    if "original_message" in action:
        response.update(action["original_message"])
    if "attachments" not in response:
        response["attachments"] = []

    if requested_action == "do_not_show_slash_hint":
        SlackUser.objects.filter(user_id=action["user"]["id"]).update(show_slash_prompt_hint=False)
        response["attachments"] = replace_attachment(response["attachments"], callback_id, {"text": "You won't see this hint again."})
    elif requested_action == "flag_helpful":
        feedback.update(flagged_helpful=True)
        response["attachments"] = replace_attachment(response["attachments"], callback_id, {"text": "Ok, great! This information will be available for the person who gave the feedback to you. <%s|View or reply to this feedback>" % feedback[0].get_feedback_url(), "mrkdwn_in": ["text"]})
    elif requested_action == "didnt_understand":
        feedback.update(flagged_difficult_to_understand=True)
        response["attachments"] = replace_attachment(response["attachments"], callback_id, {"text": "Ok, thanks for the information! This will be available for the person who gave the feedback for you - hopefully they will clarify what they meant. <%s|View or reply to this feedback>" % (feedback[0].get_feedback_url()), "mrkdwn_in": ["text"]})
    elif requested_action == "feedback_received":
        response["attachments"] = replace_attachment(response["attachments"], callback_id, {"text": "You can view feedback you have received with `/peer_feedback list`. You can <%s|view or reply to this feedback>" % feedback[0].get_feedback_url(), "mrkdwn_in": ["text"]})
    elif requested_action == "add_name":
        feedback.update(anonymous=False)
        response["attachments"] = replace_attachment(response["attachments"], callback_id, {
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
        })

    elif requested_action == "cancel":
        delivered = False
        for single_feedback in feedback:
            if single_feedback.delivered:
                delivered = True
                break
        if not delivered:
            feedback.update(cancelled=True)
            response["attachments"] = replace_attachment(response["attachments"], callback_id, {
                "fallback": "Edit your feedback.",
                "callback_id": callback_id,
                "color": "#3AA3E3",
                "attachment_type": "default",
                "actions": [{
                    "name": "undo_cancel",
                    "text": "Undo - show this feedback",
                    "type": "button",
                    "value": "undo_cancel",
                }]
            })
            response["text"] = "Ok, your feedback has been cancelled."
        else:
            single_feedback = None
            if len(feedback) == 1:
                single_feedback = feedback[0]
            text = render_to_string("already_delivered.txt", context={
                "single_feedback": single_feedback,
                "feedbacks": feedback,
            })
            response["attachments"] = replace_attachment(response["attachments"], callback_id, {
                "fallback": "Feedback has been delivered.",
                "text": text,
                "mrkdwn_in": ["text"],
                "callback_id": callback_id,
                "color": "#3AA3E3",
                "attachment_type": "default"
            })
            response["text"] = "Already delivered."
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
        response["attachments"] = replace_attachment(response["attachments"], callback_id, {
            "fallback": "Edit your feedback.",
            "callback_id": callback_id,
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": actions,
        })
    elif requested_action == "done":
        response["text"] = "Ok, thanks!"
    return HttpResponse(json.dumps(response), content_type="application/json")
