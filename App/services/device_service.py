import requests
import json
import random
import string
import base64


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
            'Content-Type': 'application/json; charset=UTF-8',
            'Accept': 'application/json'
        })
        return session

    def get_capabilities(self):
        """
        Получает capabilities с устройства и сохраняет max_record_num, max_results в self.device
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/capabilities?format=json'
        session = self._create_session()
        data = {}
        success = False
        try:
            response = session.get(path)
            response.raise_for_status()
            data = response.json()

            # Обновляем поля в модели Device
            self.device.max_record_num = data['UserInfo']['maxRecordNum']
            self.device.max_results = data['UserInfo']['UserInfoSearchCond']['maxResults']['@max']
            self.device.save()
            success = True
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
        finally:
            session.close()
        return success

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

    def get_persons(self, employeeNo=None):
        """
        Получение списка/одного пользователя с устройства
        """
        # Если max_record_num или max_results не заполнены, сначала вызовем get_capabilities()
        if self.device.max_record_num is None or self.device.max_results is None:
            self.get_capabilities()

        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/Search?format=json'
        session = self._create_session()
        data = {}

        #если employeeNo = None то возвращаем список всех
        if employeeNo is None:
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
        #если нет то возвращаем с указанным employeeNo
        else:
            # Возвращаем одного
            body = {
                "UserInfoSearchCond": {
                    "searchID": "0",
                    "searchResultPosition": 0,
                    "maxResults": 1,
                    "EmployeeNoList": [{"employeeNo": str(employeeNo)}]
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

    def add_person(self, employeeNo, name, userType, Valid, **kwargs):
        """
        Добавить нового пользователя (person) на устройство
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/Record?format=json'
        session = self._create_session()
        body = {
            "UserInfo": {
                "employeeNo": str(employeeNo),
                "name": name,
                "userType": userType,
                "Valid": Valid,
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

    def edit_person(self, employeeNo, **kwargs):
        """
        Редактировать данные пользователя
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/Modify?format=json'
        session = self._create_session()
        body = {
            "UserInfo": {"employeeNo": str(employeeNo)}
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

    def delete_person(self, employeeNo):
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/AccessControl/UserInfo/Delete?format=json'
        session = self._create_session()
        body = {
            "UserInfoDelCond": {
                "EmployeeNoList": [{"employeeNo": str(employeeNo)}]
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
    def add_face(self, face_lib_type, fdid, employeeNo, image_data):
        """
        Добавить лицо (face) к пользователю (POST FaceDataRecord).
        Внимание: используем form-data, именуя части "faceURL" и "img".
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json'
        session = self._create_session()
        boundary = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))

        # Формируем JSON для первой части (faceURL)
        json_data = {
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": employeeNo,
            "name": "John Doe",    # Пример, можно передать имя
            "gender": "male",      # Пример
            "bornTime": "2000-01-01",
        }

        body = (
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="faceURL"\r\n'
            'Content-Type: application/json\r\n\r\n'
            + json.dumps(json_data) + '\r\n'
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="img"; filename="faceImage.jpg"\r\n'
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
            if 'response' in locals() and response is not None:
                try:
                    data = response.json()
                except:
                    data = {"error": str(e)}
        finally:
            session.close()

        return data

    def edit_face(self, face_lib_type, fdid, employeeNo, image_data):
        """
        Изменить (перезаписать) данные лица.
        Документация: PUT /ISAPI/Intelligent/FDLib/FDModify?format=json
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/Intelligent/FDLib/FDModify?format=json'
        session = self._create_session()
        boundary = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))

        # Аналогично: form-data, именуем части "faceURL" и "img"
        json_data = {
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": employeeNo,
            "name": "John Updated",
            "bornTime": "2000-01-01"
        }

        body = (
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="faceURL"\r\n'
            'Content-Type: application/json\r\n\r\n'
            + json.dumps(json_data) + '\r\n'
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="img"; filename="faceImage.jpg"\r\n'
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
            if 'response' in locals() and response is not None:
                try:
                    data = response.json()
                except:
                    data = {"error": str(e)}
        finally:
            session.close()
        return data

    def get_face(self, face_lib_type, fdid, fpid):
        """
        POST /ISAPI/Intelligent/FDLib/FDSearch?format=json
        """
        path = f'http://{self.device.ip_address}:{self.device.port_no}/ISAPI/Intelligent/FDLib/FDSearch?format=json'
        session = self._create_session()

        body = {
            "searchResultPosition": 0,
            "maxResults": 1,
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": fpid
        }

        data = {}
        try:
            response = session.post(path, json=body)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if 'response' in locals() and response is not None:
                try:
                    data = response.json()
                except:
                    data = {"error": str(e)}
        finally:
            session.close()
        return data

    def delete_face(self, face_lib_type, fdid, employeeNo):
        """
        Удалить лицо (face) по FPID:
        PUT /ISAPI/Intelligent/FDLib/FDSearch/Delete?format=json&FDID=<fdid>&faceLibType=<face_lib_type>
        """
        path = (
            f'http://{self.device.ip_address}:{self.device.port_no}'
            f'/ISAPI/Intelligent/FDLib/FDSearch/Delete?format=json'
            f'&FDID={fdid}&faceLibType={face_lib_type}'
        )
        session = self._create_session()
        json_data = {
            "FPID": [
                {"value": str(employeeNo)}
            ],
            # В некоторых прошивках нужен operateType
            "operateType": "byDevice"
        }

        data = {}
        try:
            response = session.put(path, json=json_data)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            if 'response' in locals() and response is not None:
                try:
                    data = response.json()
                except:
                    data = {"error": str(e)}
        finally:
            session.close()
        return data

    def fetch_face_image(self, face_url):
        """
        Скачиваем фото по face_url, возвращаем base64
        """
        session = self._create_session()
        data = {}
        try:
            r = session.get(face_url, stream=False)
            r.raise_for_status()
            data["image_data"] = base64.b64encode(r.content).decode('utf-8')
        except requests.exceptions.RequestException as e:
            data["error"] = str(e)
        finally:
            session.close()

        return data
