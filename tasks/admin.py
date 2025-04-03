from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'status', 'is_done',
                    'created_on', 'completed_on', 'parent_task']
    list_filter = ['status', 'is_done', 'label']
    search_fields = ['title', 'description']
