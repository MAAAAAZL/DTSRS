import time

import wx
import datetime
import pytz

from firebase_admin import db, exceptions

import HvacSubsystem
import LightSubsystem
import RoomSubsystem
import SafetySubsystem
import SecuritySubsystem
import AudioSubsystem
from FirebaseDatabase import FirebaseDatabase


class DTSRS:
    def __init__(self):
        self.currentUsername = None
        self.initialCheckDone = False
        self.initialize_safety_settings()
        self.check_for_accounts()

    def check_for_accounts(self):
        FirebaseDatabase.get_instance()
        try:
            account_ref = db.reference('security/account')
            accounts = account_ref.get()
            if not accounts:
                wx.CallAfter(self.prompt_for_account_creation)
            else:
                self.show_login_dialog()
        except exceptions.FirebaseError as e:
            print(f"Error checking for accounts: {e}")

    @staticmethod
    def prompt_for_account_creation():
        message = "There is no user account in the current system, it is recommended to create one."
        wx.MessageBox(message, "Set up user", wx.OK | wx.ICON_INFORMATION)

    def show_login_dialog(self):
        login_dialog = LoginDialog(None, self)
        if login_dialog.ShowModal() == wx.ID_OK:
            pass

    def initialize_safety_settings(self):
        FirebaseDatabase.get_instance()
        safety_ref = db.reference('settings/safety')
        safety_settings = safety_ref.get()

        amsterdam_timezone = pytz.timezone('Europe/Amsterdam')
        current_time = datetime.datetime.now(amsterdam_timezone).strftime("%Y-%m-%d %H:%M:%S")

        if not safety_settings or "isEmergency" not in safety_settings or "emergencyDevices" not in safety_settings:
            safety_ref.set({
                'isEmergency': False,
                'emergencyDevices': [],
                'expirationDatetime': current_time
            })

        safety_ref.child('isEmergency').listen(self.on_isEmergency_change)
        time.sleep(1)
        self.initialCheckDone = True

    def on_isEmergency_change(self, event):
        if self.initialCheckDone and event.data is not None:
            wx.CallAfter(self.handle_emergency_mode, event.data)

    @staticmethod
    def handle_emergency_mode(isEmergency):
        try:
            safety_ref = db.reference('settings/safety')
            expiration_datetime = safety_ref.child('expirationDatetime').get()

            if isEmergency:
                message = f"Emergency mode has been changed to activated. Please take necessary actions."
            else:
                message = (f"Emergency mode has been changed to deactivated. "
                           f"Please take necessary actions.\n"
                           f"Expiration of auto detection is {expiration_datetime}.")

            wx.MessageBox(message, "Emergency Mode", wx.OK | wx.ICON_WARNING if isEmergency else wx.ICON_INFORMATION)
        except exceptions.FirebaseError as e:
            print(f"Error fetching expirationDatetime: {e}")
            wx.MessageBox("Error fetching expirationDatetime.", "Error", wx.OK | wx.ICON_ERROR)


class LoginDialog(wx.Dialog):
    def __init__(self, parent, dtsrs_instance):
        super(LoginDialog, self).__init__(parent, title="Login", size=(300, 200))
        self.dtsrs_instance = dtsrs_instance

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)

        username_sizer = wx.BoxSizer(wx.HORIZONTAL)
        username_label = wx.StaticText(panel, label="Username:")
        self.username = wx.TextCtrl(panel)
        username_sizer.Add(username_label, 0, wx.ALL | wx.CENTER, 5)
        username_sizer.Add(self.username, 1, wx.ALL | wx.EXPAND, 5)

        password_sizer = wx.BoxSizer(wx.HORIZONTAL)
        password_label = wx.StaticText(panel, label="Password:")
        self.password = wx.TextCtrl(panel, style=wx.TE_PASSWORD)
        password_sizer.Add(password_label, 0, wx.ALL | wx.CENTER, 5)
        password_sizer.Add(self.password, 1, wx.ALL | wx.EXPAND, 5)

        login_button = wx.Button(panel, label="Login")
        login_button.Bind(wx.EVT_BUTTON, self.on_login_click)

        sizer.Add(username_sizer, 0, wx.EXPAND | wx.ALL, 10)
        sizer.Add(password_sizer, 0, wx.EXPAND | wx.ALL, 10)
        sizer.Add(login_button, 0, wx.ALL | wx.CENTER, 10)
        panel.SetSizer(sizer)

        self.Centre(wx.BOTH)

        self.Bind(wx.EVT_CLOSE, self.on_close)

    def on_login_click(self, event):
        username = self.username.GetValue()
        password = self.password.GetValue()

        FirebaseDatabase.get_instance()
        try:
            account_ref = db.reference(f'security/account/{username}/password')
            db_password = account_ref.get()

            if db_password == password:
                self.dtsrs_instance.currentUsername = username
                self.EndModal(wx.ID_OK)
            elif db_password is None:
                wx.MessageBox("Incorrect username or password。", "Error", wx.OK | wx.ICON_ERROR)
            else:
                wx.MessageBox("Incorrect username or password。", "Error", wx.OK | wx.ICON_ERROR)
        except exceptions.FirebaseError as e:
            print(f"An error occurred while logging in: {e}")
            wx.MessageBox("An error occurred during login。", "Error", wx.OK | wx.ICON_ERROR)
            self.EndModal(wx.ID_CANCEL)

    def on_close(self, event):
        self.EndModal(wx.ID_CANCEL)


