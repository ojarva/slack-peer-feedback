from django.shortcuts import render
import models
import forms
from django.views.generic import ListView

def teams(request):
    queryset = models.Team.objects.filter(slack_team_id=request.session["team_id"])
    return render(request, "teams.html", context={"teams": queryset})

def team_edit(request, team_id):
    team = models.Team.objects.get(id=team_id)

def create_new_team(request):
    if request.method == "POST":
        form = forms.TeamForm(request.POST)
        if form.is_valid():
            team = models.Team(form["team_name"])
    else:
        form = forms.TeamForm()
    return render(request, "create_new_team.html", context={"form": form})
