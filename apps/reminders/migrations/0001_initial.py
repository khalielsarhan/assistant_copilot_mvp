from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [('tasks', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='Reminder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('remind_at', models.DateTimeField()),
                ('sent_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDING','Pending'),('SENT','Sent'),('CANCELLED','Cancelled')], default='PENDING', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reminders', to='tasks.task')),
            ],
        ),
    ]
