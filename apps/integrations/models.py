from django.db import models

class GitLabIntegration(models.Model):
    project_name = models.CharField(max_length=200)
    gitlab_project_id = models.CharField(max_length=120)
    repo_url = models.URLField(blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.project_name
