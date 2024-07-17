from django.db import models
from  django.core.validators  import RegexValidator
import requests
from requests.auth import HTTPDigestAuth
import xmltodict, json
import random
import string

from django.contrib.auth.models import (
    AbstractBaseUser, BaseUserManager, PermissionsMixin)
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.translation import gettext_lazy as _



#validators
Validator_IIN_BIIN = RegexValidator(r'^\d{12}$', message="IIN or BIN must be 12 digits")


# Handbook models
class Region(models.Model):

    number = models.PositiveSmallIntegerField(unique=True)
    name   = models.CharField(unique=True)

    class Meta:
        verbose_name        = '(Handbook) Region'
        verbose_name_plural = '(Handbook) Regions'

    def __str__(self):
        return self.name

class Organization(models.Model):

    bin       = models.CharField(validators=[Validator_IIN_BIIN], unique=True)
    number    = models.PositiveSmallIntegerField()
    name      = models.CharField()
    region    = models.ForeignKey(Region, on_delete= models.PROTECT)
    
    class Meta:
        verbose_name        = '(Handbook) School'
        verbose_name_plural = '(Handbook) Schools'

    def __str__(self):
        return self.region.name + self.name


class Device(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    ip_address = models.CharField(max_length=25)
    port_no = models.IntegerField()
    channel_id = models.IntegerField()
    name = models.CharField(max_length=25)
    login = models.CharField(max_length=25)
    password = models.CharField(max_length=25)
    max_record_num = models.IntegerField(null=True, blank=True, default=None)
    max_results = models.IntegerField(null=True, blank=True, default=None)
    
    class Meta:
        verbose_name = '(Basic) Device'
        verbose_name_plural = '(Basic) Devices'

    def __str__(self):
        return self.name

    def _create_session(self):
        session = requests.Session()
        session.auth = HTTPDigestAuth(self.login, self.password)
        session.headers.update({
            'Content-Type': "application/xml; charset='UTF-8'",
            'Accept': 'text/html'
        })
        return session

    def get_capabilities(self):
        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserInfo/capabilities?format=json'
        session = self._create_session()
        try:
            response = session.get(path)
            response.raise_for_status()
            data = response.json()
            self.max_record_num = data['UserInfo']['maxRecordNum']
            self.max_results = data['UserInfo']['UserInfoSearchCond']['maxResults']['@max']
            self.save()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
        finally:
            session.close()

    def get_persons(self, employee_no=None):
        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserInfo/Search?format=json'
        session = self._create_session()
        
        if employee_no is None:
            persons_list = []
            position = 0

            while position < self.max_record_num:
                body = {
                    "UserInfoSearchCond": {
                        "searchID": "0",
                        "searchResultPosition": position,
                        "maxResults": self.max_results
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
                    if num_of_matches < self.max_results:
                        break
                    position += self.max_results
                except requests.exceptions.RequestException as e:
                    print(f'HTTP Request failed: {e}')
                    break

            session.close()
            return persons_list
        else:
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
                
                session.close()
                if data["UserInfoSearch"]['numOfMatches'] > 0:
                    return data["UserInfoSearch"]["UserInfo"][0]
                return  json.loads(response.text)
            except requests.exceptions.RequestException as e:
                print(f'HTTP Request failed: {e}')
                session.close()
                return json.loads(response.text)

    def add_person(self, employeeNo, name, userType, Valid, **kwargs):

        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserInfo/Record?format=json'
        session = self._create_session()
        body = {
            "UserInfo": {
                "employeeNo": str(employeeNo),
                "name": name,
                "userType": userType,
                "Valid": Valid,
                "doorRight": "1",
                "RightPlan":[{
                        "doorNo": 1,
                        "planTemplateNo":"1"
                        }],
            }
        }
        body['UserInfo'].update(kwargs)
        
        try:
            response = session.post(path, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            data = json.loads(response.text)
        finally:
            session.close()
        return data

    def edit_person(self, employee_no, **kwargs):
        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserInfo/Modify?format=json'
        session = self._create_session()
        body = {
            "UserInfo": {"employeeNo": str(employee_no)}
        }
        body['UserInfo'].update(kwargs)
        
        try:
            response = session.put(path, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            data =  json.loads(response.text)
        finally:
            session.close()
        return data

    def delete_person(self, employee_no):
        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserInfo/Delete?format=json'
        session = self._create_session()
        body = {
            "UserInfoDelCond": {
                "EmployeeNoList": [{"employeeNo": str(employee_no)}]
            }
        }
        try:
            response = session.put(path, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            data = json.loads(response.text)
        finally:
            session.close()
        return data
#------------------------------------------------------------------------------------------------------------------

    def add_face(self, face_lib_type, fdid, employeeNo, image_data):
      
        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/Intelligent/FDLib/FaceDataRecord?format=json'
        session = self._create_session()
        boundary = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))

        json_data = {
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": employeeNo,
            "bornTime": "2004-05-03",
        }

        body = (
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="FaceDataRecord"\r\n'
            'Content-Type: application/json\r\n\r\n'
            + json.dumps(json_data)+'\r\n'
            f'--{boundary}\r\n'
            'Content-Disposition: form-data; name="face_image"; filename="image.jpg"\r\n'
            'Content-Type: image/jpeg\r\n\r\n'
            ).encode('utf-8') + image_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
        
        headers = {
        'Content-Type': f'multipart/form-data; boundary={boundary}'
        }
        
        try:
            response = session.post(path, data=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            data = json.loads(response.text)
        finally:
            session.close()
        return data
    
    def edit_face(self, face_lib_type, fdid, employeeNo, image_data):
        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/Intelligent/FDLib/FDModify?format=json'
        session = self._create_session()
        boundary = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(30))

        json_data = {
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": employeeNo,
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

        try:
            response = session.put(path, data=body, headers=headers)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            data = json.loads(response.text)
        finally:
            session.close()
        return data

    def get_face(self, face_lib_type, fdid, fpid):
        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/Intelligent/FDLib/FDSearch?format=json'

        session = self._create_session()

        body = {
            "searchResultPosition": 0,
            "maxResults": 1,
            "faceLibType": face_lib_type,
            "FDID": fdid,
            "FPID": fpid,
        }

        try:
            response = session.post(path, data=json.dumps(body))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            data = json.loads(response.text)

        session.close()
        return data
    
    def delete_face(self, employeeNo):
        path = f'http://{self.ip_address}:{self.port_no}/ISAPI/Intelligent/FDLib/FDSearch/Delete?format=json&FDID=1&faceLibType=blackFD'
        session = self._create_session()
        json_data = {
            "FPID": [
                {
                    "value": str(employeeNo),
                }
            ],
        }   
        try:
            response = session.put(path, data=json.dumps(json_data))
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as e:
            print(f'HTTP Request failed: {e}')
            data = json.loads(response.text)
        finally:
            session.close()
        return data
#------------------------------------------------------------------------------------------------------------

    def get_schedule_template(self, plan_template_id):
        url = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserRightPlanTemplate/{plan_template_id}?format=json'
        session = self._create_session()
        response = session.get(url)
        response.raise_for_status()
        return response.json()

    def update_schedule_template(self, plan_template_id, data):
        url = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserRightPlanTemplate/{plan_template_id}?format=json'
        session = self._create_session()
        response = session.put(url, json=data)
        response.raise_for_status()
        return response.json()

    def get_week_plan(self, week_plan_id):
        url = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserRightWeekPlanCfg/{week_plan_id}?format=json'
        session = self._create_session()
        response = session.get(url)
        response.raise_for_status()
        return response.json()

    def update_week_plan(self, week_plan_id, data):
        url = f'http://{self.ip_address}:{self.port_no}/ISAPI/AccessControl/UserRightWeekPlanCfg/{week_plan_id}?format=json'
        session = self._create_session()
        response = session.put(url, json=data)
        response.raise_for_status()
        return response.json()


class AccessEvent(models.Model):
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    ipAddress = models.CharField(max_length=15)
    portNo = models.IntegerField()
    protocol = models.CharField(max_length=10)
    macAddress = models.CharField(max_length=17)
    channelID = models.IntegerField()
    dateTime = models.DateTimeField()
    activePostCount = models.IntegerField()
    eventType = models.CharField(max_length=50)
    eventState = models.CharField(max_length=20)
    eventDescription = models.CharField(max_length=100)
    
    # AccessControllerEvent fields
    deviceName = models.CharField(max_length=50)
    majorEventType = models.IntegerField()
    subEventType = models.IntegerField()
    name = models.CharField(max_length=50)
    cardReaderKind = models.IntegerField()
    cardReaderNo = models.IntegerField()
    verifyNo = models.IntegerField()
    employeeNoString = models.CharField(max_length=50)
    serialNo = models.IntegerField()
    userType = models.CharField(max_length=20)
    currentVerifyMode = models.CharField(max_length=20)
    frontSerialNo = models.IntegerField()
    attendanceStatus = models.CharField(max_length=20)
    label = models.CharField(max_length=50)
    statusValue = models.IntegerField()
    mask = models.CharField(max_length=5)
    purePwdVerifyEnable = models.BooleanField()

    def __str__(self):
        return f"Access Event {self.id} - {self.dateTime}"



# class CustomUserManager(BaseUserManager):
#     def create_user(self, username, email, password=None, **extra_fields):
#         if not username:
#             raise ValueError('The Username field must be set')
#         if not email:
#             raise ValueError('The Email field must be set')
#         email = self.normalize_email(email)
#         user = self.model(username=username, email=email, **extra_fields)
#         user.set_password(password)
#         user.save(using=self._db)
#         return user

#     def create_superuser(self, username, email, password=None, **extra_fields):
#         extra_fields.setdefault('is_staff', True)
#         extra_fields.setdefault('is_superuser', True)
#         return self.create_user(username, email, password, **extra_fields)


# class User(AbstractBaseUser, PermissionsMixin):
#     username = models.CharField(
#         max_length=150,
#         unique=True,
#         validators=[UnicodeUsernameValidator()],
#     )
#     email = models.EmailField(_("email address"), unique=True, db_index=True)
#     FIO = models.CharField(_("FIO"), max_length=55)
#     phone = models.CharField(_("phone"), max_length=15)
#     organization = models.ManyToManyField('Organization', blank=True)

#     is_active = models.BooleanField(default=True)
#     is_staff = models.BooleanField(default=False)
#     date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
#     updated_at = models.DateTimeField(auto_now=True)
#     approved = models.BooleanField(default=False)
#     is_verified = models.BooleanField(default=False)

#     objects = CustomUserManager()

#     USERNAME_FIELD = 'username'
#     REQUIRED_FIELDS = ['email']

#     class Meta:
#         verbose_name = _("user")
#         verbose_name_plural = _("users")

#     def __str__(self):
#         return self.username

#     def clean(self):
#         super().clean()
#         self.email = self.__class__.objects.normalize_email(self.email)

#     def email_user(self, subject, message, from_email=None, **kwargs):
#         """Send an email to this user."""
#         send_mail(subject, message, from_email, [self.email], **kwargs)
