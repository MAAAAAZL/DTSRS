import wx
import math
import tkinter as tk

from tkinter import ttk, messagebox
from tkinter.simpledialog import askstring
from io import BytesIO
from PIL import Image, ImageTk
from firebase_admin import db, storage

from FirebaseDatabase import FirebaseDatabase
from RoomDataManager import RoomDataManager


class RoomArea:
    def __init__(self, parent):
        super().__init__()
        room_manager = RoomDataManager()
        room_manager.update_room_data_from_firebase()
        self.room_data = room_manager.room_data
        self.area_data = self.room_data["area"]
        self.current_image = None

    def select_room_area(self):
        FirebaseDatabase.get_instance()
        bucket = storage.bucket()

        room_layout_path = "remote/room/layout"
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

        blobs = bucket.list_blobs(prefix=room_layout_path)

        filtered_files = [blob.name for blob in blobs
                          if any(blob.name.lower().endswith(ext) for ext in image_extensions)]

        if len(filtered_files) > 0:
            image_blob_name = filtered_files[0]
            root = tk.Tk()
            self.current_image = self.download_image(image_blob_name)
            app = self.RoomAreaSelector(root, self.current_image)
            root.mainloop()

        else:
            messagebox.showinfo("Error", "No image file found.")

    @staticmethod
    def download_image(image_blob_name):
        FirebaseDatabase.get_instance()
        bucket = storage.bucket()

        blob = bucket.blob(image_blob_name)

        try:
            image_bytes = BytesIO(blob.download_as_bytes())
            return Image.open(image_bytes)

        except Exception as e:
            messagebox.showinfo("Error", f"Error opening or displaying image: {e}")

    def show_room_areas(self, window):
        if self.area_data is not None:
            tree = ttk.Treeview(window, columns=('area_id', 'room_name', 'points'), show='headings')
            tree.heading('area_id', text='Area ID')
            tree.heading('room_name', text='Room Name')
            tree.heading('points', text='Points')

            tree.column('area_id', width=100)
            tree.column('room_name', width=150)
            tree.column('points', width=350)

            for area in self.area_data:
                tree.insert('', tk.END, values=(area.area_id, area.area_name, str(area.coordinates)))

            tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        else:
            tk.messagebox.showinfo("Info", "No data found.")

    def display_room_areas_data(self):
        root = tk.Tk()
        root.title("Firebase Room Area Data Viewer")
        root.geometry("800x600")

        room_manager = RoomDataManager()
        room_manager.update_room_data_from_firebase()
        self.room_data = room_manager.room_data
        self.area_data = self.room_data['area']

        self.show_room_areas(root)
        root.mainloop()

    @staticmethod
    def update_check_status(tree, checked_items, check_all=True):
        """Updates the check status of items in a tree. Determine whether items selected"""
        for item in tree.get_children():
            if check_all:
                tree.set(item, column="check", value="1")
                checked_items.add(item)
            else:
                tree.set(item, column="check", value="0")
                checked_items.clear()

    @staticmethod
    def delete_selected_areas(tree, checked_items):
        """Deletes selected items in Firebase db"""
        for item in checked_items:
            area_id = tree.set(item, column="area_id")
            ref = db.reference(f'room/area/{area_id}')
            ref.delete()
            tree.delete(item)
        messagebox.showinfo("Success", "Selected areas have been deleted.")
        checked_items.clear()

    def show_delete_room_areas(self, window):
        """Functions to display data and delete functions"""
        checked_items = set()  # Store checked items

        tree = ttk.Treeview(window, columns=('check', 'area_id', 'room_name', 'points'), show='headings')
        tree.heading('check', text='Select')
        tree.heading('area_id', text='Area ID')
        tree.heading('room_name', text='Room Name')
        tree.heading('points', text='Points')

        # 添加勾选框逻辑
        tree.column('check', width=50, anchor='center')
        tree.column('area_id', width=100)
        tree.column('room_name', width=150)
        tree.column('points', width=350)

        for area in self.area_data:
            iid = tree.insert('', tk.END,
                              values=("0", area.area_id, area.area_name, str(area.coordinates)))
            tree.set(iid, column="check", value="0")

        def toggle_check(event):
            """Checkbox click event"""
            item = tree.identify_row(event.y)
            if item:
                current_value = tree.set(item, column="check")
                new_value = "1" if current_value == "0" else "0"
                tree.set(item, column="check", value=new_value)
                if new_value == "1":
                    checked_items.add(item)
                else:
                    checked_items.discard(item)

        tree.bind('<Button-1>', toggle_check)
        tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        btn_frame = tk.Frame(window)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        select_all_btn = tk.Button(btn_frame, text="Select All",
                                   command=lambda: self.update_check_status(tree, checked_items, True))
        select_all_btn.pack(side=tk.LEFT)

        deselect_all_btn = tk.Button(btn_frame, text="Deselect All",
                                     command=lambda: self.update_check_status(tree, checked_items, False))
        deselect_all_btn.pack(side=tk.LEFT)

        delete_btn = tk.Button(btn_frame, text="Delete Selected",
                               command=lambda: self.delete_selected_areas(tree, checked_items))
        delete_btn.pack(side=tk.RIGHT)

    def display_delete_room_areas(self):
        root = tk.Tk()
        root.title("Delete Room Areas on Firebase")
        root.geometry("800x600")

        room_manager = RoomDataManager()
        room_manager.update_room_data_from_firebase()
        self.room_data = room_manager.room_data
        self.area_data = self.room_data['area']

        self.show_delete_room_areas(root)
        root.mainloop()

    class RoomAreaSelector:
        def __init__(self, root, image):
            self.root = root
            self.original_image = image
            self.image, self.scale_ratio = self.resize_image(image)
            self.canvas = tk.Canvas(root, width=self.image.width, height=self.image.height)
            self.canvas.pack()
            self.tk_image = ImageTk.PhotoImage(self.image)
            self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)
            self.points = []
            self.starting_point = None
            self.area_closed = False
            self.canvas.bind("<Button-1>", self.add_point)
            self.canvas.bind("<Button-3>", self.remove_last_point)

            self.confirm_button = tk.Button(root, text="Confirm Area", command=self.confirm_area, state='disabled')
            self.confirm_button.pack()

        @staticmethod
        def resize_image(image, max_width=1200, max_height=700):
            original_width, original_height = image.size
            ratio = min(max_width / original_width, max_height / original_height)
            new_size = (int(original_width * ratio), int(original_height * ratio))
            # Use Image.Resampling.LANCZOS for high-quality downsampling
            resized_image = image.resize(new_size, Image.Resampling.LANCZOS)
            return resized_image, ratio

        @staticmethod
        def distance(p1, p2):
            return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)

        def add_point(self, event):
            if self.area_closed:
                return
            point = (event.x, event.y)
            self.draw_point(point)
            if not self.starting_point:
                self.starting_point = point
                self.points.append(point)  # Ensure the starting point is added to the points list
            else:
                if self.distance(point, self.starting_point) < 20 * self.scale_ratio and len(self.points) >= 3:
                    self.complete_area()
                else:
                    self.points.append(point)
                    self.canvas.create_line(self.points[-2], point, fill='red', tags="line")

        def complete_area(self):
            self.points.append(self.starting_point)  # Ensure the starting point is included for area closure
            self.canvas.create_polygon(self.points, fill='blue', outline='red', tags="polygon")
            self.area_closed = True
            self.confirm_button['state'] = 'normal'
            self.points.pop()  # Remove the duplicated starting point after drawing

        def remove_last_point(self, event):
            if self.points:
                if self.area_closed:
                    self.canvas.delete("polygon")
                    self.area_closed = False
                    self.confirm_button['state'] = 'disabled'
                else:
                    self.canvas.delete("line")
                self.points.pop()
                self.redraw_points_and_lines()
                if not self.points:  # If the point list is empty, reset the starting point
                    self.starting_point = None
            else:
                # When the point list is empty, make sure no unnecessary operations are performed
                self.starting_point = None
                self.canvas.delete("all")  # 清除画布上的所有绘制
                self.canvas.create_image(0, 0, anchor="nw", image=self.tk_image)  # Redraw the image

        def redraw_points_and_lines(self):
            self.canvas.delete("point")
            self.canvas.delete("line")
            for i, point in enumerate(self.points):
                self.draw_point(point)
                if i > 0:
                    self.canvas.create_line(self.points[i - 1], point, fill='red', tags="line")

        def draw_point(self, point):
            size = 3
            self.canvas.create_oval(point[0] - size, point[1] - size, point[0] + size, point[1] + size, fill='red',
                                    tags="point")

        def confirm_area(self):
            room_name = askstring("Room Name", "Enter the room area name:")
            if room_name:  # Make sure the user enters a room name
                original_points = [(int(x / self.scale_ratio), int(y / self.scale_ratio)) for x, y in self.points]
                self.upload_area_info(room_name, original_points)  # Call the upload function

        @staticmethod
        def upload_area_info(room_name, points):
            """Upload region information to Firebase Realtime Database"""
            ref = db.reference('room/area')
            areas = ref.get()
            if areas:
                next_id = max([int(key.split('_')[-1]) for key in areas.keys()]) + 1
            else:
                next_id = 1
            area_id = f'room_area_{next_id:04d}'
            area_info = {
                'id': area_id,
                'area_name': room_name,
                'coordinates': points,
                'isEmergency': False
            }
            ref.child(area_id).set(area_info)
            message = f"Room Name: {room_name}\n"
            message += "Original Points: " + ", ".join([f"({x}, {y})" for x, y in points]) + "\n"
            message += f"Area {area_id} uploaded successfully."
            messagebox.showinfo("Upload Success", message)


