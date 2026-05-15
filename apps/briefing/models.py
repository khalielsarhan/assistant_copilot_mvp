from django.db import models

class DailyBriefing(models.Model):
    briefing_date = models.DateField(unique=True)
    content = models.TextField()
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.briefing_date)
