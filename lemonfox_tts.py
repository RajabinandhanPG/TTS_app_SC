import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
import json
from tkinter import filedialog
import os
import io
from tkinter import Scale, DoubleVar, BooleanVar
import pygame
import datetime
import threading
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class LemonFoxApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LemonFox TTS Client")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Initialize voice data
        self.init_voice_data()
        
        # API credentials and settings
        self.api_key = ""
        self.base_url = "https://api.lemonfox.ai/" 
        self.timeout = 60  # Default timeout in seconds
        self.proxies = None
        
        # Create app directories
        self.app_dir = os.path.join(os.path.expanduser("~"), "LemonFoxTTS")
        self.audio_dir = os.path.join(self.app_dir, "audio_files")
        self.ensure_directories()
        
        # Load history
        self.audio_history = self.load_history()
        # Auto-load config if exists
        config_file = os.path.join(self.app_dir, "config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as file:
                    config = json.load(file)
                    if 'api_key' in config:
                        self.api_key = config['api_key']
                        self.api_key_var.set(config['api_key'])
            except:
                pass
        
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
        self.tab_control.add(self.settings_tab, text="API Settings")
        
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # Initialize tabs
        self.init_tts_tab()
        self.init_history_tab()
        self.init_settings_tab()
        
        # Initialize pygame (properly initialize without display)
        pygame.init()
        pygame.mixer.init()
        
        # Currently playing audio
        self.currently_playing = None
        self.is_paused = False
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Set up an audio status checker 
        self.root.after(100, self.check_audio_status)
        
        # Set up cleanup on exit
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        
    def init_voice_data(self):
        """Initialize the voice and language data structure with gender information"""
        # Create a dictionary of voices organized by language code and gender
        self.voices_by_language_gender = {
            "en-us": {
                "female": ["heart", "bella", "aoede", "kore", "jessica", "nicole", "nova", "river", "sarah", "sky", "echo"],
                "male": ["michael", "alloy", "eric", "fenrir", "adam", "santa", "liam", "onyx", "puck"]
            },
            "en-gb": {
                "female": ["alice", "emma", "isabella", "lily"],
                "male": ["fable", "george", "lewis", "daniel"]
            },
            "es": {
                "female": ["dora"],
                "male": ["alex", "noel"]
            },
            "fr": {
                "female": ["siwis"],
                "male": []
            },
            "hi": {
                "female": ["alpha", "beta"],
                "male": ["omega", "psi"]
            },
            "it": {
                "female": ["sara"],
                "male": ["nicola"]
            },
            "ja": {
                "female": ["sakura", "gongitsune", "nezumi", "tebukuro"],
                "male": ["kumo"]
            },
            "pt-br": {
                "female": ["clara"],
                "male": ["tiago", "papai"]
            },
            "zh": {
                "female": ["xiaobei", "xiaoni", "xiaoxiao", "xiaoyi", "yunxia", "yunyang"],
                "male": ["yunjian", "yunxi"]
            }
        }
        
        # Create a list of language codes and friendly names
        self.language_options = [
            {"code": "en-us", "name": "English (American)"},
            {"code": "en-gb", "name": "English (British)"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "hi", "name": "Hindi"},
            {"code": "it", "name": "Italian"},
            {"code": "ja", "name": "Japanese"},
            {"code": "pt-br", "name": "Portuguese (Brazil)"},
            {"code": "zh", "name": "Mandarin Chinese"}
        ]
        
        # Default gender
        self.gender_options = ["female", "male"]
        
    def on_close(self):
        """Clean up and close the application"""
        # Stop any playing audio
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            
        # Clean up temp files
        self.cleanup_temp_files()
            
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
            
    def init_tts_tab(self):
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
        
        # Language selection
        ttk.Label(param_grid, text="Language:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        
        # Prepare language dropdown values
        language_values = []
        language_names = []
        for lang in self.language_options:
            language_values.append(lang["code"])
            language_names.append(f"{lang['name']} ({lang['code']})")
        
        # Create language combobox
        self.language_var = tk.StringVar(value="en-us")
        self.language_combobox = ttk.Combobox(param_grid, textvariable=self.language_var, width=25)
        self.language_combobox['values'] = language_names
        self.language_combobox.current(0)  # Set to first option
        self.language_combobox.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Bind the language selection to update voices
        self.language_combobox.bind("<<ComboboxSelected>>", lambda e: self.on_language_selected())
        
        # Gender selection
        ttk.Label(param_grid, text="Gender:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        
        # Gender radio buttons
        self.gender_var = tk.StringVar(value="female")
        gender_frame = ttk.Frame(param_grid)
        gender_frame.grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        ttk.Radiobutton(gender_frame, text="Female", variable=self.gender_var, 
                        value="female", command=lambda: self.update_voice_selection(True)).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(gender_frame, text="Male", variable=self.gender_var, 
                        value="male", command=lambda: self.update_voice_selection(True)).pack(side=tk.LEFT, padx=10)
        
        # Voice selection
        ttk.Label(param_grid, text="Voice:").grid(column=0, row=2, sticky=tk.W, padx=5, pady=5)
        # Set a default voice value right away
        self.voice_var = tk.StringVar(value="heart")
        self.voice_combobox = ttk.Combobox(param_grid, textvariable=self.voice_var, width=25)
        self.voice_combobox.grid(column=1, row=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Response format selection
        ttk.Label(param_grid, text="Format:").grid(column=2, row=0, sticky=tk.W, padx=5, pady=5)
        
        # Supported audio formats
        self.formats = ["mp3", "wav", "ogg", "flac"]
        self.format_var = tk.StringVar(value="mp3")
        format_combobox = ttk.Combobox(param_grid, textvariable=self.format_var)
        format_combobox['values'] = self.formats
        format_combobox.grid(column=3, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Speed selection
        ttk.Label(param_grid, text="Speed:").grid(column=2, row=1, sticky=tk.W, padx=5, pady=5)
        
        # Speed options
        self.speed_var = DoubleVar(value=1.0)
        speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 3.0, 4.0]
        speed_combobox = ttk.Combobox(param_grid, textvariable=self.speed_var, width=10)
        speed_combobox['values'] = speeds
        speed_combobox.grid(column=3, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Word timestamps checkbox
        ttk.Label(param_grid, text="Word Timestamps:").grid(column=2, row=2, sticky=tk.W, padx=5, pady=5)
        
        self.timestamps_var = BooleanVar(value=False)
        timestamps_check = ttk.Checkbutton(param_grid, variable=self.timestamps_var)
        timestamps_check.grid(column=3, row=2, sticky=tk.W, padx=5, pady=5)
        
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
        
        # Now playing label
        self.now_playing_var = tk.StringVar(value="")
        ttk.Label(playback_frame, textvariable=self.now_playing_var, 
                 font=("Helvetica", 9, "italic")).pack(side=tk.LEFT, padx=20)
        
        # Variable to store the audio data
        self.audio_data = None
        self.temp_audio_file = None
        
        # Initialize the voice dropdown with voices for the default language and gender
        self.update_voice_selection(show_message=False)
        
    def on_language_selected(self):
        """Handle language selection change"""
        # Get the selected index
        selected_index = self.language_combobox.current()
        
        # Get the corresponding language code
        if selected_index >= 0 and selected_index < len(self.language_options):
            selected_language = self.language_options[selected_index]["code"]
            self.language_var.set(selected_language)
        
        # Update the voice dropdown with message (since this is user-initiated)
        self.update_voice_selection(show_message=True)
        
    def update_voice_selection(self, show_message=True):
        """Update the voices in the dropdown based on selected language and gender"""
        # Get the current language code and gender
        language_code = self.language_var.get()
        gender = self.gender_var.get()
        
        # Get available voices for this language and gender
        available_voices = self.voices_by_language_gender.get(language_code, {}).get(gender, [])
        
        # Update the voice combobox values
        self.voice_combobox['values'] = available_voices
        
        if available_voices:
            # If we have voices available, enable the dropdown
            self.voice_combobox.config(state="normal")
            self.generate_button.config(state="normal")
            
            # If current voice isn't in the list or is empty, select the first available voice
            if not self.voice_var.get() or self.voice_var.get() not in available_voices:
                self.voice_var.set(available_voices[0])
        else:
            # No voices available for this language/gender combination
            self.voice_var.set("")
            self.voice_combobox.config(state="disabled")
            self.generate_button.config(state="disabled")
            
            if show_message:
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
        
        # Playback controls
        controls_frame = ttk.Frame(details_frame)
        controls_frame.grid(column=0, row=4, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=10)
        
        self.history_play_button = ttk.Button(controls_frame, text="▶ Play",
                                            command=self.play_history_item)
        self.history_play_button.pack(side=tk.LEFT, padx=5)
        self.history_play_button.config(state="disabled")
        
        self.history_delete_button = ttk.Button(controls_frame, text="🗑 Delete",
                                              command=self.delete_history_item)
        self.history_delete_button.pack(side=tk.LEFT, padx=5)
        self.history_delete_button.config(state="disabled")
        
        # Populate the history list
        self.populate_history_list()
        
    def init_settings_tab(self):
        # Create a frame for API settings
        settings_frame = ttk.LabelFrame(self.settings_tab, text="API Connection Settings", padding="10")
        settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # API Key entry
        ttk.Label(settings_frame, text="API Key:").grid(column=0, row=0, sticky=tk.W, padx=5, pady=5)
        self.api_key_var = tk.StringVar()
        self.api_key_entry = ttk.Entry(settings_frame, width=50, textvariable=self.api_key_var, show="*")
        self.api_key_entry.grid(column=1, row=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Toggle to show/hide API key
        self.show_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, text="Show API Key", variable=self.show_key_var, 
                       command=self.toggle_api_key_visibility).grid(column=2, row=0, padx=5, pady=5)
        
        # API Base URL
        ttk.Label(settings_frame, text="API Base URL:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.base_url_var = tk.StringVar(value="https://api.lemonfox.ai/")
        self.base_url_entry = ttk.Entry(settings_frame, width=50, textvariable=self.base_url_var)
        self.base_url_entry.grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Connection timeout
        ttk.Label(settings_frame, text="Timeout (seconds):").grid(column=0, row=2, sticky=tk.W, padx=5, pady=5)
        self.timeout_var = tk.StringVar(value="60")
        timeout_entry = ttk.Entry(settings_frame, width=10, textvariable=self.timeout_var)
        timeout_entry.grid(column=1, row=2, sticky=tk.W, padx=5, pady=5)
        
        # Proxy settings
        proxy_frame = ttk.LabelFrame(self.settings_tab, text="Proxy Settings (Optional)", padding="10")
        proxy_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Enable proxy checkbox
        self.use_proxy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(proxy_frame, text="Use Proxy", variable=self.use_proxy_var, 
                       command=self.toggle_proxy_settings).grid(column=0, row=0, padx=5, pady=5)
        
        # Proxy URL
        ttk.Label(proxy_frame, text="Proxy URL:").grid(column=0, row=1, sticky=tk.W, padx=5, pady=5)
        self.proxy_url_var = tk.StringVar()
        self.proxy_url_entry = ttk.Entry(proxy_frame, width=50, textvariable=self.proxy_url_var, state="disabled")
        self.proxy_url_entry.grid(column=1, row=1, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Save settings button
        ttk.Button(settings_frame, text="Save Settings", command=self.save_settings).grid(
            column=1, row=3, sticky=tk.E, padx=5, pady=10)
        
        # Load/Save Config File
        config_frame = ttk.LabelFrame(self.settings_tab, text="Configuration File", padding="10")
        config_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(config_frame, text="Load Config", command=self.load_config).grid(
            column=0, row=0, padx=5, pady=5)
        ttk.Button(config_frame, text="Save Config", command=self.save_config).grid(
            column=1, row=0, padx=5, pady=5)
        
        # Testing connection
        test_frame = ttk.Frame(self.settings_tab, padding="10")
        test_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(test_frame, text="Test Connection", command=self.test_connection).pack(padx=5, pady=5)
            
    def toggle_proxy_settings(self):
        if self.use_proxy_var.get():
            self.proxy_url_entry.config(state="normal")
        else:
            self.proxy_url_entry.config(state="disabled")
            
    def test_connection(self):
        """Test the connection to the API"""
        if not self.api_key:
            messagebox.showwarning("Warning", "Please enter an API key first.")
            return
            
        # Make sure the URL is correct
        base_url = self.base_url_var.get()
        if not base_url.endswith('/'):
            base_url += '/'
            
        # Just try to hit a simple endpoint
        url = f"{base_url}v1/models"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        proxies = None
        if self.use_proxy_var.get() and self.proxy_url_var.get():
            proxies = {
                "http": self.proxy_url_var.get(),
                "https": self.proxy_url_var.get()
            }
        
        self.status_var.set("Testing connection...")
        
        try:
            # Use a session with a longer timeout
            session = requests.Session()
            timeout = int(self.timeout_var.get())
            
            response = session.get(url, headers=headers, proxies=proxies, timeout=timeout)
            
            if response.status_code == 200:
                messagebox.showinfo("Connection Successful", 
                                  f"Successfully connected to {base_url}\n\nResponse: {response.text[:100]}...")
                self.status_var.set("Connection test successful")
            else:
                messagebox.showerror("Connection Failed", 
                                   f"Failed to connect. Status code: {response.status_code}\n\nResponse: {response.text}")
                self.status_var.set(f"Connection test failed: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Connection Error", f"Error connecting to API: {str(e)}")
            self.status_var.set("Connection test failed: Error")
            
    def toggle_api_key_visibility(self):
        if self.show_key_var.get():
            self.api_key_entry.config(show="")
        else:
            self.api_key_entry.config(show="*")

    def save_settings(self):
        self.api_key = self.api_key_var.get()
        self.base_url = self.base_url_var.get()
        self.timeout = int(self.timeout_var.get())
        
        # Set up proxy if enabled
        if self.use_proxy_var.get() and self.proxy_url_var.get():
            self.proxies = {
                "http": self.proxy_url_var.get(),
                "https": self.proxy_url_var.get()
            }
        else:
            self.proxies = None
            
        # Auto-save config
        config_file = os.path.join(self.app_dir, "config.json")
        try:
            config = {
                'api_key': self.api_key_var.get(),
                'base_url': self.base_url_var.get(),
                'timeout': int(self.timeout_var.get()),
                'use_proxy': self.use_proxy_var.get(),
                'proxy_url': self.proxy_url_var.get()
            }
            with open(config_file, 'w') as file:
                json.dump(config, file, indent=4)
        except:
            pass
            
        messagebox.showinfo("Settings Saved", "API settings have been updated.")
        self.status_var.set("Settings saved")
    def load_config(self):
        file_path = filedialog.askopenfilename(
            title="Select Configuration File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    config = json.load(file)
                    if 'api_key' in config:
                        self.api_key_var.set(config['api_key'])
                    if 'base_url' in config:
                        self.base_url_var.set(config['base_url'])
                    if 'timeout' in config:
                        self.timeout_var.set(str(config['timeout']))
                    if 'use_proxy' in config:
                        self.use_proxy_var.set(config['use_proxy'])
                        self.toggle_proxy_settings()
                    if 'proxy_url' in config:
                        self.proxy_url_var.set(config['proxy_url'])
                messagebox.showinfo("Config Loaded", "Configuration successfully loaded.")
                self.status_var.set(f"Config loaded from {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")

    def save_config(self):
        file_path = filedialog.asksaveasfilename(
            title="Save Configuration File",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                config = {
                    'api_key': self.api_key_var.get(),
                    'base_url': self.base_url_var.get(),
                    'timeout': int(self.timeout_var.get()),
                    'use_proxy': self.use_proxy_var.get(),
                    'proxy_url': self.proxy_url_var.get()
                }
                with open(file_path, 'w') as file:
                    json.dump(config, file, indent=4)
                messagebox.showinfo("Config Saved", "Configuration successfully saved.")
                self.status_var.set(f"Config saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")
                
    def clear_tts_text(self):
        """Clear the text input area"""
        self.tts_text.delete("1.0", tk.END)
        
    def toggle_play_pause(self):
        """Toggle between play and pause for the current audio"""
        if not self.temp_audio_file or not os.path.exists(self.temp_audio_file):
            return
            
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
                pygame.mixer.music.load(self.temp_audio_file)
                pygame.mixer.music.play()
                self.play_button.config(text="⏸ Pause")
                self.status_var.set("Playing audio...")
                
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
        
        # Save the audio file
        try:
            with open(file_path, 'wb') as file:
                file.write(self.audio_data)
                
            # Create history entry
            history_entry = {
                'title': self.title_var.get(),
                'filename': filename,
                'path': file_path,
                'text': self.tts_text.get("1.0", tk.END).strip(),
                'voice': self.voice_var.get(),
                'language': self.language_var.get(),
                'gender': self.gender_var.get(),
                'format': self.format_var.get(),
                'speed': float(self.speed_var.get()),
                'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
            gender_icon = "👩" if entry.get('gender', '') == 'female' else "👨"
            self.history_listbox.insert(tk.END, f"{entry['title']} ({gender_icon} {entry['voice']})")
            
        # Disable buttons if no history
        if len(self.audio_history) == 0:
            self.history_play_button.config(state="disabled")
            self.history_delete_button.config(state="disabled")
            
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
        language_name = next((lang["name"] for lang in self.language_options 
                             if lang["code"] == entry['language']), entry['language'])
        
        # Format the voice info with gender
        gender = entry.get('gender', 'Unknown')
        gender_icon = "👩" if gender == 'female' else "👨" if gender == 'male' else "⚪"
        
        self.history_voice_var.set(f"{gender_icon} {entry['voice']} / {language_name} / {entry['speed']}x")
        self.history_date_var.set(entry['timestamp'])
        
        # Update the text display
        self.history_text.config(state="normal")
        self.history_text.delete("1.0", tk.END)
        self.history_text.insert("1.0", entry['text'])
        self.history_text.config(state="disabled")
        
        # Enable the buttons
        self.history_play_button.config(state="normal")
        self.history_delete_button.config(state="normal")
        
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
            
        # Delete the file
        try:
            if os.path.exists(entry['path']):
                os.remove(entry['path'])
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not delete file: {str(e)}")
            
        # Remove from history
        self.audio_history.pop(self.selected_history_index)
        self.save_history()
        
        # Update the list
        self.populate_history_list()
        
        # Clear the details
        self.history_title_var.set("")
        self.history_voice_var.set("")
        self.history_date_var.set("")
        self.history_text.config(state="normal")
        self.history_text.delete("1.0", tk.END)
        self.history_text.config(state="disabled")
        
        # Disable buttons
        self.history_play_button.config(state="disabled")
        self.history_delete_button.config(state="disabled")
        
        # Reset selection
        self.selected_history_index = None
        
        # Update status
        self.status_var.set("Item deleted from history")
            
    def generate_speech(self):
        """Generate speech from the input text"""
        # Check if API key is set
        if not self.api_key:
            messagebox.showwarning("Warning", "Please set your API key in Settings tab.")
            self.tab_control.select(2)  # Switch to settings tab
            return
            
        # Get the text to convert
        text = self.tts_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Warning", "Please enter some text to convert to speech.")
            return
            
        # Check if text is too long (some APIs have limits)
        if len(text) > 5000:
            messagebox.showwarning("Warning", "Text is too long. Please limit to 5000 characters.")
            return
            
        # Check if a voice is selected
        if not self.voice_var.get():
            messagebox.showwarning("Warning", "No voice selected. Please select a voice.")
            return
            
        # Disable generate button
        self.generate_button.config(state="disabled")
        
        # Update status
        self.status_var.set("Generating speech...")
        
        # Start a thread for the API request
        thread = threading.Thread(target=self._generate_speech_thread, args=(text,))
        thread.daemon = True
        thread.start()
        
    def _generate_speech_thread(self, text):
        """Background thread for API communication"""
        try:
            # Set up the API endpoint
            base_url = self.base_url
            if not base_url.endswith('/'):
                base_url += '/'
                
            url = f"{base_url}v1/audio/speech"
            
            # Set up the headers
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Set up the request data
            data = {
                "input": text,
                "voice": self.voice_var.get(),
                "language": self.language_var.get(),
                "response_format": self.format_var.get(),
                "speed": float(self.speed_var.get())
            }
            
            # Add word timestamps if enabled
            if self.timestamps_var.get():
                data["word_timestamps"] = True
                
            # Set up retry strategy
            retry_strategy = Retry(
                total=3,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504]
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            
            with requests.Session() as session:
                session.mount("http://", adapter)
                session.mount("https://", adapter)
                
                # Make the API request
                timeout = int(self.timeout_var.get())
                response = session.post(
                    url, 
                    headers=headers, 
                    json=data, 
                    proxies=self.proxies,
                    timeout=timeout
                )
                
                # Check if the request was successful
                if response.status_code == 200:
                    # Get the audio content
                    audio_content = response.content
                    
                    # Create a temporary file for playback
                    temp_dir = os.path.join(self.app_dir, "temp")
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    # Create a unique temporary filename
                    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    temp_file = os.path.join(temp_dir, f"temp_{timestamp}.{self.format_var.get()}")
                    
                    # Write the audio to the temp file
                    with open(temp_file, 'wb') as f:
                        f.write(audio_content)
                        
                    # Store the audio data
                    self.audio_data = audio_content
                    
                    # Cleanup previous temp file if it exists
                    if hasattr(self, 'temp_audio_file') and self.temp_audio_file and os.path.exists(self.temp_audio_file):
                        try:
                            os.remove(self.temp_audio_file)
                        except:
                            pass
                            
                    # Set the new temp file
                    self.temp_audio_file = temp_file
                    
                    # Update the UI on the main thread
                    self.root.after(0, self._update_ui_after_generation, True, None)
                else:
                    # Handle error
                    error_message = f"API error: {response.status_code}"
                    try:
                        error_json = response.json()
                        if 'error' in error_json:
                            error_message = f"API error: {error_json['error']['message']}"
                    except:
                        pass
                        
                    # Update the UI with the error
                    self.root.after(0, self._update_ui_after_generation, False, error_message)
                    
        except Exception as e:
            # Handle any exceptions
            self.root.after(0, self._update_ui_after_generation, False, str(e))
            
    def _update_ui_after_generation(self, success, error_message):
        """Update the UI after speech generation (called on main thread)"""
        # Re-enable generate button
        self.generate_button.config(state="normal")
        
        if success:
            # Enable playback controls
            self.play_button.config(state="normal")
            self.save_button.config(state="normal")
            self.add_history_button.config(state="normal")
            
            # Update labels
            gender_icon = "👩" if self.gender_var.get() == 'female' else "👨"
            self.now_playing_var.set(f"{self.title_var.get()} - {gender_icon} {self.voice_var.get()}")
            
            # Update status
            self.status_var.set("Speech generated successfully")
            
            # Offer to play
            play_now = messagebox.askyesno("Success", "Speech generated successfully. Play now?")
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
        elif file_ext == "flac":
            filetypes.append(("FLAC files", "*.flac"))
            
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
                    
                messagebox.showinfo("Success", f"Audio saved as: {file_path}")
                self.status_var.set(f"Audio saved to {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save audio: {str(e)}")


# Initialize and run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = LemonFoxApp(root)
    root.mainloop()