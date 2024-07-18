from rest_framework import routers
from django.urls import path, include
from .views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView


# Создаем маршруты вручную для вложенных путей
urlpatterns = [
    # Маршруты для пользователей
    path('users/', UserViewSet.as_view({'post': 'create', 'get': 'list'}), name='user-list'),  # Получить список пользователей и создать нового
    path('users/<int:pk>/', UserViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='user-detail'),  # Получить данные пользователя и обновить его
    
    # Маршруты для работы с токенами
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),  # Получение JWT токенов
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # Обновление JWT токенов

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

    # Маршруты для событий доступа
    path('access-events/', AccessEventViewSet.as_view({'get': 'list'}), name='access-event-list'),  # Получить список событий доступа
    path('access-events/<int:pk>/', AccessEventViewSet.as_view({'get': 'retrieve'}), name='access-event-detail'),  # Получить данные события доступа

]



