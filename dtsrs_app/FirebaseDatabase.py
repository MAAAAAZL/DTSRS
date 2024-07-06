import firebase_admin
from firebase_admin import credentials, exceptions, db

import os


class FirebaseDatabase:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(FirebaseDatabase, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        # Check Firebase initialization status
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.initialize_firebase_admin()

    @staticmethod
    def get_instance():
        if FirebaseDatabase._instance is None:
            FirebaseDatabase()
        return FirebaseDatabase._instance

    # initialize Firebase Admin SDK
    @staticmethod
    def initialize_firebase_admin():
        # Set path for the credential file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        credentials_path = os.path.join(
            script_dir, 'dtsrs-39010-firebase-adminsdk-1jlzc-61844505e2.json')

        # Authenticate and initialize Firebase Admin SDK
        cred = credentials.Certificate(credentials_path)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://dtsrs-39010-default-rtdb.europe-west1.firebasedatabase.app',
            'storageBucket': 'dtsrs-39010.appspot.com'
        })

    @staticmethod
    def fetch_room_area_data():
        # Fetch room area data from Firebase database
        try:
            FirebaseDatabase.get_instance()

            areas_ref = db.reference('room/area/')
            area_data = areas_ref.get()
            return area_data
        except exceptions.FirebaseError as e:
            print(f"Error fetching mode: {e}")

    @staticmethod
    def fetch_room_device_data():
        # Fetch room devices data from Firebase database
        # Nested dictionaries where the first level is category
        try:
            FirebaseDatabase.get_instance()
            devices_ref = db.reference('room/device/')
            device_data = devices_ref.get()
            return device_data
        except exceptions.FirebaseError as e:
            print(f"Error fetching mode: {e}")

    @staticmethod
    def instantiate_all_room_area(area_data):
        area_objs = []
        if area_data:
            for area_id, area_data in area_data.items():
                area_objs.append(Area(area_id, area_data))
        return area_objs

    @staticmethod
    def instantiate_all_room_devices(device_data):
        devices_obj = {}
        if 'rpi' in device_data:
            del device_data['rpi']
        if device_data:
            for category, devices in device_data.items():
                instantiated_device_ls = []
                for device_id, device_data in devices.items():
                    instantiated_device_ls.append(Device(device_id, device_data))
                devices_obj[category] = instantiated_device_ls
        return devices_obj


class Area:
    def __init__(self, area_id, area_data):
        self.area_id = area_id
        self.area_name = area_data.get("area_name", None)
        self.coordinates = area_data.get("coordinates", None)
        self.isEmergency = area_data.get("isEmergency", None)


class Device:
    def __init__(self, device_id, device_data):
        self.device_id = device_id
        self.device_name = device_data.get("device_name", None)
        self.coordinates = device_data.get("coordinates", None)
        self.area = device_data.get("area", None)
        self.type = device_data.get("type", None)
        self.detailed_type = device_data.get("detailed_type", None)
        self.bound_devices = device_data.get("bound_devices", None)
        self.rpi_id = device_data.get("rpi_id", None)
        self.gpio = device_data.get("gpio", None)
        self.auto_mode = device_data.get("auto_mode", None)
        self.target = device_data.get("target", None)
        self.threshold = device_data.get("threshold", None)
        self.isEmergency = device_data.get("isEmergency", None)
