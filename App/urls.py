from rest_framework import routers
from django.urls import path, include
from .views import *


# Создаем маршруты вручную для вложенных путей
urlpatterns = [
    # Маршруты для устройств
    path('devices/', DeviceViewSet.as_view({'get': 'list'}), name='device-list'),
    path('devices/<int:pk>/', DeviceViewSet.as_view({'get': 'retrieve'}), name='device-detail'),

    # Маршруты для расписания времени
    path('devices/<int:pk>/weekplan/<int:wk>/', WeekPlanViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='weekplan-detail'),
    path('devices/<int:pk>/schedule/<int:sk>/', ScheduleViewSet.as_view({'get': 'retrieve', 'put': 'update'}), name='schedule-detail'),

    # Маршруты для персон
    path('devices/<int:deviceid>/persons/', PersonViewSet.as_view({'get': 'list', 'post': 'create'}), name='person-list'),
    path('devices/<int:deviceid>/persons/<int:pk>/', PersonViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='person-detail'),
    
    # Маршруты для лиц
    path('devices/<int:deviceid>/persons/<int:pk>/face/', FaceViewSet.as_view({'post': 'create', 'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='face-detail'),

]
