from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, unique=True)),
                ('client_name', models.CharField(blank=True, max_length=200)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('HOLD', 'Hold'), ('PIPELINE', 'Pipeline'), ('CLOSED', 'Closed')], default='ACTIVE', max_length=20)),
                ('health', models.CharField(choices=[('GREEN', 'Green'), ('YELLOW', 'Yellow'), ('RED', 'Red')], default='GREEN', max_length=20)),
                ('owner_name', models.CharField(default='Nour', max_length=120)),
                ('last_update_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='task',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tasks', to='tasks.project'),
        ),
    ]
