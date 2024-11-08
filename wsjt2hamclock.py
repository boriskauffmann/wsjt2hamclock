import tkinter as tk
from tkinter import ttk, messagebox
import socket
import struct
import sys
import binascii
import datetime
from enum import IntEnum
import time
import requests
import json
import os
from threading import Thread
import xml.etree.ElementTree as ET

CONFIG_FILE = 'config.json'

class Config:
    def __init__(self):
        self.config = {
            'hamclock_api': 'http://localhost:8080',
            'multicast_group': '224.0.0.1',
            'multicast_port': 2237,
            'qrz_username': '',
            'qrz_password': ''
        }
        self.load_config()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.config.update(json.load(f))

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

class MessageType(IntEnum):
    HEARTBEAT = 0
    STATUS = 1
    DECODE = 2
    CLEAR = 3
    REPLY = 4
    QSO_LOGGED = 5
    CLOSE = 6
    REPLAY = 7
    HALT_TX = 8
    FREE_TEXT = 9
    WSPR_DECODE = 10
    LOCATION = 11
    LOGGED_ADIF = 12
    HIGHLIGHT_CALLSIGN = 13

class WSJTXDecoder:
    MAGIC_NUMBER = 0xadbccbda
    
    @staticmethod
    def _read_utf8_string(data, offset):
        if offset + 4 > len(data):
            return None, offset
        length = struct.unpack('>I', data[offset:offset + 4])[0]
        if length == 0xffffffff:  # Null string
            return None, offset + 4
        if offset + 4 + length > len(data):
            return None, offset
        string_data = data[offset + 4:offset + 4 + length]
        return string_data.decode('utf-8'), offset + 4 + length

    @staticmethod
    def _read_qtime(data, offset):
        msecs = struct.unpack('>I', data[offset:offset + 4])[0]
        hours = msecs // (3600 * 1000)
        msecs %= 3600 * 1000
        minutes = msecs // (60 * 1000)
        msecs %= 60 * 1000
        seconds = msecs // 1000
        msecs %= 1000
        return datetime.time(hours, minutes, seconds, msecs * 1000), offset + 4

    def decode_message(self, raw_data):
        try:
            data = raw_data
            
            if len(data) < 12:
                return {"error": "Message too short"}
            
            magic, schema, type_int = struct.unpack('>III', data[:12])
            offset = 12
            
            if magic != self.MAGIC_NUMBER:
                return {"error": f"Invalid magic number: {magic:08x}"}
            
            message_id, offset = self._read_utf8_string(data, offset)
            
            # Using UTC time
            utc_time = datetime.datetime.now(datetime.timezone.utc).strftime("%H:%M:%S")
            
            result = {
                "time": utc_time,
                "schema": schema,
                "type": MessageType(type_int).name,
                "id": message_id
            }
            
            if type_int == MessageType.STATUS:
                freq = struct.unpack('>Q', data[offset:offset + 8])[0]
                offset += 8
                mode, offset = self._read_utf8_string(data, offset)
                dx_call, offset = self._read_utf8_string(data, offset)
                
                result.update({
                    "freq": freq,
                    "mode": mode,
                    "dx_call": dx_call
                })
                
            return result
            
        except Exception as e:
            return {
                "error": f"Decoding error: {str(e)}", 
                "raw_hex": binascii.hexlify(data).decode('ascii'),
                "type_int": type_int if 'type_int' in locals() else None
            }

class QRZLookup:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.base_url = "https://xmldata.qrz.com/xml/current/"
        self.last_dx_call = None

    def extract_tag_value(self, xml_text, tag_name):
        start_tag = f"<{tag_name}>"
        end_tag = f"</{tag_name}>"
        if start_tag in xml_text and end_tag in xml_text:
            start_pos = xml_text.find(start_tag) + len(start_tag)
            end_pos = xml_text.find(end_tag)
            return xml_text[start_pos:end_pos].strip()
        return None

    def lookup_callsign(self, callsign):
        try:
            call_changed = callsign != self.last_dx_call
            self.last_dx_call = callsign
            
            params = {
                'username': self.username,
                'password': self.password,
                'callsign': callsign
            }
            
            response = requests.get(self.base_url, params=params)
            if response.status_code != 200:
                return None, None, None

            grid = self.extract_tag_value(response.text, "grid")
            fname = self.extract_tag_value(response.text, "fname") or ""
            name = self.extract_tag_value(response.text, "name") or ""
            country = self.extract_tag_value(response.text, "country") or ""
            
            operator = f"{fname} {name}".strip()
            
            if grid and call_changed:
                try:
                    requests.get(f'{config.config["hamclock_api"]}/set_newdx?grid={grid}')
                except Exception as e:
                    print(f"Error sending grid to API: {e}")
                    
                return grid, operator, country
                
            return grid, operator, country if grid else (None, None, None)
            
        except Exception as e:
            print(f"Error in QRZ lookup: {str(e)}")
            return None, None, None

