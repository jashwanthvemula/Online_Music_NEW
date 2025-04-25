"""
Utility functions for the Online Music Player application.
"""

import os
import hashlib
import mysql.connector
import time
import random
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox
import csv
import subprocess
from config import DB_CONFIG, APP_CONFIG

# ------------------- Directory Management -------------------
def ensure_directories_exist():
    """Ensure all required directories exist"""
    dirs = [
        APP_CONFIG["temp_dir"],
        APP_CONFIG["reports_dir"],
        "images"
    ]
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)

# ------------------- Database Utilities -------------------
def connect_db():
    """Connect to the MySQL database"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except mysql.connector.Error as err:
        messagebox.showerror("Database Connection Error", 
                            f"Failed to connect to database: {err}")
        return None

def connect_db_server():
    """Connect to MySQL server without specifying a database"""
    try:
        config = DB_CONFIG.copy()
        if "database" in config:
            del config["database"]
        connection = mysql.connector.connect(**config)
        return connection
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL server: {err}")
        return None

# ------------------- Authentication Utilities -------------------
def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def get_current_user():
    """Get the current logged-in user information"""
    try:
        # Read user ID from file
        if not os.path.exists("current_user.txt"):
            messagebox.showerror("Error", "You are not logged in!")
            return None
            
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
            
        if not user_id:
            messagebox.showerror("Error", "User ID not found!")
            return None
            
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, first_name, last_name, email FROM Users WHERE user_id = %s",
            (user_id,)
        )
        
        user = cursor.fetchone()
        return user
        
    except Exception as e:
        print(f"Error getting current user: {e}")
        return None
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_admin_info():
    """Get the current admin information"""
    try:
        # Read admin ID from file
        if not os.path.exists("current_admin.txt"):
            messagebox.showerror("Error", "Admin session not found!")
            return None
            
        with open("current_admin.txt", "r") as f:
            admin_id = f.read().strip()
            
        if not admin_id:
            messagebox.showerror("Error", "Admin ID not found!")
            return None
            
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            "SELECT user_id, first_name, last_name, email FROM Users WHERE user_id = %s AND is_admin = 1",
            (admin_id,)
        )
        
        admin = cursor.fetchone()
        if not admin:
            messagebox.showerror("Access Denied", "You do not have admin privileges!")
            return None
            
        return admin
        
    except Exception as e:
        print(f"Error getting admin info: {e}")
        return None
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- File Utilities -------------------
def format_file_size(size_bytes):
    """Format file size from bytes to human-readable format"""
    if not size_bytes:
        return "0 B"
    
    # Define size units
    units = ['B', 'KB', 'MB', 'GB']
    size = float(size_bytes)
    unit_index = 0
    
    # Convert to appropriate unit
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    # Return formatted size
    return f"{size:.2f} {units[unit_index]}"

# ------------------- Report Utilities -------------------
def generate_report(report_type, data, filename=None):
    """Generate a report and save it to the reports directory"""
    ensure_directories_exist()
    
    if filename is None:
        # Generate default filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{report_type}_{timestamp}.csv"
    
    file_path = os.path.join(APP_CONFIG["reports_dir"], filename)
    
    try:
        with open(file_path, 'w', newline='') as csvfile:
            if data and len(data) > 0:
                # Get field names from the first row
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                # Write header and data
                writer.writeheader()
                writer.writerows(data)
                
                return file_path
            else:
                csvfile.write("No data available for this report")
                return file_path
    except Exception as e:
        print(f"Error generating report: {e}")
        return None

def open_file(file_path):
    """Open a file with the default application"""
    try:
        if os.path.exists(file_path):
            if os.name == 'nt':  # Windows
                os.startfile(file_path)
            elif os.name == 'posix':  # macOS, Linux
                subprocess.call(('xdg-open', file_path))
        else:
            messagebox.showerror("Error", f"File not found: {file_path}")
    except Exception as e:
        messagebox.showerror("Error", f"Could not open file: {e}")

# ------------------- UI Utilities -------------------
def create_song_card(parent, song_id, title, artist, play_command=None):
    """Create a clickable song card"""
    # Create song card frame
    song_card = ctk.CTkFrame(parent, fg_color="#1A1A2E", corner_radius=10, 
                           width=150, height=180)
    song_card.pack_propagate(False)
    
    # Center the text vertically by adding a spacer frame
    spacer = ctk.CTkFrame(song_card, fg_color="#1A1A2E", height=30)
    spacer.pack(side="top")
    
    # Song title with larger font
    song_label = ctk.CTkLabel(song_card, text=title, 
                             font=("Arial", 16, "bold"), text_color="white")
    song_label.pack(pady=(5, 0))
    
    # Artist name below with smaller font
    artist_label = ctk.CTkLabel(song_card, text=artist, 
                               font=("Arial", 12), text_color="#A0A0A0")
    artist_label.pack(pady=(5, 0))
    
    # Play button
    if play_command is None:
        play_command = lambda: None  # Empty function
    
    play_song_btn = ctk.CTkButton(song_card, text="▶️ Play", 
                                font=("Arial", 12, "bold"),
                                fg_color="#B146EC", hover_color="#9333EA",
                                command=lambda: play_command(song_id))
    play_song_btn.pack(pady=(15, 0))
    
    return song_card