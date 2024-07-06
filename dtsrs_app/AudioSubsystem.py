import wx
import sys
import socket
import sounddevice as sd
import numpy as np
import threading

from firebase_admin import storage, db
from FirebaseDatabase import FirebaseDatabase


class AudioSubsystem:
    def __init__(self):
        pass


class AudioSubsystemFrame(AudioSubsystem, wx.Frame):
    def __init__(self, parent, mainFrame):
        AudioSubsystem.__init__(self)
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title="Audio Subsystem",
                          pos=wx.DefaultPosition, size=wx.Size(400, 300),
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
        self.mainFrame = mainFrame

        self.threads = []
        self.running = False

        self.panel = wx.Panel(self)
        self.SetPosition(wx.Point(650, 350))

        self.grid = wx.GridSizer(4, 1, 10, 10)

        buttons = [
            ("Upload Emergency Audio", 7001),
            ("Broadcast", 7002),
            ("Stop Broadcast", 7004),
            ("Return to DTSRS", 7003)
        ]

        for label, btnId in buttons:
            button = wx.Button(self.panel, btnId, label)
            self.grid.Add(button, 0, wx.EXPAND)
            button.Bind(wx.EVT_BUTTON, self.OnButtonClicked)

        self.panel.SetSizer(self.grid)
        self.Layout()
        self.Centre(wx.BOTH)
        self.statusBar = self.CreateStatusBar()

    def OnButtonClicked(self, event):
        clickedBtnId = event.GetId()
        if clickedBtnId == 7001:
            self.upload_emergency_audio()
        elif clickedBtnId == 7002:
            if not self.running:
                self.broadcast_audio()
        elif clickedBtnId == 7004:
            self.stop_audio_stream()
        elif clickedBtnId == 7003:
            self.mainFrame.Show()
            self.Close()

    def upload_emergency_audio(self):
        with wx.FileDialog(self, "Select MP3 file", wildcard="MP3 files (*.mp3)|*.mp3",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as fileDialog:
            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return

            filepath = fileDialog.GetPath()
            filename = filepath.split('\\')[-1]

            self.clear_directory()

            try:
                FirebaseDatabase.get_instance()
                bucket = storage.bucket()
                blob = bucket.blob('remote/safety/' + filename)
                blob.upload_from_filename(filepath)
                wx.MessageBox("File uploaded successfully!", "Success", wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f"An error occurred: {str(e)}", "Error", wx.OK | wx.ICON_ERROR)

    @staticmethod
    def clear_directory():
        bucket = storage.bucket()
        blobs = bucket.list_blobs(prefix='remote/safety/')
        for blob in blobs:
            blob.delete()

    def broadcast_audio(self):
        self.upload_ip_to_firebase()
        self.running = True
        speaker_ips = self.fetch_pi_ip_address()

        for ip in speaker_ips:
            thread = threading.Thread(target=self.audio_stream, args=(ip,))
            thread.start()
            self.threads.append(thread)
        self.statusBar.SetStatusText("Broadcasting audio to all speakers...")

    def audio_stream(self, target_ip):
        samplerate = 44100
        channels = 1
        port = 12345
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            client_socket.connect((target_ip, port))
            print(f"Connected to server at {target_ip}:{port}")

            def audio_callback(indata, frames, time, status):
                if status:
                    print(status, file=sys.stderr)
                mono_data = indata[:, 0]
                int16_data = np.int16(mono_data * 32767)
                client_socket.send(int16_data.tobytes())

            with sd.InputStream(callback=audio_callback, samplerate=samplerate, channels=channels, blocksize=2048):
                while self.running:
                    pass
        except Exception as e:
            wx.CallAfter(self.update_status_bar, f"Failed to connect to {target_ip}: {e}")
        finally:
            client_socket.close()
            wx.CallAfter(self.update_status_bar, f"Stopped broadcasting to {target_ip}")

    def stop_audio_stream(self):
        self.running = False
        for thread in self.threads:
            thread.join()
        self.threads.clear()
        self.statusBar.SetStatusText("Stopped all broadcasts.")

    def update_status_bar(self, message):
        self.statusBar.SetStatusText(message)

    @staticmethod
    def get_local_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        finally:
            s.close()
        return IP

    def upload_ip_to_firebase(self):
        ip_address = self.get_local_ip()
        ref = db.reference('settings/general')
        ref.update({'ip_address': ip_address})
        print(f"Uploaded IP Address: {ip_address}")

    @staticmethod
    def fetch_pi_ip_address():
        ref = db.reference('room/device/audio/')

        devices = ref.get()
        speaker_ips = []

        if devices:
            for device_id, details in devices.items():
                if details.get('detailed_type') == 'speaker' and 'ip_address' in details:
                    speaker_ips.append(details['ip_address'])
        return speaker_ips

