from django.contrib import admin

import models

class TeamAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Team, TeamAdmin)

class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("team", "user", "can_see_feedbacks")

admin.site.register(models.TeamMember, TeamMemberAdmin)

class SlackUserAdmin(admin.ModelAdmin):
    list_display = ("real_name", "name", "deleted", "is_bot")
    list_filter = ("deleted", "is_bot")

admin.site.register(models.SlackUser, SlackUserAdmin)

class FeedbackQuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "generic_question", "team_question", "team")

admin.site.register(models.FeedbackQuestion, FeedbackQuestionAdmin)
