from rest_framework import serializers
from .models import *
from datetime import datetime
import re
from django.contrib.auth import authenticate

from django.core.mail import send_mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.conf import settings
from django.utils.translation import gettext_lazy as _  # если хотите i18n

#Cериализаторы для работы с Device
class   DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Device
        fields = '__all__'

#Cериализаторы для работы с Person
class ValidSerializer(serializers.Serializer):
    enable = serializers.BooleanField()
    beginTime = serializers.CharField()
    endTime = serializers.CharField()
    timeType = serializers.CharField(required=False)

    def validate_time_format(self, value):
        """
        Валидатор для полей beginTime и endTime.
        Проверяет формат времени и возвращает значение.
        """
        if not re.match(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
            raise serializers.ValidationError("Неверный формат времени. Используйте формат '%Y-%m-%dT%H:%M:%S'.(01, не 1)")

        try:
            # Пытаемся преобразовать значение в datetime по заданному формату
            datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            raise serializers.ValidationError("Неверный формат времени. Используйте формат '%Y-%m-%dT%H:%M:%S'.")
        return value

    def validate_beginTime(self, value):
        return self.validate_time_format(value)

    def validate_endTime(self, value):
        return self.validate_time_format(value)
    
    def validate_timeType(self, value):
        if value not in ["local", "UTC"]:
            raise serializers.ValidationError("userType must be 'local' or 'UTC'.")
        return value
    
class RightPlanSerializer(serializers.Serializer):
    doorNo = serializers.IntegerField()
    planTemplateNo = serializers.CharField()


class PersonSerializer(serializers.Serializer):
    employeeNo = serializers.CharField()
    name = serializers.CharField()
    userType = serializers.CharField()
    closeDelayEnabled = serializers.BooleanField(required=False)
    Valid = ValidSerializer()
    belongGroup = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=False, allow_blank=True)
    doorRight = serializers.CharField(required=False)
    RightPlan = serializers.ListField(child=RightPlanSerializer(), required=False)
    maxOpenDoorTime = serializers.IntegerField(required=False)
    openDoorTime = serializers.IntegerField(required=False)
    roomNumber = serializers.IntegerField(required=False)
    floorNumber = serializers.IntegerField(required=False)
    localUIRight = serializers.BooleanField(required=False)
    gender = serializers.CharField(required=False)
    numOfCard = serializers.IntegerField(required=False)
    numOfFace = serializers.IntegerField(required=False)
    PersonInfoExtends = serializers.ListField(child=serializers.DictField(), required=False)

    def validate_employeeNo(self, value):
        if not re.fullmatch(r'\d{12}', value):
            raise serializers.ValidationError("Поле employeeNo должно состоять ровно из 12 цифр.")
        return value

    def validate_userType(self, value):
        if value not in ["normal", "visitor", "blackList", "maintenance"]:
            raise serializers.ValidationError("userType must be 'normal', 'visitor', 'blackList' or 'maintenance'.")
        return value


#Cериализаторы для работы с WeekPlan
class TimeSegmentSerializer(serializers.Serializer):
    beginTime = serializers.CharField(max_length=8)
    endTime = serializers.CharField(max_length=8)

class WeekPlanCfgSerializer(serializers.Serializer):
    week = serializers.CharField(max_length=10)
    id = serializers.IntegerField()
    enable = serializers.BooleanField()
    TimeSegment = TimeSegmentSerializer()
    #authenticationTimesEnabled = serializers.BooleanField(required=False),
    #authenticationTimes = serializers.IntegerField(required=False) 

class UserRightWeekPlanCfgInnerSerializer(serializers.Serializer):
    enable = serializers.BooleanField()
    WeekPlanCfg = serializers.ListField(child=WeekPlanCfgSerializer())

class UserRightWeekPlanCfgSerializer(serializers.Serializer):
    UserRightWeekPlanCfg = UserRightWeekPlanCfgInnerSerializer()


