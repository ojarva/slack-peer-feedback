from django import forms

class TeamForm(forms.Form):
    team_name = forms.CharField(label="Team name", max_length=50)
