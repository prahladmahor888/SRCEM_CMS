from django.contrib import admin
from .models import HODNotification

@admin.register(HODNotification)
class HODNotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'department', 'priority', 'is_active', 'created_at')
    list_filter = ('priority', 'department', 'is_active')
