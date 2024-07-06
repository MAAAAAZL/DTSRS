import wx
import wx.adv
import webbrowser
import os
import tempfile
import requests
import cv2

from datetime import datetime, timedelta
from firebase_admin import db, storage

from FirebaseDatabase import FirebaseDatabase


class SecuritySubsystem:
    def __init__(self):
        pass


class SecuritySubsystemFrame(wx.Frame):
    def __init__(self, parent, mainFrame, currentUsername):
        SecuritySubsystem.__init__(self)
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title="Security",
                          pos=wx.DefaultPosition, size=wx.Size(400, 300),
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
        self.mainFrame = mainFrame
        self.currentUsername = currentUsername
        self.panel = wx.Panel(self)
        self.SetPosition(wx.Point(650, 350))

        # Set up a grid layout
        self.grid = wx.GridSizer(3, 2, 10, 10)

        self.buttons = {
            6001: ("Edit Current Account", self.onEditCurrentAccount),
            6002: ("Add New Account", self.onAddNewAccount),
            6003: ("Delete Account", self.onDeleteAccount),
            6004: ("Check Live Camera", self.onCheckLiveCamera),
            6005: ("View Camera Records", self.onViewCameraRecords),
            6007: ("Return to Main", self.onReturnToMain)
        }

        for btnId, (label, handler) in self.buttons.items():
            button = wx.Button(self.panel, btnId, label)
            button.Bind(wx.EVT_BUTTON, handler)
            self.grid.Add(button, 0, wx.EXPAND)

        self.panel.SetSizer(self.grid)
        self.Layout()
        self.Centre(wx.BOTH)

    def onEditCurrentAccount(self, event):
        editDialog = EditAccountDialog(self, self.currentUsername)
        editDialog.ShowModal()

    def onAddNewAccount(self, event):
        addDialog = AddAccountDialog(self)
        addDialog.ShowModal()

    def onDeleteAccount(self, event):
        deleteDialog = DeleteAccountDialog(self)
        deleteDialog.ShowModal()

    def onCheckLiveCamera(self, event):
        dialog = CameraSelectionDialog(self)
        dialog.ShowModal()

    def onViewCameraRecords(self, event):
        dialog = ViewCameraRecordsDialog(self)
        dialog.ShowModal()

    def onReturnToMain(self, event):
        self.mainFrame.Show()
        self.Close()


class EditAccountDialog(wx.Dialog):
    def __init__(self, parent, currentUsername):
        super(EditAccountDialog, self).__init__(parent, title="Edit Account", size=(250, 300))
        self.currentUsername = currentUsername
        self.panel = wx.Panel(self)

        sizer = wx.BoxSizer(wx.VERTICAL)

        # Get UID from Firebase
        db_instance = FirebaseDatabase.get_instance()
        user_ref = db.reference(f'security/account/{currentUsername}')
        user_data = user_ref.get() or {}
        uid = user_data.get('uid', 'Unknown UID')

        # Display UID
        self.uidText = wx.StaticText(self.panel, label=f"UID: {uid}")
        sizer.Add(self.uidText, 0, wx.ALL | wx.EXPAND, 5)

        self.btnChangePassword = wx.Button(self.panel, label="Change Password")
        sizer.Add(self.btnChangePassword, 0, wx.ALL | wx.EXPAND, 5)
        self.btnChangePassword.Bind(wx.EVT_BUTTON, self.onChangePassword)

        self.btnSetAccessPin = wx.Button(self.panel, label="Set/Change Access PIN")
        sizer.Add(self.btnSetAccessPin, 0, wx.ALL | wx.EXPAND, 5)
        self.btnSetAccessPin.Bind(wx.EVT_BUTTON, self.onSetAccessPin)

        self.btnReturn = wx.Button(self.panel, label="Return")
        sizer.Add(self.btnReturn, 0, wx.ALL | wx.EXPAND, 5)
        self.btnReturn.Bind(wx.EVT_BUTTON, self.onReturn)

        self.panel.SetSizer(sizer)
        self.Centre()

    def onChangePassword(self, event):
        dialog = ChangePasswordDialog(self, self.currentUsername)
        result = dialog.ShowModal()
        if result == wx.ID_OK:
            wx.MessageBox("Password changed successfully.", "Success", wx.OK | wx.ICON_INFORMATION)

    def onSetAccessPin(self, event):
        dialog = SetAccessPINDialog(self, self.currentUsername)
        result = dialog.ShowModal()
        if result == wx.ID_OK:
            wx.MessageBox("Access PIN set successfully.", "Success", wx.OK | wx.ICON_INFORMATION)

    def onReturn(self, event):
        self.EndModal(wx.ID_CANCEL)


