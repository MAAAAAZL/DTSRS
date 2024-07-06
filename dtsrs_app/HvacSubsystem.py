import wx
import wx.adv
import datetime
import pytz

from firebase_admin import db

from FirebaseDatabase import FirebaseDatabase
from RoomDataManager import RoomDataManager


class HvacSubsystem:
    def __init__(self):
        pass

    @staticmethod
    def get_or_set_air_auto_mode():
        FirebaseDatabase.get_instance()
        ref = db.reference('settings/hvac/isAirQualityAutoMode')

        isAirQualityAutoMode = ref.get()

        if isAirQualityAutoMode is None:
            ref.set(False)
            return False
        else:
            return isAirQualityAutoMode

    @staticmethod
    def get_or_set_hvac_auto_mode():
        FirebaseDatabase.get_instance()
        ref = db.reference(f'settings/hvac/')
        data = ref.get()

        default_values = {
            "autoTemperatureValue": 25.0,
            "autoHumidityValue": 40.0,
            "autoAirQualityValue": 30.0
        }

        values = {
            "isTemperatureAutoMode": None,
            "autoTemperatureValue": None,
            "isHumidityAutoMode": None,
            "autoHumidityValue": None,
            "isAirQualityAutoMode": None,
            "autoAirQualityValue": None
        }

        for key in default_values:
            mode_key = "is" + key[4:-5] + "AutoMode"
            mode_value = data.get(mode_key, None)
            auto_value = data.get(key, None)
            if mode_value is None:
                mode_value = False
                ref.update({mode_key: False})

            if auto_value is None:
                auto_value = default_values[key]
                ref.update({key: auto_value})

            values[mode_key] = mode_value
            values[key] = auto_value

        return_tuple = tuple(values.values())

        return return_tuple

    @staticmethod
    def get_or_set_humidity_auto_mode():
        FirebaseDatabase.get_instance()
        ref = db.reference('settings/hvac/isHumidityAutoMode')

        isHumidityAutoMode = ref.get()

        if isHumidityAutoMode is None:
            ref.set(False)
            return False
        else:
            return isHumidityAutoMode


