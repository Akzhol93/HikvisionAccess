# Generated by Django 5.0.6 on 2025-02-28 13:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('App', '0005_alter_user_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='device',
            name='is_online',
            field=models.BooleanField(default=False),
        ),
    ]
