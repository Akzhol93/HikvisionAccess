from django.shortcuts import render, redirect
from rest_framework import  generics, viewsets, views,  permissions
from .models import *
from .serializers import *
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404 
from rest_framework.views import APIView
from django.views.generic import TemplateView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.contrib.auth import authenticate, login, logout
from .forms import UserRegistrationForm, UserLoginForm

class DeviceViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Device.objects.all()
    serializer_class   = DeviceSerializer
    #permission_classes = (IsAuthenticated,isVerified)


class PersonViewSet(viewsets.ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = PersonSerializer

    def get_device(self, deviceid):
        try:
            return Device.objects.get(pk=deviceid)
        except Device.DoesNotExist:
            return None
        
    def get_object(self):
        deviceid = self.kwargs['deviceid']
        personpk = self.kwargs['pk']
        device = self.get_device(deviceid)
        if not device:
            raise Http404("Device not found")
        person = device.get_persons(personpk)
        return person

    def list(self, request, deviceid=None):
        device = self.get_device(deviceid)
        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)
        persons = device.get_persons()
        serializer = self.get_serializer(persons, many=True)
        return Response(serializer.data)

   
    def retrieve(self, request, deviceid=None, pk=None):
        person = self.get_object()
        try:
            serializer = self.get_serializer(person)
            data = serializer.data
            return Response(data)
        except Exception:
            return Response(person, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deviceid = kwargs['deviceid']
        device = self.get_device(deviceid)

        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            response = device.add_person(**serializer.validated_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response(response, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        deviceid = self.kwargs['deviceid']
        personpk = self.kwargs['pk']
        device = self.get_device(deviceid)

        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            response = device.edit_person(personpk, **serializer.validated_data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        deviceid = self.kwargs['deviceid']
        personpk = self.kwargs['pk']
        device = self.get_device(deviceid)

        if not device:
            return Response({"error": "Device not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            response = device.delete_person(personpk)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(response, status=status.HTTP_204_NO_CONTENT)




class FaceViewSet(viewsets.ViewSet):
    def create(self, request, deviceid,pk):
        serializer = FaceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            face_lib_type = serializer.validated_data['face_lib_type']
            fdid = serializer.validated_data['fdid']
            image = serializer.validated_data['image']
            device = Device.objects.get(id=deviceid)
            image_data = image.read()
            response_data = device.add_face(face_lib_type, fdid, str(pk), image_data)
            return Response(response_data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, deviceid, pk=None):
        serializer = FaceSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            face_lib_type = serializer.validated_data['face_lib_type']
            fdid = serializer.validated_data['fdid']
            image = serializer.validated_data.get('image')
            device = Device.objects.get(id=deviceid)
            image_data = image.read()
            response_data = device.edit_face(face_lib_type, fdid, str(pk), image_data)
            return Response(response_data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def retrieve(self, request, deviceid, pk=None):
        face_lib_type = request.query_params.get('face_lib_type')
        fdid = request.query_params.get('fdid')
        device = Device.objects.get(id=deviceid)
        response_data = device.get_face(face_lib_type, fdid, str(pk))
        return Response(response_data)
    
    def destroy(self, request, deviceid, pk=None):
        device = Device.objects.get(id=deviceid)
        response_data = device.delete_face(str(pk))
        return Response(response_data)



class WeekPlanViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk=None, wk=None):
        device = Device.objects.get(pk=pk)
        week_plan = device.get_week_plan(wk)
        serializer = UserRightWeekPlanCfgSerializer(week_plan)
        return Response(serializer.data)

    def update(self, request, pk=None, wk=None):
        device = Device.objects.get(pk=pk)
        serializer = UserRightWeekPlanCfgSerializer(data=request.data)
        if serializer.is_valid():
            updated_plan = device.update_week_plan(wk, serializer.validated_data)
            return Response(updated_plan)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def partial_update(self, request, pk=None, wk=None):
        device = Device.objects.get(pk=pk)
        week_plan = device.get_week_plan(wk)
        serializer = UserRightWeekPlanCfgSerializer(week_plan, data=request.data, partial=True)
        if serializer.is_valid():
            updated_plan = device.update_week_plan(wk, serializer.validated_data)
            return Response(updated_plan)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class ScheduleViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk=None, sk=None):
        device = Device.objects.get(pk=pk)
        schedule_template = device.get_schedule_template(sk)
        serializer = UserRightPlanTemplateSerializer(schedule_template)
        return Response(serializer.data)

    def update(self, request, pk=None, sk=None):
        device = Device.objects.get(pk=pk)
        serializer = UserRightPlanTemplateSerializer(data=request.data)
        if serializer.is_valid():
            updated_template = device.update_schedule_template(sk, serializer.validated_data)
            return Response(updated_template)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None, sk=None):
        device = Device.objects.get(pk=pk)
        schedule_template = device.get_schedule_template(sk)
        serializer = UserRightPlanTemplateSerializer(schedule_template, data=request.data, partial=True)
        if serializer.is_valid():
            updated_template = device.update_schedule_template(sk, serializer.validated_data)
            return Response(updated_template)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RegionViewSet(viewsets.ModelViewSet):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    ordering = ['name']  # Упорядочивание регионов по имени по умолчанию

class OrganizationViewSet(viewsets.ModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer  # Сериализатор для создания пользователя
        elif self.request.method in ['PATCH', 'PUT']:
            return UserUpdateSerializer  # Сериализатор для обновления пользователя
        return UserSerializer  # Сериализатор для получения деталей пользователя

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.AllowAny()]  # Для создания нового пользователя доступен всем
        return [permissions.IsAuthenticated()]  # Для всех остальных методов требуется аутентификация
      

class AccessEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AccessEvent.objects.all()
    serializer_class = AccessEventSerializer
    #permission_classes = [permissions.IsAuthenticated]
    

# views.py


class UserRegisterView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        form = UserRegistrationForm()
        return render(request, 'register.html', {'form': form})

    def post(self, request):
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            FIO = form.cleaned_data['FIO']
            phone = form.cleaned_data['phone']
            organizations = form.cleaned_data['organization']
            user = User.objects.create_user(username=username, email=email, password=password, FIO=FIO, phone=phone)
            user.organization.set(organizations)
            user.save()
            refresh = RefreshToken.for_user(user)
            response = redirect('main')  # Перенаправление на главную страницу
            response.set_cookie('access', str(refresh.access_token), httponly=True)
            response.set_cookie('refresh', str(refresh), httponly=True)
            return response
        return render(request, 'register.html', {'form': form})

class UserLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        form = UserLoginForm()
        return render(request, 'login.html', {'form': form})

    def post(self, request):
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                refresh = RefreshToken.for_user(user)
                response = redirect('main')  # Перенаправление на главную страницу
                response.set_cookie('access', str(refresh.access_token), httponly=True)
                response.set_cookie('refresh', str(refresh), httponly=True)
                print('dd',refresh.access_token)
                return response
            return Response({'error': 'Неверное имя пользователя или пароль'}, status=status.HTTP_400_BAD_REQUEST)
        return render(request, 'login.html', {'form': form})


class MainView(TemplateView):
    template_name = 'main.html'
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  # Перенаправление на страницу логина, если пользователь не аутентифицирован
        
        # Получаем связанные с пользователем организации
        organizations = request.user.organization.all()
        
        # Данные о устройствах и их расписаниях
        organization_list = []
        
        for org in organizations:
            devices = Device.objects.filter(organization=org)
            devices_list = []
            for device in devices:
                try:
                    # Получаем расписания шаблонов
                    schedules = {}
                    for plan_template_id in range(1, 4):  # Для plan_template_id от 1 до 3
                        schedule_template = device.get_schedule_template(plan_template_id)
                 
                        if 'UserRightPlanTemplate' in schedule_template:
                            try:
                                week_plan = device.get_week_plan(plan_template_id)
                                week_plan = week_plan['UserRightWeekPlanCfg']
                            
                            except Exception:
                                week_plan = None,
                            
                            schedules[plan_template_id] = {
                                'template': schedule_template['UserRightPlanTemplate'],
                                'week_plan': week_plan
                            }
                        else:
                            schedules[plan_template_id] = None
                except Exception:
                    schedules = None
                
                devices_list.append({
                    'device_id': device.pk,
                    'device_name': device.name,
                    'device_ip': device.ip_address,
                    'device_port': device.port_no,
                    'schedules': schedules
                })
                
            organization_list.append({
                'organization_name': org.name,
                'organization_bin': org.bin,
                'devices': devices_list
            })


        context = {
            'organization_list': json.dumps(organization_list),
         
        }
       
  
        return self.render_to_response(context)

class MyOrganizationsView(TemplateView):
    template_name = 'my_organizations.html'
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  # Перенаправление на страницу логина, если пользователь не аутентифицирован
        return super().get(request, *args, **kwargs)

class ChildrenView(TemplateView):
    template_name = 'children.html'
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  # Перенаправление на страницу логина, если пользователь не аутентифицирован
        return super().get(request, *args, **kwargs)

class ReportsView(TemplateView):
    template_name = 'reports.html'
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  # Перенаправление на страницу логина, если пользователь не аутентифицирован
        return super().get(request, *args, **kwargs)

class DetailsView(TemplateView):
    template_name = 'details.html'
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')  # Перенаправление на страницу логина, если пользователь не аутентифицирован
        return super().get(request, *args, **kwargs)


def UserLogoutView(request):
    logout(request)
    response = redirect('login')  # Перенаправление на страницу логина
    response.delete_cookie('access')
    response.delete_cookie('refresh')
    return response

