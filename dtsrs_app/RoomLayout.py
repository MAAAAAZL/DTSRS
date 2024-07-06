import wx
import os
import random

from tkinter import Tk, messagebox
from tkinter.filedialog import askopenfilename
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageColor
from firebase_admin import db, storage

from RoomDataManager import RoomDataManager
from FirebaseDatabase import FirebaseDatabase


class RoomLayout:
    def __init__(self):
        super().__init__()
        self.room_data = None
        FirebaseDatabase.get_instance()
        self.bucket = storage.bucket()

    @staticmethod
    def generate_random_color():
        # Generate random colors
        color = '#' + ''.join([random.choice('0123456789ABCDEF') for _ in range(6)])
        return color

    @staticmethod
    def intersect(box1, box2):
        # Determine whether two boxes intersect
        x1, y1, x2, y2 = box1
        x3, y3, x4, y4 = box2
        return not (x2 < x3 or x1 > x4 or y2 < y3 or y1 > y4)

    @staticmethod
    def get_text_size(text, font):
        im = Image.new(mode="P", size=(0, 0))
        draw = ImageDraw.Draw(im)
        _, _, width, height = draw.textbbox((0, 0), text=text, font=font)
        return width, height

    def display_devices_on_image(self, image, device_data, area_data):
        # Display devices on the layout
        temp_image = Image.new('RGBA', image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(temp_image)

        image_width, image_height = temp_image.size

        point_size = max(image_width, image_height) // 200

        font_size = max(image_width, image_height) // 100
        font = ImageFont.truetype("arial.ttf", font_size)

        type_color_map = {
            "light": "orange",
            "hvac": "red",
            "safety": "green",
            "security": "blue",
            "audio": "purple"
        }

        # Store occupied area
        occupied_areas = []

        # Drawing area
        for area in area_data:
            area_points = area.coordinates
            area_name = area.area_name
            area_color = self.generate_random_color()

            if area_points:
                flat_room_points = [point for sublist in area_points
                                    for point in sublist]

                fill_color = ImageColor.getrgb(area_color) + (127,)

                draw.polygon(flat_room_points, outline="black", fill=fill_color)

                # Get the center coordinates of the room area
                room_center_x = (sum(point[0] for point in area_points) // len(area_points))
                room_center_y = (sum(point[1] for point in area_points) // len(area_points))

                area_text = f"Room: {area_name}"

                room_font = ImageFont.truetype("arial.ttf", font_size)
                text_width, text_height = self.get_text_size(area_text, room_font)

                text_box = (room_center_x - text_width // 2,
                            room_center_y - text_height // 2,
                            room_center_x + text_width // 2,
                            room_center_y + text_height // 2)

                occupied_areas.append(text_box)

                # Add area name
                draw.text((room_center_x, room_center_y), area_text, fill="black",
                          font=room_font, align="center")

        # Loop through all devices and draw on the image
        for device in device_data:
            if device.coordinates:
                # Get device coordinates
                x, y = device.coordinates
                detailed_type = device.detailed_type
                device_type = device.type
                device_name = device.device_name

                # Get the color corresponding to the device type.
                # If not defined, the default is black.
                device_color = type_color_map.get(device_type, "black")

                device_text = f"{detailed_type}: {device_name}"

                draw.rectangle((x - point_size, y - point_size, x + point_size,
                                y + point_size), fill=device_color, width=2)

                text_width, text_height = self.get_text_size(device_text, font)

                text_box = (x - text_width // 2, y - text_height // 2,
                            x + text_width // 2, y + text_height // 2)

                while any(self.intersect(text_box, area) for area in occupied_areas):
                    x += point_size * 2
                    y += point_size * 2
                    text_box = (x - text_width // 2, y - text_height // 2,
                                x + text_width // 2, y + text_height // 2)

                # Add device name
                draw.text((x - text_width // 2, y + point_size),
                          device_text,
                          fill=device_color,
                          font=font,
                          align="center")

                # Add new occupied area
                occupied_areas.append(text_box)

        final_image = Image.alpha_composite(image.convert("RGBA"), temp_image)

        final_image.show()

    def download_and_display_image(self, device_info, area_info, image_blob_name):
        # Download and display the layout image from Firebase storage
        blob = self.bucket.blob(image_blob_name)
        try:
            image_bytes = BytesIO(blob.download_as_bytes())
            image = Image.open(image_bytes)
            image = image.convert("RGBA")
            self.display_devices_on_image(image, device_info, area_info)
        except Exception as e:
            messagebox.showinfo("Error",
                                f"Error opening or displaying image: {e}")

    # check path on Firebase storage: "room_layout_path"
    # looking for extension of images
    def view_layout_file(self):
        room_layout_path = "remote/room/layout"
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

        blobs = self.bucket.list_blobs(prefix=room_layout_path)

        filtered_files = [blob.name for blob in blobs
                          if any(blob.name.lower().endswith(ext)
                                 for ext in image_extensions)]

        room_manager = RoomDataManager()
        room_manager.update_room_data_from_firebase()
        self.room_data = room_manager.room_data
        area_info = self.room_data["area"]
        device_info = self.flat_reformat_room_device_data()

        if len(filtered_files) > 0:
            self.download_and_display_image(device_info,
                                            area_info, filtered_files[0])

    def flat_reformat_room_device_data(self):
        # Storage room device data in a flat list (ignore category)
        device_info = []
        if self.room_data["device"]:
            for _, devices_in_category in self.room_data["device"].items():
                device_info += devices_in_category
        return device_info

    # uploada target fire to Firebase storage after delete files in folder
    def upload_layout_file(self):
        # Set Tkinter window not to display
        root = Tk()
        root.withdraw()

        # Open file selection dialog
        file_path = askopenfilename(filetypes=[("Image files",
                                                "*.jpg *.jpeg *.png *.gif *.bmp")])
        if not file_path:
            root.destroy()
            return

        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
        file_extension = os.path.splitext(file_path)[1].lower()

        if file_extension not in image_extensions:
            messagebox.showerror("Error",
                                 f"Error: File format '{file_extension}' not supported.")
            root.destroy()
            return

        self.delete_layout_file(isUpload=True)

        # Upload new layout file
        new_file_name = 'remote/room/layout/' + os.path.basename(file_path)
        blob = self.bucket.blob(new_file_name)

        try:
            blob.upload_from_filename(file_path)
            messagebox.showinfo("Success", "File uploaded successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload new layout file: {e}")
        finally:
            root.destroy()

    # delete all files in 'remote/room/layout/' of Firebase storage
    def delete_layout_file(self, isUpload=False):
        blobs = self.bucket.list_blobs(prefix='remote/room/layout/')

        try:
            for blob in blobs:
                blob.delete()
            if isUpload == False:
                messagebox.showinfo("Success", "All layout files deleted successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete layout files: {e}")


class RoomLayoutFrame(RoomLayout, wx.Frame):
    def __init__(self, parent):
        RoomLayout.__init__(self)
        self.parent = parent
        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title="Layout Options",
                          pos=wx.DefaultPosition, size=wx.Size(400, 300),
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.panel = wx.Panel(self)
        self.SetPosition(wx.Point(650, 350))

        self.grid = wx.GridSizer(2, 2, 10, 10)

        self.viewLayoutBtn = wx.Button(self.panel, label="View Layout", id=2011)
        self.editLayoutBtn = wx.Button(self.panel, label="Edit Layout", id=2012)
        self.deleteLayoutBtn = wx.Button(self.panel, label="Delete Layout", id=2013)
        self.backBtn = wx.Button(self.panel, label="Back", id=2014)

        # Add buttons to grid layout
        self.grid.Add(self.viewLayoutBtn, 0, wx.EXPAND)
        self.grid.Add(self.editLayoutBtn, 0, wx.EXPAND)
        self.grid.Add(self.deleteLayoutBtn, 0, wx.EXPAND)
        self.grid.Add(self.backBtn, 0, wx.EXPAND)

        # Bind event handler function
        self.viewLayoutBtn.Bind(wx.EVT_BUTTON, self.OnViewLayout)
        self.editLayoutBtn.Bind(wx.EVT_BUTTON, self.OnUploadLayout)
        self.deleteLayoutBtn.Bind(wx.EVT_BUTTON, self.OnDeleteLayout)
        self.backBtn.Bind(wx.EVT_BUTTON, self.OnBack)

        self.panel.SetSizer(self.grid)
        self.Layout()
        self.Centre(wx.BOTH)

    def OnViewLayout(self, event):
        RoomLayout.view_layout_file(self)

    def OnUploadLayout(self, event):
        RoomLayout.upload_layout_file(self)

    def OnDeleteLayout(self, event):
        RoomLayout .delete_layout_file(self)

    def OnBack(self, event):
        self.parent.Show()
        self.Close()
