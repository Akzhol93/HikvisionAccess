from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Импортируем ваши вьюхи
from .views import *

# 1. Основной роутер для главных сущностей
router = DefaultRouter()
router.register('api/users', UserViewSet, basename='users')
router.register('api/devices', DeviceViewSet, basename='devices')
router.register('api/access-events', AccessEventViewSet, basename='access-events')

router.register('api/regions', RegionViewSet, basename='regions')
router.register('api/organizations', OrganizationViewSet, basename='organizations')
# Если вы хотите полноценный CRUD для них — в самих ViewSet нужно иметь serializer_class и методы.

# 2. Вложенный роутер для связки "device -> persons"
#  URL вида: /devices/{device_id}/persons/
devices_router = NestedDefaultRouter(router, 'api/devices', lookup='device')
devices_router.register('persons', PersonViewSet, basename='device-persons')

# 3. Вложенный роутер для связки "person -> face"
#  URL вида: /devices/{device_id}/persons/{person_id}/face/
persons_router = NestedDefaultRouter(devices_router, 'persons', lookup='person')
persons_router.register('face', FaceViewSet, basename='person-face')

# 4. Вложенные роуты для schedule, weekplan, если они тоже зависят от device
#  URL вида: /devices/{device_id}/schedule/{pk}/, /devices/{device_id}/weekplan/{pk}/
devices_router.register('schedule', ScheduleViewSet, basename='device-schedule')
devices_router.register('weekplan', WeekPlanViewSet, basename='device-weekplan')

urlpatterns = [
    path('api/login/', UserLoginView.as_view(), name='login'),
    path('api/logout/', UserLogoutView, name='logout'),  # Выход из системы

    path('api/users/activate/<uidb64>/<token>/', ActivateUserView.as_view(), name='user_activate'),
    path('api/users/password_reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('api/users/password_reset_confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),


    # ============ JWT-токены ===============
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # ============ Подключаем наши роуты ===============
    path('', include(router.urls)),            # /users/ /devices/ /access-events/
    path('', include(devices_router.urls)),    # /devices/{device_id}/persons/ /devices/{device_id}/schedule/ ...
    path('', include(persons_router.urls)),    # /devices/{device_id}/persons/{person_id}/face/
   
    path('api/user_info/', user_info, name='user_info'),
]




