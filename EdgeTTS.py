import asyncio
import json
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import time
from typing import Dict, List, Optional, Tuple
import webbrowser

import edge_tts
from edge_tts import VoicesManager
import pygame
import pysrt

# Initialize pygame mixer for audio playback
pygame.mixer.init()

class EdgeTTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Edge TTS Application")
        self.root.geometry("900x700")
        
        # Try to set custom icon if available
        try:
            # For development
            if os.path.exists("app_icon.ico"):
                self.root.iconbitmap("app_icon.ico")
            # For PyInstaller
            elif hasattr(sys, '_MEIPASS'):
                icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
                if os.path.exists(icon_path):
                    self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not load icon: {e}")
        
        # Variables
        self.voices_data = {}  # Will store all voice data
        self.organized_voices = {}  # Organized by Language > Country > Gender > Name
        self.favorite_voices = []  # List of favorite voice IDs
        self.current_voice = tk.StringVar()
        self.pitch_value = tk.StringVar(value="0")
        self.rate_value = tk.StringVar(value="0")
        self.temp_audio_file = os.path.join(os.environ.get('TEMP', '.'), f"edge_tts_temp_{int(time.time())}.mp3")
        self.current_timestamps = []
        self.is_playing = False
        self.is_previewing = False  # Flag to track if preview is in progress
        self.preview_thread = None  # Track the preview thread
        self.favorites_file = "favorite_voices.json"
        
        # Load favorites if file exists
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r') as f:
                    self.favorite_voices = json.load(f)
            except:
                self.favorite_voices = []
        
        # Create tabs
        self.tab_control = ttk.Notebook(root)
        
        # Main tab
        self.main_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.main_tab, text="Text to Speech")
        
        # Voice list tab
        self.voice_list_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.voice_list_tab, text="Voice List")
        
        self.tab_control.pack(expand=1, fill="both")
        
        # Set up the main tab
        self.setup_main_tab()
        
        # Set up the voice list tab
        self.setup_voice_list_tab()
        
        # Load voices (async operation)
        threading.Thread(target=self.load_voices, daemon=True).start()

    def setup_main_tab(self):
        # Voice selection frame
        voice_frame = ttk.LabelFrame(self.main_tab, text="Voice Selection")
        voice_frame.pack(fill="x", padx=10, pady=5)
        
        # Voice selection dropdowns (will be populated later)
        self.language_var = tk.StringVar()
        self.country_var = tk.StringVar()
        self.gender_var = tk.StringVar()
        self.voice_var = tk.StringVar()
        
        # Create dropdowns
        ttk.Label(voice_frame, text="Language:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.language_dropdown = ttk.Combobox(voice_frame, textvariable=self.language_var, state="readonly", width=15)
        self.language_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        self.language_dropdown.bind("<<ComboboxSelected>>", self.on_language_selected)
        
        ttk.Label(voice_frame, text="Country:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.country_dropdown = ttk.Combobox(voice_frame, textvariable=self.country_var, state="readonly", width=15)
        self.country_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.country_dropdown.bind("<<ComboboxSelected>>", self.on_country_selected)
        
        ttk.Label(voice_frame, text="Gender:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.gender_dropdown = ttk.Combobox(voice_frame, textvariable=self.gender_var, state="readonly", width=15)
        self.gender_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.gender_dropdown.bind("<<ComboboxSelected>>", self.on_gender_selected)
        
        ttk.Label(voice_frame, text="Voice:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.voice_dropdown = ttk.Combobox(voice_frame, textvariable=self.voice_var, state="readonly", width=15)
        self.voice_dropdown.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        self.voice_dropdown.bind("<<ComboboxSelected>>", self.on_voice_selected)
        
        # Favorites dropdown
        ttk.Label(voice_frame, text="Favorites:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.favorites_var = tk.StringVar()
        self.favorites_dropdown = ttk.Combobox(voice_frame, textvariable=self.favorites_var, state="readonly", width=30)
        self.favorites_dropdown.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        self.favorites_dropdown.bind("<<ComboboxSelected>>", self.on_favorite_selected)
        
        # Add to favorites button
        self.fav_button = ttk.Button(voice_frame, text="Add to Favorites", command=self.add_to_favorites)
        self.fav_button.grid(row=2, column=3, padx=5, pady=5, sticky="w")
        
        # Remove from favorites button
        self.remove_fav_button = ttk.Button(voice_frame, text="Remove from Favorites", command=self.remove_from_favorites)
        self.remove_fav_button.grid(row=2, column=4, padx=5, pady=5, sticky="w")
        
        # Voice parameters frame
        params_frame = ttk.LabelFrame(self.main_tab, text="Voice Parameters (Not Supported in Current Version)")
        params_frame.pack(fill="x", padx=10, pady=5)
        
        # Pitch control
        ttk.Label(params_frame, text="Pitch:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        pitch_frame = ttk.Frame(params_frame)
        pitch_frame.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        self.pitch_entry = ttk.Entry(pitch_frame, textvariable=self.pitch_value, width=5)
        self.pitch_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(pitch_frame, text="Hz").pack(side=tk.LEFT)
        
        # Pitch presets
        ttk.Label(params_frame, text="Preset:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        
        pitch_presets = ["+0Hz", "+10Hz", "-10Hz", "+20Hz", "-20Hz"]
        self.pitch_preset_var = tk.StringVar()
        pitch_preset_dropdown = ttk.Combobox(params_frame, textvariable=self.pitch_preset_var, values=pitch_presets, width=8, state="readonly")
        pitch_preset_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        pitch_preset_dropdown.bind("<<ComboboxSelected>>", self.on_pitch_preset_selected)
        
        # Rate control
        ttk.Label(params_frame, text="Rate:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        rate_frame = ttk.Frame(params_frame)
        rate_frame.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        self.rate_entry = ttk.Entry(rate_frame, textvariable=self.rate_value, width=5)
        self.rate_entry.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(rate_frame, text="%").pack(side=tk.LEFT)
        
        # Rate presets
        ttk.Label(params_frame, text="Preset:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        
        rate_presets = ["+0%", "+10%", "-10%", "+20%", "-20%"]
        self.rate_preset_var = tk.StringVar()
        rate_preset_dropdown = ttk.Combobox(params_frame, textvariable=self.rate_preset_var, values=rate_presets, width=8, state="readonly")
        rate_preset_dropdown.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        rate_preset_dropdown.bind("<<ComboboxSelected>>", self.on_rate_preset_selected)
        
        # Add a note about the parameters
        ttk.Label(params_frame, text="Note: Pitch and Rate controls are not supported in the current Edge TTS version", 
                 foreground="red").grid(row=2, column=0, columnspan=5, padx=5, pady=5, sticky="w")
        
        # Text input frame
        text_frame = ttk.LabelFrame(self.main_tab, text="Text Input")
        text_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.text_input = ScrolledText(text_frame, wrap=tk.WORD, width=50, height=10)
        self.text_input.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Preview and export frame
        control_frame = ttk.Frame(self.main_tab)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Preview button
        self.preview_button = ttk.Button(control_frame, text="Preview", command=self.preview_speech)
        self.preview_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Play/Pause button
        self.play_pause_button = ttk.Button(control_frame, text="Pause", command=self.toggle_play_pause)
        self.play_pause_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.play_pause_button.config(state=tk.DISABLED)
        
        # Export frame
        export_frame = ttk.LabelFrame(self.main_tab, text="Export Options")
        export_frame.pack(fill="x", padx=10, pady=5)
        
        # Format selection
        ttk.Label(export_frame, text="Format:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        
        self.format_var = tk.StringVar(value="mp3")
        formats = ["mp3", "wav", "ogg", "webm"]
        format_dropdown = ttk.Combobox(export_frame, textvariable=self.format_var, values=formats, width=8, state="readonly")
        format_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Generate button
        self.generate_button = ttk.Button(export_frame, text="Generate and Save", command=self.generate_and_save)
        self.generate_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Timestamps options
        ttk.Label(export_frame, text="Timestamps:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        
        self.timestamps_var = tk.StringVar(value="json")
        timestamps_formats = ["json", "srt", "both"]
        timestamps_dropdown = ttk.Combobox(export_frame, textvariable=self.timestamps_var, values=timestamps_formats, width=8, state="readonly")
        timestamps_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.main_tab, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

    def setup_voice_list_tab(self):
        # Main container frame for the voice list tab
        main_frame = ttk.Frame(self.voice_list_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Filter frame at the top
        filter_frame = ttk.LabelFrame(main_frame, text="Filter Voices")
        filter_frame.pack(fill="x", padx=5, pady=5)
        
        # Search box
        ttk.Label(filter_frame, text="Search:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_voices)
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=25)
        search_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        # Filter by language
        ttk.Label(filter_frame, text="Language:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.filter_language_var = tk.StringVar()
        self.filter_language_dropdown = ttk.Combobox(filter_frame, textvariable=self.filter_language_var, width=15, state="readonly")
        self.filter_language_dropdown.grid(row=0, column=3, padx=5, pady=5, sticky="w")
        self.filter_language_dropdown.bind("<<ComboboxSelected>>", self.filter_voices)
        
        # Filter by gender
        ttk.Label(filter_frame, text="Gender:").grid(row=0, column=4, padx=5, pady=5, sticky="w")
        self.filter_gender_var = tk.StringVar()
        gender_values = ["", "Male", "Female", "Neutral"]
        self.filter_gender_dropdown = ttk.Combobox(filter_frame, textvariable=self.filter_gender_var, values=gender_values, width=10, state="readonly")
        self.filter_gender_dropdown.grid(row=0, column=5, padx=5, pady=5, sticky="w")
        self.filter_gender_dropdown.bind("<<ComboboxSelected>>", self.filter_voices)
        
        # Filter by favorites
        self.show_favorites_var = tk.BooleanVar()
        show_favorites_check = ttk.Checkbutton(filter_frame, text="Favorites Only", variable=self.show_favorites_var, command=self.filter_voices)
        show_favorites_check.grid(row=0, column=6, padx=5, pady=5, sticky="w")
        
        # Reset filters button
        reset_button = ttk.Button(filter_frame, text="Reset Filters", command=self.reset_filters)
        reset_button.grid(row=0, column=7, padx=5, pady=5, sticky="e")
        
        # Favorites buttons frame
        fav_buttons_frame = ttk.Frame(main_frame)
        fav_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        # Add to favorites button
        add_fav_button = ttk.Button(fav_buttons_frame, text="Add Selected to Favorites", command=self.add_selected_to_favorites)
        add_fav_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Remove from favorites button
        remove_fav_button = ttk.Button(fav_buttons_frame, text="Remove Selected from Favorites", command=self.remove_selected_from_favorites)
        remove_fav_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Preview voice button
        preview_button = ttk.Button(fav_buttons_frame, text="Preview Selected Voice", command=self.preview_selected_voice)
        preview_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Create a frame for the voice list
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create treeview for voice list
        columns = ("Voice", "Language", "Country", "Gender", "Full ID", "Favorite")
        self.voice_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Define headings
        for col in columns:
            self.voice_tree.heading(col, text=col)
            if col == "Full ID":
                self.voice_tree.column(col, width=250)
            elif col == "Favorite":
                self.voice_tree.column(col, width=70, anchor="center")
            else:
                self.voice_tree.column(col, width=100)
        
        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.voice_tree.yview)
        self.voice_tree.configure(yscrollcommand=y_scrollbar.set)
        
        x_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.voice_tree.xview)
        self.voice_tree.configure(xscrollcommand=x_scrollbar.set)
        
        # Pack the tree and scrollbars
        self.voice_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Add right-click menu to the tree
        self.tree_context_menu = tk.Menu(self.voice_tree, tearoff=0)
        self.tree_context_menu.add_command(label="Add to Favorites", command=self.add_selected_to_favorites)
        self.tree_context_menu.add_command(label="Remove from Favorites", command=self.remove_selected_from_favorites)
        self.tree_context_menu.add_separator()
        self.tree_context_menu.add_command(label="Preview Voice", command=self.preview_selected_voice)
        
        self.voice_tree.bind("<Button-3>", self.show_tree_context_menu)
        self.voice_tree.bind("<Double-1>", self.preview_selected_voice)

    def show_tree_context_menu(self, event):
        # Display context menu on right-click
        try:
            iid = self.voice_tree.identify_row(event.y)
            if iid:
                self.voice_tree.selection_set(iid)
                self.tree_context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.tree_context_menu.grab_release()

    def add_selected_to_favorites(self):
        selected = self.voice_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a voice first.")
            return
            
        # Handle multiple selections
        added_count = 0
        for item in selected:
            voice_id = self.voice_tree.item(item, "values")[-2]  # -2 because we now have Favorite column
            if voice_id not in self.favorite_voices:
                self.favorite_voices.append(voice_id)
                added_count += 1
                
        if added_count > 0:
            self.save_favorites()
            self.update_favorites_dropdown()
            # Refresh the voice list to show updated favorites
            self.filter_voices()
            messagebox.showinfo("Favorites Updated", f"{added_count} voice(s) added to favorites")

    def remove_selected_from_favorites(self):
        selected = self.voice_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select a voice first.")
            return
            
        # Handle multiple selections
        removed_count = 0
        for item in selected:
            voice_id = self.voice_tree.item(item, "values")[-2]  # -2 because we now have Favorite column
            if voice_id in self.favorite_voices:
                self.favorite_voices.remove(voice_id)
                removed_count += 1
                
        if removed_count > 0:
            self.save_favorites()
            self.update_favorites_dropdown()
            # Refresh the voice list to show updated favorites
            self.filter_voices()
            messagebox.showinfo("Favorites Updated", f"{removed_count} voice(s) removed from favorites")

    def preview_selected_voice(self, event=None):
        selected = self.voice_tree.selection()
        if selected:
            voice_id = self.voice_tree.item(selected[0], "values")[-1]
            self.current_voice.set(voice_id)
            
            # Set the dropdowns to match the selected voice
            self.select_voice_in_dropdowns(voice_id)
            
            # Preview the voice
            self.preview_speech()

    def select_voice_in_dropdowns(self, voice_id):
        # Find the voice in our organized voices structure and set the dropdowns
        for lang, countries in self.organized_voices.items():
            for country, genders in countries.items():
                for gender, voices in genders.items():
                    for voice_name, voice_data in voices.items():
                        if voice_data["full_id"] == voice_id:
                            # Set the dropdowns
                            self.language_var.set(lang)
                            self.on_language_selected()
                            self.country_var.set(country)
                            self.on_country_selected()
                            self.gender_var.set(gender)
                            self.on_gender_selected()
                            self.voice_var.set(voice_name)
                            self.on_voice_selected()
                            return

    async def get_voices(self):
        # Get all available voices
        # Use the current edge-tts API
        voices = await edge_tts.list_voices()
        return voices

    def load_voices(self):
        # This runs in a separate thread
        self.status_var.set("Loading voices...")
        
        # Create event loop in this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Get voices asynchronously
        voices = loop.run_until_complete(self.get_voices())
        
        # Process voices
        self.organize_voices(voices)
        
        # Update UI with voice data
        self.root.after(0, self.update_voice_ui)

    def organize_voices(self, voices):
        # Organize voices by Language > Country > Gender > Name
        self.voices_data = voices
        organized = {}
        
        for voice in voices:
            # Extract components from voice ID (e.g., "en-US-ChristopherNeural")
            parts = voice["ShortName"].split("-")
            
            if len(parts) >= 3:
                language_code = parts[0].lower()
                country_code = parts[1].upper()
                
                # Extract voice name and gender
                name_gender = parts[2]
                if "Neural" in name_gender:
                    name = name_gender.replace("Neural", "")
                else:
                    name = name_gender
                
                gender = voice.get("Gender", "Unknown")
                if gender == "Male":
                    gender_display = "Male"
                elif gender == "Female":
                    gender_display = "Female"
                else:
                    gender_display = "Neutral"
                
                # Get language name
                language_name = voice.get("Locale", language_code)
                
                # Initialize nested dictionaries if needed
                if language_name not in organized:
                    organized[language_name] = {}
                
                if country_code not in organized[language_name]:
                    organized[language_name][country_code] = {}
                
                if gender_display not in organized[language_name][country_code]:
                    organized[language_name][country_code][gender_display] = {}
                
                # Store voice info
                organized[language_name][country_code][gender_display][name] = {
                    "full_id": voice["ShortName"],
                    "gender": gender,
                    "voice_data": voice
                }
        
        self.organized_voices = organized

    def update_voice_ui(self):
        # Update language dropdown
        languages = sorted(self.organized_voices.keys())
        self.language_dropdown['values'] = languages
        
        if languages:
            self.language_var.set(languages[0])
            self.on_language_selected()
        
        # Update voice list tab
        self.update_voice_list()
        
        # Update favorites dropdown
        self.update_favorites_dropdown()
        
        self.status_var.set("Ready")

    def update_voice_list(self, filter_text="", filter_language="", filter_gender="", favorites_only=False):
        # Clear existing items
        for item in self.voice_tree.get_children():
            self.voice_tree.delete(item)
        
        # Add voices to the list based on filters
        for language, countries in self.organized_voices.items():
            # Apply language filter
            if filter_language and language != filter_language:
                continue
                
            for country, genders in countries.items():
                for gender, voices in genders.items():
                    # Apply gender filter
                    if filter_gender and gender != filter_gender:
                        continue
                        
                    for voice_name, voice_data in voices.items():
                        full_id = voice_data["full_id"]
                        
                        # Apply favorites filter
                        if favorites_only and full_id not in self.favorite_voices:
                            continue
                        
                        # Apply text search filter
                        if filter_text and filter_text.lower() not in voice_name.lower() and filter_text.lower() not in language.lower():
                            continue
                        
                        # Determine favorite status
                        is_favorite = "★" if full_id in self.favorite_voices else ""
                        
                        # Add to tree
                        self.voice_tree.insert("", tk.END, values=(voice_name, language, country, gender, full_id, is_favorite))
        
        # Update filter dropdowns if needed
        if not self.filter_language_dropdown['values']:
            self.update_filter_dropdowns()
    
    def update_filter_dropdowns(self):
        # Update language filter dropdown
        languages = sorted(self.organized_voices.keys())
        self.filter_language_dropdown['values'] = [""] + languages  # Empty option for "All"
    
    def filter_voices(self, *args):
        # Get filter values
        search_text = self.search_var.get()
        language = self.filter_language_var.get()
        gender = self.filter_gender_var.get()
        favorites_only = self.show_favorites_var.get()
        
        # Apply filters
        self.update_voice_list(search_text, language, gender, favorites_only)
    
    def reset_filters(self):
        # Clear all filters
        self.search_var.set("")
        self.filter_language_var.set("")
        self.filter_gender_var.set("")
        self.show_favorites_var.set(False)
        
        # Update the list
        self.update_voice_list()

    def update_favorites_dropdown(self):
        # Update the favorites dropdown
        favorite_display = []
        favorite_mapping = {}
        
        for voice_id in self.favorite_voices:
            # Find the voice name
            for language, countries in self.organized_voices.items():
                for country, genders in countries.items():
                    for gender, voices in genders.items():
                        for voice_name, voice_data in voices.items():
                            if voice_data["full_id"] == voice_id:
                                display = f"{voice_name} ({language}, {country}, {gender})"
                                favorite_display.append(display)
                                favorite_mapping[display] = voice_id
        
        self.favorites_dropdown['values'] = favorite_display
        self.favorites_display_to_id = favorite_mapping

    def on_language_selected(self, event=None):
        # Update country dropdown based on selected language
        language = self.language_var.get()
        
        if language and language in self.organized_voices:
            countries = sorted(self.organized_voices[language].keys())
            self.country_dropdown['values'] = countries
            
            if countries:
                self.country_var.set(countries[0])
                self.on_country_selected()
            else:
                self.country_dropdown['values'] = []
                self.country_var.set("")
                self.gender_dropdown['values'] = []
                self.gender_var.set("")
                self.voice_dropdown['values'] = []
                self.voice_var.set("")
        else:
            self.country_dropdown['values'] = []
            self.country_var.set("")
            self.gender_dropdown['values'] = []
            self.gender_var.set("")
            self.voice_dropdown['values'] = []
            self.voice_var.set("")

    def on_country_selected(self, event=None):
        # Update gender dropdown based on selected country
        language = self.language_var.get()
        country = self.country_var.get()
        
        if language and country and country in self.organized_voices.get(language, {}):
            genders = sorted(self.organized_voices[language][country].keys())
            self.gender_dropdown['values'] = genders
            
            if genders:
                self.gender_var.set(genders[0])
                self.on_gender_selected()
            else:
                self.gender_dropdown['values'] = []
                self.gender_var.set("")
                self.voice_dropdown['values'] = []
                self.voice_var.set("")
        else:
            self.gender_dropdown['values'] = []
            self.gender_var.set("")
            self.voice_dropdown['values'] = []
            self.voice_var.set("")

    def on_gender_selected(self, event=None):
        # Update voice dropdown based on selected gender
        language = self.language_var.get()
        country = self.country_var.get()
        gender = self.gender_var.get()
        
        if (language and country and gender and 
            gender in self.organized_voices.get(language, {}).get(country, {})):
            voices = sorted(self.organized_voices[language][country][gender].keys())
            self.voice_dropdown['values'] = voices
            
            if voices:
                self.voice_var.set(voices[0])
                self.on_voice_selected()
            else:
                self.voice_dropdown['values'] = []
                self.voice_var.set("")
        else:
            self.voice_dropdown['values'] = []
            self.voice_var.set("")

    def on_voice_selected(self, event=None):
        # Set the current voice based on the dropdown selections
        language = self.language_var.get()
        country = self.country_var.get()
        gender = self.gender_var.get()
        voice = self.voice_var.get()
        
        if (language and country and gender and voice and 
            voice in self.organized_voices.get(language, {}).get(country, {}).get(gender, {})):
            voice_id = self.organized_voices[language][country][gender][voice]["full_id"]
            self.current_voice.set(voice_id)

    def on_favorite_selected(self, event=None):
        # Set the current voice based on the selected favorite
        selected = self.favorites_var.get()
        
        if selected and selected in self.favorites_display_to_id:
            voice_id = self.favorites_display_to_id[selected]
            self.current_voice.set(voice_id)
            
            # Also set the dropdowns
            self.select_voice_in_dropdowns(voice_id)

    def on_pitch_preset_selected(self, event=None):
        # Update pitch entry based on selected preset
        preset = self.pitch_preset_var.get()
        if preset:
            # Extract the numeric value without the Hz
            value = preset.replace("Hz", "")
            self.pitch_value.set(value)

    def on_rate_preset_selected(self, event=None):
        # Update rate entry based on selected preset
        preset = self.rate_preset_var.get()
        if preset:
            # Extract the numeric value without the %
            value = preset.replace("%", "")
            self.rate_value.set(value)

    def add_to_favorites(self):
        # Add current voice to favorites
        voice_id = self.current_voice.get()
        self.add_voice_to_favorites(voice_id)

    def add_voice_to_favorites(self, voice_id):
        if voice_id and voice_id not in self.favorite_voices:
            self.favorite_voices.append(voice_id)
            self.save_favorites()
            self.update_favorites_dropdown()
            messagebox.showinfo("Favorite Added", f"Voice added to favorites")

    def remove_from_favorites(self):
        # Remove current voice from favorites
        voice_id = self.current_voice.get()
        if voice_id in self.favorite_voices:
            self.favorite_voices.remove(voice_id)
            self.save_favorites()
            self.update_favorites_dropdown()
            messagebox.showinfo("Favorite Removed", f"Voice removed from favorites")

    def save_favorites(self):
        # Save favorites to file
        with open(self.favorites_file, 'w') as f:
            json.dump(self.favorite_voices, f)

    def get_tts_options(self):
        # Get TTS options from UI
        options = ""
        
        # Add pitch if set
        pitch = self.pitch_value.get()
        if pitch and pitch != "0":
            options += f"--pitch={pitch}Hz "
        
        # Add rate if set
        rate = self.rate_value.get()
        if rate and rate != "0":
            options += f"--rate={rate}% "
        
        return options.strip()

    async def stream_speech(self, text, voice):
        """Generate speech with Edge TTS (streaming mode)"""
        try:
            # Get pitch and rate values
            pitch = self.pitch_value.get()
            rate = self.rate_value.get()
            
            # Create communicate object
            communicate = edge_tts.Communicate(text, voice)
            
            # Clear previous timestamps
            self.current_timestamps = []
            
            # Stream the audio chunks
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
                elif chunk["type"] == "WordBoundary":
                    self.current_timestamps.append(chunk)
                
        except Exception as e:
            print(f"Error in stream_speech: {e}")
            # If there's an error, we'll yield empty data
            yield b""

    async def save_speech(self, text, voice, output_file):
        """Generate speech with Edge TTS and save to file"""
        try:
            # Create communicate object with plain text
            communicate = edge_tts.Communicate(text, voice)
            
            # Collect timestamps
            timestamps = []
            
            # Process the stream
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    with open(output_file, "ab") as f:
                        f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    timestamps.append(chunk)
            
            return timestamps
                
        except Exception as e:
            print(f"Error in save_speech: {e}")
            return []

    def preview_speech(self):
        # Preview the selected voice
        voice_id = self.current_voice.get()
        text = self.text_input.get("1.0", tk.END).strip()
        
        if not voice_id:
            messagebox.showerror("Error", "Please select a voice first.")
            return
        
        if not text:
            messagebox.showerror("Error", "Please enter some text to speak.")
            return
            
        # Check if a preview is already in progress
        if self.is_previewing:
            # Cancel the current preview
            self.cancel_preview()
            
        # Generate a new temporary file name
        self.temp_audio_file = os.path.join(os.environ.get('TEMP', '.'), f"edge_tts_temp_{int(time.time())}.mp3")
            
        # Clear previous audio file if exists
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        
        self.is_playing = False
        self.play_pause_button.config(text="Pause", state=tk.DISABLED)
        
        # Set preview state
        self.is_previewing = True
        self.preview_button.config(state=tk.DISABLED)
        
        # Generate speech in a separate thread
        self.status_var.set("Generating speech preview...")
        self.preview_thread = threading.Thread(target=self._preview_thread, args=(voice_id, text), daemon=True)
        self.preview_thread.start()
        
    def cancel_preview(self):
        """Cancel any ongoing preview generation"""
        self.is_previewing = False
        # Stop any playing audio
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        self.is_playing = False
        self.play_pause_button.config(text="Play", state=tk.DISABLED)
        # The preview thread will terminate itself since it's a daemon thread
        self.preview_thread = None
        self.status_var.set("Preview cancelled")

    def _preview_thread(self, voice_id, text):
        # Run in a separate thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create the output directory if it doesn't exist
            temp_dir = os.path.dirname(self.temp_audio_file)
            if temp_dir and not os.path.exists(temp_dir):
                os.makedirs(temp_dir, exist_ok=True)
            
            # Generate the audio file
            with open(self.temp_audio_file, "wb") as f:
                pass  # Create empty file
            
            # Generate and write audio
            async def generate():
                try:
                    async for audio_chunk in self.stream_speech(text, voice_id):
                        # Check if preview was cancelled
                        if not self.is_previewing:
                            return
                            
                        with open(self.temp_audio_file, "ab") as f:
                            f.write(audio_chunk)
                except Exception as e:
                    # Handle any exceptions during generation
                    print(f"Error during speech generation: {e}")
                    self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
                    self.root.after(0, lambda: self.preview_button.config(state=tk.NORMAL))
                    self.is_previewing = False
                    return
            
            loop.run_until_complete(generate())
            
            # If preview was cancelled, don't play
            if not self.is_previewing:
                return
                
            # Small delay to ensure file is fully written
            time.sleep(0.1)
                
            # Play the audio using a method we know exists
            self.root.after(0, self._play_audio_preview)
            
        except Exception as e:
            # Handle any exceptions
            print(f"Error in preview thread: {e}")
            self.root.after(0, lambda: self.status_var.set(f"Error: {str(e)}"))
            self.root.after(0, lambda: self.preview_button.config(state=tk.NORMAL))
            self.is_previewing = False
        finally:
            # Clean up the event loop
            loop.close()

        def _play_audio_preview(self):
            """Play the generated preview audio file"""
        # Play the generated preview
        if os.path.exists(self.temp_audio_file) and os.path.getsize(self.temp_audio_file) > 0:
            try:
                pygame.mixer.music.load(self.temp_audio_file)
                pygame.mixer.music.play()
                self.is_playing = True
                self.play_pause_button.config(text="Pause", state=tk.NORMAL)
                self.status_var.set("Playing preview...")
                
                # Re-enable preview button
                self.preview_button.config(state=tk.NORMAL)
                
                # Monitor playback status
                threading.Thread(target=self._monitor_playback, daemon=True).start()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to play audio: {e}")
                self.status_var.set("Error playing preview")
                self.preview_button.config(state=tk.NORMAL)
                self.is_previewing = False
        else:
            self.status_var.set("No audio generated")
            self.preview_button.config(state=tk.NORMAL)
            self.is_previewing = False

    def _monitor_playback(self):
        # Monitor playback and update UI when done
        while pygame.mixer.music.get_busy() and self.is_playing:
            time.sleep(0.1)
        
        if not self.is_playing:
            return
        
        self.is_playing = False
        self.is_previewing = False  # Reset preview flag when playback ends
        self.root.after(0, lambda: self.play_pause_button.config(text="Play", state=tk.NORMAL))
        self.root.after(0, lambda: self.status_var.set("Preview complete"))

    def toggle_play_pause(self):
        # Toggle play/pause for preview
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.play_pause_button.config(text="Play")
            self.status_var.set("Preview paused")
        else:
            pygame.mixer.music.unpause()
            self.is_playing = True
            self.play_pause_button.config(text="Pause")
            self.status_var.set("Playing preview...")

    def generate_and_save(self):
        # Generate speech and save to file
        voice_id = self.current_voice.get()
        text = self.text_input.get("1.0", tk.END).strip()
        
        if not voice_id:
            messagebox.showerror("Error", "Please select a voice first.")
            return
        
        if not text:
            messagebox.showerror("Error", "Please enter some text to speak.")
            return
        
        # Get output format
        output_format = self.format_var.get()
        timestamps_format = self.timestamps_var.get()
        
        # Ask for output file location
        output_file = filedialog.asksaveasfilename(
            defaultextension=f".{output_format}",
            filetypes=[(f"{output_format.upper()} files", f"*.{output_format}")],
            title="Save Audio File"
        )
        
        if not output_file:
            return
        
        # Generate speech in a separate thread
        self.status_var.set("Generating speech...")
        threading.Thread(
            target=self._generate_thread, 
            args=(voice_id, text, output_file, timestamps_format),
            daemon=True
        ).start()

    def _generate_thread(self, voice_id, text, output_file, timestamps_format):
        # Run in a separate thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Generate the audio file
        timestamps = loop.run_until_complete(
            self.save_speech(text, voice_id, output_file)
        )
        
        # Save timestamps if requested
        if timestamps_format in ["json", "both"]:
            self._save_json_timestamps(timestamps, output_file)
        
        if timestamps_format in ["srt", "both"]:
            self._save_srt_timestamps(timestamps, output_file)
        
        # Update UI
        self.root.after(0, lambda: self.status_var.set(f"Speech saved to {output_file}"))
        self.root.after(0, lambda: messagebox.showinfo("Success", f"Speech saved to {output_file}"))

    def _save_json_timestamps(self, timestamps, output_file):
        # Save timestamps as JSON
        json_file = output_file.rsplit(".", 1)[0] + ".json"
        
        # Convert to per-word format
        formatted_timestamps = []
        for ts in timestamps:
            formatted_timestamps.append({
                "word": ts["text"],
                "start": ts["offset"] / 10000000,  # Convert to seconds
                "end": (ts["offset"] + ts["duration"]) / 10000000  # Convert to seconds
            })
        
        with open(json_file, "w") as f:
            json.dump(formatted_timestamps, f, indent=2)

    def _save_srt_timestamps(self, timestamps, output_file):
        # Save timestamps as SRT
        srt_file = output_file.rsplit(".", 1)[0] + ".srt"
        
        # Convert to SRT format (per word)
        srt_subs = pysrt.SubRipFile()
        
        for i, ts in enumerate(timestamps):
            start_time = ts["offset"] / 10000000  # Convert to seconds
            end_time = (ts["offset"] + ts["duration"]) / 10000000  # Convert to seconds
            
            # Create SRT subtitle
            item = pysrt.SubRipItem(
                index=i+1,
                start=pysrt.SubRipTime(seconds=start_time),
                end=pysrt.SubRipTime(seconds=end_time),
                text=ts["text"]
            )
            srt_subs.append(item)
        
        # Save SRT file
        srt_subs.save(srt_file, encoding='utf-8')


if __name__ == "__main__":
    root = tk.Tk()
    app = EdgeTTSApp(root)
    root.mainloop()