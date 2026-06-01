import json, os, sys, re
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, colorchooser
from PIL import Image, ImageEnhance
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import threading

SQUARE_SIZE = 30

squares_cache = {}
image_cache = {}
pokedex = {}
ref = None
firebase_listener = None
local_only = False
cred = None


def get_asset_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def on_closing():
    print("Shutting down cleanly...")
    app.destroy()
    os._exit(0)


def show_tracker_menu(event):
    load_pokedex_menu.post(event.x_root, event.y_root)


def printPokedex():
    if not pokedex:
        print(pokedex)
    for pokemon in pokedex.items():
        print(pokemon)


def get_pokemon_images(pokemon_name):
    if pokemon_name in image_cache:
        return image_cache[pokemon_name]
    
    image_path = get_asset_path(os.path.join("assets", "pokemon", f"{pokemon_name.lower()}.png"))
    raw_img = Image.open(image_path).convert("RGBA")
    
    enhancer = ImageEnhance.Brightness(raw_img)
    dark_raw_img = enhancer.enhance(0.3)
    
    img_size = SQUARE_SIZE - 4
    normal = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(img_size, img_size))
    dark = ctk.CTkImage(light_image=dark_raw_img, dark_image=dark_raw_img, size=(img_size, img_size))
    
    image_cache[pokemon_name] = (normal, dark)
    return normal, dark


def open_database_creds():
    global ref, local_only, cred
    
    file_path = filedialog.askopenfilename(
        title="Select Database Credentials JSON File",
        filetypes=[("JSON Files", "*.json")]
    )

    if firebase_admin._apps:
        print("Found an existing Firebase app connection. Resetting...")

        old_app = firebase_admin.get_app()

        firebase_admin.delete_app(old_app)
        print("Previous connection terminated successfully.")

    if file_path:
        try:
            database_url = ctk.CTkInputDialog(
                text="Enter Database URL:",
                title="Database URL Required"
            ).get_input()

            if not re.match(r"https:\/\/[\w.-]+\.(?:firebasedatabase\.app|firebaseio\.com)\/?", database_url):
                raise ValueError("Invalid Database URL")

            if database_url:
                cred = credentials.Certificate(file_path)
                firebase_admin.initialize_app(cred, {
                    "databaseURL": database_url
                })
                local_only = False

        except Exception as e:
            messagebox.showerror(
                title="Error", 
                message=f"Database error: {e}"
            )


def open_pokedex_file():
    global pokedex, ref, firebase_listener, local_only, pokedex_file_path, pokedex_file_name

    if not cred:
        messagebox.showwarning(
            title="Local-Only Mode",
            message="Since no database credentials file was loaded, program will use Local mode!"
        )
        local_only = True
    
    if not local_only and cred is None:
        messagebox.showerror(
            title="Database Error",
            message="Please reload the database credentials file!"
        )
        return

    pokedex_file_path = filedialog.askopenfilename(
        title="Select Pokedex JSON Data",
        filetypes=[("JSON Files", "*.json")]
    )

    if pokedex_file_path:
        try:
            with open(pokedex_file_path, 'r') as f:
                pokedex = json.load(f)

            pokedex_file_name = os.path.basename(pokedex_file_path).rstrip(".json")

            if not local_only:
                ref = db.reference(pokedex_file_name)
                db_data = ref.get()

                if db_data and isinstance(db_data, dict):
                    pokedex = db_data
                else:
                    for pokemon_info in pokedex.values():
                        pokemon_info['is_caught'] = bool(pokemon_info.get('is_caught', False))
                    ref.set(pokedex)
            else:
                for pokemon_info in pokedex.values():
                    pokemon_info['is_caught'] = bool(pokemon_info.get('is_caught', False))

            create_pokedex_boxes()
            arrange_pokedex_boxes()
            printPokedex()

            if not local_only:
                if firebase_listener is not None:
                    threading.Thread(target=firebase_listener.close, daemon=True).start()
                    firebase_listener = None

                firebase_listener = ref.listen(on_firebase_update)

        except Exception as e:
            messagebox.showerror(
                title="Error",
                message=f"Error: {str(e)}"
            )


