from django.conf.urls import include, url
from django.views.generic import TemplateView

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
    url(r'^login', oauth_handlers.views.user_login, name="login"),
    url(r'^logout', oauth_handlers.views.logout, name="logout"),
    url(r'^user_oauth_callback', oauth_handlers.views.user_login_callback),

    url(r'^teams$', teams.views.teams),
    url(r'^team/(?P<team_id>[0-9+])$', teams.views.team_edit),
    url(r'^teams/create', teams.views.create_new_team, name='create_new_team'),

    url(r'^api/slack/members$', teams.views.get_team_members),
    url(r'^api/slack/members/simple$', teams.views.get_team_members, kwargs={"list": True}),

    url(r'^feedback/(?P<feedback_id>[0-9A-Fa-f-]{32,36})$', feedback.views.single_feedback, name='single_feedback'),
    url(r'^sent_feedback$', feedback.views.sent_feedback, name='sent_feedback'),
    url(r'^new_feedback$', feedback.views.leave_new_feedback_page, name='new_feedback'),
    url(r'^new_feedback/random$', feedback.views.leave_new_feedback_page, name='new_feedback_random', kwargs={"random": True}),
    url(r'^new_feedback/question/(?P<question_id>[0-9A-Fa-f-]{32,36})$', feedback.views.leave_new_feedback_page, name='new_feedback_for_question'),
    url(r'^api/feedback/dismiss_pending_question/(?P<question_id>[0-9A-Fa-f-]{32,36})$', feedback.views.dismiss_pending_question, name="dismiss_pending_question"),
    url(r'^feedback_received$', feedback.views.feedback_received, name='feedback_received'),
    url(r'^$', feedback.views.dashboard, name='dashboard'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^about$', TemplateView.as_view(template_name='about.html'), name='about'),
]
