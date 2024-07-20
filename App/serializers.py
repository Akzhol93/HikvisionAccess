from rest_framework import serializers
from .models import *
from datetime import datetime
import re

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

class   PersonSerializer(serializers.Serializer):
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

    def validate_userType(self, value):
        if value not in ["normal", "visitor", "blackList", "maintenance"]:
            raise serializers.ValidationError("userType must be 'normal', 'visitor', 'blackList' or 'maintenance'.")
        return value
    
    
#Cериализатор для работы с изображениями лица
class FaceSerializer(serializers.Serializer):
    face_lib_type = serializers.CharField(max_length=50)
    fdid = serializers.CharField(max_length=50)
    employeeNo = serializers.CharField(max_length=50, required=False)
    image = serializers.ImageField()


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
    region = RegionSerializer()  # Включаем данные региона в сериализатор организации

    class Meta:
        model = Organization
        fields = ['id', 'bin', 'number', 'name', 'region']

# Сериализатор для модели User
class UserSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(many=True, read_only=True)  # Включаем данные об организации

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'FIO', 'phone', 'organization', 
            'is_active', 'is_staff', 'date_joined', 'updated_at', 'approved', 'is_verified'
        ]
class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)  # Добавляем поле подтверждения пароля
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.all(),
        many=True,
        write_only=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'FIO', 'phone', 'organization']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match'})
        return data

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        organizations = validated_data.pop('organization', [])
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        user.organization.set(organizations)
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['FIO', 'phone', 'is_active', 'is_staff', 'approved', 'is_verified']

    def validate(self, attrs):
        # Можно добавить дополнительные проверки здесь, если требуется
        return super().validate(attrs)

class UserDetailSerializer(serializers.ModelSerializer):
    organization = OrganizationSerializer(many=True, read_only=True)  # Включаем данные об организации

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'FIO', 'phone', 'organization', 
            'is_active', 'is_staff', 'date_joined', 'updated_at', 'approved', 'is_verified'
        ]

    def get_full_name(self):
        return self.FIO



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