def clear_squares_data():
    global squares_cache
    
    for square in squares_cache.values():
        square.destroy()

    squares_cache = {}


def clear_pokedex_data():
    global pokedex, ref, image_cache
    image_cache = {}
    pokedex = {}
    ref = None

    clear_squares_data()

    tracker_container.pack_forget()

    printPokedex()


def enter_local_mode():
    global firebase_listener, cred, local_only
    cred = None
    local_only = True
    if firebase_listener:
        threading.Thread(target=firebase_listener.close, daemon=True).start()
        firebase_listener = None


def save_pokedex_data():
    global pokedex

    if not pokedex:
        messagebox.showwarning(
            title="Warning", message="Pokedex is empty! Nothing to save."
        )
        return

    file_path = filedialog.asksaveasfilename(
        title="Save Pokedex Data",
        initialfile=pokedex_file_name,
        defaultextension=".json",
        filetypes=[("JSON Files", "*.json")],
    )

    if file_path:
        try:
            with open(file_path, "w") as f:
                json.dump(pokedex, f, indent=4)

            messagebox.showinfo(
                title="Success", 
                message="Pokedex data saved successfully!"
            )

        except Exception as e:
            print(f"Error saving data: {e}")
            messagebox.showerror(
                title="Error", 
                message="Could not save the file!"
            )


def create_pokedex_boxes():
    global squares_cache

    if not pokedex: return

    clear_squares_data()
    tracker_container.pack(fill="both", expand=True, padx=5, pady=5)

    sorted_pokedex = sorted(pokedex.items(), key=lambda x: x[1].get('num', 0))

    for i, (pokemon_name, pokemon_info) in enumerate(sorted_pokedex, start=1):
        square = ctk.CTkFrame(
            tracker_container,
            corner_radius=0,
            width=SQUARE_SIZE,
            height=SQUARE_SIZE
        )
        square.grid_propagate(False)
        square.pack_propagate(False)
        square.bind("<Button-3>", show_tracker_menu)
        square.bind("<Button-1>", toggle_caught)
        square.bind("<Button-2>", on_middle_click_square)
        
        square.is_caught = pokemon_info.get('is_caught', False)
        square.pokemon_id = str(pokemon_name)
        square.configure(fg_color = pokemon_info['color'] if not square.is_caught else "#494949")

        image_path = None

        try:
            ctk_image, ctk_image_dark = get_pokemon_images(pokemon_name)

            img_label = ctk.CTkLabel(
                master=square,
                image=ctk_image,
                text=""
            )
            img_label.pack(expand=True, fill="both")

            square.normal_img = ctk_image
            square.dark_img = ctk_image_dark

            img_label.bind("<Button-1>", toggle_caught)
            img_label.bind("<Button-3>", show_tracker_menu)
            img_label.bind("<Button-2>", on_middle_click_square)

        except Exception as e:
            print(f"[Image Error] pokemon='{pokemon_name}', path='{image_path}', error={e}")
            label = ctk.CTkLabel(
                master=square,
                text=str(i),
                text_color="#FFFFFF",
                font=("Segoe UI", 10, "bold")
            )
            label.pack(expand=True, fill="both")

            label.bind("<Button-1>", toggle_caught)
            label.bind("<Button-3>", show_tracker_menu)
            label.bind("<Button-2>", on_middle_click_square)
        
        squares_cache[pokemon_name] = square

    sync_squares_to_ui()


