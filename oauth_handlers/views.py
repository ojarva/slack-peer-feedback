from django.shortcuts import render
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied

import pprint
from django.conf import settings
import requests
from .models import AuthorizationData
from teams.models import SlackTeam

def oauth_authorization_url(scopes, redirect_uri):
    return "https://slack.com/oauth/authorize?scope=%s&client_id=%s&redirect_uri=%s" % (scopes, settings.CLIENT_ID, redirect_uri)

def request_oauth_data(code, redirect_uri):
    resp = requests.get("https://slack.com/api/oauth.access", {"client_id": settings.CLIENT_ID, "client_secret": settings.CLIENT_SECRET, "code": code, "redirect_uri": redirect_uri})
    auth = resp.json()
    print auth
    if not auth["ok"]:
        raise PermissionDenied
    return auth

def gen_oauth_authorization_url(request):
    return HttpResponse(oauth_authorization_url("incoming-webhook,commands,bot,users:read,usergroups:read,team:read,chat:write:bot", settings.OAUTH_CALLBACK))

def oauth_callback(request):
    code = request.GET.get("code")
    auth = request_oauth_data(code, settings.OAUTH_CALLBACK)
    data = {
        "user_id": auth["user_id"],
        "access_token": auth["access_token"],
        "bot_access_token": auth["bot"]["bot_access_token"],
        "bot_user_id": auth["bot"]["bot_user_id"],
        "incoming_webhook_url": auth["incoming_webhook"]["url"],
        "incoming_webhook_channel_id": auth["incoming_webhook"]["channel_id"],
        "incoming_webhook_channel": auth["incoming_webhook"]["channel"],
        "incoming_webhook_configuration_url": auth["incoming_webhook"]["configuration_url"],
        "scopes": auth["scope"],
        "team_name": auth["team_name"],
    }
    obj, created = AuthorizationData.objects.update_or_create(team_id=auth["team_id"], defaults=data)
    SlackTeam.objects.update_or_create(team_id=auth["team_id"], defaults={"team_name": auth["team_name"]})
    return HttpResponse("ok")

def user_login(request):
    return HttpResponse(oauth_authorization_url("identity.basic", settings.USER_LOGIN_CALLBACK))

def user_login_callback(request):
    code = request.GET.get("code")
    auth = request_oauth_data(code, settings.USER_LOGIN_CALLBACK)
    print auth
    request.session["user_id"] = auth["user"]["id"]
    request.session["team_id"] = auth["team"]["id"]
    print request.session
    return HttpResponse("ok")
