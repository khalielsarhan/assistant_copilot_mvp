from django.db import models
from django.utils import timezone

class Task(models.Model):
    class Category(models.TextChoices):
        CEO = 'CEO', 'CEO'
        ENGINEERING = 'ENGINEERING', 'Engineering'
        HR = 'HR', 'HR'
        FINANCE = 'FINANCE', 'Finance'
        SALES = 'SALES', 'Sales'
        CLIENT = 'CLIENT', 'Client'
        PERSONAL = 'PERSONAL', 'Personal'

    class Priority(models.TextChoices):
        LOW = 'LOW', 'Low'
        MEDIUM = 'MEDIUM', 'Medium'
        HIGH = 'HIGH', 'High'
        URGENT = 'URGENT', 'Urgent'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        WAITING = 'WAITING', 'Waiting'
        DONE = 'DONE', 'Done'
        CANCELLED = 'CANCELLED', 'Cancelled'

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=30, choices=Category.choices, default=Category.CEO)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    owner_name = models.CharField(max_length=120, default='Nour')
    source = models.CharField(max_length=50, default='telegram')
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_overdue(self):
        return self.due_date and self.status in [self.Status.OPEN, self.Status.WAITING] and self.due_date < timezone.now()

    def __str__(self):
        return f'#{self.id} {self.title}'
