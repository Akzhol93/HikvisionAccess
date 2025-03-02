from django.shortcuts import render, redirect
from rest_framework import generics, viewsets, views, permissions, status
from rest_framework.response import Response
from django.http import Http404
from rest_framework.views import APIView
from django.views.generic import TemplateView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate, login, logout

from django.views import View
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode

from django.utils.encoding import force_bytes, force_str
from rest_framework.decorators import action


from .models import (
    Device, Organization, Region, User, AccessEvent
)
from .serializers import *
from .filters import *
from .services.device_service import DeviceAPIService
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404


# =============================================================================
# (1) DEVICE VIEWSET
# =============================================================================

class DeviceViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        
        org = user.organization
        # Если пользователь из главной организации, по умолчанию возвращаем все устройства её и «дочерних»
        if org.is_main():
            sub_orgs = org.get_all_suborganizations()
            qs = qs.filter(organization__in=sub_orgs)
        else:
            # Если нет, то только свои
            qs = qs.filter(organization=org)

        # Дополнительно смотрим, пришёл ли параметр organization_id
        requested_org_id = self.request.query_params.get('organization_id')
        if requested_org_id:
            # Теперь сузим выборку до конкретной organization_id
            qs = qs.filter(organization_id=requested_org_id)
            # Но нужно учесть, чтобы это был «разрешённый» organization_id,
            # т.е. он входит в те, которые user может видеть.
            # Если нужно делать более тонкую проверку, то добавьте.
        
        return qs
    permission_classes = (IsAuthenticated,)
 

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
   
            response = service.edit_person( **serializer.validated_data)
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



