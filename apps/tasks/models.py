from django.db import models
from django.utils import timezone

class Project(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        HOLD = 'HOLD', 'Hold'
        PIPELINE = 'PIPELINE', 'Pipeline'
        CLOSED = 'CLOSED', 'Closed'

    class Health(models.TextChoices):
        GREEN = 'GREEN', 'Green'
        YELLOW = 'YELLOW', 'Yellow'
        RED = 'RED', 'Red'

    name = models.CharField(max_length=200, unique=True)
    client_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    health = models.CharField(max_length=20, choices=Health.choices, default=Health.GREEN)
    owner_name = models.CharField(max_length=120, default='Nour')
    last_update_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


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
    project = models.ForeignKey(Project, on_delete=models.SET_NULL, null=True, blank=True, related_name='tasks')
    source = models.CharField(max_length=50, default='telegram')
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_overdue(self):
        return self.due_date and self.status in [self.Status.OPEN, self.Status.WAITING] and self.due_date < timezone.now()

    def __str__(self):
        return f'#{self.id} {self.title}'
