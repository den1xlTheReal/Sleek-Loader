import os
import sys
import json
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

try:
    import pywinstyles
except ImportError:
    pywinstyles = None

# --- Constants & Paths ---
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
YT_DLP_PATH = os.path.join(BASE_DIR, "yt-dlp.exe")
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
ICON_PATH = os.path.join(BASE_DIR, "icon.ico")
CREATE_NO_WINDOW = 0x08000000 if os.name == 'nt' else 0

DEFAULT_CONFIG = {
    "save_dir": os.path.expanduser("~/Downloads"),
    "mode": "Simple", "format": "Video", "scope": "Single",
    "resolution": "Best Available", "cast_mode": "Confirmation"
}

class DownloaderApp(ctk.CTk):
    def __init__(self):
        self.is_initializing = True
        super().__init__()

        self.title("Sleek Loader")
        if os.path.exists(ICON_PATH):
            try:
                self.iconbitmap(ICON_PATH)
            except Exception:
                pass
        self.geometry("750x850") # Opening dimensions
        self.minsize(700, 700)
        
        # Borderless window configurations with Snap Assist
        if os.name == 'nt':
            self.overrideredirect(False)
            self.after(10, self.enable_snap_assist)
        else:
            self.overrideredirect(True)
            self.bind("<Map>", self.on_map)
        
        # Drag offsets for non-Windows fallback
        self.drag_x = 0
        self.drag_y = 0
        
        # Resize start geometry for non-Windows fallback
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_start_w = 0
        self.resize_start_h = 0

        # TUI Color Palette (Solid Charcoal Black)
        self.bg_color = "#1a1a1a"     # Solid charcoal black
        self.accent_color = "#ffb000" # Amber
        self.text_color = "#d0d0d0"   # Light gray
        self.muted_color = "#555555"  # Dark gray
        self.subdued_color = "#8c8c8c" # Gray
        
        ctk.set_appearance_mode("dark")
        self.configure(fg_color=self.bg_color)
        self.config(bg=self.bg_color) # Force Tkinter root background to match solid charcoal

        self.config_data = self.load_config()
        self.current_process = None
        self.is_downloading = False
        self.viewing_logs = False
        self.log_box_content = ""
        self.focused_index = 0
        self.current_layout_mode = "single"
        self.download_queue = []

        self.build_ui()
        self.apply_config_to_ui()
        
        # Bindings
        self.bind("<Control-v>", self.auto_paste)
        self.bind("<Control-Return>", lambda e: self.start_download())
        self.bind("<Configure>", self.on_resize)
        self.bind("<Escape>", self.handle_escape)
        self.bind("<BackSpace>", self.handle_backspace)

        self.is_initializing = False

    def new_wndproc(self, h_wnd, msg, w_param, l_param):
        WM_NCCALCSIZE = 0x0083
        if msg == WM_NCCALCSIZE:
            if w_param == 1:
                # Return 0 to specify the client area covers the entire window.
                # This natively hides the title bar/caption while keeping snap and resizing frame intact.
                return 0
        try:
            import ctypes
            return ctypes.windll.user32.CallWindowProcW(self.old_wndproc, h_wnd, msg, w_param, l_param)
        except:
            return 0

    def enable_snap_assist(self):
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if not hwnd:
                hwnd = self.winfo_id()
            
            # Subclass the window procedure to handle WM_NCCALCSIZE.
            # Explicitly declare ctypes argtypes and restypes to prevent pointer truncation on 64-bit systems.
            GWL_WNDPROC = -4
            if ctypes.sizeof(ctypes.c_void_p) == 8:
                SetWindowLong = ctypes.windll.user32.SetWindowLongPtrW
                GetWindowLong = ctypes.windll.user32.GetWindowLongPtrW
                SetWindowLong.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_void_p]
                SetWindowLong.restype = ctypes.c_void_p
                GetWindowLong.argtypes = [ctypes.c_void_p, ctypes.c_int32]
                GetWindowLong.restype = ctypes.c_void_p
            else:
                SetWindowLong = ctypes.windll.user32.SetWindowLongW
                GetWindowLong = ctypes.windll.user32.GetWindowLongW
                SetWindowLong.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
                SetWindowLong.restype = ctypes.c_int32
                GetWindowLong.argtypes = [ctypes.c_void_p, ctypes.c_int32]
                GetWindowLong.restype = ctypes.c_int32

            # Declare types for CallWindowProcW to ensure safe execution
            ctypes.windll.user32.CallWindowProcW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint64, ctypes.c_int64]
            ctypes.windll.user32.CallWindowProcW.restype = ctypes.c_int64

            # Declare types for GetWindowLongW and SetWindowLongW
            ctypes.windll.user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int32]
            ctypes.windll.user32.GetWindowLongW.restype = ctypes.c_int32
            ctypes.windll.user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32]
            ctypes.windll.user32.SetWindowLongW.restype = ctypes.c_int32

            # Declare types for SetWindowPos
            ctypes.windll.user32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_uint32]
            ctypes.windll.user32.SetWindowPos.restype = ctypes.c_bool

            self.old_wndproc = GetWindowLong(hwnd, GWL_WNDPROC)

            # WNDPROC callback signature
            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint64, ctypes.c_int64)
            
            # Keep a reference to prevent garbage collection of the hook callback
            self._c_wndproc = WNDPROC(self.new_wndproc)
            SetWindowLong(hwnd, GWL_WNDPROC, self._c_wndproc)
            
            # Ensure window styles include WS_THICKFRAME and WS_CAPTION to allow snap and native borders
            GWL_STYLE = -16
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            style |= 0x00C40000 # WS_CAPTION | WS_THICKFRAME
            style |= 0x00080000 # WS_SYSMENU
            style |= 0x00020000 # WS_MINIMIZEBOX
            style |= 0x00010000 # WS_MAXIMIZEBOX
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

            # Refresh window style
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010)
        except Exception as e:
            self.overrideredirect(True)

    def on_map(self, event):
        # Fallback Map binder for non-Windows platforms
        if os.name != 'nt':
            self.after_idle(lambda: self.overrideredirect(True))

    def on_resize(self, event):
        if event.widget != self:
            return
        h = event.height
        mode = "double" if h < 750 else "single"
        if self.current_layout_mode != mode:
            self.current_layout_mode = mode
            self.adjust_layout(mode == "double")

    def adjust_layout(self, two_column):
        # Reset row/column weights on container
        self.container.grid_rowconfigure(1, weight=1)
        self.container.grid_rowconfigure(2, weight=0)
        self.container.grid_rowconfigure(3, weight=0)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=0)

        # Unpack elements to re-grid cleanly
        self.list_frame.grid_forget()
        self.help_label.grid_forget()
        if hasattr(self, "logs_screen_frame"):
            self.logs_screen_frame.grid_forget()

        if self.viewing_logs:
            # Logs screen: always occupies the entire container under the title
            self.logs_screen_frame.grid_configure(row=1, column=0, columnspan=2, sticky="nsew")
        else:
            # Main screen: since the history box is completely removed, it's a clean full-height list frame
            self.title_bar_frame.grid_configure(row=0, column=0, columnspan=1, sticky="ew")
            self.list_frame.grid_configure(row=1, column=0, sticky="nsew")
            self.help_label.grid_configure(row=2, column=0, sticky="ew", pady=(5, 15))

    def start_drag(self, event):
        if os.name == 'nt':
            # Send WM_NCLBUTTONDOWN with HTCAPTION using PostMessageW to delegate drag asynchronously to Windows DWM
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if not hwnd:
                    hwnd = self.winfo_id()
                
                ctypes.windll.user32.ReleaseCapture.argtypes = []
                ctypes.windll.user32.ReleaseCapture.restype = ctypes.c_bool
                ctypes.windll.user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint64, ctypes.c_int64]
                ctypes.windll.user32.PostMessageW.restype = ctypes.c_bool

                ctypes.windll.user32.ReleaseCapture()
                ctypes.windll.user32.PostMessageW(hwnd, 0x00A1, 2, 0)
            except:
                self.drag_x = event.x
                self.drag_y = event.y
        else:
            self.drag_x = event.x
            self.drag_y = event.y

    def do_drag(self, event):
        if os.name != 'nt':
            x = self.winfo_x() + (event.x - self.drag_x)
            y = self.winfo_y() + (event.y - self.drag_y)
            self.geometry(f"+{x}+{y}")
            self.update_idletasks()

    def start_resize(self, event):
        if os.name == 'nt':
            # Send WM_NCLBUTTONDOWN with HTBOTTOMRIGHT using PostMessageW to delegate corner resize asynchronously to Windows DWM
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if not hwnd:
                    hwnd = self.winfo_id()
                
                ctypes.windll.user32.ReleaseCapture.argtypes = []
                ctypes.windll.user32.ReleaseCapture.restype = ctypes.c_bool
                ctypes.windll.user32.PostMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint64, ctypes.c_int64]
                ctypes.windll.user32.PostMessageW.restype = ctypes.c_bool

                ctypes.windll.user32.ReleaseCapture()
                ctypes.windll.user32.PostMessageW(hwnd, 0x00A1, 17, 0)
            except:
                self.resize_start_x = event.x_root
                self.resize_start_y = event.y_root
                self.resize_start_w = self.winfo_width()
                self.resize_start_h = self.winfo_height()
        else:
            self.resize_start_x = event.x_root
            self.resize_start_y = event.y_root
            self.resize_start_w = self.winfo_width()
            self.resize_start_h = self.winfo_height()

    def do_resize(self, event):
        if os.name != 'nt':
            delta_x = event.x_root - self.resize_start_x
            delta_y = event.y_root - self.resize_start_y
            new_w = max(700, self.resize_start_w + delta_x)
            new_h = max(700, self.resize_start_h + delta_y)
            self.geometry(f"{new_w}x{new_h}")
            self.update_idletasks()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return {**DEFAULT_CONFIG, **json.load(f)}
            except: return DEFAULT_CONFIG.copy()
        return DEFAULT_CONFIG.copy()

    def save_config(self, *_):
        if getattr(self, "is_initializing", False):
            return
        mapping = {
            "save_dir": self.save_dir_var,
            "mode": self.mode_var,
            "format": self.format_var,
            "scope": self.scope_var,
            "resolution": self.res_var,
            "cast_mode": self.cast_mode_var
        }
        for key, var in mapping.items():
            self.config_data[key] = var.get()
            
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config_data, f, indent=4)
        except: pass

    def build_ui(self):
        # Configure main window grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main Container
        self.container = tk.Frame(self, bg=self.bg_color)
        self.container.grid(row=0, column=0, sticky="nsew", padx=25, pady=20)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(1, weight=1)

        # 1. Title bar frame at top (draggable)
        self.title_bar_frame = tk.Frame(self.container, bg=self.bg_color)
        self.title_bar_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.title_bar_frame.grid_columnconfigure(0, weight=1)

        # Title text label
        self.title_label = tk.Label(
            self.title_bar_frame, 
            text="■ Sleek Loader\n────────────────────────────────────────────────────────", 
            font=("Consolas", 11, "bold"), 
            fg=self.text_color, 
            bg=self.bg_color, 
            anchor="w", 
            justify="left"
        )
        self.title_label.grid(row=0, column=0, sticky="ew")

        # Simplified controls (Only Red circle)
        self.controls_canvas = tk.Canvas(self.title_bar_frame, width=20, height=20, bg=self.bg_color, bd=0, highlightthickness=0)
        self.controls_canvas.grid(row=0, column=1, sticky="ne", padx=(10, 0), pady=(0, 15))
        
        # Red circle (Close)
        self.controls_canvas.create_oval(5, 5, 15, 15, fill="#ff5f56", outline="")
        self.controls_canvas.bind("<Button-1>", self.handle_control_click)

        # Draggable bindings on the top header
        self.title_bar_frame.bind("<Button-1>", self.start_drag)
        self.title_label.bind("<Button-1>", self.start_drag)
        if os.name != 'nt':
            self.title_bar_frame.bind("<B1-Motion>", self.do_drag)
            self.title_label.bind("<B1-Motion>", self.do_drag)

        # 2. Main Interactive List Frame
        self.list_frame = tk.Frame(self.container, bg=self.bg_color)
        self.list_frame.grid(row=1, column=0, sticky="nsew")
        self.list_frame.grid_columnconfigure(0, minsize=40)
        self.list_frame.grid_columnconfigure(1, weight=1)

        # Persistent URL Entry Widget
        self.url_var = tk.StringVar()
        self.url_var.trace_add("write", self.on_url_change)
        self.url_entry = tk.Entry(
            self.list_frame,
            textvariable=self.url_var,
            font=("Consolas", 11),
            bg=self.bg_color,
            fg=self.accent_color,
            insertbackground=self.accent_color,
            bd=0,
            highlightthickness=0
        )
        self.url_entry.bind("<FocusIn>", lambda e: self.set_focused_index_by_id("url"))
        self.url_entry.bind("<Tab>", self.focus_next)
        self.url_entry.bind("<Down>", self.focus_next)
        self.url_entry.bind("<Up>", self.focus_prev)
        self.url_entry.bind("<Return>", self.activate_focused)

        # 3. Shortcut Help Legend
        self.help_label = tk.Label(
            self.container,
            text="ctrl ↵ submit    tab navigate    ↑/↓ move    space/enter select",
            font=("Consolas", 9),
            fg=self.muted_color,
            bg=self.bg_color,
            anchor="w"
        )
        self.help_label.grid(row=2, column=0, sticky="ew", pady=(5, 15))

        # 4. Dedicated Logs Screen Frame (hidden initially)
        self.logs_screen_frame = tk.Frame(self.container, bg=self.bg_color)
        self.logs_screen_frame.grid_rowconfigure(0, weight=1)
        self.logs_screen_frame.grid_columnconfigure(0, weight=1)

        self.logs_output_frame = tk.Frame(self.logs_screen_frame, bg=self.bg_color, bd=1, relief="solid")
        self.logs_output_frame.configure(highlightbackground=self.muted_color, highlightcolor=self.muted_color, highlightthickness=1)
        self.logs_output_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.logs_output_frame.grid_rowconfigure(0, weight=1)
        self.logs_output_frame.grid_columnconfigure(0, weight=1)

        self.output_box = tk.Text(
            self.logs_output_frame,
            font=("Consolas", 10),
            bg="#101010",
            fg=self.text_color,
            bd=0,
            highlightthickness=0,
            state="disabled",
            wrap="word"
        )
        self.output_box.grid(row=0, column=0, sticky="nsew")

        self.logs_bottom_frame = tk.Frame(self.logs_screen_frame, bg=self.bg_color)
        self.logs_bottom_frame.grid(row=1, column=0, sticky="ew")
        self.logs_bottom_frame.grid_columnconfigure(0, weight=1)

        self.logs_back_btn = tk.Label(
            self.logs_bottom_frame,
            text="[ Return to Downloader ]",
            font=("Consolas", 11, "bold"),
            fg=self.accent_color,
            bg=self.bg_color,
            cursor="hand2"
        )
        self.logs_back_btn.grid(row=0, column=0, sticky="w")
        self.logs_back_btn.bind("<Button-1>", lambda e: self.show_main_screen())

        self.logs_help_label = tk.Label(
            self.logs_bottom_frame,
            text="press esc or backspace to return",
            font=("Consolas", 9),
            fg=self.muted_color,
            bg=self.bg_color,
            anchor="e"
        )
        self.logs_help_label.grid(row=0, column=1, sticky="e")

        # Resize grip in the bottom right corner (Styled with Unicode bottom-right triangle ◢)
        self.grip = tk.Label(
            self, 
            text="◢", 
            font=("Consolas", 10), 
            fg=self.muted_color, 
            bg=self.bg_color, 
            cursor="size_nw_se"
        )
        self.grip.place(relx=1.0, rely=1.0, anchor="se")
        self.grip.bind("<Button-1>", self.start_resize)
        if os.name != 'nt':
            self.grip.bind("<B1-Motion>", self.do_resize)

        # Setup variables
        self.save_dir_var = tk.StringVar()
        self.save_dir_var.trace_add("write", self.save_config)
        
        self.format_var = tk.StringVar()
        self.format_var.trace_add("write", self.save_config)
        
        self.scope_var = tk.StringVar()
        self.scope_var.trace_add("write", self.save_config)
        
        self.mode_var = tk.StringVar()
        self.mode_var.trace_add("write", self.toggle_advanced_mode)
        
        self.res_var = tk.StringVar()
        self.res_var.trace_add("write", self.save_config)

        self.cast_mode_var = tk.StringVar()
        self.cast_mode_var.trace_add("write", self.save_config)

        # Keyboard Bindings for navigation
        self.bind("<Down>", self.focus_next)
        self.bind("<Up>", self.focus_prev)
        self.bind("<Tab>", self.focus_next)
        self.bind("<Shift-Tab>", self.focus_prev)
        self.bind("<Return>", self.activate_focused)
        self.bind("<space>", self.activate_focused)

    def handle_control_click(self, event):
        x, y = event.x, event.y
        if 5 <= x <= 15 and 5 <= y <= 15:
            # Red circle: Close
            self.destroy()

    def apply_config_to_ui(self):
        mapping = {
            "save_dir": self.save_dir_var,
            "format": self.format_var,
            "scope": self.scope_var,
            "mode": self.mode_var,
            "resolution": self.res_var,
            "cast_mode": self.cast_mode_var
        }
        for key, var in mapping.items():
            val = self.config_data.get(key, DEFAULT_CONFIG[key])
            if val == "":
                val = DEFAULT_CONFIG[key]
            var.set(val)
        self.rebuild_menu_items()
        self.refresh_ui()

    def rebuild_menu_items(self):
        mode = self.mode_var.get()
        self.menu_items = []

        # 0. URL
        self.menu_items.append({
            "id": "url",
            "type": "input",
            "section": "URL",
            "label": "URL Input"
        })

        # Cast Mode (Under URL line)
        self.menu_items.append({
            "id": "cast_confirm",
            "type": "option",
            "section": "Cast Mode",
            "label": "Confirmation",
            "group": "cast_mode",
            "value": "Confirmation"
        })
        self.menu_items.append({
            "id": "cast_insta",
            "type": "option",
            "section": "Cast Mode",
            "label": "Insta Cast",
            "group": "cast_mode",
            "value": "Insta Cast"
        })

        # 1. Save Directory
        self.menu_items.append({
            "id": "save_dir",
            "type": "action",
            "section": "SaveDir",
            "label": self.save_dir_var.get(),
            "action": self.browse_folder
        })

        # 2. Scope - Single
        self.menu_items.append({
            "id": "scope_single",
            "type": "option",
            "section": "Scope",
            "label": "Single",
            "group": "scope",
            "value": "Single"
        })
        # 3. Scope - Playlist
        self.menu_items.append({
            "id": "scope_playlist",
            "type": "option",
            "section": "Scope",
            "label": "Playlist",
            "group": "scope",
            "value": "Playlist"
        })

        # 4. Mode - Simple
        self.menu_items.append({
            "id": "mode_simple",
            "type": "option",
            "section": "Mode",
            "label": "Simple",
            "group": "mode",
            "value": "Simple"
        })
        # 5. Mode - Advanced
        self.menu_items.append({
            "id": "mode_advanced",
            "type": "option",
            "section": "Mode",
            "label": "Advanced",
            "group": "mode",
            "value": "Advanced"
        })

        # Format / Resolutions
        if mode == "Simple":
            self.menu_items.append({
                "id": "fmt_video_best",
                "type": "option",
                "section": "Format",
                "label": "Video (Best Available)",
                "group": "format_res",
                "value": "Video_Best"
            })
            self.menu_items.append({
                "id": "fmt_audio",
                "type": "option",
                "section": "Format",
                "label": "Audio Only (M4A)",
                "group": "format_res",
                "value": "Audio"
            })
        else:
            self.menu_items.append({
                "id": "fmt_video_title",
                "type": "header",
                "section": "Format",
                "label": "Video"
            })
            for r in ["Best Available", "2160p", "1440p", "1080p", "720p", "480p"]:
                self.menu_items.append({
                    "id": f"fmt_video_{r}",
                    "type": "option",
                    "section": "Format",
                    "label": r,
                    "group": "format_res",
                    "value": f"Video_{r}"
                })
            self.menu_items.append({
                "id": "fmt_audio_title",
                "type": "header",
                "section": "Format",
                "label": "Audio Only"
            })
            self.menu_items.append({
                "id": "fmt_audio",
                "type": "option",
                "section": "Format",
                "label": "Audio Only (M4A)",
                "group": "format_res",
                "value": "Audio"
            })

        # Actions at the bottom
        if self.is_downloading:
            remaining = len(self.download_queue)
            label_text = f"PROCESSING ({remaining} remaining)..." if remaining > 0 else "PROCESSING..."
            self.menu_items.append({
                "id": "action_download",
                "type": "header",
                "section": "Actions",
                "label": label_text
            })
            self.menu_items.append({
                "id": "action_open",
                "type": "action",
                "section": "Actions",
                "label": "CANCEL",
                "action": self.cancel_download
            })
        else:
            self.menu_items.append({
                "id": "action_download",
                "type": "action",
                "section": "Actions",
                "label": "DOWNLOAD",
                "action": self.start_download
            })
            self.menu_items.append({
                "id": "action_open",
                "type": "action",
                "section": "Actions",
                "label": "Open Folder",
                "action": self.open_folder
            })
            
        self.menu_items.append({
            "id": "action_view_logs",
            "type": "action",
            "section": "Actions",
            "label": "VIEW LOGS",
            "action": self.show_logs_screen
        })
        self.menu_items.append({
            "id": "action_update",
            "type": "action",
            "section": "Actions",
            "label": "Update Tool",
            "action": self.update_dependencies
        })

    def is_focusable(self, item):
        return item["type"] in ["input", "action", "option"]

    def validate_focused_index(self):
        if self.focused_index >= len(self.menu_items):
            self.focused_index = 0
        if not self.is_focusable(self.menu_items[self.focused_index]):
            n = len(self.menu_items)
            for i in range(n):
                idx = (self.focused_index + i) % n
                if self.is_focusable(self.menu_items[idx]):
                    self.focused_index = idx
                    break

    def focus_next(self, event=None):
        n = len(self.menu_items)
        for i in range(1, n + 1):
            idx = (self.focused_index + i) % n
            if self.is_focusable(self.menu_items[idx]):
                self.focused_index = idx
                break
        self.refresh_ui()
        return "break"

    def focus_prev(self, event=None):
        n = len(self.menu_items)
        for i in range(1, n + 1):
            idx = (self.focused_index - i) % n
            if self.is_focusable(self.menu_items[idx]):
                self.focused_index = idx
                break
        self.refresh_ui()
        return "break"

    def set_focused_index_by_id(self, item_id):
        for idx, it in enumerate(self.menu_items):
            if it["id"] == item_id:
                if self.focused_index != idx:
                    self.focused_index = idx
                    self.refresh_ui()
                break

    def activate_focused(self, event=None):
        if self.focused_index == 0 and event and event.keysym == "space":
            return None # Let standard Entry behavior handle space
        
        if self.focused_index == 0 and event and event.keysym == "Return":
            self.start_download()
            return "break"

        item = self.menu_items[self.focused_index]
        self.activate_item(item)
        return "break"

    def activate_item(self, item):
        if item["type"] == "action":
            item["action"]()
        elif item["type"] == "option":
            group = item["group"]
            val = item["value"]
            
            if group == "scope":
                self.scope_var.set(val)
            elif group == "cast_mode":
                self.cast_mode_var.set(val)
            elif group == "mode":
                self.mode_var.set(val)
            elif group == "format_res":
                if val == "Audio":
                    self.format_var.set("Audio Only")
                elif val == "Video_Best":
                    self.format_var.set("Video")
                    self.res_var.set("Best Available")
                elif val.startswith("Video_"):
                    res_val = val.split("Video_")[1]
                    self.format_var.set("Video")
                    self.res_var.set(res_val)

            self.save_config()
            self.rebuild_menu_items()
            self.refresh_ui()

    def select_item_by_click(self, item):
        for idx, it in enumerate(self.menu_items):
            if it["id"] == item["id"]:
                self.focused_index = idx
                self.activate_item(it)
                break

    def refresh_ui(self):
        # If we are viewing logs, do not draw main menu items
        if self.viewing_logs:
            self.update_output_box()
            return

        # 1. Clear list_frame except url_entry
        for widget in self.list_frame.winfo_children():
            if widget == self.url_entry:
                widget.grid_forget()
            else:
                widget.destroy()

        # 2. Sync / rebuild menu
        self.rebuild_menu_items()
        self.validate_focused_index()

        # 3. Draw items
        row_idx = 0
        current_section = None

        for idx, item in enumerate(self.menu_items):
            if item["section"] != current_section:
                current_section = item["section"]
                
                # Check if focused item is in this section
                section_has_focus = False
                for f_idx, f_item in enumerate(self.menu_items):
                    if f_item["section"] == current_section and f_idx == self.focused_index:
                        section_has_focus = True
                        break
                
                header_fg = self.accent_color if section_has_focus else self.text_color
                header_mapping = {
                    "URL": "◇ URL",
                    "Cast Mode": "◇ Cast Mode",
                    "SaveDir": "◇ Save Directory",
                    "Scope": "◇ Scope",
                    "Mode": "◇ Mode",
                    "Format": "◆ Format",
                    "Actions": "◇ Actions"
                }
                header_text = header_mapping.get(current_section, f"◇ {current_section}")
                
                lbl = tk.Label(
                    self.list_frame,
                    text=header_text,
                    font=("Consolas", 11, "bold"),
                    fg=header_fg,
                    bg=self.bg_color,
                    anchor="w"
                )
                lbl.grid(row=row_idx, column=0, columnspan=2, sticky="w", pady=(8, 2))
                row_idx += 1

            is_focused = (idx == self.focused_index)
            prefix = "│   "
            if is_focused:
                prefix = "│ > "

            if item["type"] == "header":
                lbl = tk.Label(
                    self.list_frame,
                    text=f"│   {item['label']}",
                    font=("Consolas", 11, "bold"),
                    fg=self.subdued_color,
                    bg=self.bg_color,
                    anchor="w"
                )
                lbl.grid(row=row_idx, column=0, columnspan=2, sticky="w")
                row_idx += 1
                
            elif item["type"] == "input":
                prefix_lbl = tk.Label(
                    self.list_frame,
                    text=prefix,
                    font=("Consolas", 11),
                    fg=self.accent_color if is_focused else self.muted_color,
                    bg=self.bg_color,
                    anchor="w"
                )
                prefix_lbl.grid(row=row_idx, column=0, sticky="w")
                
                self.url_entry.grid(row=row_idx, column=1, sticky="ew", padx=(5, 0))
                self.url_entry.configure(
                    fg=self.accent_color if is_focused else self.text_color,
                    insertbackground=self.accent_color
                )
                
                if is_focused and self.focus_get() != self.url_entry:
                    self.url_entry.focus_set()
                row_idx += 1

            elif item["type"] == "action":
                display_text = f"{prefix}{item['label']}" if item["id"] == "save_dir" else f"{prefix}[ {item['label']} ]"
                item_fg = self.accent_color if is_focused else self.text_color
                
                lbl = tk.Label(
                    self.list_frame,
                    text=display_text,
                    font=("Consolas", 11),
                    fg=item_fg,
                    bg=self.bg_color,
                    anchor="w",
                    cursor="hand2"
                )
                lbl.grid(row=row_idx, column=0, columnspan=2, sticky="w")
                lbl.bind("<Button-1>", lambda e, it=item: self.select_item_by_click(it))
                row_idx += 1

            elif item["type"] == "option":
                is_selected = False
                group = item["group"]
                val = item["value"]
                
                if group == "scope":
                    is_selected = (self.scope_var.get() == val)
                elif group == "cast_mode":
                    is_selected = (self.cast_mode_var.get() == val)
                elif group == "mode":
                    is_selected = (self.mode_var.get() == val)
                elif group == "format_res":
                    current_fmt = self.format_var.get()
                    current_res = self.res_var.get()
                    if val == "Audio":
                        is_selected = (current_fmt == "Audio Only")
                    elif val == "Video_Best":
                        is_selected = (current_fmt == "Video" and current_res == "Best Available")
                    elif val.startswith("Video_"):
                        res_val = val.split("Video_")[1]
                        is_selected = (current_fmt == "Video" and current_res == res_val)

                if group == "cast_mode":
                    display_text = f"{prefix}[ {item['label']} ]"
                else:
                    indicator = "• " if is_selected else "o "
                    indent = "  " if (item["section"] == "Format" and self.mode_var.get() == "Advanced") else ""
                    display_text = f"{prefix}{indent}{indicator}{item['label']}"
                
                if is_selected:
                    item_fg = self.accent_color
                elif is_focused:
                    item_fg = self.text_color
                else:
                    item_fg = self.subdued_color

                lbl = tk.Label(
                    self.list_frame,
                    text=display_text,
                    font=("Consolas", 11),
                    fg=item_fg,
                    bg=self.bg_color,
                    anchor="w",
                    cursor="hand2"
                )
                lbl.grid(row=row_idx, column=0, columnspan=2, sticky="w")
                lbl.bind("<Button-1>", lambda e, it=item: self.select_item_by_click(it))
                row_idx += 1

        if self.focused_index != 0:
            self.focus_set()

        self.update_output_box()

    def auto_paste(self, event=None):
        try:
            self.url_var.set(self.clipboard_get())
            self.url_entry.icursor("end")
            self.set_focused_index_by_id("url")
            return "break"
        except: pass

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_dir_var.get())
        if folder:
            self.save_dir_var.set(folder)
            self.save_config()
            self.rebuild_menu_items()
            self.refresh_ui()

    def open_folder(self):
        if os.path.exists(self.save_dir_var.get()):
            os.startfile(self.save_dir_var.get())

    def toggle_advanced_mode(self, *_):
        self.save_config()
        self.rebuild_menu_items()
        self.refresh_ui()

    def log(self, message):
        self.after(0, self._write_log, message)

    def _write_log(self, message):
        self.log_box_content += message
        self.output_box.configure(state="normal")
        self.output_box.insert("end", message)
        self.output_box.see("end")
        self.output_box.configure(state="disabled")

    def add_history_item(self, filename):
        self.log(f"\n[System] Finished: {filename}\n")

    def update_output_box(self):
        self.output_box.configure(state="normal")
        self.output_box.delete("1.0", "end")
        if not self.log_box_content:
            self.output_box.insert("end", "(No logs yet)")
        else:
            self.output_box.insert("end", self.log_box_content)
        self.output_box.see("end")
        self.output_box.configure(state="disabled")

    def show_main_screen(self):
        self.viewing_logs = False
        self.title_label.configure(text="■ Sleek Loader\n────────────────────────────────────────────────────────")
        self.adjust_layout(self.current_layout_mode == "double")
        self.refresh_ui()
        self.url_entry.focus_set()

    def show_logs_screen(self):
        self.viewing_logs = True
        self.title_label.configure(text="■ Sleek Loader / Log\n────────────────────────────────────────────────────────")
        self.adjust_layout(self.current_layout_mode == "double")
        self.update_output_box()

    def handle_escape(self, event=None):
        if self.viewing_logs:
            self.show_main_screen()
            return "break"

    def handle_backspace(self, event=None):
        if self.viewing_logs:
            self.show_main_screen()
            return "break"

    def set_ui_state(self, downloading=True):
        self.is_downloading = downloading
        self.refresh_ui()

    def cancel_download(self):
        if self.current_process: 
            self.log("\n[User] Cancelling...\n")
            self.current_process.kill()

    def update_dependencies(self):
        self.log("[System] Checking for updates...\n")
        def run_update():
            try:
                p = subprocess.Popen([YT_DLP_PATH, "-U"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=CREATE_NO_WINDOW)
                for line in p.stdout: self.log(line)
                p.wait()
                self.log("[System] Done.\n")
            except Exception as e: self.log(f"[Error] {e}\n")
        threading.Thread(target=run_update, daemon=True).start()

    def start_download(self):
        url = self.url_var.get().strip()
        self.url_entry.delete(0, 'end')
        if not url: return
        
        self.download_queue.append(url)
        self.log(f"[System] Added to queue: {url}\n")
        self.trigger_next_download()

    def trigger_next_download(self):
        if self.is_downloading:
            self.refresh_ui()
            return
        
        if not self.download_queue:
            self.set_ui_state(False)
            return
            
        next_url = self.download_queue.pop(0)
        self.set_ui_state(True)
        threading.Thread(target=self._download_thread, args=(next_url,), daemon=True).start()

    def _finish_download_and_continue(self):
        self.is_downloading = False
        self.trigger_next_download()

    def is_valid_url(self, url):
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            return False
        if "." not in url:
            return False
        if len(url) < 12:
            return False
        if any(c.isspace() for c in url):
            return False
        return True

    def on_url_change(self, *_):
        url = self.url_var.get().strip()
        if self.cast_mode_var.get() == "Insta Cast":
            if self.is_valid_url(url):
                self.start_download()

    def _download_thread(self, url):
        s_dir, mode, fmt, scope, res = [self.config_data[k] for k in ["save_dir", "mode", "format", "scope", "resolution"]]
        cmd = [YT_DLP_PATH, "--ffmpeg-location", FFMPEG_PATH, "--no-colors", "-o", os.path.join(s_dir, "%(title)s.%(ext)s")]
        cmd.extend(["--no-write-thumbnail", "--postprocessor-args", "-map_metadata -1", "-N", "6"])
        if scope == "Playlist": cmd.extend(["--yes-playlist", "--sleep-requests", "3"])
        else: cmd.extend(["--no-playlist"])
        
        if fmt == "Audio Only": cmd.extend(["-x", "--audio-format", "m4a"])
        else:
            r = res.replace("p", "") if mode == "Advanced" and res != "Best Available" else None
            cmd.extend(["-S", f"res:{r},vcodec:h264,acodec:m4a" if r else "vcodec:h264,res,acodec:m4a"])

        cmd.append(url)
        try:
            self.current_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, creationflags=CREATE_NO_WINDOW)
            fname = None
            for line in self.current_process.stdout:
                self.log(line)
                if "Destination:" in line: 
                    try: fname = os.path.basename(line.split("Destination: ")[1].strip())
                    except: pass
                if "Merging formats into" in line: 
                    try: fname = os.path.basename(line.split('into "')[1].split('"')[0])
                    except: pass
            self.current_process.wait()
            if self.current_process.returncode == 0: self.add_history_item(fname if fname else "Completed")
        except Exception as e: self.log(f"\n[Error] {e}\n")
        finally:
            self.current_process = None
            self.after(0, self._finish_download_and_continue)

if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()