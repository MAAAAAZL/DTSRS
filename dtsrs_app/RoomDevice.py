import wx
import re
import tkinter as tk
import pytz
from datetime import datetime

from tkinter import ttk, messagebox, Toplevel, Canvas
from io import BytesIO
from PIL import Image, ImageTk
from firebase_admin import db, storage

from FirebaseDatabase import FirebaseDatabase


class RoomDevice:
    def __init__(self):
        super().__init__()
        self.devices_data = None

    @staticmethod
    def download_and_display_image(image_blob_name, parent):
        try:
            FirebaseDatabase.get_instance()
            bucket = storage.bucket()

            blob = bucket.blob(image_blob_name)
            image_bytes = BytesIO(blob.download_as_bytes())
            image = Image.open(image_bytes)

            # Scale image to fit display
            fixed_width = 350
            original_width, original_height = image.size
            height_ratio = fixed_width / original_width
            new_height = int(original_height * height_ratio)
            image = image.resize((fixed_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)

            # Create Frame and Canvas to display images
            image_frame = tk.Frame(parent)
            image_frame.pack()
            canvas = tk.Canvas(image_frame, width=fixed_width, height=new_height)
            canvas.pack()
            canvas.create_image(fixed_width / 2, new_height / 2, anchor="center", image=photo)
            canvas.image = photo

            def on_canvas_click(event):
                global coordinates
                canvas.delete("point")
                size = 3
                # Draw the clicked point (optional, if you want to show the clicked location on the UI)
                canvas.create_oval(event.x - size, event.y - size, event.x + size, event.y + size, fill='red',
                                   tags="point")
                original_x = round(event.x * (original_width / fixed_width))
                original_y = round(event.y * (original_height / new_height))
                # Update global coordinate variables to original coordinates
                coordinates = (original_x, original_y)

            canvas.bind("<Button-1>", on_canvas_click)

        except Exception as e:
            tk.Label(parent, text="No available room layout.").pack()
            messagebox.showerror("Error", f"Error opening or displaying image: {e}")

    @staticmethod
    def check_room_layout_files():
        FirebaseDatabase.get_instance()
        bucket = storage.bucket()

        room_layout_path = "remote/room/layout"
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

        blobs = bucket.list_blobs(prefix=room_layout_path)

        filtered_files = [blob.name for blob in blobs
                          if any(blob.name.lower().endswith(ext) for ext in image_extensions)]
        if len(filtered_files) > 0:
            return filtered_files[0]
        else:
            pass

    @staticmethod
    def fetch_rpi_ids():
        """Fetch all RPi IDs from Firebase database."""
        ref = db.reference('room/device/rpi')
        rpi_ids = ref.get()
        return rpi_ids if rpi_ids else []

    def create_new_rpi_id(self, rpi_id_combobox):
        """Create a new RPI ID in the Firebase database and refresh the combobox list."""
        rpi_ids = self.fetch_rpi_ids()
        if rpi_ids:
            next_id = max(int(rpi) for rpi in rpi_ids) + 1  # Find the highest ID and increment it
        else:
            next_id = 0  # Start from 0 if no IDs are present

        # Append the new RPi ID to the list and update Firebase
        rpi_ids.append(str(next_id))
        ref = db.reference('room/device/rpi')
        ref.set(rpi_ids)  # Update the entire list

        # Update the combobox on the UI
        rpi_id_combobox['values'] = rpi_ids
        rpi_id_combobox.set(str(next_id))  # Set the new RPi ID as the selected value

    def add_device_ui(self):
        """"Create a GUI window for user to add device on the layout image"""
        global coordinates
        coordinates = None

        add_device_window = tk.Tk()
        add_device_window.title("Add Device")

        layout_filename = self.check_room_layout_files()

        if layout_filename:
            self.download_and_display_image(layout_filename, add_device_window)
        else:
            tk.Label(add_device_window, text="No available room layout.").pack()

        main_frame = tk.Frame(add_device_window)
        main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # RPi ID Selection
        tk.Label(main_frame, text="RPi ID:").pack(fill=tk.X)
        rpi_id_var = tk.StringVar()
        rpi_id_combobox = ttk.Combobox(main_frame, textvariable=rpi_id_var, state="readonly")
        rpi_ids = self.fetch_rpi_ids()
        rpi_id_combobox['values'] = rpi_ids
        rpi_id_combobox.pack(fill=tk.X)

        create_new_rpi_id_button = tk.Button(main_frame, text="Create New RPi ID",
                                             command=lambda: self.create_new_rpi_id(rpi_id_combobox))
        create_new_rpi_id_button.pack()

        # Device name
        tk.Label(main_frame, text="Device Name:").pack(fill=tk.X)
        device_name_var = tk.StringVar()
        tk.Entry(main_frame, textvariable=device_name_var).pack(fill=tk.X)

        # Device type
        tk.Label(main_frame, text="Device Type:").pack(fill=tk.X)
        device_type_var = tk.StringVar()
        device_type_combobox = ttk.Combobox(main_frame, textvariable=device_type_var, state="readonly")
        device_type_combobox['values'] = ('Light', 'HVAC', 'Safety', 'Security', 'Audio')
        device_type_combobox.pack(fill=tk.X)

        apply_button = tk.Button(main_frame, text="Apply",
                                 command=lambda: self.update_detailed_type(main_frame, device_type_var.get()))
        apply_button.pack()

        # Detailed type
        tk.Label(main_frame, text="Detailed Type:").pack(fill=tk.X)
        detailed_type_var = tk.StringVar()
        detailed_type_combobox = ttk.Combobox(main_frame, textvariable=detailed_type_var, state="readonly")
        detailed_type_combobox.pack(fill=tk.X)

        self.detailed_type_combobox = detailed_type_combobox

        def on_add_device():
            """Check whether the data filled in by the user is complete"""
            if not device_name_var.get().strip():
                messagebox.showerror("Error", "Device name is required.")
                return
            if not device_type_var.get().strip():
                messagebox.showerror("Error", "Device type is required.")
                return
            if not detailed_type_var.get().strip():
                messagebox.showerror("Error", "Detailed type is required.")
                return
            if coordinates is None:
                messagebox.showerror("Error", "Device coordinates are required.")
                return
            if not rpi_id_var.get().strip():
                messagebox.showerror("Error", "RPi ID is required.")
                return
            self.add_device(device_name_var.get(),
                            device_type_var.get(),
                            detailed_type_var.get(),
                            coordinates,
                            rpi_id_var.get())

        tk.Button(main_frame, text="Add Device", command=on_add_device).pack()

        # Adapt window size
        add_device_window.update()  # Update window to calculate component size
        # Set minimum size to prevent content from being compressed
        add_device_window.minsize(add_device_window.winfo_width(), add_device_window.winfo_height())

        add_device_window.mainloop()

    def update_detailed_type(self, parent, device_type):
        detailed_type_options = {
            "Light": ('Light', 'Light Rotary Encoder', 'Light intensity sensor'),
            "HVAC": ('Temperature and humidity sensor', 'Air sensor', 'Ventilation', 'Fan controller'),
            "Safety": ('Flame sensor', 'Gas sensor', 'Emergency button', 'Emergency light'),
            "Security": ('Camera', 'Access keypad'),
            "Audio": ('Speaker')
        }

        self.detailed_type_combobox['values'] = detailed_type_options.get(device_type, ('Generic',))

    @staticmethod
    def generate_device_id(device_type):
        """Format the device type to ensure it is used correctly in the database path"""
        formatted_device_type = device_type.lower()
        ref = db.reference(f'room/device/{formatted_device_type}')
        devices = ref.get()
        max_device_number = 0

        if devices:
            for device_id in devices.keys():
                number_part = device_id.split('_')[-1]  # Get numbered part
                try:
                    device_number = int(number_part)  # Try converting the number part to an integer
                    max_device_number = max(max_device_number, device_number)  # Update maximum device number
                except ValueError:
                    continue

        next_device_number = max_device_number + 1
        device_id = f"device_{formatted_device_type}_{next_device_number:04}"
        return device_id

    def add_device(self, device_name, device_type, detailed_type, coordinates, rpi_id):
        # Generate device ID
        device_id = self.generate_device_id(device_type)
        # Assume that the function to get the name of the area is get_area_name_by_coordinates
        area_name = self.get_area_name_by_coordinates(coordinates) if coordinates else None
        # Generate the default data based on the detailed type
        default_data = self.get_default_data_by_detailed_type(detailed_type)

        # Build device information to save
        device_info = {
            "device_name": device_name,
            "type": device_type.lower(),
            "detailed_type": detailed_type.lower(),
            "coordinates": coordinates,
            "area": area_name,
            "gpio": [],
            "bound_device": [],
            "isEmergency": False,
            "rpi_id": str(rpi_id),
            **default_data
        }

        history_paths = {
            "Light": "light/light/",
            "Light intensity sensor": "light/light_sensor/",
            "Temperature and humidity sensor": "hvac/dht_sensor/",
            "Air sensor": "hvac/mq_135_sensor/",
            "Ventilation": "hvac/ventilation/",
            "Flame sensor": "safety/flame_sensor/",
            "Gas sensor": "safety/mq_2_sensor/"
        }

        # Get the current time in Amsterdam timezone
        amsterdam = pytz.timezone('Europe/Amsterdam')
        now = datetime.now(amsterdam)
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

        # Upload device information to the corresponding path of Firebase
        ref = db.reference(f'room/device/{device_type.lower()}')
        new_device_ref = ref.child(device_id)
        new_device_ref.set(device_info)
        print(detailed_type)

        if detailed_type in history_paths.keys():
            history_ref = db.reference(f"{history_paths[detailed_type]}{device_id}/{timestamp}")
            history_ref.set(default_data)

        messagebox.showinfo("Success", f"Device {device_id} added successfully.")

    @staticmethod
    def get_default_data_by_detailed_type(detailed_type):
        """Generate default data based on the detailed type using a switch-case-like dictionary structure"""
        default_data = {
            "Light": {"switch": False, "brightness": 0, "auto_mode": False},
            "Light intensity sensor": {"light_intensity": 50},
            "Temperature and humidity sensor": {"temperature": 25, "humidity": 45},
            "Air sensor": {"air_quality": 0.05},
            "Ventilation": {"speed": 0, "switch": False, "auto_mode": False},
            "Flame sensor": {"flame_intensity": 0, "threshold": 50},
            "Gas sensor": {"gas_level": 0.05, "threshold": 50},
            "Emergency light": {"isActivate": False},
            "camera": {"ip_address": "0.0.0.0"}
        }
        return default_data.get(detailed_type, {})

    def get_area_name_by_coordinates(self, device_coordinates):
        """Determine which area the current coordinates are in"""
        ref = db.reference('room/area')
        areas = ref.get()
        matching_area = []
        if areas:
            for area_id, area_info in areas.items():
                points = area_info.get('coordinates')
                if points and self.point_in_polygon(device_coordinates[0], device_coordinates[1], points):
                    matching_area.append(area_info.get('area_name'))
        return matching_area if matching_area else None

    @staticmethod
    def point_in_polygon(x, y, polygon):
        """Determine whether a point is in a polygon"""
        n = len(polygon)
        inside = False

        p1x, p1y = polygon[0]
        for i in range(n + 1):
            p2x, p2y = polygon[i % n]
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    @staticmethod
    def fetch_devices_data():
        try:
            FirebaseDatabase.get_instance()
            ref = db.reference('room/device')
            data = ref.get()
            if 'rpi' in data:
                del data['rpi']
            return data
        except Exception as e:
            print("Error fetching device data:", e)
            return {}

    def display_devices_ui(self):
        """Create the main window that displays the device"""
        root = tk.Tk()
        root.title("Firebase Devices Data Viewer")
        root.geometry("1200x600")

        self.devices_data = self.fetch_devices_data()

        if self.devices_data:
            tree = ttk.Treeview(root,
                                columns=(
                                    'device_id', 'device_name', 'device_type', 'detailed_type', 'coordinates', 'area',
                                    'rpi_id', 'gpio', 'bound_devices'),
                                show='headings')

            tree.heading('device_id', text='Device ID')
            tree.heading('device_name', text='Device Name')
            tree.heading('device_type', text='Device Type')
            tree.heading('detailed_type', text='Detail Type')
            tree.heading('coordinates', text='Coordinates')
            tree.heading('area', text='Area')
            tree.heading('rpi_id', text='RPi ID')
            tree.heading('gpio', text='GPIO')
            tree.heading('bound_devices', text='Bound Devices')

            tree.column('device_id', width=100, anchor='w')
            tree.column('device_name', width=150, anchor='w')
            tree.column('device_type', width=100, anchor='w')
            tree.column('detailed_type', width=125, anchor='w')
            tree.column('coordinates', width=150, anchor='w')
            tree.column('area', width=100, anchor='w')
            tree.column('rpi_id', width=100, anchor='w')
            tree.column('gpio', width=50, anchor='w')
            tree.column('bound_devices', width=125, anchor='w')

            for device_type, devices in self.devices_data.items():
                for device_id, device_info in devices.items():
                    area_info = device_info.get('area')
                    area_info = ', '.join(area_info) if isinstance(area_info, (list, set)) else area_info
                    gpio_display = ', '.join(map(str, device_info.get('gpio', [])))
                    bound_devices_display = ', '.join(device_info.get('bound_devices', []))
                    tree.insert('', 'end',
                                values=(device_id,
                                        device_info.get('device_name'),
                                        device_type,
                                        device_info.get('detailed_type'),
                                        str(device_info.get('coordinates')),
                                        area_info,
                                        device_info.get('rpi_id', 'N/A'),
                                        gpio_display,
                                        bound_devices_display))

            tree.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        else:
            tk.messagebox.showinfo("Info", "No devices found.")

        root.mainloop()

    def refresh_devices_ui(self):
        """Refresh all devices data to display"""
        data = self.fetch_devices_data()
        if data:
            tree.delete(*tree.get_children())
            for device_type, devices in data.items():
                for device_id, device_info in devices.items():
                    area_info = device_info.get('area')
                    area_info_str = ', '.join(area_info) if isinstance(area_info, (list, set)) else area_info

                    rpi_id = device_info.get('rpi_id', 'N/A')
                    gpio = ', '.join(map(str, device_info.get('gpio', [])))
                    bound_devices = ', '.join(device_info.get('bound_devices', []))

                    tree.insert('', 'end',
                                values=('0',
                                        device_id,
                                        device_info.get('device_name'),
                                        device_type,
                                        device_info.get('detailed_type'),
                                        str(device_info.get('coordinates')),
                                        area_info_str,
                                        rpi_id,
                                        gpio,
                                        bound_devices))

    def edit_device_ui(self):
        """Create the main window that edit devices"""
        global tree
        root = tk.Tk()
        root.title("Edit Devices")
        root.geometry("1200x600")

        tree = ttk.Treeview(root,
                            columns=(
                                'selected', 'device_id', 'device_name', 'device_type', 'detailed_type', 'coordinates',
                                'area', 'rpi_id', 'gpio', 'bound_devices'),
                            show='headings')

        tree.heading('selected', text='Selected')
        tree.heading('device_id', text='Device ID')
        tree.heading('device_name', text='Device Name')
        tree.heading('device_type', text='Device Type')
        tree.heading('detailed_type', text='Detail Type')
        tree.heading('coordinates', text='Coordinates')
        tree.heading('area', text='Area')
        tree.heading('rpi_id', text='RPi ID')
        tree.heading('gpio', text='GPIO')
        tree.heading('bound_devices', text='Bound Devices')

        tree.column('selected', width=25, anchor='center')
        tree.column('device_id', width=100, anchor='w')
        tree.column('device_name', width=125, anchor='w')
        tree.column('device_type', width=75, anchor='w')
        tree.column('detailed_type', width=100, anchor='w')
        tree.column('coordinates', width=100, anchor='w')
        tree.column('area', width=80, anchor='w')
        tree.column('rpi_id', width=60, anchor='w')
        tree.column('gpio', width=50, anchor='w')
        tree.column('bound_devices', width=150, anchor='w')

        scrollbar = tk.Scrollbar(root, orient="horizontal", command=tree.xview)
        tree.configure(xscrollcommand=scrollbar.set)
        scrollbar.pack(side='bottom', fill='x')

        btn_frame = tk.Frame(root)
        btn_frame.pack(fill='x', side='bottom', pady=10)

        toggle_select_btn = tk.Button(btn_frame, text="Select All", command=lambda: toggle_all_selected(tree))
        toggle_select_btn.pack(side='left', padx=10)

        deselect_all_btn = tk.Button(btn_frame, text="Deselect All", command=lambda: toggle_all_deselected(tree))
        deselect_all_btn.pack(side='left', padx=10)

        delete_selected_btn = tk.Button(btn_frame, text="Delete Selected",
                                        command=lambda: self.delete_selected(tree))
        delete_selected_btn.pack(side='right', padx=10)

        refresh_data_btn = tk.Button(btn_frame, text="Refresh Data", command=self.refresh_devices_ui)
        refresh_data_btn.pack(side='right', padx=10, before=delete_selected_btn)

        self.devices_data = self.fetch_devices_data()
        if self.devices_data:
            for device_type, devices in self.devices_data.items():
                for device_id, device_info in devices.items():
                    print(device_id, device_info)
                    area_info = device_info.get('area')
                    area_info = ', '.join(area_info) if isinstance(area_info, (list, set)) else area_info
                    rpi_id = device_info.get('rpi_id')
                    gpio_display = ', '.join(map(str, device_info.get('gpio', [])))
                    bound_devices_display = ', '.join(device_info.get('bound_devices', []))
                    tree.insert('', 'end',
                                values=('0',
                                        device_id,
                                        device_info.get('device_name'),
                                        device_type,
                                        device_info.get('detailed_type'),
                                        str(device_info.get('coordinates')),
                                        area_info,
                                        rpi_id,
                                        gpio_display,
                                        bound_devices_display))

        # Bind row click event to switch selected state
        def toggle_selected(event):
            item_id = tree.identify_row(event.y)
            if item_id:
                current_values = tree.item(item_id, 'values')
                new_selected = '1' if current_values[0] == '0' else '0'
                tree.item(item_id, values=(new_selected,) + current_values[1:])

        tree.bind("<Button-1>", toggle_selected)

        tree.pack(expand=True, fill='both', padx=10, pady=10)

        def onItemDoubleClick(event):
            """Handle double click event"""
            # Confirm the selected item
            item_id = tree.selection()[0]
            selected_item = tree.item(item_id, 'values')
            # Ignore 'selected' status value and directly unpack other required values
            _, device_id, device_name, device_type, detailed_type, coordinates, area, rpi_id, gpio, bound_devices = selected_item
            area_list = None if area is None or area == "None" else area.split(', ')

            # Edit dialog box pops up
            self.EditDeviceDialog(root, {
                'device_id': device_id,
                'device_name': device_name,
                'device_type': device_type,
                'detailed_type': detailed_type,
                'coordinates': coordinates,
                'area': area_list,
                'rpi_id': rpi_id,
                'gpio': gpio,
                'bound_devices': bound_devices,
            },
                                  update_callback=update_device_info,
                                  devices_data=self.devices_data)

        def toggle_all_selected(tree):
            for item in tree.get_children():
                tree.item(item, values=('1',) + tree.item(item, 'values')[1:])

        def toggle_all_deselected(tree):
            for item in tree.get_children():
                tree.item(item, values=('0',) + tree.item(item, 'values')[1:])

        def update_device_info(device_id, updated_info):

            for item in tree.get_children():
                if tree.item(item, 'values')[1] == device_id:
                    tree.item(item, values=(
                        tree.item(item, 'values')[0], device_id, updated_info['device_name'],
                        updated_info['device_type'],
                        updated_info['coordinates'], updated_info['area']))
                    break

        # Bind the double-click event handler function in the edit_device_ui function
        tree.bind("<Double-1>", onItemDoubleClick)

        root.mainloop()

    def delete_selected(self, tree):
        for item in tree.get_children():
            item_values = tree.item(item, 'values')
            # The selected state is in the first column
            selected = item_values[0]
            if selected == '1':
                device_id = item_values[1]
                device_type = item_values[3]
                self.delete_device_from_firebase(device_type, device_id)
                tree.delete(item)

        messagebox.showinfo("Success", "Selected devices have been successfully deleted.")

    @staticmethod
    def delete_device_from_firebase(device_type, device_id):
        ref = db.reference(f'room/device/{device_type}/{device_id}')
        ref.delete()

    class EditDeviceDialog(tk.Toplevel):
        def __init__(self, parent, device_info, update_callback, devices_data):
            super().__init__(parent)
            self.device_info = device_info
            self.update_callback = update_callback
            self.devices_data = devices_data

            self.title("Edit Device")
            self.geometry("600x500")

            form_frame = tk.Frame(self)
            form_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

            tk.Label(form_frame, text="Device Name:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
            self.name_var = tk.StringVar(value=device_info['device_name'])
            tk.Entry(form_frame, textvariable=self.name_var).grid(row=0, column=1, sticky="ew", padx=5, pady=5)

            tk.Label(form_frame, text="Device Type:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
            self.type_var = tk.StringVar(value=device_info['device_type'])
            tk.Label(form_frame, textvariable=self.type_var, anchor="w").grid(row=1, column=1, sticky="w", padx=5, pady=5)

            tk.Label(form_frame, text="Detailed Type:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
            self.detail_var = tk.StringVar(value=device_info['detailed_type'])
            tk.Label(form_frame, textvariable=self.detail_var, anchor="w").grid(row=2, column=1, sticky="w", padx=5,
                                                                                pady=5)

            tk.Label(form_frame, text="RPi ID:").grid(row=3, column=0, sticky="e", padx=5, pady=5)
            self.rpi_id_var = tk.StringVar(value=device_info['rpi_id'])
            self.rpi_id_combobox = ttk.Combobox(form_frame, textvariable=self.rpi_id_var, state="readonly")
            rpi_ids = self.fetch_rpi_ids()
            self.rpi_id_combobox['values'] = rpi_ids
            self.rpi_id_combobox.grid(row=3, column=1, sticky="ew", padx=5, pady=5)

            tk.Label(form_frame, text="GPIO:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
            self.gpio_var = tk.StringVar(value=str(device_info.get('gpio', '')))
            gpio_entry = tk.Entry(form_frame, textvariable=self.gpio_var)
            gpio_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=5)

            tk.Label(form_frame, text="Bind Devices:").grid(row=5, column=0, sticky="e", padx=5, pady=5)
            self.bind_devices_listbox = tk.Listbox(form_frame, selectmode='multiple')
            self.bind_devices_listbox.grid(row=5, column=1, sticky="ew", padx=5, pady=5)

            for temp_device_type, temp_devices in self.devices_data.items():
                if temp_device_type == device_info['device_type']:
                    for temp_device_id, temp_device_info in temp_devices.items():
                        if temp_device_id != device_info['device_id']:
                            self.bind_devices_listbox.insert('end', temp_device_id)
                            if temp_device_id in self.device_info.get('bound_devices', []):
                                self.bind_devices_listbox.select_set('end')

            tk.Label(form_frame, text="Coordinates:").grid(row=6, column=0, sticky="e", padx=5, pady=5)
            self.coord_var = tk.StringVar(value=str(device_info['coordinates']))
            coord_entry = tk.Entry(form_frame, textvariable=self.coord_var, state='readonly')
            coord_entry.grid(row=6, column=1, sticky="ew", padx=5, pady=5)

            tk.Label(form_frame, text="Area:").grid(row=7, column=0, sticky="e", padx=5, pady=5)
            if device_info['area'] and isinstance(device_info['area'], list):
                area_info_str = ', '.join(device_info['area'])
            else:
                area_info_str = ""
            self.area_var = tk.StringVar(value=area_info_str)
            area_entry = tk.Entry(form_frame, textvariable=self.area_var, state='readonly')
            area_entry.grid(row=7, column=1, sticky="ew", padx=5, pady=5)

            tk.Button(form_frame, text="Update", command=self.on_update).grid(row=8, column=0, columnspan=2, pady=10, sticky="ew")
            form_frame.grid_columnconfigure(1, weight=1)

            select_location_btn = tk.Button(form_frame, text="Select New Location",
                                            command=lambda: self.handle_select_new_location(self,
                                                                                            tuple(map(float, re.sub(
                                                                                                r'[^\d,]', '',
                                                                                                self.coord_var.get()).split(
                                                                                                ',')))))
            select_location_btn.grid(row=9, column=0, columnspan=2, sticky="ew", padx=5, pady=5)


        @staticmethod
        def fetch_rpi_ids():
            """Fetch all RPi IDs from Firebase database."""
            ref = db.reference('room/device/rpi')
            rpi_ids = ref.get()
            return rpi_ids if rpi_ids else []

        def on_update(self):
            device_name = self.name_var.get()
            device_type = self.type_var.get()
            coordinates_str = self.coord_var.get().strip('[]')

            coordinates = list(map(int, coordinates_str.split(', ')))

            area_names_str = self.area_var.get()
            area_info_list = area_names_str.split(', ')

            rpi_id = self.rpi_id_var.get()

            gpio_str = self.gpio_var.get()
            gpio = list(map(int, gpio_str.split(','))) if gpio_str else []

            selected_indices = self.bind_devices_listbox.curselection()
            bound_devices = [self.bind_devices_listbox.get(i) for i in selected_indices]

            updated_info = {
                'device_name': device_name,
                'type': device_type,
                'coordinates': coordinates,
                'area': area_info_list,
                'rpi_id': rpi_id,
                'gpio': gpio,
                'bound_devices': bound_devices,
            }

            self.update_device_in_firebase(self.device_info['device_id'], updated_info, area_info_list)
            messagebox.showinfo("Update Successful", "The device information has been successfully updated.")
            self.destroy()

        @staticmethod
        def update_device_in_firebase(device_id, updated_info, area_names_list):
            ref = db.reference(f"room/device/{updated_info['type']}/{device_id}")
            ref.update(updated_info)

            area_ref = ref.child("area")
            area_ref.delete()

            if area_names_list is not None or area_names_list != ['']:
                for index, area_name in enumerate(area_names_list):
                    area_ref.child(str(index)).set(area_name)
            else:
                pass

        def handle_select_new_location(self, device_dialog_instance, original_coordinates=None):
            """Processing when the user selects a new coordinate location on the image"""
            new_window = Toplevel()
            new_window.title("Select New Location")

            layout_filename = self.check_room_layout_files()
            FirebaseDatabase.get_instance()
            bucket = storage.bucket()
            blob = bucket.blob(layout_filename)
            image_bytes = BytesIO(blob.download_as_bytes())
            image = Image.open(image_bytes)

            fixed_width = 350
            original_width, original_height = image.size
            height_ratio = fixed_width / original_width
            new_height = int(original_height * height_ratio)
            image = image.resize((fixed_width, new_height), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)

            canvas = Canvas(new_window, width=fixed_width, height=new_height)
            canvas.pack()
            canvas.create_image(fixed_width / 2, new_height / 2, anchor="center", image=photo)

            if original_coordinates:
                scaled_x = original_coordinates[0] * (fixed_width / original_width)
                scaled_y = original_coordinates[1] * (height_ratio)
                canvas.create_oval(scaled_x - 5, scaled_y - 5, scaled_x + 5, scaled_y + 5, fill='red')

            new_coordinates = None

            def on_canvas_click(event):
                nonlocal new_coordinates
                original_x = event.x * (original_width / fixed_width)
                original_y = event.y / height_ratio
                new_coordinates = (original_x, original_y)
                # Update the canvas display, first clear the previous mark
                canvas.delete("new_point")
                canvas.create_oval(event.x - 5, event.y - 5, event.x + 5, event.y + 5, fill='blue', tags="new_point")

            def confirm_selection():
                if new_coordinates:
                    rounded_coordinates = (round(new_coordinates[0]), round(new_coordinates[1]))
                    device_dialog_instance.coord_var.set(f"{rounded_coordinates[0]}, {rounded_coordinates[1]}")
                    area_name = self.get_area_name_by_coordinates(rounded_coordinates)
                    area_name_str = ', '.join(area_name) if isinstance(area_name, list) else area_name
                    device_dialog_instance.area_var.set(area_name_str)
                new_window.destroy()

            canvas.bind("<Button-1>", on_canvas_click)
            canvas.image = photo

            confirm_btn = tk.Button(new_window, text="Confirm", command=confirm_selection)
            confirm_btn.pack()

        def get_area_name_by_coordinates(self, device_coordinates):
            """Determine which area the current coordinates are in"""
            ref = db.reference('room/area')
            areas = ref.get()
            matching_area = []
            if areas:
                for area_id, area_info in areas.items():
                    points = area_info.get('coordinates')
                    if points and self.point_in_polygon(device_coordinates[0], device_coordinates[1], points):
                        matching_area.append(area_info.get('area_name'))
            return matching_area if matching_area else None

        @staticmethod
        def point_in_polygon(x, y, polygon):
            """Determine whether a point is in a polygon"""
            n = len(polygon)
            inside = False

            p1x, p1y = polygon[0]
            for i in range(n + 1):
                p2x, p2y = polygon[i % n]
                if y > min(p1y, p2y):
                    if y <= max(p1y, p2y):
                        if x <= max(p1x, p2x):
                            if p1y != p2y:
                                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or x <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y

            return inside

        @staticmethod
        def check_room_layout_files():
            FirebaseDatabase.get_instance()
            bucket = storage.bucket()

            room_layout_path = "remote/room/layout"
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

            blobs = bucket.list_blobs(prefix=room_layout_path)

            filtered_files = [blob.name for blob in blobs
                              if any(blob.name.lower().endswith(ext) for ext in image_extensions)]
            if len(filtered_files) > 0:
                return filtered_files[0]
            else:
                pass


class RoomDeviceFrame(RoomDevice, wx.Frame):
    def __init__(self, parent):
        RoomDevice.__init__(self)

        wx.Frame.__init__(self, parent, id=wx.ID_ANY, title="Device Options",
                          pos=wx.DefaultPosition, size=wx.Size(400, 300),
                          style=wx.DEFAULT_FRAME_STYLE | wx.TAB_TRAVERSAL)

        self.parent = parent
        self.panel = wx.Panel(self)
        self.SetPosition(wx.Point(650, 350))

        self.grid = wx.GridSizer(2, 2, 10, 10)

        self.addDeviceBtn = wx.Button(self.panel, label="Add Device", id=2031)
        self.viewDeviceBtn = wx.Button(self.panel, label="View Device List", id=2032)
        self.editDeviceBtn = wx.Button(self.panel, label="Edit Device", id=2033)
        self.backBtn = wx.Button(self.panel, label="Back", id=2034)

        self.grid.Add(self.addDeviceBtn, 0, wx.EXPAND)
        self.grid.Add(self.viewDeviceBtn, 0, wx.EXPAND)
        self.grid.Add(self.editDeviceBtn, 0, wx.EXPAND)
        self.grid.Add(self.backBtn, 0, wx.EXPAND)

        self.addDeviceBtn.Bind(wx.EVT_BUTTON, self.OnAddDevice)
        self.viewDeviceBtn.Bind(wx.EVT_BUTTON, self.OnViewDevice)
        self.editDeviceBtn.Bind(wx.EVT_BUTTON, self.OnEditDevice)
        self.backBtn.Bind(wx.EVT_BUTTON, self.OnBack)

        self.panel.SetSizer(self.grid)
        self.Layout()
        self.Centre(wx.BOTH)

    def OnAddDevice(self, event):
        RoomDevice.add_device_ui(self)

    def OnViewDevice(self, event):
        RoomDevice.display_devices_ui(self)

    def OnEditDevice(self, event):
        RoomDevice.edit_device_ui(self)

    def OnBack(self, event):
        self.parent.Show()
        self.Close()
