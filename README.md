# Peer feedback bot for Slack

A simple bot for Slack to give anonymous feedback to other team members, and to have correspondence anonymously.

All (non-delivered) feedback can be converted to non-anonymous as well. Feedback senders can reply anonymously to continue discussion and provide clarifications, in case feedback recipient did not understand the feedback.

## Setting up Slack app

- Create a new [Slack app](https://api.slack.com/apps?new_app=1)
- Go to "OAuth & Permissions" tab, enter your development environment and production environment URLs
- Go to "Bot Users" tab, add new bot, enable "Always Show My Bot as Online"
- Go to "Interactive Messages", enter the URL with `/interactive_message/`
- Go to "Slash Commands", add new slash command. For example, `/peer_feedback`, "Request URL" `/hooks/peer_feedback_handler`, "Usage hint", `[@username] [feedback_text]`
- Go to "Event subscriptions", enable, "Request URL" `/hooks/incoming_slack_event`. Add Team Event, `user_change`. Before this, you must have the server up and running with valid SSL cert, and reachable from general internet.

## Setting up server on Heroku

- Create a new Heroku app. Do note you need either hobby or pro dynos, as Heroku has strict timeouts for some operations.
- Go to "Resources" tab and add "Heroku Postgres :: Database" with whatever version you want.
- Go to "Settings" tab, and configure necessary config variables.
- Push this repository to Heroku app
- `heroku run python manage.py migrate` to create database tables

## Required config variables (settings read from environment variables)

- `CLIENT_ID`, from Slack app - Basic Information - App Credentials
- `CLIENT_SECRET` - see previous
- `VERIFICATION_TOKEN` - see previous
- `DATABASE_URL` - set automatically by Heroku; sqlite for local development.
- `OAUTH_CALLBACK` - `https://your-app-name.herokuapp.com/oauth_callback`. Note that this must be configured to Slack app as well.
- `SECRET_KEY` - generate a long random string for this. Never share it with anyone. Used by Django for CSRF tokens and signing sessions.
- `USER_LINK_SECRET` - generate a long random string for this. Never share it with anyone. Used by peer feedback to sign feedback links.
- `USER_LOGIN_CALLBACK` - `https://your-app-name.herokuapp.com/user_oauth_callback`. Do note that this must be configured to Slack app as well.
- `WEB_ROOT` - `https://your-app-name.herokuapp.com/`. Include trailing slash.

## Installing locally

- Recommended: use python virtual environments
- `pip install -r requirements.txt`
- `python manage migrate` to create database tables
