import slacker
from oauth_handlers.models import AuthorizationData
from .models import SlackUser, SlackTeam

def update_user(user_data):
    profile = user_data.get("profile", {})
    slack_team = SlackTeam.objects.get(team_id=user_data.get("team_id"))
    data = {
        "is_bot": user_data.get("is_bot", False),
        "is_admin": user_data.get("is_admin", False),
        "deleted": user_data.get("deleted", False),
        "name": user_data.get("name"),
        "real_name": profile.get("real_name"),
        "first_name": profile.get("first_name"),
        "last_name": profile.get("last_name"),
        "slack_team": slack_team,
        "tz": user_data.get("tz"),
        "email": profile.get("email"),
        "image_192": profile.get("image_192"),
        "image_24": profile.get("image_24"),
        "tz_offset": user_data.get("tz_offset"),
    }
    SlackUser.objects.update_or_create(user_id=user_data["id"], defaults=data)


def refresh_slack_users(team_id):
    authorization_data = AuthorizationData.objects.get(team_id=team_id)
    slack = slacker.Slacker(authorization_data.access_token)
    users = slack.users.list().body["members"]
    i = 0
    for user in users:
        update_user(user)
        i += 1
    return i
