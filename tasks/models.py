from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User


class Task(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Done', 'Done'),
        ('Cancelled', 'Cancelled'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_on = models.DateTimeField(auto_now_add=True)
    completed_on = models.DateTimeField(null=True, blank=True)
    is_done = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='Pending')
    label = models.CharField(max_length=50, blank=True)
    parent_task = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='sub_tasks')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='tasks')

    def __str__(self):
        return self.title

    def update_parent_status(self):
        """Auto-update the parent task status based on its subtasks."""
        if self.parent_task:
            siblings = self.parent_task.sub_tasks.all()
            all_done = all(sub.is_done for sub in siblings)

            if all_done:
                self.parent_task.is_done = True
                self.parent_task.status = 'Done'
                self.parent_task.completed_on = timezone.now()
            else:
                self.parent_task.is_done = False
                self.parent_task.status = 'Pending'
                self.parent_task.completed_on = None

            self.parent_task.save()

    def save(self, *args, **kwargs):
        if self.is_done and not self.completed_on:
            self.completed_on = timezone.now()
        elif not self.is_done:
            self.completed_on = None

        super().save(*args, **kwargs)

        self.update_parent_status()

    def delete(self, *args, **kwargs):
        parent = self.parent_task
        super().delete(*args, **kwargs)
        if parent:
            parent.update_parent_status()
