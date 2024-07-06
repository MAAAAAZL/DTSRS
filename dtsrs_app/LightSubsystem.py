import wx
import wx.adv
import io
import pytz
import datetime

from pytz import timezone
from PIL import Image
from firebase_admin import db, storage

from FirebaseDatabase import FirebaseDatabase


class LightSubsystem:
    def __init__(self):
        pass

    @staticmethod
    def get_or_set_light_auto_brightness():
        FirebaseDatabase.get_instance()
        ref = db.reference('settings/light/isLightAutoBrightness')

        isLightAutoBrightness = ref.get()

        if isLightAutoBrightness is None:
            ref.set(False)
            return False
        else:
            return isLightAutoBrightness


class LightSubsystemFrame(LightSubsystem, wx.Frame):
    def __init__(self, parent, main_frame):
        LightSubsystem.__init__(self)
        wx.Frame.__init__(self, parent, title="Light Settings", size=(400, 300))
        self.main_frame = main_frame

        panel = wx.Panel(self)
        self.SetPosition(wx.Point(650, 350))
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Call the Firebase function to get or set the settings for automatic light adjustment
        self.isLightAutoBrightness = self.get_or_set_light_auto_brightness()

        # Light Control Panel Button
        self.light_control_btn = wx.Button(panel, label="Light Control Panel")
        font = self.light_control_btn.GetFont()
        font.SetPointSize(12)
        self.light_control_btn.SetFont(font)
        self.light_control_btn.Bind(wx.EVT_BUTTON, self.onLightControlPanel)
        main_sizer.Add(self.light_control_btn, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # View History Button
        self.view_history_btn = wx.Button(panel, label="View History")
        self.view_history_btn.Bind(wx.EVT_BUTTON, self.onViewHistoryClicked)
        main_sizer.Add(self.view_history_btn, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # Back Button
        back_btn = wx.Button(panel, label="Back to DTSRS")
        back_btn.Bind(wx.EVT_BUTTON, self.OnBackClicked)
        main_sizer.Add(back_btn, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        panel.SetSizer(main_sizer)

    def onLightControlPanel(self, event):
        light_control_panel = LightControlPanel(None, title="Light Control Panel")
        light_control_panel.Show()

    def onViewHistoryClicked(self, event):
        # Get all light source devices
        ref = db.reference('room/device/light')
        light_devices = ref.get()
        light_choices = []
        light_ids = []
        for device_id, device_info in light_devices.items():
            temp_type = device_info.get('detailed_type')
            if temp_type == 'light' or temp_type == 'light intensity sensor':
                light_choices.append(f"{device_info.get('device_name', 'Unknown')} ({device_id})")
                light_ids.append(device_id)

        # Let the user select a light source device
        dialog = wx.SingleChoiceDialog(self, "Choose a light device:", "Light Devices", light_choices)
        if dialog.ShowModal() == wx.ID_OK:
            selected_index = dialog.GetSelection()
            selected_light_id = light_ids[selected_index]
            # Functions can be called here to handle subsequent steps
            self.selectTimePeriod(selected_light_id)
        dialog.Destroy()

    def selectTimePeriod(self, light_id):
        dialog = SelectTimePeriodDialog(self)
        if dialog.ShowModal() == wx.ID_OK:
            startDateTime, durationMinutes = dialog.getValues()
            py_startDateTime = wx.DateTime(startDateTime).GetTicks()
            end_time = datetime.datetime.fromtimestamp(py_startDateTime)
            eastern = timezone('Europe/Amsterdam')
            end_time = end_time.astimezone(eastern)
            start_time = end_time - datetime.timedelta(minutes=durationMinutes)

            samples = 20
            interval = durationMinutes / samples
            time_points = [start_time + datetime.timedelta(minutes=i * interval) for i in range(samples + 1)]

            # retrieve data
            data, temp_type = self.fetchDataFromFirebase(light_id, start_time, end_time)
            processed_data = self.processData(data, temp_type, time_points)
            # Display Data
            self.displayDataInNewWindow(processed_data)

        dialog.Destroy()

    def displayDataInNewWindow(self, processed_data):
        dlg = HistoryDialog(self, "Light History Data", processed_data)
        dlg.ShowModal()
        dlg.Destroy()

    def OnBackClicked(self, event):
        self.Hide()
        self.main_frame.Show()

    @staticmethod
    def fetchDataFromFirebase(light_id, startDateTime, endDateTime):
        device_ref = db.reference(f'room/device/light/{light_id}')
        device_info = device_ref.get()
        temp_type = device_info['detailed_type']

        start_time = startDateTime
        end_time = endDateTime

        if temp_type == 'light':
            ref = db.reference(f'/light/light/{light_id}/')
        elif temp_type == 'light intensity sensor':
            ref = db.reference(f'/light/light_sensor/{light_id}')
        else:
            wx.MessageBox("No data found!", "Error")
        data = ref.order_by_key().start_at(start_time.strftime('%Y-%m-%d %H:%M:%S')).end_at(
            end_time.strftime('%Y-%m-%d %H:%M:%S')).get()

        return data, temp_type

    @staticmethod
    def processData(data, device_type, time_points):
        processed_data = []
        previous_data = None
        amsterdam = timezone('Europe/Amsterdam')

        for slot in time_points:
            for timestamp, values in data.items():
                data_time_naive = datetime.datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S')
                data_time = amsterdam.localize(data_time_naive)
                if data_time <= slot:
                    found_data = values
                    previous_data = found_data
                else:
                    break
            if previous_data:
                if device_type == "light":
                    processed_data.append((slot.strftime('%Y-%m-%d %H:%M:%S'), previous_data['brightness']))
                elif device_type == "light intensity sensor":
                    processed_data.append((slot.strftime('%Y-%m-%d %H:%M:%S'), previous_data['light_intensity']))
            else:
                processed_data.append((slot.strftime('%Y-%m-%d %H:%M:%S'), 'Unknown'))

        return processed_data


class LightControlPanel(wx.Frame):
    def __init__(self, parent, title):
        super(LightControlPanel, self).__init__(parent, title=title, size=(1150, 500))
        self.popup_window = None
        self.panel = wx.Panel(self)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.final_bitmap = None

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_refresh, self.timer)
        self.timer.Start(10000)

        # Image display area on the left
        self.image_panel = wx.Panel(self.panel, size=(500, 800))
        self.image_panel.SetBackgroundColour(wx.WHITE)
        hbox.Add(self.image_panel, 0, wx.EXPAND | wx.RIGHT, 5)

        # The right area is used to display light devices
        self.right_panel = wx.Panel(self.panel, size=(745, 800))
        hbox.Add(self.right_panel, 1, wx.EXPAND)

        self.list_ctrl = wx.ListCtrl(self.right_panel, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list_ctrl.InsertColumn(0, "Light Id", width=120)
        self.list_ctrl.InsertColumn(1, "Light Name", width=80)
        self.list_ctrl.InsertColumn(2, "Switch", width=70)
        self.list_ctrl.InsertColumn(3, "Brightness", width=80)
        self.list_ctrl.InsertColumn(4, "Auto", width=70)
        self.list_ctrl.InsertColumn(5, "Bound Devices", width=200)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)
        self.right_panel.SetSizer(vbox)

        self.panel.SetSizer(hbox)

        self.scale_factor = 1

        self.device_coordinates = []

        self.view_layout_file()

        self.image_panel.Bind(wx.EVT_PAINT, self.on_image_panel_paint)
        self.list_ctrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_double_click)

        self.display_light_devices_on_image()

        self.display_light_devices()

    def on_item_double_click(self, event):
        """Handle double click event"""
        index = event.GetIndex()
        light_data = self.fetch_light_devices()[index]

        # Check for existing popup and close it if needed
        if hasattr(self, 'popup_window') and self.popup_window:
            self.popup_window.Destroy()

        self.popup_window = LightControlPopup(self, light_data)
        self.popup_window.Show()

    def on_image_panel_paint(self, event):
        if self.final_bitmap is not None:
            dc = wx.PaintDC(self.image_panel)
            # Used to draw the final image and mark points
            dc.DrawBitmap(self.final_bitmap, 0, 0, True)

    def view_layout_file(self):
        room_layout_path = "remote/room/layout"
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

        FirebaseDatabase.get_instance()
        bucket = storage.bucket()

        blobs = bucket.list_blobs(prefix=room_layout_path)

        filtered_files = [blob.name for blob in blobs
                          if any(blob.name.lower().endswith(ext) for ext in image_extensions)]

        if len(filtered_files) > 0:
            self.download_and_display_image(filtered_files[0])

        else:
            wx.MessageBox("No image file found.", "Error")

    def download_and_display_image(self, file_path):
        FirebaseDatabase.get_instance()
        bucket = storage.bucket()
        blob = bucket.blob(file_path)
        image_data = blob.download_as_bytes()

        pil_image = Image.open(io.BytesIO(image_data))
        original_width, original_height = pil_image.size

        # Calculate scaling
        if original_width / original_height > 500 / 800:
            # If the image aspect ratio is wider, it will be scaled according to the width
            self.scale_factor = 500 / original_width
        else:
            # If the image is narrow in width and height, it will be scaled according to the height
            self.scale_factor = 800 / original_height

        pil_image.thumbnail((original_width * self.scale_factor,
                             original_height * self.scale_factor),
                            Image.Resampling.LANCZOS)

        with io.BytesIO() as output:
            pil_image.save(output, format='PNG')
            output.seek(0)
            wx_image = wx.Image(output)
            if wx_image.IsOk():
                self.final_bitmap = wx_image.ConvertToBitmap()
                self.update_image_with_devices()

    def display_light_devices_on_image(self):
        FirebaseDatabase.get_instance()
        ref = db.reference('room/device/light')

        light_devices = ref.get()
        for device_id, device_info in light_devices.items():
            if 'coordinates' in device_info and 'detailed_type' in device_info:
                if device_info['detailed_type'] == 'light':
                    scaled_x = device_info['coordinates'][0] * self.scale_factor
                    scaled_y = device_info['coordinates'][1] * self.scale_factor
                    self.device_coordinates.append((scaled_x, scaled_y))

        self.update_image_with_devices()

    def update_image_with_devices(self):
        if self.final_bitmap is not None and self.device_coordinates:
            # Create a temporary memory DC to draw marker points
            temp_bitmap = wx.Bitmap(self.final_bitmap.Width, self.final_bitmap.Height)
            dc = wx.MemoryDC(temp_bitmap)
            dc.DrawBitmap(self.final_bitmap, 0, 0, True)

            # Draw marker points on the image
            dc.SetPen(wx.Pen(wx.Colour(255, 165, 0), 3))
            dc.SetBrush(wx.Brush(wx.Colour(255, 165, 0)))
            for x, y in self.device_coordinates:
                dc.DrawCircle(round(x), round(y), 7)

            dc.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            dc.SetTextForeground(wx.Colour(255, 165, 0))

            FirebaseDatabase.get_instance()
            ref = db.reference('room/device/light')

            light_devices = ref.get()
            for device_id, device_info in light_devices.items():
                if 'coordinates' in device_info and 'detailed_type' in device_info:
                    if device_info['detailed_type'] == 'light':
                        if device_id in light_devices and 'device_name' in light_devices[device_id]:
                            device_name = light_devices[device_id]['device_name']
                            scaled_x = device_info['coordinates'][0] * self.scale_factor
                            scaled_y = device_info['coordinates'][1] * self.scale_factor
                            dc.DrawText(device_name, round(scaled_x) + 10, round(scaled_y) + 10)

            dc.SelectObject(wx.NullBitmap)
            self.final_bitmap = temp_bitmap

            self.image_panel.Refresh()

    @staticmethod
    def fetch_light_devices():
        light_devices_ref = db.reference('room/device/light')
        light_devices = light_devices_ref.get()
        light_status_ref = db.reference('light/light')

        light_data = []
        for device_id, device_info in light_devices.items():
            if 'detailed_type' in device_info and device_info['detailed_type'] == 'light':
                related_devices = []
                for temp_id, temp_info in light_devices.items():
                    if device_id in temp_info.get('bound_devices', []):
                        related_devices.append(temp_id)

                light_data.append({
                    'Light Id': device_id,
                    'Light Name': device_info.get('device_name', ''),
                    'Switch': device_info.get('switch', False),
                    'Brightness': device_info.get('brightness', 0),
                    'Auto': device_info.get('auto_mode', False),
                    'Related Devices': related_devices
                })
        return light_data

    def display_light_devices(self):
        light_data = self.fetch_light_devices()
        self.list_ctrl.DeleteAllItems()

        for item in light_data:
            index = self.list_ctrl.InsertItem(self.list_ctrl.GetItemCount(), item['Light Id'])
            self.list_ctrl.SetItem(index, 1, item['Light Name'])
            self.list_ctrl.SetItem(index, 2, str(item['Switch']))
            self.list_ctrl.SetItem(index, 3, str(item['Brightness']))
            self.list_ctrl.SetItem(index, 4, str(item['Auto']))
            self.list_ctrl.SetItem(index, 5, str(", ".join(item['Related Devices'])))

    def on_refresh(self, event):
        self.display_light_devices()


class LightControlPopup(wx.Frame):
    def __init__(self, parent, light_data):
        super().__init__(parent, title=f"Control Light: {light_data['Light Name']}")

        self.light_data = light_data

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.timer.Start(10000)

        self.switch_label = wx.StaticText(self, label=f"Switch: {light_data['Switch']}")
        self.switch_button = wx.Button(self, label="Turn ON/OFF")

        self.auto_label = wx.StaticText(self, label=f"Auto mode: {light_data['Auto']}")
        self.auto_button = wx.Button(self, label="Turn ON/OFF")

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.switch_label, 1, wx.ALL | wx.EXPAND, 5)
        hbox1.Add(self.switch_button, 1, wx.ALL | wx.EXPAND, 5)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(self.auto_label, 1, wx.ALL | wx.EXPAND, 5)
        hbox2.Add(self.auto_button, 1, wx.ALL | wx.EXPAND, 5)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox1, 1, wx.EXPAND)
        vbox.Add(hbox2, 1, wx.EXPAND)

        self.brightness_label = wx.StaticText(self, label=f"Brightness: {light_data['Brightness']}")
        self.brightness_plus_button = wx.Button(self, label="Brightness +")
        self.brightness_minus_button = wx.Button(self, label="Brightness -")

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(self.brightness_label, 1, wx.ALL | wx.EXPAND, 5)
        hbox3.Add(self.brightness_plus_button, 1, wx.ALL | wx.EXPAND, 5)
        hbox3.Add(self.brightness_minus_button, 1, wx.ALL | wx.EXPAND, 5)

        vbox.Add(hbox3, 1, wx.EXPAND)

        self.Bind(wx.EVT_BUTTON, self.on_switch_button_click, self.switch_button)
        self.Bind(wx.EVT_BUTTON, self.on_auto_button_click, self.auto_button)
        self.Bind(wx.EVT_BUTTON, self.on_brightness_plus_button_click, self.brightness_plus_button)
        self.Bind(wx.EVT_BUTTON, self.on_brightness_minus_button_click, self.brightness_minus_button)

        self.update_buttons_status()

        self.SetSizer(vbox)

    def on_switch_button_click(self, event):
        # Toggle the switch status
        current_switch_status = self.light_data['Switch']
        new_switch_status = not current_switch_status
        if new_switch_status:
            new_brightness = 80
        else:
            new_brightness = 0

        # Update the switch status and brightness in the light_data
        self.light_data['Switch'] = new_switch_status
        self.light_data['Brightness'] = new_brightness

        self.switch_label.SetLabel(f"Switch: {'ON' if new_switch_status else 'OFF'}")
        self.brightness_label.SetLabel(f"Brightness: {new_brightness}")

        try:
            amsterdam_timezone = pytz.timezone('Europe/Amsterdam')
            current_time = datetime.datetime.now(amsterdam_timezone).strftime("%Y-%m-%d %H:%M:%S")
            history_ref = db.reference('/light/light/' + self.light_data['Light Id'] + '/' + current_time)
            history_ref.update({'switch': new_switch_status, 'brightness': new_brightness, 'auto_mode': self.light_data['Auto']})

            ref = db.reference('/room/device/light/' + self.light_data['Light Id'] + '/')
            ref.update({'switch': new_switch_status, 'brightness': new_brightness})
        except Exception as e:
            print(f"Error uploading data to Firebase: {e}")

    def on_auto_button_click(self, event):
        # Toggle the auto mode status
        current_auto_status = self.light_data['Auto']
        if current_auto_status == "Unknown":
            new_auto_status = False
        else:
            new_auto_status = not current_auto_status

        self.light_data['Auto'] = new_auto_status
        self.auto_label.SetLabel(f"Auto mode: {'ON' if new_auto_status else 'OFF'}")

        self.update_buttons_status()

        try:
            ref = db.reference(f"/room/device/light/{self.light_data['Light Id']}/auto_mode")
            ref.set(new_auto_status)
            amsterdam_timezone = pytz.timezone('Europe/Amsterdam')
            current_time = datetime.datetime.now(amsterdam_timezone).strftime("%Y-%m-%d %H:%M:%S")
            history_ref = db.reference('/light/light/' + self.light_data['Light Id'] + '/' + current_time)
            history_ref.update({'switch': self.light_data['Switch'], 'brightness': self.light_data['Brightness'], 'auto_mode': new_auto_status})
        except Exception as e:
            print(f"Error uploading auto mode data to Firebase: {e}")

    def on_brightness_plus_button_click(self, event):
        # Increase the brightness by a certain amount in the light_data
        current_switch_status = self.light_data['Switch']
        current_brightness = int(self.light_data['Brightness'])
        new_brightness = min(current_brightness + 10, 100)
        self.light_data['Brightness'] = new_brightness
        # Update the brightness label on the GUI
        self.brightness_label.SetLabel(f"Brightness: {new_brightness}")

        if current_switch_status == 0:
            self.switch_label.SetLabel("Switch: ON")

        # Upload data to Firebase
        try:
            amsterdam_timezone = pytz.timezone('Europe/Amsterdam')
            current_time = datetime.datetime.now(amsterdam_timezone).strftime("%Y-%m-%d %H:%M:%S")
            history_ref = db.reference('/light/light/' + self.light_data['Light Id'] + '/' + current_time)
            history_ref.update({'switch': True, 'brightness': new_brightness, 'auto_mode': self.light_data['Auto']})

            ref = db.reference('/room/device/light/' + self.light_data['Light Id'] + '/')
            ref.update({'switch': True, 'brightness': new_brightness})
        except Exception as e:
            print(f"Error uploading brightness data to Firebase: {e}")

    def on_brightness_minus_button_click(self, event):
        # Decrease the brightness by a certain amount in the light_data
        current_brightness = int(self.light_data['Brightness'])
        new_brightness = max(current_brightness - 10, 0)  # Decrease brightness by 10, capped at 0

        self.light_data['Brightness'] = new_brightness
        # Update the brightness label on the GUI
        self.brightness_label.SetLabel(f"Brightness: {new_brightness}")

        if new_brightness == 0:
            self.switch_label.SetLabel("Switch: OFF")
            new_switch_status = 0
        else:
            new_switch_status = 1

        # Upload data to Firebase
        try:
            amsterdam_timezone = pytz.timezone('Europe/Amsterdam')
            current_time = datetime.datetime.now(amsterdam_timezone).strftime("%Y-%m-%d %H:%M:%S")

            history_ref = db.reference('/light/light/' + self.light_data['Light Id'] + '/' + current_time)
            history_ref.update({'switch': new_switch_status, 'brightness': new_brightness, 'auto_mode': self.light_data['Auto']})

            ref = db.reference('/room/device/light/' + self.light_data['Light Id'] + '/')
            ref.update({'switch': new_switch_status, 'brightness': new_brightness})
        except Exception as e:
            print(f"Error uploading brightness data to Firebase: {e}")

    def on_timer(self, event):
        # Timer events, update data and update display
        light_data = self.GetParent().fetch_light_devices()
        # Find the latest data for the corresponding lamp
        for item in light_data:
            if item['Light Id'] == self.light_data['Light Id']:
                self.light_data = item
                break
        # Update display
        self.switch_label.SetLabel(f"Switch: {self.light_data['Switch']}")
        self.auto_label.SetLabel(f"Auto mode: {self.light_data['Auto']}")
        self.brightness_label.SetLabel(f"Brightness: {self.light_data['Brightness']}")

    def update_buttons_status(self):
        # If auto mode is True, disables a specific button
        is_auto_mode = self.light_data.get('Auto', False)
        self.switch_button.Enable(not is_auto_mode)
        self.brightness_plus_button.Enable(not is_auto_mode)
        self.brightness_minus_button.Enable(not is_auto_mode)