class HvacSubsystemFrame(HvacSubsystem, wx.Frame):
    def __init__(self, parent, main_frame):
        HvacSubsystem.__init__(self)
        wx.Frame.__init__(self, parent, title="HVAC Settings", size=(800, 400))
        self.main_frame = main_frame

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.auto_temp_label = None
        self.auto_temp_switch = None
        self.isTemperatureAutoMode = None
        self.autoTemperatureValue = None
        self.isHumidityAutoMode = None
        self.autoHumidityValue = None
        self.isAirQualityAutoMode = None
        self.autoAirQualityValue = None
        self.ui_elements = {}
        self.panel = wx.Panel(self)

        self.InitUI()

    def InitUI(self):
        general_hvac_data = HvacSubsystem.get_or_set_hvac_auto_mode()
        (self.isTemperatureAutoMode,
         self.autoTemperatureValue,
         self.isHumidityAutoMode,
         self.autoHumidityValue,
         self.isAirQualityAutoMode,
         self.autoAirQualityValue) = general_hvac_data

        self.addControlSection("Temperature", self.isTemperatureAutoMode, self.autoTemperatureValue)
        self.addControlSection("Humidity", self.isHumidityAutoMode, self.autoHumidityValue)
        self.addControlSection("Air Quality", self.isAirQualityAutoMode, self.autoAirQualityValue)

        back_btn = wx.Button(self.panel, label="Back to DTSRS")
        back_btn.Bind(wx.EVT_BUTTON, self.OnBackClicked)
        self.main_sizer.Add(back_btn, proportion=0, flag=wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP | wx.BOTTOM, border=80)

        self.panel.SetSizer(self.main_sizer)

    def addControlSection(self, label, isAutoMode, autoValue):
        step = 0.5 if label == "Temperature" else 1
        incr_btn_label = f"+{step}"
        decr_btn_label = f"-{step}"

        control_label = wx.StaticText(self.panel, label=f"Global Auto {label}: {autoValue}")
        control_switch = wx.CheckBox(self.panel, label="ON/OFF")
        control_switch.SetValue(isAutoMode)
        incr_btn = wx.Button(self.panel, label=incr_btn_label)
        decr_btn = wx.Button(self.panel, label=decr_btn_label)
        apply_btn = wx.Button(self.panel, label="Apply Changes")
        detail_btn = wx.Button(self.panel, label=f"{label} Details")
        history_btn = wx.Button(self.panel, label="View History")

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(control_label, 0, wx.ALL, 5)
        sizer.Add(control_switch, 0, wx.ALL, 5)
        sizer.Add(incr_btn, 0, wx.ALL, 5)
        sizer.Add(decr_btn, 0, wx.ALL, 5)
        sizer.Add(apply_btn, 0, wx.ALL, 5)
        sizer.Add(detail_btn, 0, wx.ALL, 5)
        sizer.Add(history_btn, 0, wx.ALL, 5)

        self.main_sizer.Add(sizer, 0, wx.EXPAND | wx.ALL, 5)

        incr_btn.Bind(wx.EVT_BUTTON, lambda evt, lbl=label: self.onIncrease(evt, lbl))
        decr_btn.Bind(wx.EVT_BUTTON, lambda evt, lbl=label: self.onDecrease(evt, lbl))
        apply_btn.Bind(wx.EVT_BUTTON, lambda evt, lbl=label: self.onApplyChanges(evt, lbl))
        detail_btn.Bind(wx.EVT_BUTTON, lambda evt, lbl=label: self.onShowDetails(evt, lbl))
        history_btn.Bind(wx.EVT_BUTTON, lambda evt, lbl=label: self.onShowSensorHistory(evt, lbl))

        self.ui_elements[label] = {
            "label": control_label,
            "switch": control_switch,
            "incr_btn": incr_btn,
            "decr_btn": decr_btn,
            "apply_btn": apply_btn,
            "detail_btn": detail_btn,
            "history_btn": history_btn
        }

    def onIncrease(self, event, label):
        step = 0.5 if label == "Temperature" else 1.0
        self.updateValue(label, step)

    def onDecrease(self, event, label):
        step = -0.5 if label == "Temperature" else -1.0
        self.updateValue(label, step)

    def updateValue(self, label, step):
        newValue = 0
        if label == "Temperature":
            self.autoTemperatureValue += step
            newValue = self.autoTemperatureValue
        elif label == "Humidity":
            self.autoHumidityValue += step
            newValue = self.autoHumidityValue
        elif label == "Air Quality":
            self.autoAirQualityValue += step
            newValue = self.autoAirQualityValue

        self.ui_elements[label]["label"].SetLabel(f"Global Auto {label}: {newValue}")

    def onApplyChanges(self, event, label):
        ref_path = 'settings/hvac/'
        autoValue = None

        isAutoMode = self.ui_elements[label]["switch"].IsChecked()
        if label == "Temperature":
            autoValue = self.autoTemperatureValue
            self.isTemperatureAutoMode = isAutoMode
        elif label == "Humidity":
            autoValue = self.autoHumidityValue
            self.isHumidityAutoMode = isAutoMode
        elif label == "Air Quality":
            autoValue = self.autoAirQualityValue
            self.isAirQualityAutoMode = isAutoMode

        mode_key = f"is{label.replace(' ', '')}AutoMode"
        value_key = f"auto{label.replace(' ', '')}Value"
        data_to_update = {
            mode_key: isAutoMode,
            value_key: autoValue
        }

        label_to_device_type = {
            "Temperature": "temperature",
            "Humidity": "humidity",
            "Air Quality": "air"
        }

        device_type = label_to_device_type.get(label)
        if not device_type:
            wx.MessageBox("Unsupported device type", "Error", wx.OK | wx.ICON_ERROR)
            return

        try:
            FirebaseDatabase.get_instance()
            ref = db.reference(ref_path)
            ref.update(data_to_update)
            self.get_hvac_data_update_global_value(device_type)
            wx.MessageBox(f"{label} settings have been successfully applied to Firebase.",
                          "Update Successful", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Failed to apply {label} settings to Firebase: {e}",
                          "Update Failed", wx.OK | wx.ICON_ERROR)

    def onShowDetails(self, event, label):
        label_to_device_type = {
            "Temperature": "temperature",
            "Humidity": "humidity",
            "Air Quality": "air"
        }

        device_type = label_to_device_type.get(label)
        if not device_type:
            wx.MessageBox("Unsupported device type", "Error", wx.OK | wx.ICON_ERROR)
            return

        device_ls = self.get_hvac_data_update_global_value(device_type)

        dlg = DeviceDetailsDialog(self, f"{label} Details", device_ls, device_type)
        dlg.ShowModal()
        dlg.Destroy()

    def get_hvac_data_update_global_value(self, device_type):
        type_map = {
            "temperature": {
                "device_type": "air conditioning",
                "sensor_type": "temperature and humidity sensor",
                "device_path": "air_conditioning",
                "sensor_path": "dht_sensor",
                "target": self.autoTemperatureValue,
                "global_auto": self.isTemperatureAutoMode

            },
            "humidity": {
                "device_type": "humidifier",
                "sensor_type": "temperature and humidity sensor",
                "device_path": "humidifier",
                "sensor_path": "dht_sensor",
                "target": self.autoHumidityValue,
                "global_auto": self.isHumidityAutoMode
            },
            "air": {
                "device_type": "ventilation",
                "sensor_type": "air sensor",
                "device_path": "ventilation",
                "sensor_path": "mq_135_sensor",
                "target": self.autoAirQualityValue,
                "global_auto": self.isAirQualityAutoMode
            }
        }

        current_type = type_map.get(device_type)
        if not current_type:
            raise ValueError("Unsupported type")

        room_manager = RoomDataManager()
        room_manager.update_room_data_from_firebase()
        hvac_devices = room_manager.room_data["device"]["hvac"]

        device_ls = []

        for device in hvac_devices:
            if device.detailed_type == current_type["device_type"]:
                self.uploadGlobalTargetData(device.device_id, current_type["target"], current_type['global_auto'])
                last_device_data = self.getLatestDeviceData(device.device_id)
                record = {
                    "device_class": device,
                    "last_device_target_data": last_device_data,
                    "sensor_class": None,
                    "last_sensor_data": None
                }

                for sensor_device in hvac_devices:
                    bound_devices = sensor_device.bound_devices or []
                    if device.device_id in bound_devices and sensor_device.detailed_type == current_type["sensor_type"]:
                        last_sensor_data = self.getLatestSensorData(sensor_device.device_id, current_type["sensor_path"])
                        record.update({
                            "sensor_class": sensor_device,
                            "last_sensor_data": last_sensor_data
                        })
                        break
                device_ls.append(record)

        return device_ls

    def get_hvac_data(self, device_type):
        type_map = {
            "temperature": {
                "device_type": "air conditioning",
                "sensor_type": "temperature and humidity sensor",
                "device_path": "air_conditioning",
                "sensor_path": "dht_sensor",
                "target": self.autoTemperatureValue,
                "global_auto": self.isTemperatureAutoMode

            },
            "humidity": {
                "device_type": "humidifier",
                "sensor_type": "temperature and humidity sensor",
                "device_path": "humidifier",
                "sensor_path": "dht_sensor",
                "target": self.autoHumidityValue,
                "global_auto": self.isHumidityAutoMode
            },
            "air": {
                "device_type": "ventilation",
                "sensor_type": "air sensor",
                "device_path": "ventilation",
                "sensor_path": "mq_135_sensor",
                "target": self.autoAirQualityValue,
                "global_auto": self.isAirQualityAutoMode
            }
        }

        current_type = type_map.get(device_type)
        if not current_type:
            raise ValueError("Unsupported type")

        room_manager = RoomDataManager()
        room_manager.update_room_data_from_firebase()
        hvac_devices = room_manager.room_data["device"]["hvac"]

        device_ls = []

        for device in hvac_devices:
            if device.detailed_type == current_type["device_type"]:
                last_device_data = self.getLatestDeviceData(device.device_id)
                record = {
                    "device_class": device,
                    "last_device_target_data": last_device_data,
                    "sensor_class": None,
                    "last_sensor_data": None
                }

                for sensor_device in hvac_devices:
                    bound_devices = sensor_device.bound_devices or []
                    if device.device_id in bound_devices and sensor_device.detailed_type == current_type["sensor_type"]:
                        last_sensor_data = self.getLatestSensorData(sensor_device.device_id, current_type["sensor_path"])
                        record.update({
                            "sensor_class": sensor_device,
                            "last_sensor_data": last_sensor_data
                        })
                        break
                device_ls.append(record)
        return device_ls

    def onShowSensorHistory(self, event, label):
        dlg = self.SensorHistoryDialog(self, label)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            selected_device, start_time, duration = dlg.get_selected_values()
            self.displaySensorHistory(selected_device, start_time, duration, label)
        dlg.Destroy()

    def displaySensorHistory(self, selected_device, start_datetime_str, duration_minutes, label):
        start_datetime = datetime.datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
        end_datetime = start_datetime + datetime.timedelta(minutes=duration_minutes)

        sensor_path = "dht_sensor" if label in ["Temperature", "Humidity"] else "mq_135_sensor"
        ref_path = f'hvac/{sensor_path}/{selected_device}'

        FirebaseDatabase.get_instance()
        ref = db.reference(ref_path)
        data = ref.get()

        if data is None:
            wx.MessageBox("No data found for the selected device and time period.", "No Data", wx.OK | wx.ICON_INFORMATION)
            return

        # Filter data to select data within a time range
        filtered_data = {}
        for timestamp_str, entry in data.items():
            try:
                data_time = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                print(f"Error converting timestamp: {timestamp_str} - {e}")
                continue

            if start_datetime <= data_time <= end_datetime:
                filtered_data[timestamp_str] = entry

        if not filtered_data:
            wx.MessageBox("No data found for the selected device and time period", "No Data", wx.OK | wx.ICON_INFORMATION)
            return

        # Calculate time intervals and find the latest data point for each interval
        intervals = self.get_time_intervals(start_datetime_str, duration_minutes)
        data_points = self.find_data_for_intervals(filtered_data, intervals)

        # Format and display data
        message = "\n".join(
            [f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {value if value is not None else 'No data'}" for timestamp, value in data_points])
        wx.MessageBox(message, "Historical Data", wx.OK | wx.ICON_INFORMATION)

    @staticmethod
    def get_time_intervals(start_time_str, duration_minutes):
        start_datetime = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
        interval_duration = duration_minutes / 20
        intervals = [(start_datetime + datetime.timedelta(minutes=i * interval_duration),
                      start_datetime + datetime.timedelta(minutes=(i + 1) * interval_duration))
                     for i in range(20)]
        return intervals

    @staticmethod
    def find_data_for_intervals(filtered_data, intervals):
        data_with_datetime_keys = {datetime.datetime.strptime(k, "%Y-%m-%d %H:%M:%S"): v for k, v in filtered_data.items()}
        data_points = []
        for start, end in intervals:
            relevant_data = [(k, v) for k, v in data_with_datetime_keys.items() if start < k <= end]
            relevant_data.sort(key=lambda x: x[0], reverse=True)
            data_points.append((end, relevant_data[0][1] if relevant_data else None))
        return data_points

    @staticmethod
    def uploadGlobalTargetData(device_id, target_value, auto_mode):
        ref = db.reference(f'room/device/hvac/{device_id}')
        ref.update({"target": target_value, "auto_mode": auto_mode})

    @staticmethod
    def getLatestDeviceData(device_id):
        ref = db.reference(f'room/device/hvac/{device_id}')
        data = ref.get()
        if data:
            return data
        else:
            return None

    @staticmethod
    def getLatestSensorData(sensor_id, path):
        ref = db.reference(f'hvac/{path}/{sensor_id}')
        sensor_data = ref.get()
        if sensor_data:
            latest_timestamp = max(sensor_data.keys())
            return sensor_data[latest_timestamp]
        else:
            return None

    def OnBackClicked(self, event):
        self.Hide()
        self.main_frame.Show()

    class SensorHistoryDialog(wx.Dialog):
        def __init__(self, parent, label):
            super().__init__(parent, title="Select History Parameters", size=(400, 400))
            self.label = label
            self.init_ui()

        def init_ui(self):
            panel = wx.Panel(self)
            vbox = wx.BoxSizer(wx.VERTICAL)

            device_label = wx.StaticText(panel, label="Select Device:")
            self.device_choice = wx.Choice(panel, choices=self.get_device_choices())

            start_date_label = wx.StaticText(panel, label="Start Date:")
            self.start_date_picker = wx.adv.DatePickerCtrl(panel, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)

            start_time_label = wx.StaticText(panel, label="Start Time:")
            self.start_time_picker = wx.adv.TimePickerCtrl(panel)

            duration_label = wx.StaticText(panel, label="Duration (minutes):")
            self.duration_ctrl = wx.TextCtrl(panel)

            self.ok_btn = wx.Button(panel, wx.ID_OK, label="OK")
            self.cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="Cancel")

            vbox.Add(device_label, flag=wx.ALL, border=5)
            vbox.Add(self.device_choice, flag=wx.ALL | wx.EXPAND, border=5)
            vbox.Add(start_date_label, flag=wx.ALL, border=5)
            vbox.Add(self.start_date_picker, flag=wx.ALL | wx.EXPAND, border=5)
            vbox.Add(start_time_label, flag=wx.ALL, border=5)
            vbox.Add(self.start_time_picker, flag=wx.ALL | wx.EXPAND, border=5)
            vbox.Add(duration_label, flag=wx.ALL, border=5)
            vbox.Add(self.duration_ctrl, flag=wx.ALL | wx.EXPAND, border=5)
            vbox.Add(self.ok_btn, flag=wx.ALL | wx.ALIGN_CENTER, border=5)
            vbox.Add(self.cancel_btn, flag=wx.ALL | wx.ALIGN_CENTER, border=5)

            panel.SetSizer(vbox)

        def get_device_choices(self):
            detailed_type_map = {
                "Temperature": "temperature and humidity sensor",
                "Humidity": "temperature and humidity sensor",
                "Air Quality": "air sensor"
            }

            device_type = detailed_type_map.get(self.label, "")
            if not device_type:
                return []

            FirebaseDatabase.get_instance()
            hvac_ref = db.reference('room/device/hvac')
            devices = hvac_ref.get() if hvac_ref.get() else {}

            device_choices = []
            for device_id, device_info in devices.items():
                if device_info.get("detailed_type") == device_type:
                    device_choices.append(device_id)
            return device_choices

        def get_selected_values(self):
            selected_device = self.device_choice.GetStringSelection()
            start_date = self.start_date_picker.GetValue().FormatISODate()
            start_time = self.start_time_picker.GetValue().Format("%H:%M")
            start_datetime_str = f"{start_date} {start_time}"
            duration_minutes = int(self.duration_ctrl.GetValue())

            return selected_device, start_datetime_str, duration_minutes


class DeviceDetailsDialog(wx.Dialog):
    def __init__(self, parent, title, device_ls, device_type):
        super().__init__(parent, title=title, size=(700, 400))
        self.parent = parent
        self.device_ls = device_ls
        self.device_type = device_type
        self.selected_device_index = None
        self.initUI()
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.onRefresh, self.timer)
        self.timer.Start(5000)

    def initUI(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(0, "Device ID", width=120)
        self.list_ctrl.InsertColumn(1, "Target Data", width=80)
        self.list_ctrl.InsertColumn(2, "Auto", width=80)
        self.list_ctrl.InsertColumn(3, "Switch", width=80)
        self.list_ctrl.InsertColumn(4, "Sensor Data", width=200)
        self.list_ctrl.InsertColumn(5, "Speed", width=80)

        self.populateList()

        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onSelect)
        vbox.Add(self.list_ctrl, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        btn_panel = wx.Panel(panel)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.auto_btn = wx.Button(btn_panel, label="Auto")
        self.increase_btn = wx.Button(btn_panel, label="+0.5")
        self.decrease_btn = wx.Button(btn_panel, label="-0.5")
        self.switch_btn = wx.CheckBox(btn_panel, label="Switch")
        self.speed_increase_btn = wx.Button(btn_panel, label="Speed +")
        self.speed_decrease_btn = wx.Button(btn_panel, label="Speed -")

        hbox.Add(self.auto_btn)
        hbox.Add(self.increase_btn)
        hbox.Add(self.decrease_btn)
        hbox.Add(self.switch_btn)
        hbox.Add(self.speed_increase_btn)
        hbox.Add(self.speed_decrease_btn)

        btn_panel.SetSizer(hbox)
        vbox.Add(btn_panel, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=5)

        panel.SetSizer(vbox)

        self.auto_btn.Bind(wx.EVT_BUTTON, self.onAuto)
        self.increase_btn.Bind(wx.EVT_BUTTON, self.onIncrease)
        self.decrease_btn.Bind(wx.EVT_BUTTON, self.onDecrease)
        self.switch_btn.Bind(wx.EVT_CHECKBOX, self.onSwitch)
        self.speed_increase_btn.Bind(wx.EVT_BUTTON, self.onSpeedIncrease)
        self.speed_decrease_btn.Bind(wx.EVT_BUTTON, self.onSpeedDecrease)

    def populateList(self):
        self.list_ctrl.DeleteAllItems()
        for device_data in self.device_ls:
            index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), device_data['device_class'].device_id)

            if device_data['last_device_target_data'] is None:
                switch_state_display = "Data missing"
            else:
                switch_state_display = "ON" if device_data['last_device_target_data'].get('switch') else "OFF"
            self.list_ctrl.SetItem(index, 1, str(device_data['device_class'].target))
            self.list_ctrl.SetItem(index, 2, "Auto" if device_data['device_class'].auto_mode else "Manual")
            self.list_ctrl.SetItem(index, 3, switch_state_display)
            self.list_ctrl.SetItem(index, 4, str(device_data['last_sensor_data']))
            self.list_ctrl.SetItem(index, 5, str(device_data['last_device_target_data'].get('speed')))

    def onSelect(self, event):
        self.selected_device_index = event.GetIndex()
        selected_device = self.device_ls[self.selected_device_index]
        switch_state = selected_device.get('switch', None)
        if switch_state is None:
            self.switch_btn.SetValue(False)
        else:
            self.switch_btn.SetValue(switch_state)

    def onAuto(self, event):
        if self.selected_device_index is not None:
            selected_device = self.device_ls[self.selected_device_index]
            # Switch the auto_mode value, if it is None, set it to True
            auto_mode = selected_device['device_class'].auto_mode
            selected_device['device_class'].auto_mode = not auto_mode if auto_mode is not None else True
            switch_state = selected_device['last_device_target_data'].get('switch')
            speed = selected_device['last_device_target_data'].get('speed')
            # Update list display
            auto_mode_display = "ON" if selected_device['device_class'].auto_mode else "OFF"
            self.list_ctrl.SetItem(self.selected_device_index, 2, auto_mode_display)
            # Update Firebase database
            self.updateDeviceInFirebaseAutoMode(
                selected_device['device_class'].device_id,
                selected_device['device_class'].auto_mode,
                selected_device['device_class'].detailed_type,
                switch_state,
                speed
            )
            # Update list display
            self.getRefresh(selected_device['device_class'].detailed_type)

    @staticmethod
    def updateDeviceInFirebaseAutoMode(device_id, auto_mode, device_type, switch_state, speed):
        amsterdam = pytz.timezone('Europe/Amsterdam')
        amsterdam_time = datetime.datetime.now(amsterdam).strftime('%Y-%m-%d %H:%M:%S')

        ref = db.reference(f'room/device/hvac/{device_id}/')
        ref.update({"auto_mode": auto_mode})

        ref_device = db.reference(f'hvac/{device_type}/{device_id}/{amsterdam_time}')
        update_data = {"auto_mode": auto_mode, "switch": switch_state, "speed": speed}
        ref_device.update(update_data)

    def onIncrease(self, event):
        if self.selected_device_index is not None:
            self.adjustDeviceTargetValue(0.5)

    def onDecrease(self, event):
        if self.selected_device_index is not None:
            self.adjustDeviceTargetValue(-0.5)

    def onSpeedIncrease(self, event):
        if self.selected_device_index is not None:
            self.adjustDeviceSpeed(10)

    def onSpeedDecrease(self, event):
        if self.selected_device_index is not None:
            self.adjustDeviceSpeed(-10)

    def adjustDeviceTargetValue(self, adjustment):
        selected_device = self.device_ls[self.selected_device_index]
        if selected_device['device_class'].target is None:
            selected_device['device_class'].target = 25
            current_value = 25
        else:
            current_value = selected_device['device_class'].target

        new_value = current_value + adjustment
        selected_device['device_class'].target = new_value
        current_speed = selected_device['last_device_target_data'].get('speed', 0)
        self.list_ctrl.SetItem(self.selected_device_index, 1, str(new_value))
        current_switch_state = selected_device['last_device_target_data']['switch']
        self.updateDeviceInFirebase(True,
                                    selected_device['device_class'].device_id,
                                    selected_device['device_class'].detailed_type,
                                    new_value,
                                    current_switch_state,
                                    current_speed)
        self.getRefresh(selected_device['device_class'].detailed_type)

    def adjustDeviceSpeed(self, adjustment):
        selected_device = self.device_ls[self.selected_device_index]
        if selected_device['device_class'].auto_mode:  # Check auto mode
            wx.MessageBox("Cannot adjust speed while in Auto mode.", "Error", wx.OK | wx.ICON_ERROR)
            return
        current_speed = selected_device['last_device_target_data'].get('speed', 0)
        new_speed = current_speed + adjustment
        if new_speed > 70:
            new_speed = 70
        elif new_speed < 0:
            new_speed = 0
        selected_device['last_device_target_data']['speed'] = new_speed

        if new_speed > 0 and not selected_device['last_device_target_data'].get('switch'):
            selected_device['last_device_target_data']['switch'] = True
        elif new_speed == 0 and selected_device['last_device_target_data'].get('switch'):
            selected_device['last_device_target_data']['switch'] = False

        switch_state_display = "ON" if selected_device['last_device_target_data']['switch'] else "OFF"
        self.list_ctrl.SetItem(self.selected_device_index, 3, switch_state_display)
        self.list_ctrl.SetItem(self.selected_device_index, 5, str(new_speed))
        self.updateDeviceInFirebase(False,
                                    selected_device['device_class'].device_id,
                                    selected_device['device_class'].detailed_type,
                                    selected_device['device_class'].target,
                                    selected_device['last_device_target_data']['switch'],
                                    new_speed)

    def onSwitch(self, event):
        if self.selected_device_index is not None:
            selected_device = self.device_ls[self.selected_device_index]
            if selected_device['device_class'].auto_mode:  # Check auto mode
                wx.MessageBox("Cannot adjust switch while in Auto mode.", "Error", wx.OK | wx.ICON_ERROR)
                return
            if selected_device['device_class'].target is None:
                selected_device['device_class'].target = 25

            new_switch_state = self.switch_btn.GetValue()
            if new_switch_state:
                new_speed = 70
            else:
                new_speed = 0
            selected_device['last_device_target_data']['switch'] = new_switch_state
            selected_device['last_device_target_data']['speed'] = new_speed
            selected_device['device_class'].target = selected_device['device_class'].target or 25

            switch_state_display = "ON" if new_switch_state else "OFF"
            self.list_ctrl.SetItem(self.selected_device_index, 3, switch_state_display)
            self.list_ctrl.SetItem(self.selected_device_index, 5, str(new_speed))

            self.updateDeviceInFirebase(False,
                                        selected_device['device_class'].device_id,
                                        selected_device['device_class'].detailed_type,
                                        selected_device['device_class'].target,
                                        new_switch_state,
                                        new_speed)
        self.getRefresh(selected_device['device_class'].detailed_type)

    @staticmethod
    def updateDeviceInFirebase(isAuto, device_id, device_type, new_value, new_switch_state, new_speed):
        amsterdam = pytz.timezone('Europe/Amsterdam')
        amsterdam_time = datetime.datetime.now(amsterdam).strftime('%Y-%m-%d %H:%M:%S')

        if new_value is None:
            new_value = 25
        else:
            pass
        ref_room = db.reference(f'room/device/hvac/{device_id}')
        ref_device = db.reference(f'hvac/{device_type}/{device_id}/{amsterdam_time}')

        if isAuto:
            ref_room.update({"target": new_value, "switch": new_switch_state, "speed": new_speed, "auto_mode": True})
            update_data = {"switch": new_switch_state, "speed": new_speed, "auto_mode": True}
        else:
            ref_room.update({"target": new_value, "switch": new_switch_state, "speed": new_speed, "auto_mode": False})
            update_data = {"switch": new_switch_state, "speed": new_speed, "auto_mode": False}
        ref_device.update(update_data)

    def onRefresh(self, event):
        device_ls = self.parent.get_hvac_data(self.device_type)
        self.device_ls = device_ls
        self.populateList()

    def getRefresh(self, label):
        label_to_device_type = {
            "air conditioning": "temperature",
            "humidifier": "humidity",
            "ventilation": "air"
        }

        device_type = label_to_device_type.get(label)
        if not device_type:
            wx.MessageBox("Unsupported device type", "Error", wx.OK | wx.ICON_ERROR)
            return
        device_ls = self.parent.get_hvac_data(device_type)
        self.device_ls = device_ls
        self.populateList()
