from django.conf.urls import include, url

from django.contrib import admin
admin.autodiscover()

import receiving_hooks.views
import oauth_handlers.views
import teams.views
import feedback.views

urlpatterns = [
    url(r'^new_feedback', receiving_hooks.views.new_feedback, name='new_feedback'),
    url(r'^oauth_authorize', oauth_handlers.views.gen_oauth_authorization_url),
    url(r'^oauth_callback', oauth_handlers.views.oauth_callback),
    url(r'^login', oauth_handlers.views.user_login),
    url(r'^user_oauth_callback', oauth_handlers.views.user_login_callback),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^teams/$', teams.views.teams),
    url(r'^team/(?P<team_id>[0-9+])$', teams.views.team_edit),
    url(r'^teams/create', teams.views.create_new_team, name='create_new_team'),
    url(r'^interactive_message/', feedback.views.receive_interactive_command),
    url(r'^hooks/incoming_event', receiving_hooks.views.incoming_event),
]
