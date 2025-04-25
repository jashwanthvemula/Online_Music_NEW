"""
Configuration settings for the Online Music Player application.
Contains database connection parameters and global settings.
"""

# Database Configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "new_password",
    "database": "online_music_system"
}

# Application Configuration
APP_CONFIG = {
    "name": "Online Music System",
    "version": "1.0",
    "temp_dir": "temp",
    "reports_dir": "reports"
}

# UI Configuration
UI_CONFIG = {
    "theme": "dark",
    "color_theme": "blue",
    "default_window_size": "1000x600",
    "min_window_size": "800x500"
}

# Colors
COLORS = {
    "primary": "#B146EC",     # Purple
    "primary_hover": "#9333EA",
    "secondary": "#2563EB",   # Blue
    "secondary_hover": "#1D4ED8",
    "success": "#16A34A",     # Green
    "success_hover": "#15803D",
    "danger": "#DC2626",      # Red
    "danger_hover": "#B91C1C",
    "warning": "#FACC15",     # Yellow
    "warning_hover": "#CA8A04",
    "background": "#1E1E2E",  # Dark blue/purple
    "sidebar": "#111827",     # Darker background
    "content": "#131B2E",     # Medium background
    "card": "#1A1A2E",        # Slightly lighter background
    "text": "white",
    "text_secondary": "#A0A0A0"
}