class DTSRSFrame(DTSRS, wx.Frame):
    def __init__(self, parent):
        DTSRS.__init__(self)

        # Initialize the frame
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title="DTSRS - Initializing...",
                          pos=wx.DefaultPosition, size=wx.Size(400, 300),
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.panel = wx.Panel(self)  # Create a panel in this frame
        self.SetPosition(wx.Point(650, 350))  # Set the window position
        self.grid = wx.GridSizer(3, 3, 10, 10)  # Create a grid layout

        # Map button ID to subsystem framework constructor
        self.subsystem_frames = {
            1001: RoomSubsystem.RoomSubsystemFrame,
            1002: LightSubsystem.LightSubsystemFrame,
            1003: HvacSubsystem.HvacSubsystemFrame,
            1004: SafetySubsystem.SafetySubsystemFrame,
            1005: SecuritySubsystem.SecuritySubsystemFrame,
            1006: AudioSubsystem.AudioSubsystemFrame
        }

        # Define buttons with IDs
        self.buttons = {}
        btn_ids = [
            ("Room", 1001),
            ("Light", 1002),
            ("HVAC", 1003),
            ("Safety", 1004),
            ("Security", 1005),
            ("Audio", 1006),
            ("Emergency", 1007),
            ("Exit", 1008)
        ]

        for label, label_id in btn_ids:
            if label_id == 1008:
                button = wx.Button(self.panel, label_id, label)
                button.Bind(wx.EVT_BUTTON, self.OnButtonClicked)
                self.grid.Add(button, 0, wx.EXPAND)
            elif label_id == 1007:
                button = wx.Button(self.panel, label_id, label)
                button.Bind(wx.EVT_BUTTON, self.OnEmergencySwitch)
                self.grid.Add(button, 0, wx.EXPAND)
            else:
                button = wx.Button(self.panel, label_id, label)
                button.Bind(wx.EVT_BUTTON, self.OnButtonClicked)
                self.grid.Add(button, 0, wx.EXPAND)
                self.buttons[label] = button

        self.fetch_and_set_mode()

        self.panel.SetSizer(self.grid)
        self.Layout()
        self.Centre(wx.BOTH)

        # Create SafetySubsystem instance
        self.safety_subsystem = SafetySubsystem.SafetySubsystem()

        # Show login dialog and check result
        login_dialog = LoginDialog(None, self)
        if login_dialog.ShowModal() != wx.ID_OK:
            self.Close(True)

    def fetch_and_set_mode(self):
        """Fetch and set the system mode from the database"""
        try:
            FirebaseDatabase.get_instance()
            ref = db.reference('settings/safety')
            mode_value = ref.child('isEmergency').get()
            if mode_value:
                self.SetTitle("DTSRS - Emergency Mode")
            else:
                self.SetTitle("DTSRS")
        except exceptions.FirebaseError as e:
            print(f"Error fetching mode: {e}")

    def OnEmergencySwitch(self, event):
        try:
            FirebaseDatabase.get_instance()
            ref = db.reference('settings/safety')
            current_mode = bool(ref.child('isEmergency').get())
            new_mode = not current_mode

            # Upload the mode indicator in the database
            db.reference('settings/safety').update({'isEmergency': new_mode})
            if new_mode:
                self.SetTitle(f"DTSRS - Emergency Mode")
            else:
                self.SetTitle(f"DTSRS")

            if current_mode and not new_mode:
                self.update_expiration_datetime()
        except exceptions.FirebaseError as e:
            print(f"Error applying mode change: {e}")

    @staticmethod
    def update_expiration_datetime():
        amsterdam_timezone = pytz.timezone('Europe/Amsterdam')
        new_expiration_time = datetime.datetime.now(amsterdam_timezone) + datetime.timedelta(minutes=5)
        new_expiration_time_str = new_expiration_time.strftime("%Y-%m-%d %H:%M:%S")

        # Update expirationDatetime in database
        try:
            safety_ref = db.reference('settings/safety')
            safety_ref.update({'expirationDatetime': new_expiration_time_str})
            print("Updated expirationDatetime successfully.")
        except exceptions.FirebaseError as e:
            print(f"Error updating expirationDatetime: {e}")

    def OnButtonClicked(self, event):
        """Handle button click events"""
        clicked_btn_id = event.GetId()
        if clicked_btn_id == 1008:
            self.Close(True)
        elif clicked_btn_id == 1005:
            self.Hide()
            frame_class = self.subsystem_frames[clicked_btn_id]
            subsystemFrame = frame_class(None, self, self.currentUsername)
            subsystemFrame.Show()
        elif clicked_btn_id in self.subsystem_frames:
            self.Hide()
            frame_class = self.subsystem_frames[clicked_btn_id]
            subsystemFrame = frame_class(None, self)
            subsystemFrame.Show()


if __name__ == "__main__":
    # State: System_Initialization
    app = wx.App(False)
    frame = DTSRSFrame(None)
    frame.Show(True)

    app.MainLoop()
