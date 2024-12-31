from django.shortcuts import render, redirect
from rest_framework import generics, viewsets, views, permissions, status
from rest_framework.response import Response
from django.http import Http404
from rest_framework.views import APIView
from django.views.generic import TemplateView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout

import json

from .models import (
    Device, Organization, Region, User, AccessEvent
)
from .serializers import (
    DeviceSerializer, PersonSerializer, FaceSerializer,
    UserRightWeekPlanCfgSerializer, UserRightPlanTemplateSerializer,
    RegionSerializer, OrganizationSerializer, UserSerializer,
    UserCreateSerializer, UserUpdateSerializer,
    AccessEventSerializer,  UserLoginSerializer
)
from .services.device_service import DeviceAPIService


# =============================================================================
# (1) DEVICE VIEWSET
# =============================================================================

class DeviceViewSet(viewsets.ModelViewSet):
    """
    Полноценный CRUD для модели Device:
      - GET    /devices/        -> list
      - POST   /devices/        -> create
      - GET    /devices/{pk}/   -> retrieve
      - PUT    /devices/{pk}/   -> update
      - PATCH  /devices/{pk}/   -> partial_update
      - DELETE /devices/{pk}/   -> destroy
    """
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer
    # permission_classes = (IsAuthenticated,)


# =============================================================================
# (2) PERSON VIEWSET (вложенный в devices)
# =============================================================================
#
#  При использовании NestedDefaultRouter с:
#     router.register('devices', DeviceViewSet, basename='devices')
#     devices_router = NestedDefaultRouter(router, 'devices', lookup='device')
#     devices_router.register('persons', PersonViewSet, basename='device-persons')
#
#  => URL станет: /devices/{device_pk}/persons/{pk}/
#  => Параметры: device_pk, pk
# =============================================================================

class PersonViewSet(viewsets.ViewSet):
    serializer_class = PersonSerializer

    def get_device(self, device_pk):
        try:
            return Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return None

    def list(self, request, device_pk=None):
        device = self.get_device(device_pk)
        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)
        service = DeviceAPIService(device)
        persons = service.get_persons()  # все персоны на устройстве
        serializer = self.serializer_class(persons, many=True)
        return Response(serializer.data)

    def retrieve(self, request, device_pk=None, pk=None):
        device = self.get_device(device_pk)
        if not device:
            raise Http404("Device not found")
        service = DeviceAPIService(device)
        person = service.get_persons(pk)  # получить одного
        # Если хотите сериализовать:
        try:
            serializer = self.serializer_class(person)
            return Response(serializer.data)
        except Exception:
            # Если person не является словарём, а уже json, возможно вернём как есть
            return Response(person, status=status.HTTP_200_OK)

    def create(self, request, device_pk=None):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        device = self.get_device(device_pk)
        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        try:
            response = service.add_person(**serializer.validated_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_201_CREATED)

    def update(self, request, device_pk=None, pk=None):
        # partial_update и update можно различать, но здесь упрощённо
        partial = True
        serializer = self.serializer_class(data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        device = self.get_device(device_pk)
        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        try:
            response = service.edit_person(pk, **serializer.validated_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_200_OK)

    def partial_update(self, request, device_pk=None, pk=None):
        return self.update(request, device_pk, pk)  # переиспользуем логику

    def destroy(self, request, device_pk=None, pk=None):
        device = self.get_device(device_pk)
        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        try:
            response = service.delete_person(pk)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# (3) FACE VIEWSET (вложенный глубже: /devices/{device_pk}/persons/{person_pk}/face/...)
# =============================================================================
#
#  Если вы используете ещё один NestedDefaultRouter для persons:
#    persons_router = NestedDefaultRouter(devices_router, 'persons', lookup='person')
#    persons_router.register('face', FaceViewSet, basename='person-face')
#
#  => URL: /devices/{device_pk}/persons/{person_pk}/face/{pk}/
#
#  => Аргументы: device_pk, person_pk, pk (при необходимости)
# =============================================================================

class FaceViewSet(viewsets.ViewSet):
    serializer_class = FaceSerializer

    def create(self, request, device_pk=None, person_pk=None):
        serializer = FaceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            face_lib_type = serializer.validated_data['face_lib_type']
            fdid = serializer.validated_data['fdid']
            image = serializer.validated_data['image']

            # Получаем устройство
            try:
                device = Device.objects.get(pk=device_pk)
            except Device.DoesNotExist:
                return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

            service = DeviceAPIService(device)
            image_data = image.read()
            # pk = не всегда используется, но если вы хотите, чтобы pk = employeeNo, тогда:
            response_data = service.add_face(face_lib_type, fdid, str(person_pk), image_data)
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, device_pk=None, person_pk=None, pk=None):
        face_lib_type = request.query_params.get('face_lib_type')
        fdid = request.query_params.get('fdid')

        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        response_data = service.get_face(face_lib_type, fdid, str(person_pk))
        return Response(response_data)

    def update(self, request, device_pk=None, person_pk=None, pk=None):
        serializer = FaceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            face_lib_type = serializer.validated_data['face_lib_type']
            fdid = serializer.validated_data['fdid']
            image = serializer.validated_data.get('image')

            try:
                device = Device.objects.get(pk=device_pk)
            except Device.DoesNotExist:
                return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

            service = DeviceAPIService(device)
            image_data = image.read()
            response_data = service.edit_face(face_lib_type, fdid, str(person_pk), image_data)
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, device_pk=None, person_pk=None, pk=None):
        return self.update(request, device_pk, person_pk, pk)

    def destroy(self, request, device_pk=None, person_pk=None, pk=None):
        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        response_data = service.delete_face(str(person_pk))
        return Response(response_data)