def arrange_pokedex_boxes(event=None):
    if not pokedex: return

    def get_actual_size():
        scale = ctk.ScalingTracker.get_widget_scaling(app)
        return round(SQUARE_SIZE * scale)
    
    COLS = max(1, tracker_container._parent_frame.winfo_width() // (get_actual_size() + 2))

    current_col, current_row = 0, 0
    for square in squares_cache.values():
        square.grid(row=current_row, column=current_col, padx=1, pady=1, sticky="nsew")
        current_col += 1
        if current_col >= COLS:
            current_col = 0
            current_row += 1


def toggle_caught(event):
    global pokedex
    
    widget = event.widget
    while widget is not None:
        if hasattr(widget, 'pokemon_id'):
            break
        widget = getattr(widget, 'master', None)
    
    if widget is None:
        return

    pokemon_id = widget.pokemon_id
    
    if pokemon_id and pokemon_id in pokedex:
        current_caught = pokedex[pokemon_id].get('is_caught', False)
        new_caught_state = not current_caught

        pokedex[pokemon_id]['is_caught'] = new_caught_state

        widget.configure(fg_color="#494949" if new_caught_state else pokedex[pokemon_id]['color'])
        widget.is_caught = new_caught_state
        
        if not local_only:
            try:
                ref.child(pokemon_id).update({"is_caught": new_caught_state})
            except Exception as e:
                print(f"Failed to transmit data to Firebase: {e}")


def sync_squares_to_ui(target_id=None):
    squares_to_update = [target_id] if target_id else squares_cache.keys()

    try:
        for pokemon_name in squares_to_update:
            if pokemon_name not in squares_cache or pokemon_name not in pokedex:
                raise KeyError("p_id not in square cache or not in pokedex")
            
            square = squares_cache[pokemon_name]
            is_caught = bool(pokedex[pokemon_name].get('is_caught', False)) # Cast to bool — Firebase can return 0/1 instead of False/True

            # 1. Determine what the color *should* be
            expected_color = "#494949" if is_caught else pokedex[pokemon_name].get('color', '#9C9C9C')
            
            # 2. OPTIMIZATION: Only update if the caught state or color has actually changed
            current_color = square.cget("fg_color")
            if getattr(square, 'is_caught', None) == is_caught and current_color == expected_color:
                continue # Skip redrawing if nothing changed
                
            # 3. Apply changes only when necessary
            print(f"Syncing UI for {pokemon_name}: caught={is_caught}, color={expected_color}")
            square.configure(fg_color=expected_color)
            square.is_caught = is_caught

    except Exception as e:
        print(f"Error: {e}")


def on_firebase_update(event):
    global pokedex

    path_parts = [p for p in event.path.strip('/').split('/') if p]

    # --- HANDLE COLD DELETIONS FROM FIREBASE CONSOLE ---
    if event.data is None:
        if len(path_parts) == 1:
            # Whole pokemon was deleted directly (e.g., event.path = '/Pikachu')
            pokemon_name = path_parts[0]

            # 1. Pop from local memory cache dictionary
            pokedex.pop(pokemon_name, None)

            # 2. Safely wipe the UI element and remove from layout tracking
            if pokemon_name in squares_cache:
                squares_cache[pokemon_name].destroy()
                del squares_cache[pokemon_name]

            # 3. Schedule a structural layout recalculation on the main thread
            app.after(0, arrange_pokedex_boxes)

        elif len(path_parts) == 2:
            # A single interior attribute field was deleted (e.g., '/Pikachu/is_caught')
            pokemon_name, field = path_parts
            if pokemon_name in pokedex:
                pokedex[pokemon_name].pop(field, None)
                app.after(0, lambda: sync_squares_to_ui(pokemon_name))
        return

    target_id = None

    # --- HANDLE NEW INSERTS AND VALUE CHANGES ---
    if len(path_parts) == 0:
        # Initial full snapshot: event.data = {full pokedex}
        if isinstance(event.data, dict):
            for pokemon_name, pokemon_data in event.data.items():
                if pokemon_name in pokedex and isinstance(pokemon_data, dict):
                    pokedex[pokemon_name].update(pokemon_data)
            app.after(0, lambda: sync_squares_to_ui(None))

    elif len(path_parts) == 1:
        # Whole pokemon updated: event.path = '/Pikachu'
        pokemon_name = path_parts[0]
        if pokemon_name in pokedex and isinstance(event.data, dict):
            pokedex[pokemon_name].update(event.data)
            target_id = pokemon_name

    elif len(path_parts) == 2:
        # Single field updated: event.path = '/Pikachu/is_caught'
        pokemon_name, field = path_parts
        if pokemon_name in pokedex:
            pokedex[pokemon_name][field] = event.data
            target_id = pokemon_name

    app.after(0, lambda: sync_squares_to_ui(target_id))


def open_pokemon_editor(pokemon_name=None):
    is_edit = pokemon_name is not None
    if not pokedex and not is_edit:
        messagebox.showwarning(
            title="Warning", 
            message="Load a Pokédex file first!", 
            parent=app
        )
        return

    if is_edit:
        data = pokedex[pokemon_name]
    else:
        data = {
            "num": 0,
            "type": [],
            "color": "#9C9C9C",
            "locations": {"ruby": [], "sapphire": [], "emerald": []},
            "is_caught": False
        }
    
    editor = ctk.CTkToplevel(app)
    editor.title("Edit Pokemon" if is_edit else "Add Pokemon")
    editor.geometry("420x620")
    editor.grab_set()
    editor.resizable(False, True)

    scroll = ctk.CTkScrollableFrame(editor)
    scroll.pack(fill="both", expand=True, padx=5, pady=5)

    # Name
    ctk.CTkLabel(scroll, text="Name:", anchor="w").pack(fill="x", pady=(5, 0))
    name_var = tk.StringVar(value=pokemon_name or "")
    name_entry = ctk.CTkEntry(scroll, textvariable=name_var)
    if is_edit: name_entry.configure(state="disabled")
    name_entry.pack(fill="x", pady=(0, 5))

    # Dex Number
    ctk.CTkLabel(scroll, text="Dex Number:", anchor="w").pack(fill="x", pady=(5, 0))
    num_var = tk.StringVar(value=str(data.get("num", 0)))
    ctk.CTkEntry(scroll, textvariable=num_var).pack(fill="x", pady=(0, 5))

    # Type
    ctk.CTkLabel(scroll, text="Types (comma-separated):", anchor="w").pack(fill="x", pady=(5, 0))
    type_var = tk.StringVar(value=", ".join(data.get("type", [])))
    ctk.CTkEntry(scroll, textvariable=type_var).pack(fill="x", pady=(0, 5))

    # Color
    ctk.CTkLabel(scroll, text="Color (hex e.g. #9C9C9C):", anchor="w").pack(
        fill="x", pady=(5, 0)
    )
    color_row = ctk.CTkFrame(scroll, fg_color="transparent")
    color_row.pack(fill="x", pady=(0, 5))
    color_row.columnconfigure(0, weight=1)

    color_var = tk.StringVar(value=data.get("color", "#9C9C9C"))
    ctk.CTkEntry(color_row, textvariable=color_var).grid(
        row=0, column=0, sticky="ew", padx=(0, 8)
    )

    # Clickable preview frame transformed into an interactive widget element
    color_preview = ctk.CTkButton(
        color_row,
        width=32,
        height=32,
        fg_color=data.get("color", "#9C9C9C"),
        hover_color=data.get("color", "#9C9C9C"),
        text="",
        corner_radius=4,
    )
    color_preview.grid(row=0, column=1)


    def update_preview(*_):
        c = color_var.get()
        if re.match(r'^#[0-9A-Fa-f]{6}$', c):
            color_preview.configure(fg_color=c)
    color_var.trace_add("write", update_preview)


    def open_windows_color_picker():
        import ctypes
        from ctypes import wintypes

        pokemon_presets = [
            "#9C9C9C",  # All Games
            "#E1432E",  # Multiple game but prefered Ruby
            "#AF0D0D",  # Only Ruby
            "#2E81E1",  # Multiple game but prefered Sapphire
            "#0E0EB7",  # Only Sapphire
            "#2EE140",  # Multiple game but prefered Emerald
            "#1D9808",  # Only Emerald
            "#E5DC29",  # Only Ruby and Emerald
            "#DB1DCB",  # Only Ruby and Sapphire
            "#29DCE5",  # Only Sapphire and Emerald
            "#5A5A5A",  # Not Catchable
        ]

        COLORREF_ARRAY = wintypes.DWORD * 16
        custom_colors_memory = COLORREF_ARRAY()

        for idx in range(16):
            if idx < len(pokemon_presets):
                hex_str = pokemon_presets[idx].lstrip("#")
                # Parse out RGB values
                r, g, b = (
                    int(hex_str[0:2], 16),
                    int(hex_str[2:4], 16),
                    int(hex_str[4:6], 16),
                )
                # Pack them in BGR order for Windows memory
                custom_colors_memory[idx] = (b << 16) | (g << 8) | r
            else:
                custom_colors_memory[idx] = 0x00FFFFFF  # Fallback to white padding

        # 3. Define the Windows structural blueprint for CHOOSECOLORW
        class CHOOSECOLORW(ctypes.Structure):
            _fields_ = [
                ("lStructSize", wintypes.DWORD),
                ("hwndOwner", wintypes.HWND),
                ("hInstance", wintypes.HWND),
                ("rgbResult", wintypes.DWORD),
                ("lpCustColors", ctypes.POINTER(wintypes.DWORD)),
                ("Flags", wintypes.DWORD),
                ("lCustData", wintypes.LPARAM),
                ("lpfnHook", ctypes.c_void_p),
                ("lpTemplateName", wintypes.LPCWSTR),
            ]

        # Get parent frame handle ID so the modal locks properly over the app window
        try:
            hwnd_parent = editor.winfo_id()
        except:
            hwnd_parent = None

        # Parse current active color value to set the picker crosshair default
        current_hex = color_var.get().lstrip("#")
        curr_r, curr_g, curr_b = (
            int(current_hex[0:2], 16),
            int(current_hex[2:4], 16),
            int(current_hex[4:6], 16),
        )
        initial_bgr = (curr_b << 16) | (curr_g << 8) | curr_r

        # Initialize the native layout configuration object
        cc = CHOOSECOLORW()
        cc.lStructSize = ctypes.sizeof(CHOOSECOLORW)
        cc.hwndOwner = hwnd_parent
        cc.lpCustColors = ctypes.cast(
            custom_colors_memory, ctypes.POINTER(wintypes.DWORD)
        )
        cc.rgbResult = initial_bgr
        cc.Flags = (0x00000001 | 0x00000002)  # CC_RGBINIT (Use default color) | CC_FULLOPEN (Auto expand window)

        # 4. Trigger the native Windows DLL window
        if ctypes.windll.comdlg32.ChooseColorW(ctypes.byref(cc)):
            # Extract returned BGR configuration integer back out to python hex string
            b = (cc.rgbResult >> 16) & 0xFF
            g = (cc.rgbResult >> 8) & 0xFF
            r = cc.rgbResult & 0xFF
            selected_color = f"#{r:02X}{g:02X}{b:02X}"

            color_var.set(selected_color)


    # Bind the button press action to directly trigger the OS dialog window
    color_preview.configure(command=open_windows_color_picker)

    # Locations
    location_boxes = {}
    locations_data = data.get("locations", {"ruby": [], "sapphire": [], "emerald": []})
    for game in ["ruby", "sapphire", "emerald"]:
        ctk.CTkLabel(scroll, text=f"{game.capitalize()} locations (one per line):", anchor="w").pack(fill="x", pady=(5, 0))
        tb = ctk.CTkTextbox(scroll, height=75)
        tb.pack(fill="x", pady=(0, 5))
        tb.insert("1.0", "\n".join(locations_data.get(game, [])))
        location_boxes[game] = tb

    # Caught
    caught_var = tk.BooleanVar(value=bool(data.get("is_caught", False)))
    ctk.CTkCheckBox(scroll, text="Caught", variable=caught_var).pack(anchor="w", pady=(5, 10))

    # Buttons
    btn_row = ctk.CTkFrame(scroll, fg_color="transparent")
    btn_row.pack(fill="x", pady=(5, 0))


    def save():
        name = name_var.get().strip()
        if not name:
            messagebox.showerror("Name Error", f"Error: {e}", parent=editor)
            return

        try:
            num = int(num_var.get())
            if any(info.get("num") == num for name, info in pokedex.items() if name != pokemon_name): raise KeyError(f"Dex num {num} is already taken!")
        except Exception as e:
            messagebox.showerror("Dex Num Error", f"Error: {e}", parent=editor)
            return

        color = color_var.get().strip()
        if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
            messagebox.showerror("Error", "Color must be a valid hex code (e.g. #9C9C9C)!", parent=editor)
            return

        if not is_edit and name in pokedex:
            messagebox.showerror("Error", f"'{name}' already exists!", parent=editor)
            return

        new_data = {
            "num": num,
            "type": [t.strip() for t in type_var.get().split(",") if t.strip()],
            "color": color,
            "locations": {
                game: [line.strip() for line in tb.get("1.0", "end").splitlines() if line.strip()]
                for game, tb in location_boxes.items()
            },
            "is_caught": caught_var.get()
        }

        pokedex[name] = new_data

        if not local_only and ref is not None:
            try:
                ref.child(name).set(new_data)
            except Exception as e:
                print(f"Firebase sync error: {e}")

        create_pokedex_boxes()
        arrange_pokedex_boxes()
        editor.destroy()
    

    def delete():
        if not messagebox.askyesno("Confirm", f"Delete {pokemon_name} from the Pokédex?", parent=editor):
            return

        pokedex.pop(pokemon_name, None)
        if pokemon_name in squares_cache:
            squares_cache[pokemon_name].destroy()
            del squares_cache[pokemon_name]

        if not local_only and ref is not None:
            try:
                ref.child(pokemon_name).delete()
            except Exception as e:
                print(f"Firebase delete error: {e}")

        arrange_pokedex_boxes()
        editor.destroy()


    ctk.CTkButton(btn_row, text="Save", command=save).pack(side="left", expand=True, fill="x", padx=(0, 4))
    if is_edit:
        ctk.CTkButton(btn_row, text="Delete", fg_color="#C0392B", hover_color="#922B21", command=delete).pack(side="left", expand=True, fill="x", padx=(0, 4))
    ctk.CTkButton(btn_row, text="Cancel", fg_color="#555555", hover_color="#333333", command=editor.destroy).pack(side="left", expand=True, fill="x")


def on_middle_click_square(event):
    widget = event.widget
    while widget is not None:
        if hasattr(widget, 'pokemon_id'):
            break
        widget = getattr(widget, 'master', None)
    if widget is not None:
        open_pokemon_editor(widget.pokemon_id)


def on_middle_click_empty(event):
    open_pokemon_editor()



app = ctk.CTk()
app.title("Pokemon Route Helper")
app.geometry("800x300")

paned_window = tk.PanedWindow(app, orient=tk.HORIZONTAL, sashwidth=5, sashpad=0, bg="#2b2b2b")
paned_window.pack(fill="both", expand=True, padx=5, pady=5)

app.grid_rowconfigure(0, weight=1)
app.grid_rowconfigure(1, weight=1)
app.grid_columnconfigure(0, weight=1)

tracker_frame = ctk.CTkFrame(paned_window, fg_color="#666666", corner_radius=0)
paned_window.add(tracker_frame, stretch="never")

route_frame = ctk.CTkFrame(paned_window, fg_color="#383838", corner_radius=0)
paned_window.add(route_frame, stretch="always")

tracker_container = ctk.CTkScrollableFrame(tracker_frame, fg_color="transparent", corner_radius=0)
tracker_container._parent_frame.bind("<Configure>", arrange_pokedex_boxes)

load_pokedex_menu = tk.Menu(
    app, 
    tearoff=0, 
    bg="#f2f2f2",                
    fg="#000000",                
    activebackground="#e5f1fb",  
    activeforeground="#000000",  
    font=("Segoe UI", 10),
    bd=1,                        
    relief="solid"               
)
load_pokedex_menu.add_command(label="Open Database Credentials File", command=open_database_creds)
load_pokedex_menu.add_command(label="Enter Local Mode", command=enter_local_mode)
load_pokedex_menu.add_separator()
load_pokedex_menu.add_command(label="Open Pokedex JSON File", command=open_pokedex_file)
load_pokedex_menu.add_command(label="Save Pokedex Data", command=save_pokedex_data)
load_pokedex_menu.add_command(label="Clear Pokedex Data", command=clear_pokedex_data)
load_pokedex_menu.add_separator()
load_pokedex_menu.add_command(label="Cancel")


tracker_frame.bind("<Button-3>", show_tracker_menu)
tracker_frame.bind("<Button-2>", on_middle_click_empty)
tracker_container.bind("<Button-3>", show_tracker_menu)
tracker_container.bind("<Button-2>", on_middle_click_empty)
app.protocol("WM_DELETE_WINDOW", on_closing)


app.mainloop()