from django.conf.urls import include, url

from django.contrib import admin
admin.autodiscover()

import receiving_hooks.views

# Examples:
# url(r'^$', 'peer_feedback.views.home', name='home'),
# url(r'^blog/', include('blog.urls')),

urlpatterns = [
#    url(r'^$', hello.views.index, name='index'),
    url(r'^new_feedback', receiving_hooks.views.new_feedback, name='new_feedback')
#    url(r'^db', hello.views.db, name='db'),
    url(r'^admin/', include(admin.site.urls)),
]
