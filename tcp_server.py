import asyncio
import re,os,django
import json
from datetime import datetime
from asgiref.sync import sync_to_async
import pytz

# Установка переменной окружения для указания на файл настроек Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Terminal.settings')
django.setup()
from App.models import Device,AccessEvent,Organization

# Убедитесь, что у вас есть функции для подключения к базе данных, если они нужны
# from postgre.connect import *

async def get_dict(txt):
    try:
        subs_start = 'Content-Disposition: form-data; name="event_log"'
        subs_end = '--MIME_boundary--'

        idx1 = txt.find(subs_start)
        idx2 = txt.find(subs_end)

        if idx1 == -1 or idx2 == -1:
            raise ValueError("Cannot find start or end of event_log")

        res = txt[idx1 + len(subs_start) + 1: idx2].strip()
        
        # Removing unnecessary characters
        res = res.strip('\r\n')
        dct = json.loads(res)
        
        time_format = "%Y-%m-%dT%H:%M:%S%z" 
        dct['dateTime'] = datetime.strptime(dct['dateTime'], time_format)
        return dct
    except Exception as e:
        print(f"Error processing data: {e}")
        return None

@sync_to_async
def create_access_event(device, dct):
    date_time = dct['dateTime']
    
    if date_time.tzinfo is None:
        # Добавляем временную зону, если она отсутствует
        date_time = date_time.replace(tzinfo=pytz.UTC)

    access_event = AccessEvent(
        device=device,
        ipAddress=dct['ipAddress'],
        portNo=dct['portNo'],
        protocol=dct['protocol'],
        macAddress=dct['macAddress'],
        channelID=dct['channelID'],
        dateTime=date_time,
        activePostCount=dct['activePostCount'],
        eventType=dct['eventType'],
        eventState=dct['eventState'],
        eventDescription=dct['eventDescription'],
        deviceName=dct['AccessControllerEvent']['deviceName'],
        majorEventType=dct['AccessControllerEvent']['majorEventType'],
        subEventType=dct['AccessControllerEvent']['subEventType'],
        name=dct['AccessControllerEvent']['name'],
        cardReaderKind=dct['AccessControllerEvent']['cardReaderKind'],
        cardReaderNo=dct['AccessControllerEvent']['cardReaderNo'],
        verifyNo=dct['AccessControllerEvent']['verifyNo'],
        employeeNoString=dct['AccessControllerEvent']['employeeNoString'],
        serialNo=dct['AccessControllerEvent']['serialNo'],
        userType=dct['AccessControllerEvent']['userType'],
        currentVerifyMode=dct['AccessControllerEvent']['currentVerifyMode'],
        frontSerialNo=dct['AccessControllerEvent']['frontSerialNo'],
        attendanceStatus=dct['AccessControllerEvent']['attendanceStatus'],
        label=dct['AccessControllerEvent']['label'],
        statusValue=dct['AccessControllerEvent']['statusValue'],
        mask=dct['AccessControllerEvent']['mask'],
        purePwdVerifyEnable=dct['AccessControllerEvent']['purePwdVerifyEnable'],
    )
    access_event.save()
    return access_event

async def client_connected_cb(reader, writer):
    try:
        data = await reader.read(1024)
        message = data.decode()
        print(f"Received data : {message}")  # Выводим данные для отладки
        dct = await get_dict(message)

        if dct.get('AccessControllerEvent') and dct['AccessControllerEvent']['majorEventType'] == 5 \
                and dct['AccessControllerEvent']['subEventType'] == 75:
            try:
                
                # Получаем или создаем устройство по его MAC-адресу
                device, created = await sync_to_async(Device.objects.get_or_create)(
                ip_address=dct['ipAddress'],
                defaults={
                    'port_no': dct['portNo'],
                    'channel_id': dct['channelID'],
                    'name': dct['AccessControllerEvent']['deviceName'],
                    'login': '',  # Задайте логин и пароль в соответствии с вашей логикой
                    'password': '',
                    'organization':  0
                    }
                )
    
                # Создаем экземпляр AccessEvent и сохраняем его
                await create_access_event(device, dct)
         
            except Exception as e:
                print(f"Error during client communication(1): {e}")

        addr = writer.get_extra_info('peername')
        #print(f"Received from {addr!r}")
        responseString = "HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n"
        responseBytes = responseString.encode()
        writer.write(responseBytes)
        await writer.drain()
    except Exception as e:
        print(f"Error during client communication(2): {e}")
    finally:
        #print("Closing the connection")
        writer.close()
        await writer.wait_closed()

async def main():

    server = await asyncio.start_server(
        client_connected_cb, '0.0.0.0', 8088)

    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Serving on {addrs}')

    async with server:
        await server.serve_forever()

asyncio.run(main())

