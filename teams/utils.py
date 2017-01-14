import slacker
from oauth_handlers.models import AuthorizationData
from .models import SlackUser, SlackTeam

def refresh_slack_users(team_id):
    authorization_data = AuthorizationData.objects.get(team_id=team_id)
    slack = slacker.Slacker(authorization_data.access_token)
    users = slack.users.list().body["members"]
    for user in users:
        profile = user.get("profile", {})
        slack_team = SlackTeam.objects.get(team_id=user.get("team_id"))
        data = {
            "is_bot": user.get("is_bot", False),
            "is_admin": user.get("is_admin", False),
            "deleted": user.get("deleted", False),
            "name": user.get("name"),
            "real_name": profile.get("real_name"),
            "slack_team": slack_team,
            "tz": user.get("tz"),
            "email": profile.get("email"),
            "image_192": profile.get("image_192"),
            "tz_offset": user.get("tz_offset"),
        }
        SlackUser.objects.update_or_create(user_id=user["id"], defaults=data)