class MainApplication(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("WSJT-X/JTDX to HamCLock DX by PY2UBK")
        self.geometry("800x600")
        
        # Configure grid weight for responsiveness
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create main container with grid
        self.container = ttk.Frame(self)
        self.container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure container grid weights
        self.container.grid_rowconfigure(1, weight=1)  # TreeView row
        self.container.grid_columnconfigure(0, weight=1)

        # Create settings frame
        self.settings_frame = ttk.LabelFrame(self.container, text="Settings")
        self.settings_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Settings fields
        self.create_settings_fields()

        # Create tree view for messages
        self.create_tree_view()

        # Start/Stop button
        self.running = False
        self.start_button = ttk.Button(self.container, text="Start", command=self.toggle_monitoring)
        self.start_button.grid(row=2, column=0, pady=10)

        # Load initial config
        self.load_config_to_gui()

    def create_settings_fields(self):
        # Configure settings frame grid
        self.settings_frame.grid_columnconfigure(1, weight=1)
        
        # HamClock API
        ttk.Label(self.settings_frame, text="HamClock API:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.hamclock_api = ttk.Entry(self.settings_frame)
        self.hamclock_api.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Multicast settings
        ttk.Label(self.settings_frame, text="Multicast Group:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.multicast_group = ttk.Entry(self.settings_frame)
        self.multicast_group.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.settings_frame, text="Multicast Port:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.multicast_port = ttk.Entry(self.settings_frame)
        self.multicast_port.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # QRZ credentials
        ttk.Label(self.settings_frame, text="QRZ Username:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.qrz_username = ttk.Entry(self.settings_frame)
        self.qrz_username.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self.settings_frame, text="QRZ Password:").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.qrz_password = ttk.Entry(self.settings_frame, show="*")
        self.qrz_password.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        # Save button
        self.save_button = ttk.Button(self.settings_frame, text="Save Settings", command=self.save_settings)
        self.save_button.grid(row=5, column=0, columnspan=2, pady=10)

    def create_tree_view(self):
        # Create a frame to hold the treeview and scrollbar
        tree_frame = ttk.Frame(self.container)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure the tree frame grid
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)

        # Define columns
        columns = ("UTC", "Type", "DX Call", "Grid", "Operator", "Country", "Frequency")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        # Define column widths and weights
        column_widths = {
            "UTC": (40, 1),
            "Type": (40, 1),
            "DX Call": (40, 1),
            "Grid": (40, 1),
            "Operator": (200, 2),  # Double weight for operator name
            "Country": (50, 1),
            "Frequency": (50, 1)
        }
        
        # Set column headings and widths
        for col in columns:
            self.tree.heading(col, text=col)
            width, weight = column_widths[col]
            self.tree.column(col, width=width, minwidth=50, stretch=True)

        # Create and configure scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Grid layout for tree and scrollbar
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    def load_config_to_gui(self):
        self.hamclock_api.insert(0, config.config['hamclock_api'])
        self.multicast_group.insert(0, config.config['multicast_group'])
        self.multicast_port.insert(0, str(config.config['multicast_port']))
        self.qrz_username.insert(0, config.config['qrz_username'])
        self.qrz_password.insert(0, config.config['qrz_password'])

    def save_settings(self):
        try:
            port = int(self.multicast_port.get())
            config.config.update({
                'hamclock_api': self.hamclock_api.get(),
                'multicast_group': self.multicast_group.get(),
                'multicast_port': port,
                'qrz_username': self.qrz_username.get(),
                'qrz_password': self.qrz_password.get()
            })
            config.save_config()
            messagebox.showinfo("Success", "Settings saved successfully!")
        except ValueError:
            messagebox.showerror("Error", "Port must be a number!")

    def toggle_monitoring(self):
        if not self.running:
            self.start_monitoring()
        else:
            self.stop_monitoring()

    def start_monitoring(self):
        self.running = True
        self.start_button.configure(text="Stop")
        self.monitoring_thread = Thread(target=self.monitor_messages, daemon=True)
        self.monitoring_thread.start()

    def stop_monitoring(self):
        self.running = False
        self.start_button.configure(text="Start")

    def monitor_messages(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', config.config['multicast_port']))
            group = socket.inet_aton(config.config['multicast_group'])
            mreq = struct.pack('4sL', group, socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            decoder = WSJTXDecoder()
            qrz = QRZLookup(config.config['qrz_username'], config.config['qrz_password'])
            last_dx_call = None

            while self.running:
                data, address = sock.recvfrom(1024)
                result = decoder.decode_message(data)

                if "error" not in result and result["type"] == "STATUS" and result.get("dx_call"):
                    current_dx_call = result.get("dx_call")

                    if current_dx_call != last_dx_call:
                        last_dx_call = current_dx_call
                        grid, operator, country = qrz.lookup_callsign(current_dx_call)

                        # Insert new data in the main thread to avoid tkinter thread issues
                        self.after(0, self.update_tree, (
                            result["time"],
                            result["type"],
                            current_dx_call,
                            grid or "---",
                            operator or "---",
                            country or "---",
                            f"{result.get('freq', 0)/1000000:.3f}MHz"
                        ))

        except Exception as e:
            # Show error in the main thread
            self.after(0, lambda: messagebox.showerror("Error", f"Monitoring error: {str(e)}"))
            self.after(0, self.stop_monitoring)
        finally:
            if 'sock' in locals():
                sock.close()

    def update_tree(self, values):
        """Update tree view in the main thread"""
        try:
            self.tree.insert('', 0, values=values)

            # Keep only last 100 entries
            children = self.tree.get_children()
            if len(children) > 100:
                self.tree.delete(children[-1])
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update display: {str(e)}")

if __name__ == "__main__":
    config = Config()
    app = MainApplication()
    app.mainloop()