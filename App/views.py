from django.shortcuts import render
from rest_framework import  generics, viewsets, views
from .models import *
from .serializers import *
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404 


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