class FaceViewSet(viewsets.ViewSet):
    serializer_class = FaceSerializer

    def create(self, request, device_pk=None, person_pk=None):
        # POST -> /devices/{device_id}/persons/{person_pk}/face/
        serializer = FaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        face_lib_type = serializer.validated_data['face_lib_type']
        fdid = serializer.validated_data['fdid']
        image = serializer.validated_data['image']

        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)

        image_data = image.read()
        response_data = service.add_face(face_lib_type, fdid, str(person_pk), image_data)
        return Response(response_data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, device_pk=None, person_pk=None, pk=None):
        # GET -> /devices/{device_id}/persons/{person_pk}/face/{pk}
        face_lib_type = request.query_params.get('face_lib_type', 'blackFD')
        fdid = request.query_params.get('fdid', '1')

        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        response_data = service.get_face(face_lib_type, fdid, str(person_pk))
        return Response(response_data)

    def update(self, request, device_pk=None, person_pk=None, pk=None):
        serializer = FaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        face_lib_type = serializer.validated_data['face_lib_type']
        fdid = serializer.validated_data['fdid']
        image = serializer.validated_data['image']

        device = get_object_or_404(Device, pk=device_pk)
        service = DeviceAPIService(device)

        # 1) Проверяем, есть ли уже лицо
        search_response = service.get_face(face_lib_type, fdid, str(person_pk))
        matches = search_response.get("MatchList", [])
        face_already_exists = (len(matches) > 0)

        image_data = image.read()

        try:
            if face_already_exists:
                # Вызываем edit_face (PUT)
                response_data = service.edit_face(face_lib_type, fdid, str(person_pk), image_data)
            else:
                # Вызываем add_face (POST)
                response_data = service.add_face(face_lib_type, fdid, str(person_pk), image_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(response_data, status=status.HTTP_200_OK)


    def partial_update(self, request, device_pk=None, person_pk=None, pk=None):
        return self.update(request, device_pk, person_pk, pk)

    def destroy(self, request, device_pk=None, person_pk=None, pk=None):
        # DELETE -> /devices/{device_id}/persons/{person_pk}/face/{pk}
        face_lib_type = request.query_params.get('face_lib_type', 'blackFD')
        fdid = request.query_params.get('fdid', '1')

        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        response_data = service.delete_face(face_lib_type, fdid, str(person_pk))
        return Response(response_data)

    @action(detail=True, methods=['get'], url_path='fetch_image')
    def fetch_image(self, request, device_pk=None, person_pk=None, pk=None):
        face_url = request.query_params.get('face_url')
        if not face_url:
            return Response({"error": "face_url is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            device = Device.objects.get(pk=device_pk)
        except Device.DoesNotExist:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

        service = DeviceAPIService(device)
        data = service.fetch_face_image(face_url)
        return Response(data)


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
    
    # def partial_update(self, request, device_pk=None, pk=None):
    #     try:
    #         device = Device.objects.get(pk=device_pk)
    #     except Device.DoesNotExist:
    #         return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

    #     service = DeviceAPIService(device)
    #     week_plan = service.get_week_plan(pk)
    #     serializer = self.serializer_class(week_plan, data=request.data, partial=True)
    #     if serializer.is_valid():
    #         updated_plan = service.update_week_plan(pk, serializer.validated_data)
    #         return Response(updated_plan)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
        if not serializer.is_valid():
            print(serializer.errors)  # <-- Посмотрим, что именно не нравится сериализатору
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        if serializer.is_valid():
            updated_template = service.update_schedule_template(pk, serializer.validated_data)
            return Response(updated_template)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # def partial_update(self, request, device_pk=None, pk=None):
    #     try:
    #         device = Device.objects.get(pk=device_pk)
    #     except Device.DoesNotExist:
    #         return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)

    #     service = DeviceAPIService(device)
    #     schedule_template = service.get_schedule_template(pk)
    #     serializer = self.serializer_class(schedule_template, data=request.data, partial=True)
    #     if serializer.is_valid():
    #         updated_template = service.update_schedule_template(pk, serializer.validated_data)
    #         return Response(updated_template)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# (6) REGION, ORG, USER, ACCESSEVENT VIEWSETS
# =============================================================================



class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    """
    ViewSet только для чтения Regions.
    """
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
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()  
        # user сейчас likely is_active=False, чтобы дождаться активации по почте

        headers = self.get_success_headers(serializer.data)
        return Response(
            {"detail": "Пользователь успешно создан. Проверьте вашу почту для завершения регистрации."},
            status=status.HTTP_201_CREATED,
            headers=headers
        )
    
from rest_framework.decorators import api_view
@api_view(['GET'])
def user_info(request):
    """
    Пример: возвращаем данные текущего пользователя, 
    включая organization и is_main
    """
    user = request.user
    serializer = UserSerializer(user)
    return Response(serializer.data)



class UserLoginView(APIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

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


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes =[AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        parent_id = self.request.query_params.get('parent_id', None)
        if parent_id is not None:
            queryset = queryset.filter(parent_id=parent_id)
        return queryset
    

    


class AccessEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AccessEvent.objects.all()
    serializer_class = AccessEventSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = AccessEventFilter
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Аналогично DeviceViewSet можно фильтровать по организации пользователя.
        Если пользователь относится к parent-организации, показываем все events 
        их child-организаций. Иначе (child) — только свои.
        """
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()

        org = user.organization
        if org.is_main():
            # Допустим, org.get_all_suborganizations() вернёт саму org + все child
            sub_orgs = org.get_all_suborganizations()
            # Фильтруем только события по устройствам, принадлежащим этим организациям
            qs = qs.filter(device__organization__in=sub_orgs)
        else:
            qs = qs.filter(device__organization=org)

        return qs



def UserLogoutView(request):
    logout(request)
    response = redirect('login')  # Перенаправление на страницу логина
    response.delete_cookie('access')
    response.delete_cookie('refresh')
    return response

class ActivateUserView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user and default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            # Можно редиректнуть на фронт, чтобы показать «Аккаунт активирован»
            return redirect("http://localhost:8080/login?activated=1")
        else:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
        

class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        email = request.data.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Обычно не сообщаем, что user не существует (безопасность),
            # но если хотите, можете вернуть ошибку.
            return Response({"detail": "Если пользователь с указанной почтой существует, письмо отправлено."}, status=status.HTTP_200_OK)

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"http://localhost:8080/password-reset-confirm?uid={uid}&token={token}"

        send_mail(
            "Восстановление пароля",
            f"Для сброса пароля перейдите по ссылке: {reset_link}",
            "no-reply@yourapp.com",
            [user.email],
        )
        return Response({"detail": "Письмо со ссылкой для сброса пароля отправлено. \nПройдите по отправленной на почту ссылке!"}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        uidb64 = request.data.get('uid')
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not uidb64 or not token or not new_password:
            return Response({"detail": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None:
            return Response({"detail": "Invalid user"}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return Response({"detail": "Invalid or expired token"}, status=status.HTTP_400_BAD_REQUEST)

        # Всё ок -> устанавливаем новый пароль
        user.set_password(new_password)
        user.save()

        return Response({"detail": "Пароль успешно изменён"}, status=status.HTTP_200_OK)