#Cериализаторы для работы с Schedule
class UserRightPlanTemplateInnerSerializer(serializers.Serializer):
    enable = serializers.BooleanField()
    templateName = serializers.CharField(max_length=50)
    weekPlanNo = serializers.IntegerField()
    holidayGroupNo = serializers.CharField(max_length=50, allow_blank=True, allow_null=True)

class UserRightPlanTemplateSerializer(serializers.Serializer):
    UserRightPlanTemplate = UserRightPlanTemplateInnerSerializer()



# Сериализатор для модели Region
class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'number', 'name']

# Сериализатор для модели Organization
class OrganizationSerializer(serializers.ModelSerializer):
    # Показываем parent как ID (или можно вложенный OrganizationSerializer)
    parent = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), allow_null=True, required=False)
    # Или если хотите вложенно:
    # parent = OrganizationSerializer(read_only=True)

    # Покажем список детей (read-only) 
    children = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # Или со вложенными сериализаторами:
    # children = OrganizationSerializer(many=True, read_only=True)

    region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all()
    )   

    class Meta:
        model = Organization
        fields = ['id', 'bin', 'number', 'name', 'region','parent', 'children']

    def validate_parent(self, value):
        if value and value.parent is not None:
            raise serializers.ValidationError("Нельзя создавать вложенность глубже 1 уровня.")
        return value


USERNAME_REGEX = r'^[A-Za-z0-9]{5,}$'

class UserSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'FIO', 'phone', 'organization',
            'is_active', 'is_staff', 'date_joined', 'updated_at', 'approved', 'can_edit'
        ]

class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        write_only=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'FIO', 'phone', 'organization']

    def validate_username(self, value):
        if not re.match(USERNAME_REGEX, value):
            raise serializers.ValidationError(
                "Имя пользователя должно содержать только латинские буквы и цифры и быть не короче 5 символов."
            )
        return value

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Пароли не совпадают.'})

        if not (6 <= len(data['password']) <= 50):
            raise serializers.ValidationError({'password': 'Пароль должен быть от 6 до 50 символов.'})

        return data

    def create(self, validated_data):
        user = User(
            username=validated_data['username'],
            email=validated_data['email'],
            FIO=validated_data['FIO'],
            phone=validated_data['phone'],
            is_active=False  # <-- деактивируем
        )
        user.set_password(validated_data['password'])
        user.save()

        # Допустим, org:
        org = validated_data.get('organization')
        if org:
            user.organization = org
            user.save()

        # Генерируем токен
        token = default_token_generator.make_token(user)  
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Берём домен из настроек
        domain = getattr(settings, "BACKEND_DOMAIN", "http://127.0.0.1:8000")

        # Формируем ссылку активации (на бэкенд)
        activate_url = f"http://{domain}/api/users/activate/{uid}/{token}/"

        # Отправляем письмо
        send_mail(
            subject="Активация учётной записи",
            message=f"Для активации перейдите по ссылке: {activate_url}",
            from_email="no-reply@yourapp.com",
            recipient_list=[user.email],
            fail_silently=False,
        )

        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['FIO', 'phone', 'is_active', 'is_staff', 'approved', 'can_edit']

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise serializers.ValidationError("Неверные логин или пароль.")
        data['user'] = user
        return data

class AccessEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessEvent
        fields = [
            'id', 'device', 'ipAddress', 'portNo', 'protocol', 'macAddress', 'channelID',
            'dateTime', 'activePostCount', 'eventType', 'eventState', 'eventDescription',
            'deviceName', 'majorEventType', 'subEventType', 'name', 'cardReaderKind',
            'cardReaderNo', 'verifyNo', 'employeeNoString', 'serialNo', 'userType',
            'currentVerifyMode', 'frontSerialNo', 'attendanceStatus', 'label',
            'statusValue', 'mask', 'purePwdVerifyEnable'
        ]
        read_only_fields = fields

#Cериализатор для работы с изображениями лица
class FaceSerializer(serializers.Serializer):
    face_lib_type = serializers.CharField(max_length=50)
    fdid = serializers.CharField(max_length=50)
    employeeNo = serializers.CharField(max_length=50, required=False)
    image = serializers.ImageField()