class SelectTimePeriodDialog(wx.Dialog):
    def __init__(self, parent):
        super(SelectTimePeriodDialog, self).__init__(parent, title="Select Time Period", size=(300, 250))

        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.startDatePicker = (wx.adv.DatePickerCtrl(self.panel, style=wx.adv.DP_DROPDOWN))
        self.startTimePicker = wx.adv.TimePickerCtrl(self.panel)
        self.durationTxt = wx.TextCtrl(self.panel, value="60", style=wx.TE_PROCESS_ENTER)

        vbox.Add(wx.StaticText(self.panel, -1, "Start Date:"), flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(self.startDatePicker, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)
        vbox.Add(wx.StaticText(self.panel, -1, "Start Time:"), flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(self.startTimePicker, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)
        vbox.Add(wx.StaticText(self.panel, -1, "Duration (minutes):"), flag=wx.LEFT|wx.TOP, border=10)
        vbox.Add(self.durationTxt, flag=wx.EXPAND | wx.LEFT | wx.RIGHT, border=10)

        self.okButton = wx.Button(self.panel, label='Ok')
        self.okButton.Bind(wx.EVT_BUTTON, self.onOk)
        self.cancelButton = wx.Button(self.panel, label='Cancel')
        self.cancelButton.Bind(wx.EVT_BUTTON, self.onCancel)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.okButton, flag=wx.RIGHT, border=5)
        hbox.Add(self.cancelButton, flag=wx.RIGHT, border=5)

        vbox.Add(hbox, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)

        self.panel.SetSizer(vbox)

    def onOk(self, event):
        self.EndModal(wx.ID_OK)

    def onCancel(self, event):
        self.EndModal(wx.ID_CANCEL)

    def getValues(self):
        startDate = self.startDatePicker.GetValue()
        startTime = self.startTimePicker.GetValue()

        # Combine date and time into a single datetime object
        startDateTime = wx.DateTime(startDate).SetHour(startTime.GetHour()).SetMinute(startTime.GetMinute())

        durationMinutes = self.durationTxt.GetValue()
        try:
            durationMinutes = int(durationMinutes)
        except ValueError:
            durationMinutes = 0

        return startDateTime, durationMinutes


class HistoryDialog(wx.Dialog):
    def __init__(self, parent, title, processed_data):
        super(HistoryDialog, self).__init__(parent, title=title)

        dataListCtrl = wx.ListCtrl(self, style=wx.LC_REPORT)
        dataListCtrl.InsertColumn(0, "Time", width=140)
        dataListCtrl.InsertColumn(1, "Data", wx.LIST_FORMAT_RIGHT, 90)

        for idx, (time, brightness) in enumerate(processed_data):
            dataListCtrl.InsertItem(idx, time)
            dataListCtrl.SetItem(idx, 1, str(brightness))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(dataListCtrl, 1, wx.EXPAND | wx.ALL, 5)
        self.SetSizerAndFit(sizer)
