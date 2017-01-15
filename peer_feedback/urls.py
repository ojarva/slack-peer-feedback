from django.conf.urls import include, url

from django.contrib import admin
admin.autodiscover()

import receiving_hooks.views
import oauth_handlers.views
import teams.views
import feedback.views

urlpatterns = [
    url(r'^hooks/peer_feedback_handler', receiving_hooks.views.peer_feedback_handler, name='peer_feedback_handler'),
    url(r'^hooks/incoming_slack_event', receiving_hooks.views.incoming_slack_event),
    url(r'^interactive_message/', feedback.views.receive_interactive_command),

    url(r'^oauth_authorize', oauth_handlers.views.gen_oauth_authorization_url),
    url(r'^oauth_callback', oauth_handlers.views.oauth_callback),
    url(r'^login', oauth_handlers.views.user_login),
    url(r'^user_oauth_callback', oauth_handlers.views.user_login_callback),

    url(r'^teams/$', teams.views.teams),
    url(r'^team/(?P<team_id>[0-9+])$', teams.views.team_edit),
    url(r'^teams/create', teams.views.create_new_team, name='create_new_team'),

    url(r'^new_feedback/$', feedback.views.leave_new_feedback_page),

    url(r'^admin/', include(admin.site.urls)),
]
