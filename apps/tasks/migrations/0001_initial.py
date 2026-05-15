from django.db import migrations, models

class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('category', models.CharField(choices=[('CEO','CEO'),('ENGINEERING','Engineering'),('HR','HR'),('FINANCE','Finance'),('SALES','Sales'),('CLIENT','Client'),('PERSONAL','Personal')], default='CEO', max_length=30)),
                ('priority', models.CharField(choices=[('LOW','Low'),('MEDIUM','Medium'),('HIGH','High'),('URGENT','Urgent')], default='MEDIUM', max_length=20)),
                ('status', models.CharField(choices=[('OPEN','Open'),('WAITING','Waiting'),('DONE','Done'),('CANCELLED','Cancelled')], default='OPEN', max_length=20)),
                ('owner_name', models.CharField(default='Nour', max_length=120)),
                ('source', models.CharField(default='telegram', max_length=50)),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
