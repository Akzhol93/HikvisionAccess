import os
import django
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Terminal.settings')
django.setup()

from asgiref.sync import sync_to_async
from App.models import Device, AccessEvent
from datetime import datetime
import pytz
import json

app = FastAPI()

@app.post("/")
async def receive_event_log(request: Request):
    """
    Принимаем multipart/form-data, ищем поле 'event_log',
    парсим JSON, проверяем majorEventType/subEventType.
    Если нужные — сохраняем в БД.
    """
    try:
        form = await request.form()
        event_log_str = form.get('event_log')
        if not event_log_str:
            return JSONResponse(
                {"detail": "No event_log field found"},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        dct = json.loads(event_log_str)

        # Если есть AccessControllerEvent, проверяем тип события
        ace = dct.get("AccessControllerEvent", {})
        major = ace.get("majorEventType")
        sub = ace.get("subEventType")

        # Пример фильтрации: берём только major=5 и sub=75
        if major == 5 and sub == 75:
            await save_to_db(dct)
            return JSONResponse({"detail": "OK, event saved"}, status_code=200)

        # Если событие не нужно - игнор
        return JSONResponse({"detail": "Event ignored"}, status_code=200)

    except Exception as e:
        # Выведем traceback в консоль, чтобы видеть, что сломалось
        import traceback
        traceback.print_exc()

        return JSONResponse({"detail": f"Error: {e}"}, status_code=500)


@sync_to_async
def save_to_db(dct):
    """
    Сохранение данных из словаря dct в базу Django ORM.
    Обратите внимание, что если какое-то поле у вас в модели NOT NULL,
    а терминал иногда не присылает его, надо:
      1) либо дать default/значение по умолчанию,
      2) либо разрешить null=True в модели,
      3) либо не сохранять такие события.
    """

    # 1. Парсим дату/время (если приходит строкой ISO-8601 с таймзоной типа "2024-12-29T13:24:37+05:00")
    dt_str = dct.get("dateTime", "")  # может не быть ключа
    date_time = None
    if dt_str:
        # Если формат всегда "YYYY-MM-DDTHH:MM:SS±HH:MM", используем strptime
        try:
            # Попытаемся распарсить с учетом таймзоны
            date_time = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            # Если формат не подошел, можно fallback
            # или просто оставить None — как вам удобнее
            pass

    # 2. Достаём AccessControllerEvent (все поля, которые могут прийти)
    ace = dct.get("AccessControllerEvent", {})

    # 3. Сохраняем (или получаем) устройство
    ip = dct.get("ipAddress", "")
    device, created = Device.objects.get_or_create(
        ip_address=ip,
        defaults={
            "port_no": dct.get("portNo", 0),
            "channel_id": dct.get("channelID", 0),
            "name": ace.get("deviceName", "Unknown"),
            "organization": 0  # или ваша логика
        }
    )

    # 4. Собираем поля для AccessEvent
    # Обязательно проверьте, что эти поля существуют в вашей модели AccessEvent!
    access_event = AccessEvent(
        device=device,
        ipAddress=ip,
        portNo=dct.get("portNo", 0),
        protocol=dct.get("protocol", ""),
        macAddress=dct.get("macAddress", ""),
        channelID=dct.get("channelID", 0),
        dateTime=date_time,
        activePostCount=dct.get("activePostCount", 0),
        eventType=dct.get("eventType", ""),
        eventState=dct.get("eventState", ""),
        eventDescription=dct.get("eventDescription", ""),
        majorEventType=ace.get("majorEventType", 0),
        subEventType=ace.get("subEventType", 0),

        # Пример дополнительных полей (зависит от вашей модели)
        name=ace.get("name", ""),
        employeeNoString=ace.get("employeeNoString", ""),
        userType=ace.get("userType", ""),
        currentVerifyMode=ace.get("currentVerifyMode", ""),
        frontSerialNo=ace.get("frontSerialNo", 0),
        attendanceStatus=ace.get("attendanceStatus", ""),
        label=ace.get("label", ""),
        statusValue=ace.get("statusValue", 0),
        mask=ace.get("mask", ""),
        purePwdVerifyEnable=ace.get("purePwdVerifyEnable", False),

        # Те поля, из-за которых бывает NOT NULL:
        # (Например, cardReaderKind, cardReaderNo, verifyNo, serialNo и т.д.)
        cardReaderKind=ace.get("cardReaderKind", 0),
        cardReaderNo=ace.get("cardReaderNo", 0),
        verifyNo=ace.get("verifyNo", 0),
        serialNo=ace.get("serialNo", 0),
    )

    access_event.save()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("tcp_server:app", host="0.0.0.0", port=8088, reload=True, log_level="debug")
