from django.db import models
from apps.tasks.models import Task

class Reminder(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        CANCELLED = 'CANCELLED', 'Cancelled'

    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='reminders')
    remind_at = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Reminder for {self.task_id} at {self.remind_at}'
