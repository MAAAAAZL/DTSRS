from threading import Lock
from FirebaseDatabase import FirebaseDatabase


class RoomDataManager:
    _instance = None
    _lock = Lock()

    def __init__(self):
        self._room_data = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(RoomDataManager, cls).__new__(cls)
                cls._room_data = {}
        return cls._instance

    @property
    def room_data(self):
        return self._room_data

    @room_data.setter
    def room_data(self, value):
        self._room_data = value

    def update_room_data_from_firebase(self):
        """Update _room_data attribute"""
        room_area_data = FirebaseDatabase.fetch_room_area_data()
        room_device_data = FirebaseDatabase.fetch_room_device_data()
        room_area = FirebaseDatabase.instantiate_all_room_area(room_area_data)
        room_device = FirebaseDatabase.instantiate_all_room_devices(room_device_data)

        self._room_data = {"area": room_area, "device": room_device}

