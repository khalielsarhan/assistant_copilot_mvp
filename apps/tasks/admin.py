from django.contrib import admin
from apps.tasks.models import Project, Task
admin.site.register(Project)
admin.site.register(Task)
