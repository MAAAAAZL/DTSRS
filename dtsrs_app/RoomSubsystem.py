import wx
from firebase_admin import db, exceptions

from RoomLayout import RoomLayoutFrame
from RoomArea import RoomAreaFrame
from RoomDevice import RoomDeviceFrame

from FirebaseDatabase import FirebaseDatabase


class RoomSubsystem:
    def __init__(self):
        pass


class RoomSubsystemFrame(RoomSubsystem, wx.Frame):
    def __init__(self, parent, mainFrame):
        RoomSubsystem.__init__(self)
        # Initialize room data and method
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title="Room",
                          pos=wx.DefaultPosition, size=wx.Size(400, 300),
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)
        self.mainFrame = mainFrame
        self.panel = wx.Panel(self)
        self.SetPosition(wx.Point(650, 350))

        # Set up a 2x2 grid layout
        self.grid = wx.GridSizer(2, 2, 10, 10)

        buttons = [
            ("Layout", 2001),
            ("Room Area", 2002),
            ("Device", 2003),
            ("Return to Main", 2004)
        ]

        # Create and add buttons to the grid
        for label, btnId in buttons:
            button = wx.Button(self.panel, btnId, label)
            self.grid.Add(button, 0, wx.EXPAND)
            button.Bind(wx.EVT_BUTTON, self.OnButtonClicked)

        self.panel.SetSizer(self.grid)
        self.Layout()
        self.Centre(wx.BOTH)

    def OnButtonClicked(self, event):
        clickedBtnId = event.GetId()
        if clickedBtnId == 2001:
            self.Hide()
            roomLayoutFrame = RoomLayoutFrame(self)
            roomLayoutFrame.Show()

        elif clickedBtnId == 2002:
            self.Hide()
            roomAreaFrame = RoomAreaFrame(self)
            roomAreaFrame.Show()

        elif clickedBtnId == 2003:
            self.Hide()
            roomDeviceFrame = RoomDeviceFrame(self)
            roomDeviceFrame.Show()

        elif clickedBtnId == 2004:
            self.mainFrame.Show()
            self.Close()