class ChangePasswordDialog(wx.Dialog):
    def __init__(self, parent, currentUsername):
        super(ChangePasswordDialog, self).__init__(parent, title="Change Password", size=(300, 300))
        self.currentUsername = currentUsername
        self.panel = wx.Panel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)

        self.currentPasswordText = wx.StaticText(self.panel, label="Current Password:")
        self.currentPassword = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)
        vbox.Add(self.currentPasswordText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.currentPassword, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.newPasswordText = wx.StaticText(self.panel, label="New Password:")
        self.newPassword = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)
        vbox.Add(self.newPasswordText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.newPassword, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.confirmPasswordText = wx.StaticText(self.panel, label="Confirm New Password:")
        self.confirmPassword = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)
        vbox.Add(self.confirmPasswordText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.confirmPassword, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.submitButton = wx.Button(self.panel, label="Submit")
        self.submitButton.Bind(wx.EVT_BUTTON, self.onSubmit)
        vbox.Add(self.submitButton, proportion=0, flag=wx.ALL | wx.CENTER, border=5)

        self.panel.SetSizer(vbox)
        self.Centre()

    def onSubmit(self, event):
        current_password = self.currentPassword.GetValue()
        new_password = self.newPassword.GetValue()
        confirm_password = self.confirmPassword.GetValue()

        if new_password != confirm_password:
            wx.MessageBox("The new passwords do not match.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if not new_password.isalnum():
            wx.MessageBox("The new password must only contain letters and numbers.", "Error", wx.OK | wx.ICON_ERROR)
            return

        FirebaseDatabase.get_instance()
        account_ref = db.reference(f'security/account/{self.currentUsername}/password')
        db_password = account_ref.get()

        if db_password != current_password:
            wx.MessageBox("Current password is incorrect.", "Error", wx.OK | wx.ICON_ERROR)
            return

        account_ref.set(new_password)
        self.EndModal(wx.ID_OK)


class SetAccessPINDialog(wx.Dialog):
    def __init__(self, parent, username):
        super(SetAccessPINDialog, self).__init__(parent, title="Set Access PIN", size=(300, 300))
        self.username = username
        self.panel = wx.Panel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)

        self.currentPasswordText = wx.StaticText(self.panel, label="Current Password:")
        self.currentPassword = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)
        vbox.Add(self.currentPasswordText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.currentPassword, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.newPINText = wx.StaticText(self.panel, label="New PIN (6 digits):")
        self.newPIN = wx.TextCtrl(self.panel)
        vbox.Add(self.newPINText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.newPIN, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.confirmPINText = wx.StaticText(self.panel, label="Confirm New PIN:")
        self.confirmPIN = wx.TextCtrl(self.panel)
        vbox.Add(self.confirmPINText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.confirmPIN, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.submitButton = wx.Button(self.panel, label="Submit")
        self.submitButton.Bind(wx.EVT_BUTTON, self.onSubmit)
        vbox.Add(self.submitButton, proportion=0, flag=wx.ALL | wx.CENTER, border=5)

        self.panel.SetSizer(vbox)
        self.Centre()

    def onSubmit(self, event):
        current_password = self.currentPassword.GetValue()
        new_pin = self.newPIN.GetValue()
        confirm_pin = self.confirmPIN.GetValue()

        if not new_pin.isdigit() or not len(new_pin) == 6:
            wx.MessageBox("The new PIN must be 6 digits.", "Error", wx.OK | wx.ICON_ERROR)
            return

        if new_pin != confirm_pin:
            wx.MessageBox("The new PINs do not match.", "Error", wx.OK | wx.ICON_ERROR)
            return

        FirebaseDatabase.get_instance()
        account_ref = db.reference(f'security/account/{self.username}')
        db_password = account_ref.child('password').get()

        if db_password != current_password:
            wx.MessageBox("Current password is incorrect.", "Error", wx.OK | wx.ICON_ERROR)
            return

        account_ref.update({'pincode': new_pin})
        wx.MessageBox("Access PIN set successfully.", "Success", wx.OK | wx.ICON_INFORMATION)
        self.EndModal(wx.ID_OK)


class AddAccountDialog(wx.Dialog):
    def __init__(self, parent):
        super(AddAccountDialog, self).__init__(parent, title="Add New Account", size=(350, 400))
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Username entry
        self.usernameText = wx.StaticText(self.panel, label="Username (max 16 characters):")
        self.username = wx.TextCtrl(self.panel)
        vbox.Add(self.usernameText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.username, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # Password entry
        self.passwordText = wx.StaticText(self.panel, label="Password (letters and numbers):")
        self.password = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)
        self.confirmPasswordText = wx.StaticText(self.panel, label="Confirm Password:")
        self.confirmPassword = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)
        vbox.Add(self.passwordText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.password, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)
        vbox.Add(self.confirmPasswordText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.confirmPassword, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # PIN code entry
        self.pinText = wx.StaticText(self.panel, label="PIN Code (6 digits):")
        self.pin = wx.TextCtrl(self.panel)
        self.confirmPinText = wx.StaticText(self.panel, label="Confirm PIN Code:")
        self.confirmPin = wx.TextCtrl(self.panel)
        vbox.Add(self.pinText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.pin, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)
        vbox.Add(self.confirmPinText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.confirmPin, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # Submit button
        self.submitButton = wx.Button(self.panel, label="Submit")
        self.submitButton.Bind(wx.EVT_BUTTON, self.onSubmit)
        vbox.Add(self.submitButton, proportion=0, flag=wx.ALL | wx.CENTER, border=5)

        self.panel.SetSizer(vbox)
        self.Centre()

    def onSubmit(self, event):
        username = self.username.GetValue()
        password = self.password.GetValue()
        confirm_password = self.confirmPassword.GetValue()
        pin = self.pin.GetValue()
        confirm_pin = self.confirmPin.GetValue()

        # Check if any field is empty
        if not all([username, password, confirm_password, pin, confirm_pin]):
            wx.MessageBox("All fields must be filled out.", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Validate the inputs
        if len(username) > 16:
            wx.MessageBox("Username must be 16 characters or less.", "Error", wx.OK | wx.ICON_ERROR)
            return
        if not (password.isalnum() and confirm_password.isalnum()):
            wx.MessageBox("Passwords must contain only letters and numbers.", "Error", wx.OK | wx.ICON_ERROR)
            return
        if password != confirm_password:
            wx.MessageBox("Passwords do not match.", "Error", wx.OK | wx.ICON_ERROR)
            return
        if not (pin.isdigit() and len(pin) == 6 and confirm_pin.isdigit() and len(confirm_pin) == 6):
            wx.MessageBox("PIN codes must be 6 digits.", "Error", wx.OK | wx.ICON_ERROR)
            return
        if pin != confirm_pin:
            wx.MessageBox("PIN codes do not match.", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Check if username already exists
        FirebaseDatabase.get_instance()
        accounts_ref = db.reference('security/account')
        accounts = accounts_ref.get() or {}

        if username in accounts:
            wx.MessageBox("This username already exists. Please choose another.", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Generate a new UID
        uids = [int(acc_info.get('uid', '0')) for acc_info in accounts.values()]
        if uids:
            new_uid = max(uids) + 1
        else:
            new_uid = 1  # Start from 1 if no UIDs are found

        if new_uid > 9999:
            wx.MessageBox("User limit reached. No more users can be added.", "Error", wx.OK | wx.ICON_ERROR)
            return

        # Upload to Firebase
        accounts_ref.child(username).set({
            'password': password,
            'pincode': pin,
            'uid': f"{new_uid:04}"
        })

        wx.MessageBox(f"Account created successfully. Your UID is {new_uid:04}.", "Success", wx.OK | wx.ICON_INFORMATION)
        self.EndModal(wx.ID_OK)


class DeleteAccountDialog(wx.Dialog):
    def __init__(self, parent):
        super(DeleteAccountDialog, self).__init__(parent, title="Delete Account", size=(350, 250))
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Username entry
        self.usernameText = wx.StaticText(self.panel, label="Username:")
        self.username = wx.TextCtrl(self.panel)
        vbox.Add(self.usernameText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.username, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # Password entry
        self.passwordText = wx.StaticText(self.panel, label="Password:")
        self.password = wx.TextCtrl(self.panel, style=wx.TE_PASSWORD)
        vbox.Add(self.passwordText, proportion=0, flag=wx.ALL, border=5)
        vbox.Add(self.password, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        # Submit button
        self.deleteButton = wx.Button(self.panel, label="Delete Account")
        self.deleteButton.Bind(wx.EVT_BUTTON, self.onDelete)
        vbox.Add(self.deleteButton, proportion=0, flag=wx.ALL | wx.CENTER, border=5)

        self.panel.SetSizer(vbox)
        self.Centre()

    def onDelete(self, event):
        username = self.username.GetValue()
        password = self.password.GetValue()

        # Verify credentials
        FirebaseDatabase.get_instance()
        account_ref = db.reference(f'security/account/{username}/password')
        db_password = account_ref.get()

        if db_password == password:
            # Ask for confirmation before deletion
            confirm = wx.MessageBox("Are you sure you want to delete this account?", "Confirm Deletion",
                                    wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            if confirm == wx.YES:
                # Delete the account
                db.reference(f'security/account/{username}').delete()
                wx.MessageBox("Account deleted successfully.", "Success", wx.OK | wx.ICON_INFORMATION)
                self.EndModal(wx.ID_OK)
            else:
                self.EndModal(wx.ID_CANCEL)
        else:
            wx.MessageBox("Incorrect username or password.", "Error", wx.OK | wx.ICON_ERROR)


class CameraSelectionDialog(wx.Dialog):
    def __init__(self, parent):
        super(CameraSelectionDialog, self).__init__(parent, title="Select Camera", size=(300, 400))
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        self.listBox = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        vbox.Add(self.listBox, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)

        self.selectButton = wx.Button(self.panel, label="Select")
        self.selectButton.Bind(wx.EVT_BUTTON, self.onSelect)
        vbox.Add(self.selectButton, proportion=0, flag=wx.EXPAND | wx.ALL, border=5)

        self.panel.SetSizer(vbox)
        self.Centre()
        self.load_cameras()

    def load_cameras(self):
        try:
            FirebaseDatabase.get_instance()
            devices_ref = db.reference('room/device/security')
            devices = devices_ref.get() or {}
            cameras = [device_id for device_id, details in devices.items() if details.get('detailed_type') == 'camera']
            for camera in cameras:
                self.listBox.Append(camera)
        except Exception as e:
            wx.MessageBox(f"Failed to load camera list: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)

    def onSelect(self, event):
        try:
            selected_camera = self.listBox.GetString(self.listBox.GetSelection())
            device_ref = db.reference(f'room/device/security/{selected_camera}')
            device_info = device_ref.get()
            if device_info:
                ip_address = device_info.get("ip_address")
                if ip_address:
                    url = f'http://{ip_address}:3333/video_feed'
                    webbrowser.open(url)
                else:
                    wx.MessageBox("No IP address available for selected camera.", "Error", wx.OK | wx.ICON_ERROR)
            else:
                wx.MessageBox("No details available for selected camera.", "Error", wx.OK | wx.ICON_ERROR)

            self.Close()
        except Exception as e:
            wx.MessageBox(f"Failed to open video feed: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)
        finally:
            self.Close()


class ViewCameraRecordsDialog(wx.Dialog):
    def __init__(self, parent):
        super(ViewCameraRecordsDialog, self).__init__(parent, title="View Camera Records", size=(400, 300))
        self.panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Camera selection
        self.cameraList = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        vbox.Add(wx.StaticText(self.panel, label="Select Camera:"), flag=wx.LEFT | wx.TOP, border=10)
        vbox.Add(self.cameraList, proportion=1, flag=wx.EXPAND | wx.ALL, border=5)
        self.load_cameras()

        # Time selection
        vbox.Add(wx.StaticText(self.panel, label="Select Time:"), flag=wx.LEFT | wx.TOP, border=10)
        self.datePicker = wx.adv.DatePickerCtrl(self.panel, style=wx.adv.DP_DROPDOWN | wx.adv.DP_SHOWCENTURY)
        vbox.Add(self.datePicker, flag=wx.EXPAND | wx.ALL, border=5)
        self.timePicker = wx.adv.TimePickerCtrl(self.panel)
        vbox.Add(self.timePicker, flag=wx.EXPAND | wx.ALL, border=5)

        # Submit button
        submitButton = wx.Button(self.panel, label="View Record")
        submitButton.Bind(wx.EVT_BUTTON, self.onViewRecord)
        vbox.Add(submitButton, flag=wx.ALIGN_CENTER | wx.ALL, border=5)

        self.panel.SetSizer(vbox)
        self.Centre()

    def load_cameras(self):
        FirebaseDatabase.get_instance()
        devices_ref = db.reference('room/device/security')
        devices = devices_ref.get() or {}
        cameras = [device_id for device_id, details in devices.items() if details.get('detailed_type') == 'camera']
        for camera in cameras:
            self.cameraList.Append(camera)

    def onViewRecord(self, event):
        selected_index = self.cameraList.GetSelection()
        if selected_index == -1:
            wx.MessageBox("Please select a camera.", "Error", wx.OK | wx.ICON_ERROR)
            return

        selected_camera = self.cameraList.GetString(selected_index)

        date_value = self.datePicker.GetValue()
        time_value = self.timePicker.GetValue()

        selected_datetime = datetime(
            year=date_value.GetYear(), month=date_value.GetMonth() + 1,
            day=date_value.GetDay(), hour=time_value.GetHour(),
            minute=time_value.GetMinute(), second=time_value.GetSecond()
        )

        self.fetch_and_play_video(selected_camera, selected_datetime)

    def fetch_and_play_video(self, camera_id, target_datetime):
        try:
            # Firebase 存储路径
            videos_path = f'remote/security/{camera_id}/'
            bucket = storage.bucket()
            blobs = bucket.list_blobs(prefix=videos_path)
            video_records = [(blob.name, self.extract_datetime_from_filename(blob.name)) for blob in blobs]

            # 找到最合适的视频文件
            video_to_play = self.find_closest_video(video_records, target_datetime)
            if video_to_play:
                print(f"Playing video from: {video_to_play}")
                self.play_video(video_to_play)
            else:
                wx.MessageBox("No suitable video file found。", "Information", wx.OK | wx.ICON_INFORMATION)

        except Exception as e:
            wx.MessageBox(f"Error accessing Firebase: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)

    @staticmethod
    def extract_datetime_from_filename(filename):
        # Example path 'remote/security/device_id/YYYYMMDD_HHMMSS.mp4'
        base = os.path.basename(filename)
        timestamp_str = base.split('/')[-1].split('.')[0]
        return datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")

    @staticmethod
    def find_closest_video(video_records, target_datetime):
        # 按照时间排序视频记录
        video_records.sort(key=lambda x: x[1])
        # 找到时间最接近且不晚于目标时间的视频
        for i in range(len(video_records) - 1, -1, -1):
            start_time = video_records[i][1]
            end_time = start_time + timedelta(minutes=5)
            if start_time <= target_datetime < end_time:
                return video_records[i][0]

        return None

    @staticmethod
    def play_video(video_path):
        bucket = storage.bucket()
        blob = bucket.blob(video_path)
        try:
            url = blob.generate_signed_url(expiration=timedelta(seconds=350), method='GET')
            webbrowser.open(url)

        except Exception as e:
            wx.MessageBox(f"An error occurred while generating the video link：{str(e)}", "Error", wx.OK | wx.ICON_ERROR)
