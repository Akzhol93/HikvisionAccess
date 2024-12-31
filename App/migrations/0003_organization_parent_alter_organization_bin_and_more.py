# Generated by Django 5.0.6 on 2024-12-31 06:50

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('App', '0002_remove_user_is_verified_user_can_edit'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='children', to='App.organization'),
        ),
        migrations.AlterField(
            model_name='organization',
            name='bin',
            field=models.CharField(max_length=12, unique=True, validators=[django.core.validators.RegexValidator('^\\d{12}$', message='IIN or BIN must be 12 digits')]),
        ),
        migrations.AlterField(
            model_name='organization',
            name='name',
            field=models.CharField(max_length=50),
        ),
        migrations.RemoveField(
            model_name='user',
            name='organization',
        ),
        migrations.AddField(
            model_name='user',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='users', to='App.organization'),
        ),
    ]
