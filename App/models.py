from django.db import models
from  django.core.validators  import RegexValidator
import requests
from requests.auth import HTTPDigestAuth
import xmltodict, json
import random
import string

from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Импортируем наши сервисы (при необходимости) 
# from .services.device_service import DeviceAPIService

# Валидатор для BIN и IIN
Validator_IIN_BIIN = RegexValidator(r'^\d{12}$', message="IIN or BIN must be 12 digits")


class Region(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
    name   = models.CharField(max_length=100, unique=True)  # Добавлено max_length и уникальность для name

    class Meta:
        verbose_name = '(Handbook) Region'
        verbose_name_plural = '(Handbook) Regions'
        ordering = ['name']  # Упорядочивание регионов по имени по умолчанию

    def __str__(self):
        return self.name


class Organization(models.Model):

    bin       = models.CharField(validators=[Validator_IIN_BIIN], max_length=12, unique=True)
    number    = models.PositiveSmallIntegerField()
    name      = models.CharField(max_length=50)
    region    = models.ForeignKey(Region, on_delete= models.PROTECT)
    
    class Meta:
        verbose_name        = '(Handbook) Organization'
        verbose_name_plural = '(Handbook) Organizations'

    def __str__(self):
        return f'{self.region.name} - {self.name}'



class CustomUserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)
    
    
class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[UnicodeUsernameValidator()],
    )
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    FIO = models.CharField(_("FIO"), max_length=55)
    phone = models.CharField(_("phone"), max_length=15)
    organization = models.ManyToManyField('Organization', blank=True)  # Это поле

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    approved = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    #is_verified = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.username

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)



class Device(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    ip_address = models.CharField(max_length=25)
    port_no = models.IntegerField()
    channel_id = models.IntegerField()
    name = models.CharField(max_length=25)
    login = models.CharField(max_length=25)
    password = models.CharField(max_length=25)
    max_record_num = models.IntegerField(null=True, blank=True, default=None)
    max_results = models.IntegerField(null=True, blank=True, default=None)

    class Meta:
        verbose_name = '(Basic) Device'
        verbose_name_plural = '(Basic) Devices'

    def __str__(self):
        return self.name
    

class AccessEvent(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    ipAddress = models.CharField(max_length=15)
    portNo = models.IntegerField()
    protocol = models.CharField(max_length=10)
    macAddress = models.CharField(max_length=17)
    channelID = models.IntegerField()
    dateTime = models.DateTimeField()
    activePostCount = models.IntegerField()
    eventType = models.CharField(max_length=50)
    eventState = models.CharField(max_length=20)
    eventDescription = models.CharField(max_length=100)
    
    # AccessControllerEvent fields
    deviceName = models.CharField(max_length=50)
    majorEventType = models.IntegerField()
    subEventType = models.IntegerField()
    name = models.CharField(max_length=50)
    cardReaderKind = models.IntegerField()
    cardReaderNo = models.IntegerField()
    verifyNo = models.IntegerField()
    employeeNoString = models.CharField(max_length=50)
    serialNo = models.IntegerField()
    userType = models.CharField(max_length=20)
    currentVerifyMode = models.CharField(max_length=20)
    frontSerialNo = models.IntegerField()
    attendanceStatus = models.CharField(max_length=20)
    label = models.CharField(max_length=50)
    statusValue = models.IntegerField()
    mask = models.CharField(max_length=5)
    purePwdVerifyEnable = models.BooleanField()

    def __str__(self):
        return f"Access Event {self.id} - {self.dateTime}"


