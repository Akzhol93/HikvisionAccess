import django_filters
from .models import AccessEvent

class AccessEventFilter(django_filters.FilterSet):
    """
    Фильтр для AccessEvent.
    Фильтруем:
    - dateTime: два поля для интервала (gte, lte)
    - device: точное совпадение по device_id
    - eventType: содержит (icontains) или точное совпадение (exact), решите сами
    - name: человек (personName) - например, icontains
    - employeeNoString: personID - icontains или exact
    """
    date_from = django_filters.DateTimeFilter(
        field_name='dateTime', lookup_expr='gte'
    )
    date_to = django_filters.DateTimeFilter(
        field_name='dateTime', lookup_expr='lte'
    )
    device = django_filters.NumberFilter(field_name='device', lookup_expr='exact')
    eventType = django_filters.CharFilter(field_name='eventType', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    employeeNoString = django_filters.CharFilter(field_name='employeeNoString', lookup_expr='icontains')
    # Новое поле:
    organization = django_filters.NumberFilter(field_name='device__organization', lookup_expr='exact')


    class Meta:
        model = AccessEvent
        # Поля, которые хотим разрешить для фильтрации.
        # Важно, чтобы совпадали с полями выше
        fields = ['date_from', 'date_to', 'device', 'eventType', 'name', 'employeeNoString', 'organization']
