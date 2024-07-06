import re
import wx
import wx.adv
import datetime
import pytz
from firebase_admin import db
from FirebaseDatabase import FirebaseDatabase


class SafetySubsystem:
    def __init__(self):
        pass

    def check_safety_devices_threshold(self):
        devices_ref = db.reference('room/device/safety')
        safety_devices = devices_ref.get()
        if not safety_devices:
            return

        amsterdam = pytz.timezone('Europe/Amsterdam')
        now = datetime.datetime.now(pytz.utc).astimezone(amsterdam)
        emergency_devices = []
        for device_id, device_info in safety_devices.items():
            threshold = device_info.get('threshold', None)

            data_ref = db.reference(f'safety/mq_2_sensor/{device_id}')
            device_record = data_ref.get()

            if not device_record:
                continue

            current_value = None
            for datetime_str, entry in sorted(device_record.items(), reverse=True):
                data_time = datetime.datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
                if (now - data_time).seconds <= 300:  # Within 5 min
                    current_value = entry.get('gas_level', None)
                    break

            if threshold is not None and current_value is None:
                print(f"{device_id} - No sensor record found")
            elif threshold is None and current_value is not None:
                print(f"{device_id} - No threshold setting data found")
            elif threshold is None and current_value is None:
                print(f"{device_id} - No data found")
            else:
                # Check if threshold is exceeded
                if current_value > threshold:
                    emergency_devices.append(device_id)

        expirationDatetime_ref = db.reference('settings/safety/expirationDatetime')
        expiration_str = expirationDatetime_ref.get()
        amsterdam_timezone = pytz.timezone('Europe/Amsterdam')

        current_time = datetime.datetime.now(amsterdam_timezone)

        current_manualButton = db.reference('settings/safety/manualButton').get()
        expirationManualDatetime_ref = db.reference('settings/safety/expirationManualDatetime')
        expirationManual_str = expirationManualDatetime_ref.get()

        is_emergency = None

        if emergency_devices:
            if expiration_str is not None:
                expiration = datetime.datetime.strptime(expiration_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=amsterdam_timezone)

                if current_time > expiration:
                    # "Emergency" is activated when the current time is later than the expiration time
                    self.update_safety_emergency_status(True, emergency_devices)
                    is_emergency = True
                else:
                    self.update_safety_emergency_status(False, [])
                    is_emergency = False
                    self.reset_manual_button()
            else:
                self.update_safety_emergency_status(True, emergency_devices)
                is_emergency = True

        elif current_manualButton:
            if expirationManual_str is not None:
                expiration = datetime.datetime.strptime(expirationManual_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=amsterdam_timezone)

                if current_time <= expiration:
                    # "Emergency" is activated when the current time is later than the expiration time
                    self.update_safety_emergency_status(True, emergency_devices)
                    is_emergency = True
                else:
                    self.update_safety_emergency_status(False, [])
                    is_emergency = False
                    self.reset_manual_button()
            else:
                self.update_safety_emergency_status(True, emergency_devices)
                is_emergency = True

        else:
            self.update_safety_emergency_status(False, [])
            is_emergency = False
            self.reset_manual_button()

        return is_emergency

    @staticmethod
    def reset_manual_button():
        db.reference('settings/safety').update({'manualButton': False})

    @staticmethod
    def update_safety_emergency_status(is_emergency, emergency_devices):
        safety_ref = db.reference('settings/safety')
        safety_ref.update({
            'isEmergency': is_emergency,
            'emergencyDevices': emergency_devices
        })


