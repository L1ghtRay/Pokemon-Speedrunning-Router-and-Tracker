import json
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageEnhance
import os
import sys
import firebase_admin
from firebase_admin import credentials
from firebase_admin import db

SQUARE_SIZE = 30

squares_cache = []
pokedex = {}
ref = None


def get_asset_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def on_closing():
    global firebase_listener
    print("Shutting down cleanly...")
    
    try:
        # If the listener exists, close the streaming connection
        if 'firebase_listener' in globals() and firebase_listener is not None:
            firebase_listener.close()
    except Exception as e:
        print(f"Error closing Firebase listener: {e}")
        
    # Destroy the Tkinter window completely
    app.destroy()
    
    # Forcefully exit the Python process to catch any remaining rogue threads
    os._exit(0)


def open_database_creds():
    global ref
    
    file_path = filedialog.askopenfilename(
        title="Select Database Credentials JSON File",
        filetypes=[("JSON Files", "*.json")]
    )

    database_url = ctk.CTkInputDialog(
        text="Enter Database URL:",
        title="Database URL Required"
    ).get_input()

    try:
        cred = credentials.Certificate(file_path)
        firebase_admin.initialize_app(cred, {
            "databaseURL": database_url
        })
        ref = db.reference("pokemon")

    except Exception as e:
        messagebox.showerror(title="Error", message=f"Database error: {e}")


def show_tracker_menu(event):
    load_pokedex_menu.post(event.x_root, event.y_root)


def printPokedex():
    if not pokedex:
        print(pokedex)
    for pokemon in pokedex.items():
        print(pokemon)


def clear_squares_data():
    global squares_cache
    
    for square in squares_cache:
        square.destroy()

    squares_cache = []

    # messagebox.showinfo(
    #     title="Success",
    #     message="Cleared Squares!"
    # )

    # printPokedex()


def clear_pokedex_data():
    global pokedex
    pokedex = {}

    clear_squares_data()

    tracker_container.pack_forget()

    # messagebox.showinfo(
    #     title="Success",
    #     message="Cleared Pokedex!"
    # )

    printPokedex()


def create_pokedex_boxes():
    if not pokedex: return

    # import sys
    # base = getattr(sys, '_MEIPASS', os.path.abspath('.'))
    # test_path = os.path.join(base, "sprites", "pokemon", "treecko.png")
    # print(f"MEIPASS base: {base}")
    # print(f"Test path exists: {os.path.exists(test_path)}")
    # print(f"Sprites folder exists: {os.path.exists(os.path.join(base, 'sprites'))}")

    clear_squares_data()
    tracker_container.pack(fill="both", expand=True, padx=5, pady=5)

    sorted_pokedex = sorted(pokedex.items(), key=lambda x: x[1].get('num', 0))

    for i, (pokemon_name, pokemon_info) in enumerate(sorted_pokedex, start=1):
        square = ctk.CTkFrame(
            tracker_container,
            fg_color=pokemon_info['color'],
            corner_radius=0,
            width=SQUARE_SIZE,
            height=SQUARE_SIZE
        )
        square.grid_propagate(False)
        square.pack_propagate(False)
        square.bind("<Button-3>", show_tracker_menu)
        square.bind("<Button-1>", toggle_caught)
        
        square.is_caught = pokemon_info.get('is_caught', False)
        square.pokemon_id = str(pokemon_name)

        image_path = None

        try:
            image_path = get_asset_path(os.path.join("sprites", "pokemon", f"{str(pokemon_name).lower()}.png"))
            raw_img = Image.open(image_path).convert("RGBA")

            # Generate bright vs darkened options natively
            enhancer = ImageEnhance.Brightness(raw_img)
            dark_raw_img = enhancer.enhance(0.3)

            img_size = SQUARE_SIZE - 4
            ctk_image = ctk.CTkImage(light_image=raw_img, dark_image=raw_img, size=(img_size, img_size))
            ctk_image_dark = ctk.CTkImage(light_image=dark_raw_img, dark_image=dark_raw_img, size=(img_size, img_size))

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
        
        squares_cache.append(square)

    sync_squares_to_ui()


