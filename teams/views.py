from django.shortcuts import render
import models
import forms
import json
from django.views.generic import ListView
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseForbidden

def teams(request):
    # TODO: authentication & redirect
    queryset = models.Team.objects.filter(slack_team_id=request.session["team_id"])
    return render(request, "teams.html", context={"teams": queryset})

def team_edit(request, team_id):
    # TODO
    team = models.Team.objects.get(id=team_id)

def create_new_team(request):
    # TODO: authentication
    if request.method == "POST":
        form = forms.TeamForm(request.POST)
        if form.is_valid():
            team = models.Team(form["team_name"])
    else:
        form = forms.TeamForm()
    return render(request, "create_new_team.html", context={"form": form})


def get_team_members(request, **kwargs):
    """ Returns team member details.

    Returns restricted and ultra restricted members. Does not return bot or deleted users. """
    team_id = request.session.get("team_id")
    if not team_id:
        return HttpResponseForbidden("You must be signed in to access this method.")
    team_members = map(lambda k: k.to_public_json(), models.SlackUser.objects.filter(slack_team__team_id=team_id).filter(deleted=False).filter(is_bot=False))
    if kwargs.get("list"):
        team_members = map(lambda k: "%s (@%s)" % (k["real_name"], k["name"]), team_members)
    return HttpResponse(json.dumps(team_members), content_type="application/json")
