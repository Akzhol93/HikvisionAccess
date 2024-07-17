# Generated by Django 5.0.6 on 2024-07-13 14:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('App', '0003_rename_channelid_device_channel_id_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccessEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ipAddress', models.CharField(max_length=15)),
                ('portNo', models.IntegerField()),
                ('protocol', models.CharField(max_length=10)),
                ('macAddress', models.CharField(max_length=17)),
                ('channelID', models.IntegerField()),
                ('dateTime', models.DateTimeField()),
                ('activePostCount', models.IntegerField()),
                ('eventType', models.CharField(max_length=50)),
                ('eventState', models.CharField(max_length=20)),
                ('eventDescription', models.CharField(max_length=100)),
                ('deviceName', models.CharField(max_length=50)),
                ('majorEventType', models.IntegerField()),
                ('subEventType', models.IntegerField()),
                ('name', models.CharField(max_length=50)),
                ('cardReaderKind', models.IntegerField()),
                ('cardReaderNo', models.IntegerField()),
                ('verifyNo', models.IntegerField()),
                ('employeeNoString', models.CharField(max_length=50)),
                ('serialNo', models.IntegerField()),
                ('userType', models.CharField(max_length=20)),
                ('currentVerifyMode', models.CharField(max_length=20)),
                ('frontSerialNo', models.IntegerField()),
                ('attendanceStatus', models.CharField(max_length=20)),
                ('label', models.CharField(max_length=50)),
                ('statusValue', models.IntegerField()),
                ('mask', models.CharField(max_length=5)),
                ('purePwdVerifyEnable', models.BooleanField()),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='App.device')),
            ],
        ),
    ]