class RoomAreaFrame(RoomArea, wx.Frame):
    def __init__(self, parent):
        RoomArea.__init__(self, parent)
        self.parent = parent
        room_manager = RoomDataManager()
        room_manager.update_room_data_from_firebase()
        self.room_data = room_manager.room_data
        self.area_data = self.room_data['area']
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title="Area Options",
                          pos=wx.DefaultPosition, size=wx.Size(400, 300),
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.parent = parent
        self.panel = wx.Panel(self)
        self.SetPosition(wx.Point(650, 350))

        self.grid = wx.GridSizer(2, 2, 10, 10)

        self.selectRoomBtn = wx.Button(self.panel, label="Select Room Area", id=2021)
        self.showRoomBtn = wx.Button(self.panel, label="Show Room Area", id=2022)
        self.deleteRoomBtn = wx.Button(self.panel, label="Delete Layout", id=2023)
        self.backBtn = wx.Button(self.panel, label="Back", id=2024)

        self.grid.Add(self.selectRoomBtn, 0, wx.EXPAND)
        self.grid.Add(self.showRoomBtn, 0, wx.EXPAND)
        self.grid.Add(self.deleteRoomBtn, 0, wx.EXPAND)
        self.grid.Add(self.backBtn, 0, wx.EXPAND)

        self.selectRoomBtn.Bind(wx.EVT_BUTTON, self.OnSelectArea)
        self.showRoomBtn.Bind(wx.EVT_BUTTON, self.OnShowArea)
        self.deleteRoomBtn.Bind(wx.EVT_BUTTON, self.OnDeleteArea)
        self.backBtn.Bind(wx.EVT_BUTTON, self.OnBack)

        self.panel.SetSizer(self.grid)
        self.Layout()
        self.Centre(wx.BOTH)

    def OnSelectArea(self, event):
        RoomArea.select_room_area(self)

    def OnShowArea(self, event):
        RoomArea.display_room_areas_data(self)

    def OnDeleteArea(self, event):
        RoomArea.display_delete_room_areas(self)

    def OnBack(self, event):
        self.parent.Show()
        self.Close()
