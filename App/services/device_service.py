import requests
import json
import random
import string

from requests.auth import HTTPDigestAuth


class DeviceAPIService:
    """
    Сервис для взаимодействия с удалённым устройством по HTTP/ISAPI
    """

    def __init__(self, device):
        """
        При инициализации сервису передаётся объект модели Device.
        Все настройки (ip_address, port_no, login, password и т.д.)
        берем из device.
        """
        self.device = device

    def _create_session(self):
        """
        Создаёт сессию c HTTP Digest авторизацией и базовыми заголовками.
        """
        session = requests.Session()
        session.auth = HTTPDigestAuth(self.device.login, self.device.password)
        session.headers.update({
            'Content-Type': "application/xml; charset=UTF-8",
            'Accept': 'text/html'
        })
        return session

    def get_capabilities(self):
        """
        Получает capabilities с устройства и сохраняет max_record_num, max_results в self.device
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/capabilities?format=json'
        session = self._create_session()
        data = {}
        try:
            response = session.get(path)
            response.raise_for_status()
            data = response.json()

            # Обновляем поля в модели Device
            self.device.max_record_num = data['UserInfo']['maxRecordNum']
            self.device.max_results = data['UserInfo']['UserInfoSearchCond']['maxResults']['@max']
            self.device.save()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
        finally:
            session.close()
        return data

    def get_schedule_template(self, plan_template_id):
        """
        Пример GET-запроса
        """
        url = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserRightPlanTemplate/{plan_template_id}?format=json'
        session = self._create_session()
        data = {}
        try:
            response = session.get(url)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
        finally:
            session.close()
        return data

    def update_schedule_template(self, plan_template_id, payload):
        """
        Пример PUT-запроса
        """
        url = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserRightPlanTemplate/{plan_template_id}?format=json'
        session = self._create_session()
        data = {}
        try:
            response = session.put(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
        finally:
            session.close()
        return data

    def get_week_plan(self, week_plan_id):
        url = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserRightWeekPlanCfg/{week_plan_id}?format=json'
        session = self._create_session()
        data = {}
        try:
            response = session.get(url)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
        finally:
            session.close()
        return data

    def update_week_plan(self, week_plan_id, payload):
        url = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserRightWeekPlanCfg/{week_plan_id}?format=json'
        session = self._create_session()
        data = {}
        try:
            response = session.put(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
        finally:
            session.close()
        return data

    def get_persons(self, employee_no=None):
        """
        Получение списка/одного пользователя с устройства
        """
        # Если max_record_num или max_results не заполнены, сначала вызовем get_capabilities()
        if self.device.max_record_num is None or self.device.max_results is None:
            self.get_capabilities()

        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/Search?format=json'
        session = self._create_session()
        data = {}

        if employee_no is None:
            # Возвращаем всех
            persons_list = []
            position = 0
            while position < self.device.max_record_num:
                body = {
                    "UserInfoSearchCond": {
                        "searchID": "0",
                        "searchResultPosition": position,
                        "maxResults": self.device.max_results
                    }
                }
                try:
                    response = session.post(path, data=json.dumps(body))
                    response.raise_for_status()
                    data = response.json()
                    num_of_matches = data["UserInfoSearch"]['numOfMatches']

                    if num_of_matches == 0:
                        break
                    guests = data["UserInfoSearch"].get("UserInfo", [])
                    persons_list.extend(guests)
                    if num_of_matches < self.device.max_results:
                        break
                    position += self.device.max_results
                except requests.exceptions.RequestException as e:
                    print(f'HTTP Request failed: {e}')
                    break
            session.close()
            return persons_list
        else:
            # Возвращаем одного
            body = {
                "UserInfoSearchCond": {
                    "searchID": "0",
                    "searchResultPosition": 0,
                    "maxResults": 1,
                    "EmployeeNoList": [{"employeeNo": str(employee_no)}]
                }
            }
            try:
                response = session.post(path, data=json.dumps(body))
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.RequestException as e:
                print(f'HTTP Request failed: {e}')
            finally:
                session.close()
            return data

    def add_person(self, employee_no, name, user_type, valid, **kwargs):
        """
        Добавить нового пользователя (person) на устройство
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/Record?format=json'
        session = self._create_session()
        body = {
            "UserInfo": {
                "employeeNo": str(employee_no),
                "name": name,
                "userType": user_type,
                "Valid": valid,
                "doorRight": "1",
                "RightPlan": [
                    {
                        "doorNo": 1,
                        "planTemplateNo": "1"
                    }
                ],
            }
        }
        body['UserInfo'].update(kwargs)

        data = {}
        try:
            response = session.post(path, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if response is not None:
                data = response.json()
        finally:
            session.close()
        return data

    def edit_person(self, employee_no, **kwargs):
        """
        Редактировать данные пользователя
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/Modify?format=json'
        session = self._create_session()
        body = {
            "UserInfo": {"employeeNo": str(employee_no)}
        }
        body["UserInfo"].update(kwargs)

        data = {}
        try:
            response = session.put(path, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if response is not None:
                data = response.json()
        finally:
            session.close()
        return data

    def delete_person(self, employee_no):
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/Delete?format=json'
        session = self._create_session()
        body = {
            "UserInfoDelCond": {
                "EmployeeNoList": [{"employeeNo": str(employee_no)}]
            }
        }

        data = {}
        try:
            response = session.put(path, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if response is not None:
                data = response.json()
        finally:
            session.close()
        return data

    def add_face(self, face_lib_type, fdid, employee_no, image_data):
        """
        Добавить лицо (face) к пользователю.
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json'
        session = self._create_session()
        boundary = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))

        json_data = {
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": str(employee_no),
            "bornTime": "2004-05-03"
        }

        body = (
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="FaceDataRecord"\r\n'
            'Content-Type: application/json\r\n\r\n'
            + json.dumps(json_data) + '\r\n'
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="face_image"; filename="image.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\n'
        ).encode('utf-8') + image_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}'
        }

        data = {}
        try:
            response = session.post(path, data=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if response is not None:
                data = response.json()
        finally:
            session.close()

        return data

    def edit_face(self, face_lib_type, fdid, employee_no, image_data):
        """
        Изменить (перезаписать) данные лица (face) пользователя
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/Intelligent/FDLib/FDModify?format=json'
        session = self._create_session()
        boundary = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))

        json_data = {
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": str(employee_no),
        }

        body = (
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="FaceDataRecord"\r\n'
            'Content-Type: application/json\r\n\r\n'
            + json.dumps(json_data) + '\r\n'
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="face_image"; filename="image.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\n'
        ).encode('utf-8') + image_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

        headers = {
            'Content-Type': f'multipart/form-data; boundary={boundary}'
        }

        data = {}
        try:
            response = session.put(path, data=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if response is not None:
                data = response.json()
        finally:
            session.close()
        return data

    def get_face(self, face_lib_type, fdid, fpid):
        """
        Получить данные о лице (face) по FID/FPID
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/Intelligent/FDLib/FDSearch?format=json'
        session = self._create_session()

        body = {
            "searchResultPosition": 0,
            "maxResults": 1,
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": fpid,
        }

        data = {}
        try:
            response = session.post(path, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if response is not None:
                data = response.json()
        finally:
            session.close()
        return data

    def delete_face(self, employee_no):
        """
        Удалить лицо (face) по FPID
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/Intelligent/FDLib/FDSearch/Delete?format=json&FDID=1&faceLibType=blackFD'
        session = self._create_session()
        json_data = {
            "FPID": [
                {
                    "value": str(employee_no),
                }
            ],
        }

        data = {}
        try:
            response = session.put(path, data=json.dumps(json_data))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if response is not None:
                data = response.json()
        finally:
            session.close()
        return data
