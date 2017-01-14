from django.contrib import admin

import models

class TeamAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.Team, TeamAdmin)

class TeamMemberAdmin(admin.ModelAdmin):
    pass

admin.site.register(models.TeamMember, TeamMemberAdmin)