class SafetySubsystemFrame(SafetySubsystem, wx.Frame):
    def __init__(self, parent, main_frame):
        SafetySubsystem.__init__(self)
        wx.Frame.__init__(self, parent, title="Safety Settings", size=(400, 300))
        self.main_frame = main_frame

        panel = wx.Panel(self)
        self.SetPosition(wx.Point(650, 350))

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        set_sizer = wx.BoxSizer(wx.HORIZONTAL)
        sensors_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # New buttons for setting thresholds
        self.set_flame_threshold_btn = wx.Button(panel, label="Set Flame Threshold")
        self.set_flame_threshold_btn.Bind(wx.EVT_BUTTON, self.onSetFlameThreshold)
        set_sizer.Add(self.set_flame_threshold_btn, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        self.set_gas_threshold_btn = wx.Button(panel, label="Set Gas Threshold")
        self.set_gas_threshold_btn.Bind(wx.EVT_BUTTON, self.onSetGasThreshold)
        set_sizer.Add(self.set_gas_threshold_btn, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        main_sizer.Add(set_sizer, proportion=3, flag=wx.EXPAND | wx.ALL, border=10)

        # View Flame Sensor History Button
        self.view_flame_sensor_btn = wx.Button(panel, label="View Flame Sensor History")
        self.view_flame_sensor_btn.Bind(wx.EVT_BUTTON, lambda event: self.onViewSensorHistory(event, "Flame Sensor"))
        sensors_sizer.Add(self.view_flame_sensor_btn, proportion=1, flag=wx.EXPAND | wx.RIGHT, border=5)

        # View Gas Sensor History Button
        self.view_gas_sensor_btn = wx.Button(panel, label="View Gas Sensor History")
        self.view_gas_sensor_btn.Bind(wx.EVT_BUTTON, lambda event: self.onViewSensorHistory(event, "Gas Sensor"))
        sensors_sizer.Add(self.view_gas_sensor_btn, proportion=1, flag=wx.EXPAND | wx.LEFT, border=5)

        main_sizer.Add(sensors_sizer, proportion=3, flag=wx.EXPAND | wx.ALL, border=10)

        # Back Button below the sensor buttons
        back_btn = wx.Button(panel, label="Back to DTSRS")
        back_btn.Bind(wx.EVT_BUTTON, self.OnBackClicked)
        main_sizer.Add(back_btn, proportion=1, flag=wx.EXPAND | wx.TOP, border=5)

        panel.SetSizer(main_sizer)

        # Event handler for setting flame threshold
    def onSetFlameThreshold(self, event):
        dlg = SetThresholdDialog(self, "Set Flame Sensor Threshold", "Flame Sensor")
        dlg.ShowModal()
        dlg.Destroy()

    # Event handler for setting gas threshold
    def onSetGasThreshold(self, event):
        dlg = SetThresholdDialog(self, "Set Gas Sensor Threshold", "Gas Sensor")
        dlg.ShowModal()
        dlg.Destroy()

    def onViewSensorHistory(self, event, label):
        dlg = self.SensorHistoryDialog(self, label)
        result = dlg.ShowModal()
        if result == wx.ID_OK:
            selected_device, start_time, duration = dlg.get_selected_values()
            device_id_match = re.search(r'\((.*?)\)$', selected_device)
            if device_id_match:
                selected_device_id = device_id_match.group(1)
                self.displaySensorHistory(selected_device_id, start_time, duration, label)
            else:
                wx.MessageBox("Failed to extract device ID.", "Error", wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def OnBackClicked(self, event):
        self.Hide()
        self.main_frame.Show()

    def displaySensorHistory(self, selected_device, start_time, duration, label):
        device_type_map = {
            "Flame Sensor": "flame_sensor",
            "Gas Sensor": "mq_2_sensor"
        }
        new_label = device_type_map.get(label, "")
        start_datetime = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M")
        end_datetime = start_datetime + datetime.timedelta(minutes=duration)

        # Fetch historical data for a specified interval
        data = self.fetch_safety_data(selected_device, new_label, start_datetime, end_datetime, duration)

        # Format and display data
        message = "\n".join(
            [f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {value if value is not None else 'No data'}" for timestamp, value in data])
        wx.MessageBox(message, "Sensor History Data", wx.OK | wx.ICON_INFORMATION)

    def fetch_safety_data(self, device_id, label, start_datetime, end_datetime, duration):
        ref_path = f"safety/{label}/{device_id}"
        print(label)
        print(device_id)
        print(ref_path)
        FirebaseDatabase.get_instance()
        ref = db.reference(ref_path)
        data = ref.get()

        if data is None:
            wx.MessageBox("No data found for the selected device and time period.", "No Data", wx.OK | wx.ICON_INFORMATION)
            return {}

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
        intervals = self.get_time_intervals(start_datetime, duration)
        data_points = self.find_data_for_intervals(filtered_data, intervals)

        return data_points

    @staticmethod
    def get_time_intervals(start_datetime, duration_minutes):
        # start_datetime = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
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

    class SensorHistoryDialog(wx.Dialog):
        def __init__(self, parent, label):
            super().__init__(parent, title="Select History Device and Time Slot", size=(400, 400))
            self.label = label
            self.init_ui()

        def init_ui(self):
            panel = wx.Panel(self)
            vbox = wx.BoxSizer(wx.VERTICAL)

            # Device Selection
            device_label = wx.StaticText(panel, label="Select Device:")
            self.device_choice = wx.Choice(panel, choices=self.get_device_choices())
            vbox.Add(device_label, flag=wx.ALL, border=5)
            vbox.Add(self.device_choice, flag=wx.ALL | wx.EXPAND, border=5)

            # Start date and time selection
            start_date_label = wx.StaticText(panel, label="Start Date:")
            self.start_date_picker = wx.adv.DatePickerCtrl(panel, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
            vbox.Add(start_date_label, flag=wx.ALL, border=5)
            vbox.Add(self.start_date_picker, flag=wx.ALL | wx.EXPAND, border=5)

            start_time_label = wx.StaticText(panel, label="Start Time:")
            self.start_time_picker = wx.adv.TimePickerCtrl(panel)
            vbox.Add(start_time_label, flag=wx.ALL, border=5)
            vbox.Add(self.start_time_picker, flag=wx.ALL | wx.EXPAND, border=5)

            # Duration input
            duration_label = wx.StaticText(panel, label="Duration (minutes):")
            self.duration_ctrl = wx.TextCtrl(panel)
            vbox.Add(duration_label, flag=wx.ALL, border=5)
            vbox.Add(self.duration_ctrl, flag=wx.ALL | wx.EXPAND, border=5)

            self.ok_btn = wx.Button(panel, wx.ID_OK, label="OK")
            self.cancel_btn = wx.Button(panel, wx.ID_CANCEL, label="Cancel")
            vbox.Add(self.ok_btn, flag=wx.ALL | wx.ALIGN_CENTER, border=5)
            vbox.Add(self.cancel_btn, flag=wx.ALL | wx.ALIGN_CENTER, border=5)

            panel.SetSizer(vbox)

        def get_device_choices(self):
            device_type_map = {
                "Flame Sensor": "flame sensor",
                "Gas Sensor": "gas sensor"
            }
            device_type = device_type_map.get(self.label, "")
            device_choices = []
            FirebaseDatabase.get_instance()
            devices_ref = db.reference('room/device/safety')
            devices = devices_ref.get() if devices_ref.get() else {}
            for device_id, device_info in devices.items():
                if device_info.get("detailed_type") == device_type:
                    device_name = device_info.get("device_name", "Unknown")
                    device_choices.append(f"{device_name} ({device_id})")
            return device_choices

        def get_selected_values(self):
            selected_device = self.device_choice.GetStringSelection()
            start_date = self.start_date_picker.GetValue().FormatISODate()
            start_time = self.start_time_picker.GetValue().Format("%H:%M")
            start_datetime_str = f"{start_date} {start_time}"
            duration_minutes = int(self.duration_ctrl.GetValue())
            return selected_device, start_datetime_str, duration_minutes


class SetThresholdDialog(wx.Dialog):
    def __init__(self, parent, title, device_type):
        super(SetThresholdDialog, self).__init__(parent, title=title, size=(400, 300))
        self.device_type = device_type
        self.init_ui()
        self.CenterOnParent()

    def init_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.device_list = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.device_list.InsertColumn(0, 'Device', width=220)
        self.device_list.InsertColumn(1, 'Current Threshold', wx.LIST_FORMAT_RIGHT, 150)

        self.populate_device_list()

        threshold_label = wx.StaticText(panel, label="Enter New Threshold (0-100):")
        self.threshold_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self.apply_button = wx.Button(panel, label="Apply")
        self.apply_button.Bind(wx.EVT_BUTTON, self.onApply)

        vbox.Add(self.device_list, proportion=1, flag=wx.ALL | wx.EXPAND, border=5)
        vbox.Add(threshold_label, flag=wx.ALL, border=5)
        vbox.Add(self.threshold_input, flag=wx.ALL | wx.EXPAND, border=5)
        vbox.Add(self.apply_button, flag=wx.ALL | wx.ALIGN_RIGHT, border=5)

        panel.SetSizer(vbox)

    def populate_device_list(self):
        self.device_list.DeleteAllItems()
        device_choices = self.get_device_choices()
        for device in device_choices:
            index = self.device_list.InsertItem(self.device_list.GetItemCount(), device[0])
            self.device_list.SetItem(index, 1, str(device[1]))

    def get_device_choices(self):
        device_type_map = {
            "Flame Sensor": "flame sensor",
            "Gas Sensor": "gas sensor"
        }
        device_type = device_type_map.get(self.device_type, "")
        FirebaseDatabase.get_instance()
        devices_ref = db.reference('room/device/safety')
        devices = devices_ref.get() if devices_ref.get() else {}
        device_choices = []
        for device_id, device_info in devices.items():
            if device_info.get("detailed_type") == device_type:
                threshold = device_info.get("threshold", "Not set")
                device_name = device_info.get("device_name", "Unknown")
                device_choices.append((f"{device_name} ({device_id})", threshold))
        return device_choices

    def onApply(self, event):
        try:
            selected_idx = self.device_list.GetFirstSelected()
            if selected_idx == -1:
                wx.MessageBox("Please select a device from the list.", "Error", wx.OK | wx.ICON_ERROR)
                return
            device_id = self.device_list.GetItemText(selected_idx, 0).split('(')[-1].rstrip(')')
            new_threshold = int(self.threshold_input.GetValue())
            if not 0 <= new_threshold <= 100:
                raise ValueError("Threshold must be between 0 and 100.")
            self.update_device_threshold(device_id, new_threshold)
        except ValueError as e:
            wx.MessageBox(str(e), "Error", wx.OK | wx.ICON_ERROR)

    def update_device_threshold(self, device_id, new_threshold):
        FirebaseDatabase.get_instance()
        threshold_ref = db.reference(f'room/device/safety/{device_id}/threshold')
        threshold_ref.set(new_threshold)
        wx.MessageBox("Threshold updated successfully.", "Success", wx.OK | wx.ICON_INFORMATION)
        self.populate_device_list()  # Refresh the list to show the updated value