def arrange_pokedex_boxes(event=None):
    if not pokedex: return

    def get_actual_size():
        scale = ctk.ScalingTracker.get_widget_scaling(app)
        return round(SQUARE_SIZE * scale)
    
    COLS = max(1, tracker_container._parent_frame.winfo_width() // (get_actual_size() + 2))

    current_col, current_row = 0, 0
    for square in squares_cache:
        square.grid(row=current_row, column=current_col, padx=1, pady=1, sticky="nsew")
        current_col += 1
        if current_col >= COLS:
            current_col = 0
            current_row += 1


def open_pokedex_file():
    global pokedex, firebase_listener

    if ref is None:
        messagebox.showerror(
            title="No Database",
            message="Please open Database Credentials first!"
        )
        return

    file_path = filedialog.askopenfilename(
        title="Select Pokedex JSON Data",
        filetypes=[("JSON Files", "*.json")]
    )

    if file_path:
        try:
            with open(file_path, 'r') as f:
                pokedex = json.load(f)
                for pokemon_name in pokedex.keys():
                        pokedex[pokemon_name]['is_caught'] = False

            # messagebox.showinfo(
            #     title="Success",
            #     message="Success!"
            # )

            db_data = ref.get()

            if not db_data:
                ref.update(pokedex)
            else:
                pokedex = db_data

            create_pokedex_boxes()
            arrange_pokedex_boxes()
            printPokedex()

            if firebase_listener is not None:
                firebase_listener.close()
                firebase_listener = None

            firebase_listener = ref.listen(on_firebase_update)

        except Exception as e:
            messagebox.showerror(
                title="Error",
                message=f"Error: {str(e)}"  # Show the real error!
            )


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
        
        try:
            ref.child(pokemon_id).update({"is_caught": new_caught_state})
        except Exception as e:
            print(f"Failed to transmit data to Firebase: {e}")


def sync_squares_to_ui():
    for square in squares_cache:
        pokemon_id = getattr(square, 'pokemon_id', None)
        if not pokemon_id or pokemon_id not in pokedex:
            continue

        # Cast to bool — Firebase can return 0/1 instead of False/True
        is_caught = bool(pokedex[pokemon_id].get('is_caught', False))

        print(pokemon_id, is_caught, square.is_caught)

        if is_caught:
            square.configure(fg_color="#494949")
        else:
            square.configure(fg_color=pokedex[pokemon_id]['color'])
        square.is_caught = is_caught


def on_firebase_update(event):
    global pokedex
    if event.data is None:
        return

    path_parts = [p for p in event.path.strip('/').split('/') if p]

    if len(path_parts) == 0:
        # Initial full snapshot: event.data = {full pokedex}
        if isinstance(event.data, dict):
            for pokemon_id, pokemon_data in event.data.items():
                if pokemon_id in pokedex and isinstance(pokemon_data, dict):
                    pokedex[pokemon_id].update(pokemon_data)

    elif len(path_parts) == 1:
        # Whole pokemon updated: event.path = '/Pikachu'
        pokemon_id = path_parts[0]
        if pokemon_id in pokedex and isinstance(event.data, dict):
            pokedex[pokemon_id].update(event.data)

    elif len(path_parts) == 2:
        # Single field updated: event.path = '/Pikachu/is_caught'
        pokemon_id, field = path_parts
        if pokemon_id in pokedex:
            pokedex[pokemon_id][field] = event.data

    app.after(0, sync_squares_to_ui)



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
load_pokedex_menu.add_command(label="Open Pokedex JSON File", command=open_pokedex_file)
load_pokedex_menu.add_command(label="Clear Pokedex Data", command=clear_pokedex_data)
load_pokedex_menu.add_separator()
load_pokedex_menu.add_command(label="Cancel")


tracker_frame.bind("<Button-3>", show_tracker_menu)
tracker_container.bind("<Button-3>", show_tracker_menu)
app.protocol("WM_DELETE_WINDOW", on_closing)


app.mainloop()