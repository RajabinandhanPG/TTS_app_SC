import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from tkinter import filedialog
import os
import io
from tkinter import Scale, DoubleVar, IntVar, BooleanVar, StringVar
import pygame
import datetime
import threading
import time
import asyncio
import edge_tts
import aiofiles
import tempfile
import re

class EdgeTTSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Edge TTS Client")
        self.root.geometry("900x650")
        self.root.resizable(True, True)
        
        # Set window icon if available
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
        
        # Create app directories
        self.app_dir = os.path.join(os.path.expanduser("~"), "EdgeTTS")
        self.audio_dir = os.path.join(self.app_dir, "audio_files")
        self.timestamp_dir = os.path.join(self.app_dir, "timestamps")
        self.ensure_directories()
        
        # Initialize favorites list
        self.favorite_voices = []
        
        # Load configuration
        self.load_app_config()
        
        # Load voice data asynchronously
        self.voices_loaded = False
        self.voice_data = {}
        self.voices_by_language = {}
        self.init_voice_data()
        
        # Load history
        self.audio_history = self.load_history()
        
        # Create the main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.tab_control = ttk.Notebook(self.main_frame)
        
        # TTS Tab
        self.tts_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.tts_tab, text="Text to Speech")
        
        # History Tab
        self.history_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.history_tab, text="History")
        
        # Settings Tab
        self.settings_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.settings_tab, text="Settings")
        
        # Voices Tab
        self.voices_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.voices_tab, text="Voice List")
        
        # Favorites Tab
        self.favorites_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.favorites_tab, text="Favorites")
        
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Initialize tabs
        self.init_tts_tab()
        self.init_history_tab()
        self.init_settings_tab()
        self.init_voices_tab()
        self.init_favorites_tab()
        
        # Initialize pygame (properly initialize without display)
        pygame.init()
        pygame.mixer.init()
        
        # Currently playing audio
        self.currently_playing = None
        self.is_paused = False
        
        # Timestamp data
        self.timestamp_data = None
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Loading voices...")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Set up an audio status checker 
        self.root.after(100, self.check_audio_status)
        
        # Set up cleanup on exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def load_app_config(self):
        """Load application configuration including favorites"""
        config_file = os.path.join(self.app_dir, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as file:
                    config = json.load(file)
                    if 'favorite_voices' in config:
                        self.favorite_voices = config['favorite_voices']
                    if 'audio_dir' in config:
                        self.audio_dir = config['audio_dir']
                    if 'timestamp_dir' in config:
                        self.timestamp_dir = config['timestamp_dir']
            except Exception as e:
                print(f"Error loading config: {str(e)}")
                self.favorite_voices = []
        else:
            self.favorite_voices = []
    
    def save_app_config(self):
        """Save application configuration including favorites"""
        config_file = os.path.join(self.app_dir, "config.json")
        try:
            # Load existing config if it exists
            config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as file:
                    config = json.load(file)
            
            # Update config with current values
            config['favorite_voices'] = self.favorite_voices
            config['audio_dir'] = self.audio_dir
            config['timestamp_dir'] = self.timestamp_dir
            
            # Save config
            with open(config_file, 'w') as file:
                json.dump(config, file, indent=4)
                
            return True
        except Exception as e:
            print(f"Error saving config: {str(e)}")
            return False
            
    def init_voice_data(self):
        """Initialize voice data from Edge TTS"""
        thread = threading.Thread(target=self.load_voice_data)
        thread.daemon = True
        thread.start()
    
    def load_voice_data(self):
        """Load voice data in a background thread"""
        try:
            # Run the async function to get voices
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            voices = loop.run_until_complete(self.get_edge_voices())
            
            # Process voices
            self.voices_by_language = {}
            for voice in voices:
                lang_code = voice["Locale"]
                gender = voice["Gender"]
                name = voice["ShortName"]
                display_name = voice["FriendlyName"]
                
                if lang_code not in self.voices_by_language:
                    self.voices_by_language[lang_code] = {"male": [], "female": [], "neutral": []}
                
                gender_key = gender.lower()
                if gender_key not in ["male", "female"]:
                    gender_key = "neutral"
                
                self.voices_by_language[lang_code][gender_key].append({
                    "name": name,
                    "display_name": display_name,
                    "gender": gender
                })
            
            # Create a list of language codes and friendly names
            self.language_options = []
            for lang_code in sorted(self.voices_by_language.keys()):
                # Get a friendly name for the language
                friendly_name = self.get_language_name(lang_code)
                self.language_options.append({
                    "code": lang_code,
                    "name": friendly_name
                })
            
            self.voices_loaded = True
            self.voice_data = voices
            
            # Update UI elements on the main thread
            self.root.after(0, self.update_ui_after_voice_loading)
        
        except Exception as e:
            print(f"Error loading voices: {str(e)}")
            error_message = str(e)
            self.root.after(0, lambda: self.status_var.set(f"Error loading voices: {error_message}"))
    
    async def get_edge_voices(self):
        """Get list of voices from Edge TTS"""
        try:
            voices = await edge_tts.list_voices()
            return voices
        except Exception as ex:
            print(f"Error retrieving voices: {str(ex)}")
            raise ex
    
    def get_language_name(self, lang_code):
        """Convert language code to friendly name"""
        # Map of language codes to friendly names
        language_names = {
            "ar-EG": "Arabic (Egypt)",
            "ar-SA": "Arabic (Saudi Arabia)",
            "bg-BG": "Bulgarian",
            "ca-ES": "Catalan",
            "cs-CZ": "Czech",
            "cy-GB": "Welsh",
            "da-DK": "Danish",
            "de-AT": "German (Austria)",
            "de-CH": "German (Switzerland)",
            "de-DE": "German (Germany)",
            "el-GR": "Greek",
            "en-AU": "English (Australia)",
            "en-CA": "English (Canada)",
            "en-GB": "English (UK)",
            "en-HK": "English (Hong Kong)",
            "en-IE": "English (Ireland)",
            "en-IN": "English (India)",
            "en-NZ": "English (New Zealand)",
            "en-PH": "English (Philippines)",
            "en-SG": "English (Singapore)",
            "en-US": "English (US)",
            "en-ZA": "English (South Africa)",
            "es-AR": "Spanish (Argentina)",
            "es-CL": "Spanish (Chile)",
            "es-CO": "Spanish (Colombia)",
            "es-ES": "Spanish (Spain)",
            "es-MX": "Spanish (Mexico)",
            "es-US": "Spanish (US)",
            "et-EE": "Estonian",
            "fi-FI": "Finnish",
            "fr-BE": "French (Belgium)",
            "fr-CA": "French (Canada)",
            "fr-CH": "French (Switzerland)",
            "fr-FR": "French (France)",
            "ga-IE": "Irish",
            "he-IL": "Hebrew",
            "hi-IN": "Hindi",
            "hr-HR": "Croatian",
            "hu-HU": "Hungarian",
            "id-ID": "Indonesian",
            "it-IT": "Italian",
            "ja-JP": "Japanese",
            "ko-KR": "Korean",
            "lt-LT": "Lithuanian",
            "lv-LV": "Latvian",
            "ms-MY": "Malay",
            "mt-MT": "Maltese",
            "nb-NO": "Norwegian",
            "nl-BE": "Dutch (Belgium)",
            "nl-NL": "Dutch (Netherlands)",
            "pl-PL": "Polish",
            "pt-BR": "Portuguese (Brazil)",
            "pt-PT": "Portuguese (Portugal)",
            "ro-RO": "Romanian",
            "ru-RU": "Russian",
            "sk-SK": "Slovak",
            "sl-SI": "Slovenian",
            "sv-SE": "Swedish",
            "ta-IN": "Tamil",
            "te-IN": "Telugu",
            "th-TH": "Thai",
            "tr-TR": "Turkish",
            "uk-UA": "Ukrainian",
            "ur-PK": "Urdu",
            "vi-VN": "Vietnamese",
            "zh-CN": "Chinese (Mainland)",
            "zh-HK": "Chinese (Hong Kong)",
            "zh-TW": "Chinese (Taiwan)"
        }
        
        if lang_code in language_names:
            return language_names[lang_code]
        return lang_code
    
    def update_ui_after_voice_loading(self):
        """Update UI elements after voice data is loaded"""
        self.status_var.set("Voices loaded successfully")
        
        # Update language dropdown
        if hasattr(self, 'language_combobox'):
            language_names = []
            for lang in self.language_options:
                language_names.append(f"{lang['name']} ({lang['code']})")
            
            self.language_combobox['values'] = language_names
            self.language_combobox.current(0)  # Set to first option
            
            # Update voice dropdown
            self.update_voice_selection()
        
        # Update voices listbox if available
        if hasattr(self, 'voices_tree'):
            self.populate_voices_listbox()
            
        # Update favorites tab
        if hasattr(self, 'favorites_tree'):
            self.populate_favorites_listbox()
            
        # Update favorites dropdown
        if hasattr(self, 'favorite_combobox'):
            self.update_favorites_dropdown()
        
    def on_close(self):
        """Clean up and close the application"""
        # Stop any playing audio
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            
        # Clean up temp files
        self.cleanup_temp_files()
            
        # Save config
        self.save_app_config()
            
        # Properly quit pygame
        pygame.quit()
        
        # Close the window
        self.root.destroy()
        
    def cleanup_temp_files(self):
        """Clean up any temporary audio files"""
        if hasattr(self, 'temp_audio_file') and self.temp_audio_file:
            if os.path.exists(self.temp_audio_file):
                try:
                    os.remove(self.temp_audio_file)
                except:
                    pass
    
    def check_audio_status(self):
        """Check if music is still playing and update UI accordingly"""
        # If music was playing but has stopped
        if hasattr(self, 'play_button') and not pygame.mixer.music.get_busy() and self.play_button.cget('text') == "⏸ Pause":
            # Reset the play button
            self.play_button.config(text="▶ Play")
            self.status_var.set("Ready")
        
        # Check history play button if applicable
        if hasattr(self, 'history_play_button') and self.currently_playing == "history" and not pygame.mixer.music.get_busy() and self.history_play_button.cget('text') == "⏸ Pause":
            self.history_play_button.config(text="▶ Play")
            self.status_var.set("Ready")
        
        # Schedule this to run again
        self.root.after(100, self.check_audio_status)
            
    def ensure_directories(self):
        """Ensure that necessary directories exist"""
        os.makedirs(self.app_dir, exist_ok=True)
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.timestamp_dir, exist_ok=True)
        os.makedirs(os.path.join(self.app_dir, "temp"), exist_ok=True)
        os.makedirs(os.path.join(self.app_dir, "srt"), exist_ok=True)
        
    def load_history(self):
        """Load audio file history from disk"""
        history_file = os.path.join(self.app_dir, "history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
        
    def save_history(self):
        """Save audio file history to disk"""
        history_file = os.path.join(self.app_dir, "history.json")
        try:
            with open(history_file, 'w') as f:
                json.dump(self.audio_history, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {str(e)}")
    
    def is_favorite(self, voice_name):
        """Check if a voice is in favorites"""
        return voice_name in self.favorite_voices
    
    def toggle_favorite(self, voice_name):
        """Add or remove a voice from favorites"""
        if self.is_favorite(voice_name):
            self.favorite_voices.remove(voice_name)
        else:
            self.favorite_voices.append(voice_name)
        
        # Update config
        self.save_app_config()
        
        # Update UI
        if hasattr(self, 'voices_tree'):
            self.filter_voices()
        
        if hasattr(self, 'favorites_tree'):
            self.populate_favorites_listbox()
            
        if hasattr(self, 'favorite_combobox'):
            self.update_favorites_dropdown()
    
    def update_favorites_dropdown(self):
        """Update the favorites dropdown in the TTS tab"""
        if not self.voices_loaded:
            return
            
        favorite_display_values = []
        favorite_values = []
        
        # Add an option to show all favorites
        favorite_display_values.append("--- Select Favorite Voice ---")
        favorite_values.append("")
        
        # Add favorites to the dropdown
        for voice in self.voice_data:
            if voice["ShortName"] in self.favorite_voices:
                favorite_display_values.append(f"{voice['FriendlyName']} ({voice['Locale']})")
                favorite_values.append(voice["ShortName"])
        
        # Update the dropdown
        self.favorite_combobox['values'] = favorite_display_values
        self.favorite_voice_values = favorite_values
        
        # If no favorites, disable the dropdown
        if len(favorite_values) <= 1:
            self.favorite_combobox.config(state="disabled")
        else:
            self.favorite_combobox.config(state="readonly")
            self.favorite_combobox.current(0)
            
    def init_tts_tab(self):
        """Initialize the Text-to-Speech tab"""
        tts_frame = ttk.Frame(self.tts_tab, padding="10")
        tts_frame.pack(fill=tk.BOTH, expand=True)
        
        # Text input section
        input_frame = ttk.LabelFrame(tts_frame, text="Text Input", padding="10")
        input_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.tts_text = scrolledtext.ScrolledText(input_frame, height=8)
        self.tts_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tts_text.insert(tk.END, "Type text to convert to speech here...")
        
        # Title for the audio file
        title_frame = ttk.Frame(input_frame)
        title_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(title_frame, text="Title:").pack(side=tk.LEFT, padx=5)
        self.title_var = tk.StringVar(value="New Audio")
        ttk.Entry(title_frame, textvariable=self.title_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # Voice selection and parameters
        param_frame = ttk.LabelFrame(tts_frame, text="Voice Parameters", padding="10")
        param_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Create a grid layout for parameters
        param_grid = ttk.Frame(param_frame)
        param_grid.pack(fill=tk.X, expand=True)
        
        # Favorites dropdown
        ttk.Label(param_grid, text="Favorites:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.favorite_combobox = ttk.Combobox(param_grid, width=30, state="disabled")
        self.favorite_combobox.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        self.favorite_voice_values = []
        
        # Bind the favorites selection to select the voice
        self.favorite_combobox.bind("<<ComboboxSelected>>", self.on_favorite_selected)
        
        # Language selection
        ttk.Label(param_grid, text="Language:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        
        # Create language combobox (will be populated later)
        self.language_var = tk.StringVar(value="en-US")
        self.language_combobox = ttk.Combobox(param_grid, textvariable=self.language_var, width=25)
        self.language_combobox.grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Bind the language selection to update voices
        self.language_combobox.bind("<<ComboboxSelected>>", lambda e: self.on_language_selected())
        
        # Gender selection
        ttk.Label(param_grid, text="Gender:").grid(column=0, row=2, sticky=tk.W, padx=5, pady=5)
        
        # Gender radio buttons
        self.gender_var = tk.StringVar(value="female")
        gender_frame = ttk.Frame(param_grid)
        gender_frame.grid(column=1, row=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Radiobutton(gender_frame, text="Female", variable=self.gender_var, 
                        value="female", command=lambda: self.update_voice_selection()).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(gender_frame, text="Male", variable=self.gender_var, 
                        value="male", command=lambda: self.update_voice_selection()).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(gender_frame, text="Neutral", variable=self.gender_var, 
                        value="neutral", command=lambda: self.update_voice_selection()).pack(side=tk.LEFT, padx=10)
        
        # Voice selection
        ttk.Label(param_grid, text="Voice:").grid(column=0, row=3, sticky=tk.W, padx=5, pady=5)
        
        voice_frame = ttk.Frame(param_grid)
        voice_frame.grid(column=1, row=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.voice_var = tk.StringVar()
        self.voice_combobox = ttk.Combobox(voice_frame, textvariable=self.voice_var, width=30)
        self.voice_combobox.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Add favorite/unfavorite button next to voice combobox
        self.voice_favorite_button = ttk.Button(voice_frame, text="★", width=3, 
                                             command=self.toggle_current_voice_favorite)
        self.voice_favorite_button.pack(side=tk.LEFT, padx=5)
        
        # Response format selection
        ttk.Label(param_grid, text="Format:").grid(column=2, row=0, sticky=tk.W, padx=5, pady=5)
        
        # Supported audio formats
        self.formats = ["mp3", "wav", "ogg", "webm"]
        self.format_var = tk.StringVar(value="mp3")
        format_combobox = ttk.Combobox(param_grid, textvariable=self.format_var)
        format_combobox['values'] = self.formats
        format_combobox.grid(column=3, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Rate (speed) selection with slider
        ttk.Label(param_grid, text="Speed:").grid(column=2, row=1, sticky=tk.W, padx=5, pady=5)
        
        speed_frame = ttk.Frame(param_grid)
        speed_frame.grid(column=3, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.speed_var = tk.StringVar(value="+0%")
        speed_label = ttk.Label(speed_frame, textvariable=self.speed_var, width=5)
        speed_label.pack(side=tk.RIGHT, padx=5)
        
        speed_slider = ttk.Scale(speed_frame, from_=-50, to=100, orient=tk.HORIZONTAL, 
                               command=self.update_speed_label)
        speed_slider.set(0)  # Default value
        speed_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Pitch selection with slider
        ttk.Label(param_grid, text="Pitch:").grid(column=2, row=2, sticky=tk.W, padx=5, pady=5)
        
        pitch_frame = ttk.Frame(param_grid)
        pitch_frame.grid(column=3, row=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.pitch_var = tk.StringVar(value="+0Hz")
        pitch_label = ttk.Label(pitch_frame, textvariable=self.pitch_var, width=5)
        pitch_label.pack(side=tk.RIGHT, padx=5)
        
        pitch_slider = ttk.Scale(pitch_frame, from_=-50, to=50, orient=tk.HORIZONTAL, 
                               command=self.update_pitch_label)
        pitch_slider.set(0)  # Default value
        pitch_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Volume selection with slider
        ttk.Label(param_grid, text="Volume:").grid(column=2, row=3, sticky=tk.W, padx=5, pady=5)
        
        volume_frame = ttk.Frame(param_grid)
        volume_frame.grid(column=3, row=3, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.volume_var = tk.StringVar(value="+0%")
        volume_label = ttk.Label(volume_frame, textvariable=self.volume_var, width=5)
        volume_label.pack(side=tk.RIGHT, padx=5)
        
        volume_slider = ttk.Scale(volume_frame, from_=-50, to=50, orient=tk.HORIZONTAL, 
                               command=self.update_volume_label)
        volume_slider.set(0)  # Default value
        volume_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Word timestamps checkbox
        timestamp_frame = ttk.Frame(param_grid)
        timestamp_frame.grid(column=0, row=4, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(timestamp_frame, text="Word Timestamps:").pack(side=tk.LEFT)
        
        self.timestamps_var = BooleanVar(value=True)
        timestamps_check = ttk.Checkbutton(timestamp_frame, variable=self.timestamps_var)
        timestamps_check.pack(side=tk.LEFT, padx=5)
        
        # Add info button for timestamps
        info_button = ttk.Button(timestamp_frame, text="ℹ️", width=2, command=self.show_timestamp_info)
        info_button.pack(side=tk.LEFT, padx=2)
        
        # SSML Mode checkbox
        ssml_frame = ttk.Frame(param_grid)
        ssml_frame.grid(column=2, row=4, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(ssml_frame, text="SSML Mode:").pack(side=tk.LEFT)
        
        self.ssml_var = BooleanVar(value=False)
        ssml_check = ttk.Checkbutton(ssml_frame, variable=self.ssml_var)
        ssml_check.pack(side=tk.LEFT, padx=5)
        
        # Add info button for SSML
        ssml_info_button = ttk.Button(ssml_frame, text="ℹ️", width=2, command=self.show_ssml_info)
        ssml_info_button.pack(side=tk.LEFT, padx=2)
        
        # Buttons frame
        button_frame = ttk.Frame(tts_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Generate speech button
        self.generate_button = ttk.Button(button_frame, text="Generate Speech", 
                                        command=self.generate_speech)
        self.generate_button.pack(side=tk.LEFT, padx=5)
        
        # Clear text button
        ttk.Button(button_frame, text="Clear Text", 
                command=self.clear_tts_text).pack(side=tk.LEFT, padx=5)
        
        # Insert SSML Sample button
        ttk.Button(button_frame, text="Insert SSML Sample", 
                command=self.insert_ssml_sample).pack(side=tk.LEFT, padx=5)
        
        # Playback controls
        playback_frame = ttk.LabelFrame(tts_frame, text="Preview", padding="10")
        playback_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Play/pause button (initially disabled)
        self.play_button = ttk.Button(playback_frame, text="▶ Play", 
                                    command=self.toggle_play_pause, state="disabled")
        self.play_button.pack(side=tk.LEFT, padx=5)
        
        # Save button (initially disabled)
        self.save_button = ttk.Button(playback_frame, text="💾 Save", 
                                    command=self.save_audio, state="disabled")
        self.save_button.pack(side=tk.LEFT, padx=5)
        
        # Add to history button (initially disabled)
        self.add_history_button = ttk.Button(playback_frame, text="Add to History", 
                                        command=self.add_to_history, state="disabled")
        self.add_history_button.pack(side=tk.LEFT, padx=5)
        
        # Add timestamp export buttons (initially disabled)
        self.export_timestamps_button = ttk.Button(playback_frame, text="Export Timestamps (JSON)", 
                                               command=self.export_timestamps, state="disabled")
        self.export_timestamps_button.pack(side=tk.LEFT, padx=5)
        
        self.export_srt_button = ttk.Button(playback_frame, text="Export as SRT", 
                                        command=self.export_srt, state="disabled")
        self.export_srt_button.pack(side=tk.LEFT, padx=5)
        
        # Now playing label
        self.now_playing_var = tk.StringVar(value="")
        ttk.Label(playback_frame, textvariable=self.now_playing_var, 
                font=("Helvetica", 9, "italic")).pack(side=tk.LEFT, padx=20)
        
        # Variable to store the audio data
        self.audio_data = None
        self.temp_audio_file = None
        self.timestamp_data = None
    
    def on_favorite_selected(self, event):
        """Handle selection from favorites dropdown"""
        index = self.favorite_combobox.current()
        if index <= 0 or index >= len(self.favorite_voice_values):
            return
            
        voice_name = self.favorite_voice_values[index]
        
        # Find the voice in the data
        for voice in self.voice_data:
            if voice["ShortName"] == voice_name:
                # Set language
                language_code = voice["Locale"]
                language_found = False
                for i, lang in enumerate(self.language_options):
                    if lang["code"] == language_code:
                        self.language_combobox.current(i)
                        self.language_var.set(language_code)
                        language_found = True
                        break
                
                # Set gender
                gender = voice["Gender"].lower()
                if gender not in ["male", "female"]:
                    gender = "neutral"
                self.gender_var.set(gender)
                
                # Update voice dropdown
                self.update_voice_selection()
                
                # Find and select the voice in the combobox
                for i, v in enumerate(self.voice_combobox['values']):
                    if voice["FriendlyName"] in v:
                        self.voice_combobox.current(i)
                        self.voice_var.set(voice_name)
                        break
                
                # Update favorite button
                self.update_favorite_button()
                
                break
    
    def update_favorite_button(self):
        """Update the favorite button based on current voice selection"""
        if not self.voice_var.get():
            return
            
        if self.is_favorite(self.voice_var.get()):
            self.voice_favorite_button.config(text="★", style="Favorite.TButton")
        else:
            self.voice_favorite_button.config(text="☆", style="")
    
    def toggle_current_voice_favorite(self):
        """Toggle favorite status of the currently selected voice"""
        voice_name = self.voice_var.get()
        if not voice_name:
            return
            
        self.toggle_favorite(voice_name)
        self.update_favorite_button()
    
    def update_speed_label(self, value):
        """Update the speed label when the slider changes"""
        # Convert to integer
        value = int(float(value))
        self.speed_var.set(f"{'+' if value >= 0 else ''}{value}%")
    
    def update_pitch_label(self, value):
        """Update the pitch label when the slider changes"""
        # Convert to integer
        value = int(float(value))
        self.pitch_var.set(f"{'+' if value >= 0 else ''}{value}Hz")
    
    def update_volume_label(self, value):
        """Update the volume label when the slider changes"""
        # Convert to integer
        value = int(float(value))
        self.volume_var.set(f"{'+' if value >= 0 else ''}{value}%")
    
    def show_timestamp_info(self):
        """Show information about word timestamps"""
        info_text = """Word Timestamps Feature:

When enabled, the system will generate timing data for each word in your audio.

This feature is useful for presentations, educational content, 
and accessibility purposes.

Note: 
1. Edge TTS provides accurate word-level timestamps
2. You can export timestamps as JSON or SRT subtitle format
3. Timestamps are automatically saved with history items"""

        messagebox.showinfo("Word Timestamps Information", info_text)
    
    def show_ssml_info(self):
        """Show information about SSML mode"""
        info_text = """SSML (Speech Synthesis Markup Language) Mode:

When enabled, your input text will be treated as SSML, allowing you to control:
- Pronunciation
- Pauses and breaks
- Emphasis
- Rate, pitch, and volume changes for specific parts
- Special characters and phonetic pronunciation

Example SSML:
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    Hello <break time="500ms"/> This is <emphasis level="strong">important</emphasis>.
    <prosody rate="+20%" pitch="+10Hz">This part is faster and higher pitched.</prosody>
</speak>

You can click "Insert SSML Sample" to see more examples."""

        messagebox.showinfo("SSML Mode Information", info_text)
    
    def insert_ssml_sample(self):
        """Insert an SSML sample into the text area"""
        ssml_sample = """<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
    <voice name="en-US-JennyNeural">
        Hello, I'm using <emphasis level="strong">SSML</emphasis> to control my speech.
        
        <break time="500ms"/>
        
        <prosody rate="+20%" pitch="+10Hz">
            This part is faster and higher pitched.
        </prosody>
        
        <break time="500ms"/>
        
        <prosody rate="-20%" pitch="-10Hz" volume="+20%">
            This part is slower, lower pitched, and louder.
        </prosody>
        
        <break time="500ms"/>
        
        Let me spell something: <say-as interpret-as="spell">Hello</say-as>
        
        <break time="500ms"/>
        
        The date <say-as interpret-as="date" format="mdy">12/31/2022</say-as> is New Year's Eve.
    </voice>
</speak>"""
        
        # Clear the text area and insert the sample
        self.tts_text.delete("1.0", tk.END)
        self.tts_text.insert(tk.END, ssml_sample)
        
        # Enable SSML mode
        self.ssml_var.set(True)
        
    def on_language_selected(self):
        """Handle language selection change"""
        # Get the selected index
        selected_index = self.language_combobox.current()
        
        # Get the corresponding language code
        if selected_index >= 0 and selected_index < len(self.language_options):
            selected_language = self.language_options[selected_index]["code"]
            self.language_var.set(selected_language)
        
        # Update the voice dropdown
        self.update_voice_selection()
        
    def update_voice_selection(self):
        """Update the voices in the dropdown based on selected language and gender"""
        if not self.voices_loaded:
            return
            
        # Get the current language code and gender
        language_code = self.language_var.get()
        gender = self.gender_var.get()
        
        # Get available voices for this language and gender
        if language_code in self.voices_by_language and gender in self.voices_by_language[language_code]:
            available_voices = self.voices_by_language[language_code][gender]
        else:
            available_voices = []
        
        # Create display values for the combobox
        voice_display_values = []
        voice_values = []
        
        for voice in available_voices:
            # Add star to favorite voices
            star = "★ " if self.is_favorite(voice["name"]) else ""
            voice_display_values.append(f"{star}{voice['display_name']}")
            voice_values.append(voice["name"])
        
        # Update the voice combobox values
        self.voice_combobox['values'] = voice_display_values
        self.voice_values = voice_values
        
        if voice_display_values:
            # If we have voices available, enable the dropdown
            self.voice_combobox.config(state="normal")
            self.generate_button.config(state="normal")
            
            # Select the first voice
            self.voice_combobox.current(0)
            self.voice_var.set(voice_values[0])
            
            # Update favorite button
            self.update_favorite_button()
        else:
            # No voices available for this language/gender combination
            self.voice_var.set("")
            self.voice_combobox.config(state="disabled")
            self.generate_button.config(state="disabled")
            
            messagebox.showinfo("No Voices Available", 
                            f"No {gender} voices available for the selected language. Please choose another gender or language.")
    
    def init_history_tab(self):
        """Initialize the history tab"""
        history_frame = ttk.Frame(self.history_tab, padding="10")
        history_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a frame for the history list
        list_frame = ttk.Frame(history_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollable listbox
        ttk.Label(list_frame, text="Generated Audio Files:").pack(anchor=tk.W, padx=5, pady=5)
        
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(list_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.history_listbox = tk.Listbox(list_container, height=15, 
                                        yscrollcommand=scrollbar.set, 
                                        font=("Helvetica", 10))
        self.history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_listbox.yview)
        
        # Bind selection event
        self.history_listbox.bind('<<ListboxSelect>>', self.on_history_select)
        
        # Details and controls frame
        details_frame = ttk.LabelFrame(history_frame, text="Audio Details", padding="10")
        details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Details fields
        ttk.Label(details_frame, text="Title:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.history_title_var = tk.StringVar()
        ttk.Label(details_frame, textvariable=self.history_title_var, font=("Helvetica", 10, "bold")).grid(
            column=1, row=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(details_frame, text="Voice:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.history_voice_var = tk.StringVar()
        ttk.Label(details_frame, textvariable=self.history_voice_var).grid(
            column=1, row=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(details_frame, text="Text:").grid(column=0, row=2, sticky=tk.NW, padx=5, pady=5)
        self.history_text = scrolledtext.ScrolledText(details_frame, height=5, width=30)
        self.history_text.grid(column=1, row=2, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        self.history_text.config(state="disabled")
        
        ttk.Label(details_frame, text="Created:").grid(column=0, row=3, sticky=tk.W, padx=5, pady=5)
        self.history_date_var = tk.StringVar()
        ttk.Label(details_frame, textvariable=self.history_date_var).grid(
            column=1, row=3, sticky=tk.W, padx=5, pady=5)
        
        # Timestamp indicator
        ttk.Label(details_frame, text="Timestamps:").grid(column=0, row=4, sticky=tk.W, padx=5, pady=5)
        self.history_timestamps_var = tk.StringVar(value="None")
        ttk.Label(details_frame, textvariable=self.history_timestamps_var).grid(
            column=1, row=4, sticky=tk.W, padx=5, pady=5)
        
        # Playback controls
        controls_frame = ttk.Frame(details_frame)
        controls_frame.grid(column=0, row=5, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=10)
        
        self.history_play_button = ttk.Button(controls_frame, text="▶ Play",
                                            command=self.play_history_item)
        self.history_play_button.pack(side=tk.LEFT, padx=5)
        self.history_play_button.config(state="disabled")
        
        self.history_delete_button = ttk.Button(controls_frame, text="🗑 Delete",
                                            command=self.delete_history_item)
        self.history_delete_button.pack(side=tk.LEFT, padx=5)
        self.history_delete_button.config(state="disabled")
        
        # Add timestamp export buttons for history items
        self.history_export_timestamps_button = ttk.Button(controls_frame, text="Export Timestamps",
                                                      command=self.export_history_timestamps)
        self.history_export_timestamps_button.pack(side=tk.LEFT, padx=5)
        self.history_export_timestamps_button.config(state="disabled")
        
        self.history_export_srt_button = ttk.Button(controls_frame, text="Export SRT",
                                               command=self.export_history_srt)
        self.history_export_srt_button.pack(side=tk.LEFT, padx=5)
        self.history_export_srt_button.config(state="disabled")
        
        # Add favorite button for history item
        self.history_favorite_button = ttk.Button(controls_frame, text="☆ Favorite Voice",
                                              command=self.favorite_history_voice)
        self.history_favorite_button.pack(side=tk.LEFT, padx=5)
        self.history_favorite_button.config(state="disabled")
        
        # Populate the history list
        self.populate_history_list()
    
    def favorite_history_voice(self):
        """Add the voice from the current history item to favorites"""
        if not hasattr(self, 'selected_history_index') or self.selected_history_index is None:
            return
            
        # Get the voice from the history entry
        entry = self.audio_history[self.selected_history_index]
        voice_name = entry.get('voice', '')
        
        if not voice_name:
            return
            
        # Add to favorites
        if not self.is_favorite(voice_name):
            self.toggle_favorite(voice_name)
            self.history_favorite_button.config(text="★ Unfavorite Voice")
            messagebox.showinfo("Voice Added to Favorites", 
                            f"Voice '{entry.get('voice_display', voice_name)}' has been added to favorites.")
        else:
            self.toggle_favorite(voice_name)
            self.history_favorite_button.config(text="☆ Favorite Voice")
            messagebox.showinfo("Voice Removed from Favorites", 
                            f"Voice '{entry.get('voice_display', voice_name)}' has been removed from favorites.")
    
    def init_settings_tab(self):
        """Initialize the settings tab"""
        settings_frame = ttk.Frame(self.settings_tab, padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Application settings
        app_frame = ttk.LabelFrame(settings_frame, text="Application Settings", padding="10")
        app_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Output directory
        ttk.Label(app_frame, text="Output Directory:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.output_dir_var = tk.StringVar(value=self.audio_dir)
        output_dir_entry = ttk.Entry(app_frame, width=50, textvariable=self.output_dir_var)
        output_dir_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Button(app_frame, text="Browse...", command=self.browse_output_dir).grid(
            column=2, row=0, padx=5, pady=5)
        
        # Timestamp directory
        ttk.Label(app_frame, text="Timestamp Directory:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.timestamp_dir_var = tk.StringVar(value=self.timestamp_dir)
        timestamp_dir_entry = ttk.Entry(app_frame, width=50, textvariable=self.timestamp_dir_var)
        timestamp_dir_entry.grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Button(app_frame, text="Browse...", command=self.browse_timestamp_dir).grid(
            column=2, row=1, padx=5, pady=5)
        
        # Default format
        ttk.Label(app_frame, text="Default Format:").grid(column=0, row=2, sticky=tk.W, padx=5, pady=5)
        self.default_format_var = tk.StringVar(value="mp3")
        default_format_combobox = ttk.Combobox(app_frame, textvariable=self.default_format_var)
        default_format_combobox['values'] = self.formats
        default_format_combobox.grid(column=1, row=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Save settings button
        ttk.Button(app_frame, text="Save Settings", command=self.save_settings).grid(
            column=1, row=3, sticky=tk.E, padx=5, pady=10)
        
        # Favorites management
        favorites_frame = ttk.LabelFrame(settings_frame, text="Favorites Management", padding="10")
        favorites_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Clear favorites button
        ttk.Button(favorites_frame, text="Clear All Favorites", command=self.clear_all_favorites).pack(
            side=tk.LEFT, padx=5, pady=5)
        
        # Config file section
        config_frame = ttk.LabelFrame(settings_frame, text="Configuration File", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(config_frame, text="Load Config", command=self.load_config).grid(
            column=0, row=0, padx=5, pady=5)
        ttk.Button(config_frame, text="Save Config", command=self.save_config).grid(
            column=1, row=0, padx=5, pady=5)
    
    def clear_all_favorites(self):
        """Clear all favorite voices"""
        if not self.favorite_voices:
            messagebox.showinfo("No Favorites", "You don't have any favorite voices to clear.")
            return
            
        confirm = messagebox.askyesno("Confirm Clear", 
                                    "Are you sure you want to clear all favorite voices?")
        if not confirm:
            return
            
        self.favorite_voices = []
        self.save_app_config()
        
        # Update UI
        if hasattr(self, 'voices_tree'):
            self.filter_voices()
        
        if hasattr(self, 'favorites_tree'):
            self.populate_favorites_listbox()
            
        if hasattr(self, 'favorite_combobox'):
            self.update_favorites_dropdown()
            
        messagebox.showinfo("Favorites Cleared", "All favorite voices have been cleared.")
    
    def init_voices_tab(self):
        """Initialize the voices tab with a list of all available voices"""
        voices_frame = ttk.Frame(self.voices_tab, padding="10")
        voices_frame.pack(fill=tk.BOTH, expand=True)
        
        # Filter controls
        filter_frame = ttk.Frame(voices_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side=tk.LEFT, padx=5)
        
        # Bind search entry to filter voices
        self.search_var.trace_add("write", lambda name, index, mode: self.filter_voices())
        
        # Filter by language
        ttk.Label(filter_frame, text="Language:").pack(side=tk.LEFT, padx=5)
        self.filter_language_var = tk.StringVar(value="All")
        
        # We'll populate this dropdown after loading voices
        self.filter_language_dropdown = ttk.Combobox(filter_frame, textvariable=self.filter_language_var, width=20)
        self.filter_language_dropdown.pack(side=tk.LEFT, padx=5)
        
        # Bind language filter to update voices
        self.filter_language_dropdown.bind("<<ComboboxSelected>>", lambda e: self.filter_voices())
        
        # Gender filter
        ttk.Label(filter_frame, text="Gender:").pack(side=tk.LEFT, padx=5)
        self.filter_gender_var = tk.StringVar(value="All")
        gender_filter = ttk.Combobox(filter_frame, textvariable=self.filter_gender_var, width=10)
        gender_filter['values'] = ["All", "Female", "Male", "Neutral"]
        gender_filter.current(0)
        gender_filter.pack(side=tk.LEFT, padx=5)
        
        # Bind gender filter to update voices
        gender_filter.bind("<<ComboboxSelected>>", lambda e: self.filter_voices())
        
        # Favorites only filter
        self.filter_favorites_var = tk.BooleanVar(value=False)
        favorites_check = ttk.Checkbutton(filter_frame, text="Show favorites only", variable=self.filter_favorites_var, 
                                      command=self.filter_voices)
        favorites_check.pack(side=tk.LEFT, padx=10)
        
        # Voice list with details
        list_frame = ttk.LabelFrame(voices_frame, text="Available Voices", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create treeview for voices
        voice_tree_frame = ttk.Frame(list_frame)
        voice_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollbars for treeview
        voice_vsb = ttk.Scrollbar(voice_tree_frame, orient="vertical")
        voice_hsb = ttk.Scrollbar(voice_tree_frame, orient="horizontal")
        
        # Create treeview with columns
        self.voices_tree = ttk.Treeview(voice_tree_frame, columns=("name", "gender", "language", "style", "favorite"), 
                                      show="headings", yscrollcommand=voice_vsb.set, xscrollcommand=voice_hsb.set)
        
        # Configure scrollbars
        voice_vsb.config(command=self.voices_tree.yview)
        voice_hsb.config(command=self.voices_tree.xview)
        
        # Configure treeview columns
        self.voices_tree.heading("name", text="Voice Name")
        self.voices_tree.heading("gender", text="Gender")
        self.voices_tree.heading("language", text="Language")
        self.voices_tree.heading("style", text="Voice Short Name")
        self.voices_tree.heading("favorite", text="Favorite")
        
        self.voices_tree.column("name", width=200)
        self.voices_tree.column("gender", width=80)
        self.voices_tree.column("language", width=150)
        self.voices_tree.column("style", width=150)
        self.voices_tree.column("favorite", width=60)
        
        # Pack treeview and scrollbars
        voice_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        voice_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.voices_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add double-click event to select voice
        self.voices_tree.bind("<Double-1>", self.select_voice_from_list)
        
        # Right-click context menu
        self.voices_tree.bind("<Button-3>", self.show_voice_context_menu)
        
        # Controls frame
        controls_frame = ttk.Frame(voices_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Voice detail frame
        detail_frame = ttk.LabelFrame(voices_frame, text="Voice Details", padding="10")
        detail_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Voice details grid
        detail_grid = ttk.Frame(detail_frame)
        detail_grid.pack(fill=tk.X, expand=True)
        
        ttk.Label(detail_grid, text="Name:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.detail_name_var = tk.StringVar()
        ttk.Label(detail_grid, textvariable=self.detail_name_var).grid(
            column=1, row=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(detail_grid, text="Short Name:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.detail_short_name_var = tk.StringVar()
        ttk.Label(detail_grid, textvariable=self.detail_short_name_var).grid(
            column=1, row=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(detail_grid, text="Gender:").grid(column=0, row=2, sticky=tk.W, padx=5, pady=5)
        self.detail_gender_var = tk.StringVar()
        ttk.Label(detail_grid, textvariable=self.detail_gender_var).grid(
            column=1, row=2, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(detail_grid, text="Language:").grid(column=0, row=3, sticky=tk.W, padx=5, pady=5)
        self.detail_language_var = tk.StringVar()
        ttk.Label(detail_grid, textvariable=self.detail_language_var).grid(
            column=1, row=3, sticky=tk.W, padx=5, pady=5)
        
        # Action buttons
        action_frame = ttk.Frame(detail_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Voice selection button
        ttk.Button(action_frame, text="Use This Voice", command=self.use_selected_voice).pack(
            side=tk.LEFT, padx=5, pady=5)
            
        # Toggle favorite button
        self.detail_favorite_button = ttk.Button(action_frame, text="☆ Add to Favorites", 
                                             command=self.toggle_detail_voice_favorite)
        self.detail_favorite_button.pack(side=tk.LEFT, padx=5, pady=5)
    
    def init_favorites_tab(self):
        """Initialize the favorites tab"""
        favorites_frame = ttk.Frame(self.favorites_tab, padding="10")
        favorites_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for favorites
        favorites_tree_frame = ttk.Frame(favorites_frame)
        favorites_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create scrollbars for treeview
        favorites_vsb = ttk.Scrollbar(favorites_tree_frame, orient="vertical")
        favorites_hsb = ttk.Scrollbar(favorites_tree_frame, orient="horizontal")
        
        # Create treeview with columns
        self.favorites_tree = ttk.Treeview(favorites_tree_frame, columns=("name", "gender", "language", "style"), 
                                         show="headings", yscrollcommand=favorites_vsb.set, xscrollcommand=favorites_hsb.set)
        
        # Configure scrollbars
        favorites_vsb.config(command=self.favorites_tree.yview)
        favorites_hsb.config(command=self.favorites_tree.xview)
        
        # Configure treeview columns
        self.favorites_tree.heading("name", text="Voice Name")
        self.favorites_tree.heading("gender", text="Gender")
        self.favorites_tree.heading("language", text="Language")
        self.favorites_tree.heading("style", text="Voice Short Name")
        
        self.favorites_tree.column("name", width=200)
        self.favorites_tree.column("gender", width=80)
        self.favorites_tree.column("language", width=150)
        self.favorites_tree.column("style", width=150)
        
        # Pack treeview and scrollbars
        favorites_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        favorites_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.favorites_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add double-click event to select voice
        self.favorites_tree.bind("<Double-1>", self.select_favorite_from_list)
        
        # Right-click context menu
        self.favorites_tree.bind("<Button-3>", self.show_favorite_context_menu)
        
        # Empty message
        self.favorites_empty_label = ttk.Label(favorites_frame, text="No favorite voices added yet. You can add favorites from the Voice List tab.", 
                                          font=("Helvetica", 10, "italic"))
    
    def populate_favorites_listbox(self):
        """Populate the favorites tab with favorite voices"""
        if not self.voices_loaded:
            return
            
        # Clear the treeview
        for i in self.favorites_tree.get_children():
            self.favorites_tree.delete(i)
            
        # If no favorites, show message
        if not self.favorite_voices:
            self.favorites_empty_label.pack(padx=20, pady=20)
            return
        else:
            self.favorites_empty_label.pack_forget()
            
        # Add favorites to the treeview
        for voice in self.voice_data:
            if voice["ShortName"] in self.favorite_voices:
                language_name = self.get_language_name(voice["Locale"])
                self.favorites_tree.insert("", "end", values=(
                    voice["FriendlyName"],
                    voice["Gender"],
                    f"{language_name} ({voice['Locale']})",
                    voice["ShortName"]
                ))
    
    def select_favorite_from_list(self, event):
        """Handle double-click on a favorite voice"""
        # Get the selected item
        selection = self.favorites_tree.selection()
        if not selection:
            return
            
        # Get the voice shortname
        item = self.favorites_tree.item(selection[0], "values")
        voice_name = item[3]  # ShortName
        
        # Find the voice in the data
        for voice in self.voice_data:
            if voice["ShortName"] == voice_name:
                # Set language
                language_code = voice["Locale"]
                language_found = False
                for i, lang in enumerate(self.language_options):
                    if lang["code"] == language_code:
                        self.language_combobox.current(i)
                        self.language_var.set(language_code)
                        language_found = True
                        break
                
                # Set gender
                gender = voice["Gender"].lower()
                if gender not in ["male", "female"]:
                    gender = "neutral"
                self.gender_var.set(gender)
                
                # Update voice dropdown
                self.update_voice_selection()
                
                # Find and select the voice in the combobox
                for i, v in enumerate(self.voice_combobox['values']):
                    if voice["FriendlyName"] in v:
                        self.voice_combobox.current(i)
                        self.voice_var.set(voice_name)
                        break
                
                # Update favorite button
                self.update_favorite_button()
                
                # Switch to TTS tab
                self.tab_control.select(0)
                
                break
    
    def show_favorite_context_menu(self, event):
        """Show context menu for favorite voice"""
        # Get the item under cursor
        item = self.favorites_tree.identify_row(event.y)
        if not item:
            return
            
        # Select the item
        self.favorites_tree.selection_set(item)
        
        # Create a menu
        menu = tk.Menu(self.favorites_tree, tearoff=0)
        menu.add_command(label="Use Voice", command=lambda: self.select_favorite_from_list(None))
        menu.add_command(label="Remove from Favorites", command=self.remove_selected_favorite)
        
        # Display the menu
        menu.post(event.x_root, event.y_root)
    
    def remove_selected_favorite(self):
        """Remove the selected voice from favorites"""
        # Get the selected item
        selection = self.favorites_tree.selection()
        if not selection:
            return
            
        # Get the voice shortname
        item = self.favorites_tree.item(selection[0], "values")
        voice_name = item[3]  # ShortName
        
        # Remove from favorites
        if voice_name in self.favorite_voices:
            self.favorite_voices.remove(voice_name)
            self.save_app_config()
            
            # Update UI
            self.populate_favorites_listbox()
            if hasattr(self, 'voices_tree'):
                self.filter_voices()
            if hasattr(self, 'favorite_combobox'):
                self.update_favorites_dropdown()
                
            messagebox.showinfo("Voice Removed", f"Voice '{item[0]}' has been removed from favorites.")
    
    def show_voice_context_menu(self, event):
        """Show context menu for voice in voice list"""
        # Get the item under cursor
        item = self.voices_tree.identify_row(event.y)
        if not item:
            return
            
        # Select the item
        self.voices_tree.selection_set(item)
        
        # Get the voice shortname
        voice_values = self.voices_tree.item(item, "values")
        voice_name = voice_values[3]  # ShortName
        
        # Create a menu
        menu = tk.Menu(self.voices_tree, tearoff=0)
        menu.add_command(label="Use Voice", command=lambda: self.select_voice_from_list(None))
        
        # Add or remove from favorites
        if self.is_favorite(voice_name):
            menu.add_command(label="Remove from Favorites", 
                          command=lambda: self.toggle_favorite_from_context(voice_name))
        else:
            menu.add_command(label="Add to Favorites", 
                          command=lambda: self.toggle_favorite_from_context(voice_name))
        
        # Display the menu
        menu.post(event.x_root, event.y_root)
    
    def toggle_favorite_from_context(self, voice_name):
        """Toggle favorite status from context menu"""
        self.toggle_favorite(voice_name)
        # Update the voice list to reflect the change
        self.filter_voices()
    
    def toggle_detail_voice_favorite(self):
        """Toggle favorite status of the voice in details panel"""
        voice_name = self.detail_short_name_var.get()
        if not voice_name:
            return
            
        if self.is_favorite(voice_name):
            self.toggle_favorite(voice_name)
            self.detail_favorite_button.config(text="☆ Add to Favorites")
        else:
            self.toggle_favorite(voice_name)
            self.detail_favorite_button.config(text="★ Remove from Favorites")
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.audio_dir
        )
        if directory:
            self.output_dir_var.set(directory)
            self.audio_dir = directory
            # Ensure the directory exists
            os.makedirs(self.audio_dir, exist_ok=True)
    
    def browse_timestamp_dir(self):
        """Browse for timestamp directory"""
        directory = filedialog.askdirectory(
            title="Select Timestamp Directory",
            initialdir=self.timestamp_dir
        )
        if directory:
            self.timestamp_dir_var.set(directory)
            self.timestamp_dir = directory
            # Ensure the directory exists
            os.makedirs(self.timestamp_dir, exist_ok=True)
    
    def save_settings(self):
        """Save application settings"""
        self.audio_dir = self.output_dir_var.get()
        self.timestamp_dir = self.timestamp_dir_var.get()
        
        # Ensure directories exist
        os.makedirs(self.audio_dir, exist_ok=True)
        os.makedirs(self.timestamp_dir, exist_ok=True)
        
        # Save to config file
        if self.save_app_config():
            messagebox.showinfo("Settings Saved", "Application settings have been updated.")
            self.status_var.set("Settings saved")
        else:
            messagebox.showerror("Error", "Failed to save settings.")
    
    def load_config(self):
        """Load configuration from a file"""
        file_path = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    config = json.load(file)
                    if 'favorite_voices' in config:
                        self.favorite_voices = config['favorite_voices']
                    if 'audio_dir' in config:
                        self.output_dir_var.set(config['audio_dir'])
                        self.audio_dir = config['audio_dir']
                    if 'timestamp_dir' in config:
                        self.timestamp_dir_var.set(config['timestamp_dir'])
                        self.timestamp_dir = config['timestamp_dir']
                    if 'default_format' in config:
                        self.default_format_var.set(config['default_format'])
                
                # Update UI
                if hasattr(self, 'voices_tree') and self.voices_loaded:
                    self.filter_voices()
                
                if hasattr(self, 'favorites_tree') and self.voices_loaded:
                    self.populate_favorites_listbox()
                    
                if hasattr(self, 'favorite_combobox') and self.voices_loaded:
                    self.update_favorites_dropdown()
                
                messagebox.showinfo("Config Loaded", "Configuration successfully loaded.")
                self.status_var.set(f"Config loaded from {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
    
    def save_config(self):
        """Save configuration to a file"""
        file_path = filedialog.asksaveasfilename(
            title="Save Configuration File",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                config = {
                    'favorite_voices': self.favorite_voices,
                    'audio_dir': self.output_dir_var.get(),
                    'timestamp_dir': self.timestamp_dir_var.get(),
                    'default_format': self.default_format_var.get()
                }
                with open(file_path, 'w') as file:
                    json.dump(config, file, indent=4)
                messagebox.showinfo("Config Saved", "Configuration successfully saved.")
                self.status_var.set(f"Config saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
    
    def populate_voices_listbox(self):
        """Populate the voices listbox with all available voices"""
        if not self.voices_loaded:
            return
            
        # Clear the treeview
        for i in self.voices_tree.get_children():
            self.voices_tree.delete(i)
            
        # Populate filter language dropdown
        languages = ["All"]
        for lang_code in sorted(self.voices_by_language.keys()):
            language_name = self.get_language_name(lang_code)
            languages.append(f"{language_name} ({lang_code})")
            
        self.filter_language_dropdown['values'] = languages
        self.filter_language_dropdown.current(0)
        
        # Add all voices to the treeview
        self.filter_voices()
    
    def filter_voices(self):
        """Filter the voices in the treeview based on search and filters"""
        if not self.voices_loaded:
            return
            
        # Get filter values
        search_text = self.search_var.get().lower()
        language_filter = self.filter_language_var.get()
        gender_filter = self.filter_gender_var.get()
        favorites_only = self.filter_favorites_var.get()
        
        # Clear the treeview
        for i in self.voices_tree.get_children():
            self.voices_tree.delete(i)
            
        # Parse language filter to get code
        language_code = None
        if language_filter != "All":
            match = re.search(r'\((.*?)\)$', language_filter)
            if match:
                language_code = match.group(1)
        
        # Add matching voices
        for voice in self.voice_data:
            # Check favorites filter
            if favorites_only and voice["ShortName"] not in self.favorite_voices:
                continue
                
            # Check language filter
            if language_code and voice["Locale"] != language_code:
                continue
                
            # Check gender filter
            if gender_filter != "All" and voice["Gender"].lower() != gender_filter.lower():
                continue
                
            # Check search text
            if (search_text and 
                search_text not in voice["FriendlyName"].lower() and
                search_text not in voice["ShortName"].lower() and
                search_text not in voice["Locale"].lower()):
                continue
                
            # Voice passed all filters, add to treeview
            language_name = self.get_language_name(voice["Locale"])
            is_favorite = "★" if voice["ShortName"] in self.favorite_voices else ""
            
            self.voices_tree.insert("", "end", values=(
                voice["FriendlyName"],
                voice["Gender"],
                f"{language_name} ({voice['Locale']})",
                voice["ShortName"],
                is_favorite
            ))
    
    def select_voice_from_list(self, event):
        """Handle double-click on a voice in the voices list"""
        # Get the selected item
        selection = self.voices_tree.selection()
        if not selection:
            return
            
        # Get the values for the selected item
        item = self.voices_tree.item(selection[0], "values")
        
        # Display voice details
        self.detail_name_var.set(item[0])
        self.detail_short_name_var.set(item[3])
        self.detail_gender_var.set(item[1])
        self.detail_language_var.set(item[2])
        
        # Update favorite button
        voice_name = item[3]
        if self.is_favorite(voice_name):
            self.detail_favorite_button.config(text="★ Remove from Favorites")
        else:
            self.detail_favorite_button.config(text="☆ Add to Favorites")
    
    def use_selected_voice(self):
        """Use the selected voice from the voices tab"""
        # Check if we have a selected voice
        if not self.detail_short_name_var.get():
            messagebox.showwarning("No Voice Selected", "Please select a voice from the list first.")
            return
            
        # Extract the language code from the language string
        language_text = self.detail_language_var.get()
        match = re.search(r'\((.*?)\)$', language_text)
        if not match:
            messagebox.showerror("Error", "Could not determine language code.")
            return
            
        language_code = match.group(1)
        
        # Find the voice in the language dropdown
        language_found = False
        for i, lang in enumerate(self.language_options):
            if lang["code"] == language_code:
                self.language_combobox.current(i)
                self.language_var.set(language_code)
                language_found = True
                break
                
        if not language_found:
            messagebox.showerror("Error", f"Language {language_code} not found in dropdown.")
            return
            
        # Set gender
        gender = self.detail_gender_var.get().lower()
        if gender not in ["male", "female"]:
            gender = "neutral"
        self.gender_var.set(gender)
        
        # Update voice dropdown
        self.update_voice_selection()
        
        # Set the voice
        voice_name = self.detail_short_name_var.get()
        # Need to find the index of this voice in the dropdown
        voice_index = -1
        for voice in self.voices_by_language[language_code][gender]:
            if voice["name"] == voice_name:
                for i, display_name in enumerate(self.voice_combobox['values']):
                    if voice["display_name"] in display_name:
                        self.voice_combobox.current(i)
                        self.voice_var.set(voice_name)
                        voice_index = i
                        break
                break
        
        if voice_index == -1:
            messagebox.showwarning("Warning", "Could not find exact voice in dropdown. Selected first available voice.")
        
        # Switch to TTS tab
        self.tab_control.select(0)
        
        # Update status
        self.status_var.set(f"Selected voice: {self.detail_name_var.get()}")
        
        # Update favorite button
        self.update_favorite_button()
    
    def clear_tts_text(self):
        """Clear the text input area"""
        self.tts_text.delete("1.0", tk.END)
    
    def toggle_play_pause(self):
        """Toggle between play and pause for the current audio"""
        if not self.temp_audio_file or not os.path.exists(self.temp_audio_file) or os.path.getsize(self.temp_audio_file) == 0:
            messagebox.showerror("Playback Error", "No valid audio file available")
            return
            
        try:
            if pygame.mixer.music.get_busy() and not self.is_paused:
                # Pause the currently playing audio
                pygame.mixer.music.pause()
                self.is_paused = True
                self.play_button.config(text="▶ Resume")
                self.status_var.set("Audio paused")
            else:
                # Either start playing or resume
                if self.is_paused:
                    pygame.mixer.music.unpause()
                    self.is_paused = False
                    self.play_button.config(text="⏸ Pause")
                    self.status_var.set("Playing audio...")
                else:
                    # Try using pygame
                    try:
                        pygame.mixer.music.load(self.temp_audio_file)
                        pygame.mixer.music.play()
                        self.play_button.config(text="⏸ Pause")
                        self.status_var.set("Playing audio...")
                    except Exception as e:
                        print(f"Pygame playback error: {str(e)}")
                        messagebox.showerror("Playback Error", 
                                        f"Error playing audio: {str(e)}\n\nTry downloading the file and playing in an external player.")
        except Exception as e:
            messagebox.showerror("Playback Error", f"Error playing audio: {str(e)}")
    
    def export_timestamps(self):
        """Export timestamp data as JSON file"""
        if not self.timestamp_data:
            messagebox.showwarning("Warning", "No timestamp data available.")
            return
        
        # Generate a safe filename
        safe_title = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in self.title_var.get()])
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        default_filename = f"{safe_title}_timestamps_{timestamp}.json"
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            title="Save Timestamp Data",
            defaultextension=".json",
            initialfile=default_filename,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    json.dump(self.timestamp_data, f, indent=2)
                messagebox.showinfo("Success", f"Timestamp data saved to:\n{file_path}")
                self.status_var.set(f"Timestamps saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save timestamp data: {str(e)}")
    
    def format_srt_time(self, seconds):
        """Format time in seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        seconds = seconds % 60
        milliseconds = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"
    
    def export_srt(self):
        """Export timestamp data as SRT subtitle file"""
        if not self.timestamp_data:
            messagebox.showwarning("Warning", "No timestamp data available.")
            return
        
        # Generate a safe filename
        safe_title = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in self.title_var.get()])
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        default_filename = f"{safe_title}_subtitles_{timestamp}.srt"
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            title="Save SRT Subtitles",
            defaultextension=".srt",
            initialfile=default_filename,
            filetypes=[("SRT files", "*.srt"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Convert to SRT
            srt_content = self.convert_timestamps_to_srt()
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
                
            messagebox.showinfo("Success", f"SRT subtitles saved to:\n{file_path}")
            self.status_var.set(f"SRT exported to {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate SRT file: {str(e)}")
    
    def convert_timestamps_to_srt(self):
        """Convert timestamp data to SRT format"""
        srt_lines = []
        index = 1
        
        # Group words into lines (max 10 words per line)
        current_line = []
        line_start = 0
        line_end = 0
        
        # Edge TTS format: list of dicts with 'text', 'offset', and 'duration'
        for word_data in self.timestamp_data:
            word = word_data.get('text', '').strip()
            if not word:
                continue
                
            offset_ms = word_data.get('offset', 0)
            duration_ms = word_data.get('duration', 500)
            
            # Convert ms to seconds
            offset_sec = offset_ms / 10000000  # Convert 100-nanosecond units to seconds
            duration_sec = duration_ms / 10000000
            
            # First word in line
            if not current_line:
                line_start = offset_sec
                
            # Add word to current line
            current_line.append(word)
            line_end = offset_sec + duration_sec
            
            # End of line condition (10 words or end of sentence punctuation)
            if len(current_line) >= 10 or word.endswith(('.', '!', '?', ':', ';')):
                # Add to SRT
                srt_lines.append(str(index))
                srt_lines.append(f"{self.format_srt_time(line_start)} --> {self.format_srt_time(line_end)}")
                srt_lines.append(" ".join(current_line))
                srt_lines.append("")  # Empty line
                
                index += 1
                current_line = []
        
        # Add any remaining words
        if current_line:
            srt_lines.append(str(index))
            srt_lines.append(f"{self.format_srt_time(line_start)} --> {self.format_srt_time(line_end)}")
            srt_lines.append(" ".join(current_line))
            srt_lines.append("")  # Empty line
        
        return "\n".join(srt_lines)
    
    def export_history_timestamps(self):
        """Export timestamps for the selected history item"""
        if not hasattr(self, 'selected_history_index') or self.selected_history_index is None:
            return
        
        # Get the history entry
        entry = self.audio_history[self.selected_history_index]
        
        # Check if it has timestamps
        if not entry.get('has_timestamps', False) or not entry.get('timestamp_file'):
            messagebox.showwarning("Warning", "No timestamp data available for this item.")
            return
        
        # Check if the timestamp file exists
        if not os.path.exists(entry['timestamp_file']):
            messagebox.showerror("Error", f"Timestamp file not found: {entry['timestamp_file']}")
            return
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            title="Save Timestamp Data",
            defaultextension=".json",
            initialfile=f"{entry['title']}_timestamps.json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                # Read the original timestamp file
                with open(entry['timestamp_file'], 'r') as src:
                    timestamp_data = json.load(src)
                
                # Write to the new location
                with open(file_path, 'w') as dest:
                    json.dump(timestamp_data, dest, indent=2)
                
                messagebox.showinfo("Success", f"Timestamp data saved to:\n{file_path}")
                self.status_var.set(f"Timestamps saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export timestamp data: {str(e)}")
    
    def export_history_srt(self):
        """Export SRT for the selected history item"""
        if not hasattr(self, 'selected_history_index') or self.selected_history_index is None:
            return
        
        # Get the history entry
        entry = self.audio_history[self.selected_history_index]
        
        # Check if it has timestamps
        if not entry.get('has_timestamps', False) or not entry.get('timestamp_file'):
            messagebox.showwarning("Warning", "No timestamp data available for this item.")
            return
        
        # Check if the timestamp file exists
        if not os.path.exists(entry['timestamp_file']):
            messagebox.showerror("Error", f"Timestamp file not found: {entry['timestamp_file']}")
            return
        
        # Ask for save location
        file_path = filedialog.asksaveasfilename(
            title="Save SRT Subtitles",
            defaultextension=".srt",
            initialfile=f"{entry['title']}_subtitles.srt",
            filetypes=[("SRT files", "*.srt"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
        
        try:
            # Load the timestamp data
            with open(entry['timestamp_file'], 'r') as f:
                self.timestamp_data = json.load(f)
            
            # Convert to SRT
            srt_content = self.convert_timestamps_to_srt()
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(srt_content)
            
            messagebox.showinfo("Success", f"SRT subtitles saved to:\n{file_path}")
            self.status_var.set(f"SRT exported to {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate SRT file: {str(e)}")
    
    def add_to_history(self):
        """Add current audio to history"""
        if not self.audio_data:
            return
            
        # Create a timestamp for unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        
        # Generate a safe filename
        safe_title = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in self.title_var.get()])
        
        # Create a filename
        filename = f"{safe_title}_{timestamp}.{self.format_var.get()}"
        file_path = os.path.join(self.audio_dir, filename)
        
        # Check for timestamp data
        timestamp_file = None
        if self.timestamp_data:
            timestamp_filename = f"{safe_title}_{timestamp}_timestamps.json"
            timestamp_file = os.path.join(self.timestamp_dir, timestamp_filename)
            
            # Save the timestamp data
            try:
                with open(timestamp_file, 'w') as f:
                    json.dump(self.timestamp_data, f, indent=2)
            except Exception as e:
                print(f"Error saving timestamp data: {str(e)}")
                timestamp_file = None
        
        # Save the audio file
        try:
            with open(file_path, 'wb') as file:
                file.write(self.audio_data)
                with open(file_path, 'wb') as file:
                    file.write(self.audio_data)
                
            # Create voice display name
            voice_display = "Unknown"
            if self.voices_loaded:
                for voice in self.voice_data:
                    if voice["ShortName"] == self.voice_var.get():
                        voice_display = voice["FriendlyName"]
                        break
            
            # Create history entry
            history_entry = {
                'title': self.title_var.get(),
                'filename': filename,
                'path': file_path,
                'text': self.tts_text.get("1.0", tk.END).strip(),
                'voice': self.voice_var.get(),
                'voice_display': voice_display,
                'language': self.language_var.get(),
                'format': self.format_var.get(),
                'rate': self.speed_var.get(),
                'pitch': self.pitch_var.get(),
                'volume': self.volume_var.get(),
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'has_timestamps': bool(timestamp_file),
                'timestamp_file': timestamp_file,
                'ssml': self.ssml_var.get()
            }
            
            # Add to history
            self.audio_history.append(history_entry)
            self.save_history()
            
            # Update the history list
            self.populate_history_list()
            
            # Show success message
            self.status_var.set(f"Added '{self.title_var.get()}' to history")
            messagebox.showinfo("Success", f"Added '{self.title_var.get()}' to history")
            
            # Switch to history tab
            self.tab_control.select(1)  # History tab
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add to history: {str(e)}")
    
    def populate_history_list(self):
        """Populate the history listbox with entries from history"""
        # Clear the listbox
        self.history_listbox.delete(0, tk.END)
        
        # Add entries to the listbox
        for i, entry in enumerate(self.audio_history):
            timestamp_icon = "🕒 " if entry.get('has_timestamps', False) else ""
            favorite_icon = "★ " if self.is_favorite(entry.get('voice', '')) else ""
            voice_display = entry.get('voice_display', entry.get('voice', 'Unknown'))
            self.history_listbox.insert(tk.END, f"{timestamp_icon}{favorite_icon}{entry['title']} ({voice_display})")
            
        # Disable buttons if no history
        if len(self.audio_history) == 0:
            self.history_play_button.config(state="disabled")
            self.history_delete_button.config(state="disabled")
            self.history_export_timestamps_button.config(state="disabled")
            self.history_export_srt_button.config(state="disabled")
            self.history_favorite_button.config(state="disabled")
    
    def on_history_select(self, event):
        """Handle selection from history list"""
        if not self.history_listbox.curselection():
            return
            
        # Get selected index
        index = self.history_listbox.curselection()[0]
        
        # Get the corresponding history entry
        entry = self.audio_history[index]
        
        # Update the details
        self.history_title_var.set(entry['title'])
        
        # Get language name from code
        language_name = self.get_language_name(entry['language'])
        
        # Format the voice info
        voice_display = entry.get('voice_display', entry.get('voice', 'Unknown'))
        self.history_voice_var.set(f"{voice_display} / {language_name}")
        self.history_date_var.set(entry['timestamp'])
        
        # Update timestamp info
        if entry.get('has_timestamps', False):
            self.history_timestamps_var.set("Available ✓")
            self.history_export_timestamps_button.config(state="normal")
            self.history_export_srt_button.config(state="normal")
        else:
            self.history_timestamps_var.set("None")
            self.history_export_timestamps_button.config(state="disabled")
            self.history_export_srt_button.config(state="disabled")
        
        # Update the text display
        self.history_text.config(state="normal")
        self.history_text.delete("1.0", tk.END)
        self.history_text.insert("1.0", entry['text'])
        self.history_text.config(state="disabled")
        
        # Enable the buttons
        self.history_play_button.config(state="normal")
        self.history_delete_button.config(state="normal")
        self.history_favorite_button.config(state="normal")
        
        # Update favorite button text
        voice = entry.get('voice', '')
        if self.is_favorite(voice):
            self.history_favorite_button.config(text="★ Unfavorite Voice")
        else:
            self.history_favorite_button.config(text="☆ Favorite Voice")
        
        # Store the currently selected index
        self.selected_history_index = index
    
    def play_history_item(self):
        """Play the currently selected history item"""
        if not hasattr(self, 'selected_history_index') or self.selected_history_index is None:
            return
            
        # Get the history entry
        entry = self.audio_history[self.selected_history_index]
        file_path = entry['path']
        
        # Check if the file exists
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"Audio file not found: {file_path}")
            return
            
        # Stop any currently playing audio
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            
        try:
            # Load and play the audio
            pygame.mixer.music.load(file_path)
            pygame.mixer.music.play()
            
            # Update the status
            self.status_var.set(f"Playing: {entry['title']}")
            
            # Update the history play button
            self.history_play_button.config(text="⏸ Pause")
            
            # Set currently playing
            self.currently_playing = "history"
            self.is_paused = False
            
        except Exception as e:
            messagebox.showerror("Playback Error", f"Error playing audio: {str(e)}")
    
    def delete_history_item(self):
        """Delete the currently selected history item"""
        if not hasattr(self, 'selected_history_index') or self.selected_history_index is None:
            return
            
        # Get the history entry
        entry = self.audio_history[self.selected_history_index]
        
        # Confirm deletion
        confirm = messagebox.askyesno("Confirm Delete", 
                                    f"Are you sure you want to delete '{entry['title']}'?")
        
        if not confirm:
            return
            
        # Stop playback if this file is playing
        if pygame.mixer.music.get_busy() and self.currently_playing == "history":
            pygame.mixer.music.stop()
            
        # Delete the audio file
        try:
            if os.path.exists(entry['path']):
                os.remove(entry['path'])
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not delete audio file: {str(e)}")
            
        # Delete timestamp file if it exists
        try:
            if entry.get('timestamp_file') and os.path.exists(entry['timestamp_file']):
                os.remove(entry['timestamp_file'])
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not delete timestamp file: {str(e)}")
            
        # Remove from history
        self.audio_history.pop(self.selected_history_index)
        self.save_history()
        
        # Update the list
        self.populate_history_list()
        
        # Clear the details
        self.history_title_var.set("")
        self.history_voice_var.set("")
        self.history_date_var.set("")
        self.history_timestamps_var.set("None")
        self.history_text.config(state="normal")
        self.history_text.delete("1.0", tk.END)
        self.history_text.config(state="disabled")
        
        # Disable buttons
        self.history_play_button.config(state="disabled")
        self.history_delete_button.config(state="disabled")
        self.history_export_timestamps_button.config(state="disabled")
        self.history_export_srt_button.config(state="disabled")
        self.history_favorite_button.config(state="disabled")
        
        # Reset selection
        self.selected_history_index = None
        
        # Update status
        self.status_var.set("Item deleted from history")
    
    def generate_speech(self):
        """Generate speech from the input text"""
        # Get the text to convert
        text = self.tts_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter some text to convert to speech.")
            return
        
        # Check if a voice is selected
        if not self.voice_var.get():
            messagebox.showwarning("Warning", "No voice selected. Please select a voice.")
            return
        
        # Check if text is too long
        if len(text) > 10000:
            messagebox.showwarning("Warning", "Text is too long. Please limit to 10000 characters.")
            return
        
        # Disable generate button
        self.generate_button.config(state="disabled")
        
        # Update status
        self.status_var.set("Generating speech...")
        
        # Start a thread for the Edge TTS generation
        thread = threading.Thread(target=self._generate_speech_thread, args=(text,))
        thread.daemon = True
        thread.start()
    
    def _generate_speech_thread(self, text):
        """Background thread for Edge TTS synthesis"""
        try:
            # Create a temporary file for the audio
            temp_dir = os.path.join(self.app_dir, "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # Create a unique temporary filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            temp_file = os.path.join(temp_dir, f"temp_{timestamp}.{self.format_var.get()}")
            
            # Create a temporary file for the timestamp data
            timestamp_file = os.path.join(temp_dir, f"temp_{timestamp}_timestamps.json")
            
            # Get voice parameters
            voice = self.voice_var.get()
            rate = self.speed_var.get().replace("%", "")
            pitch = self.pitch_var.get().replace("Hz", "")
            volume = self.volume_var.get().replace("%", "")
            
            # Create the communicate object
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Check if using SSML
            if self.ssml_var.get():
                # Use text as SSML directly
                loop.run_until_complete(self._generate_speech_with_edge_tts(voice, text, temp_file, timestamp_file, 
                                                                          rate, pitch, volume, True))
            else:
                # Add basic SSML wrapper around text
                loop.run_until_complete(self._generate_speech_with_edge_tts(voice, text, temp_file, timestamp_file, 
                                                                          rate, pitch, volume, False))
            
            # Read the audio file
            with open(temp_file, 'rb') as f:
                self.audio_data = f.read()
            
            # Read the timestamp file if it exists
            if os.path.exists(timestamp_file):
                with open(timestamp_file, 'r') as f:
                    self.timestamp_data = json.load(f)
                
                # Edge TTS timestamps are provided
                has_timestamps = True
            else:
                # No timestamps available
                self.timestamp_data = None
                has_timestamps = False
            
            # Set the temp audio file
            self.temp_audio_file = temp_file
            
            # Update the UI on the main thread
            self.root.after(0, self._update_ui_after_generation, True, None, has_timestamps)
            
        except Exception as e:
            # Handle any exceptions
            print(f"Exception in speech generation: {str(e)}")
            error_message = str(e)
            self.root.after(0, lambda: self._update_ui_after_generation(False, error_message))
    
    async def _generate_speech_with_edge_tts(self, voice, text, output_file, timestamp_file, rate="0", pitch="0", volume="0", is_ssml=False):
        """Generate speech using Edge TTS with minimal parameters"""
        try:
            # Create a communicate object with just the essential parameters
            if is_ssml:
                communicate = edge_tts.Communicate(text, voice=voice)
            else:
                communicate = edge_tts.Communicate(text, voice=voice)
            
            # Generate the audio with timestamps
            if self.timestamps_var.get():
                # Open the files for writing
                async with aiofiles.open(output_file, "wb") as file:
                    words_in_metadata = []
                    
                    # Process the speech data with timestamp extraction
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            await file.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            words_in_metadata.append(chunk)
                    
                    # Write timestamp data if we got any
                    if words_in_metadata:
                        async with aiofiles.open(timestamp_file, "w") as timestamp_output:
                            await timestamp_output.write(json.dumps(words_in_metadata))
            else:
                # Generate without timestamps
                async with aiofiles.open(output_file, "wb") as file:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            await file.write(chunk["data"])
        
        except Exception as e:
            print(f"Error in speech generation: {str(e)}")
            raise e
        
    def _update_ui_after_generation(self, success, error_message=None, has_timestamps=False):
        """Update the UI after speech generation"""
        # Re-enable generate button
        self.generate_button.config(state="normal")
        
        if success:
            # Enable playback controls
            self.play_button.config(state="normal")
            self.save_button.config(state="normal")
            self.add_history_button.config(state="normal")
            
            # Enable timestamp export buttons if timestamps are available
            if has_timestamps:
                self.export_timestamps_button.config(state="normal")
                self.export_srt_button.config(state="normal")
            else:
                self.export_timestamps_button.config(state="disabled")
                self.export_srt_button.config(state="disabled")
            
            # Update now playing label
            voice_display = "Unknown"
            if self.voices_loaded:
                for voice in self.voice_data:
                    if voice["ShortName"] == self.voice_var.get():
                        voice_display = voice["FriendlyName"]
                        break
            
            self.now_playing_var.set(f"{self.title_var.get()} - {voice_display}")
            
            # Update status
            timestamp_msg = " with timestamps" if has_timestamps else ""
            self.status_var.set(f"Speech generated successfully{timestamp_msg}")
            
            # Offer to play
            play_now = messagebox.askyesno("Success", f"Speech generated successfully{timestamp_msg}. Play now?")
            if play_now:
                self.toggle_play_pause()
        else:
            # Show error message
            messagebox.showerror("Error", f"Failed to generate speech: {error_message}")
            
            # Update status
            self.status_var.set("Speech generation failed")
    
    def save_audio(self):
        """Save the generated audio to a file"""
        if not self.audio_data:
            return
            
        # Ask for save location
        file_ext = self.format_var.get()
        filetypes = []
        
        if file_ext == "mp3":
            filetypes.append(("MP3 files", "*.mp3"))
        elif file_ext == "wav":
            filetypes.append(("WAV files", "*.wav"))
        elif file_ext == "ogg":
            filetypes.append(("OGG files", "*.ogg"))
        elif file_ext == "webm":
            filetypes.append(("WebM files", "*.webm"))
            
        filetypes.append(("All files", "*.*"))
        
        # Generate a safe filename for the default
        safe_title = "".join([c if c.isalnum() or c in [' ', '-', '_'] else '_' for c in self.title_var.get()])
        default_filename = f"{safe_title}.{file_ext}"
        
        file_path = filedialog.asksaveasfilename(
            title="Save Audio File",
            defaultextension=f".{file_ext}",
            initialfile=default_filename,
            filetypes=filetypes
        )
        
        if file_path:
            try:
                with open(file_path, 'wb') as file:
                    file.write(self.audio_data)
                
                # Ask to save timestamps if available
                if self.timestamp_data:
                    save_timestamps = messagebox.askyesno("Save Timestamps", 
                                                        "Would you also like to save the timestamp data?")
                    if save_timestamps:
                        timestamp_path = file_path + ".json"
                        with open(timestamp_path, 'w') as f:
                            json.dump(self.timestamp_data, f, indent=2)
                        messagebox.showinfo("Success", 
                                        f"Audio saved as: {file_path}\nTimestamps saved as: {timestamp_path}")
                    else:
                        messagebox.showinfo("Success", f"Audio saved as: {file_path}")
                else:
                    messagebox.showinfo("Success", f"Audio saved as: {file_path}")
                    
                self.status_var.set(f"Audio saved to {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save audio: {str(e)}")


# Initialize and run the application
if __name__ == "__main__":
    root = tk.Tk()
    
    # Create a style for favorite buttons
    style = ttk.Style()
    style.configure("Favorite.TButton", foreground="gold", background="gold")
    
    app = EdgeTTSApp(root)
    root.mainloop()