# =============================================================================
# (4) WEEK PLAN VIEWSET: /devices/{device_pk}/weekplan/{pk}/
# =============================================================================
#
#  Если вы делаете:
#  devices_router.register('weekplan', WeekPlanViewSet, basename='device-weekplan')
#
#  => URL: /devices/{device_pk}/weekplan/{pk}/
#  => Параметры: device_pk, pk
# =============================================================================

class WeekPlanViewSet(viewsets.ViewSet):
    serializer_class = UserRightWeekPlanCfgSerializer

    def retrieve(self, request, device_pk=None, pk=None):
        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        week_plan = service.get_week_plan(pk)  # pk = week_plan_id
        serializer = self.serializer_class(week_plan)
        return Response(serializer.data)

    def update(self, request, device_pk=None, pk=None):
        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            updated_plan = service.update_week_plan(pk, serializer.validated_data)
            return Response(updated_plan)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, device_pk=None, pk=None):
        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        week_plan = service.get_week_plan(pk)
        serializer = self.serializer_class(week_plan, data=request.data, partial=True)
        if serializer.is_valid():
            updated_plan = service.update_week_plan(pk, serializer.validated_data)
            return Response(updated_plan)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# (5) SCHEDULE VIEWSET: /devices/{device_pk}/schedule/{pk}/
# =============================================================================

class ScheduleViewSet(viewsets.ViewSet):
    serializer_class = UserRightPlanTemplateSerializer

    def retrieve(self, request, device_pk=None, pk=None):
        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        schedule_template = service.get_schedule_template(pk)
        serializer = self.serializer_class(schedule_template)
        return Response(serializer.data)

    def update(self, request, device_pk=None, pk=None):
        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            updated_template = service.update_schedule_template(pk, serializer.validated_data)
            return Response(updated_template)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, device_pk=None, pk=None):
        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        schedule_template = service.get_schedule_template(pk)
        serializer = self.serializer_class(schedule_template, data=request.data, partial=True)
        if serializer.is_valid():
            updated_template = service.update_schedule_template(pk, serializer.validated_data)
            return Response(updated_template)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# (6) REGION, ORG, USER, ACCESSEVENT VIEWSETS
# =============================================================================

class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    ordering = ['name']




class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        elif self.request.method in ['PATCH', 'PUT']:
            return UserUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """
        Переопределяем создание пользователя (create), чтобы вернуть JWT-токены.
        Проверка password == password_confirm будет в самом сериализаторе (validate).
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Вызов serializer.save() уже создаст пользователя (через метод create() в сериализаторе)
        user = serializer.save()  

        # Генерируем JWT-токены (refresh / access)
        refresh = RefreshToken.for_user(user)
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        # Можно дополнительно вернуть что-то ещё (ID пользователя, username и т.д.)
        # data['user_id'] = user.id
        # data['username'] = user.username

        headers = self.get_success_headers(serializer.data)
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)


class AccessEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AccessEvent.objects.all()
    serializer_class = AccessEventSerializer
    # permission_classes = [permissions.IsAuthenticated]


# =============================================================================
# (7) USER REGISTER / LOGIN VIEWS (примеры на APIView)
# =============================================================================



class UserLoginView(APIView):
    serializer_class = UserLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            # login(request, user)
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token)
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        region_id = self.request.query_params.get('region_id')
        if region_id:
            # фильтруем по региону
            qs = qs.filter(region_id=region_id)
        return qs
    

def UserLogoutView(request):
    logout(request)
    response = redirect('login')  # Перенаправление на страницу логина
    response.delete_cookie('access')
    response.delete_cookie('refresh')
    return response

