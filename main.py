"""
Main entry point for the Online Music Player application.
Provides a landing page with options to login, signup, or access admin features.
"""

import os
import subprocess
import customtkinter as ctk
from tkinter import messagebox
import mysql.connector
import threading
import time

# Import from other modules
from db_config import UI_CONFIG, COLORS, DB_CONFIG, APP_CONFIG
from db_utils import ensure_directories_exist, connect_db_server, connect_db

# ------------------- Database Setup Functions -------------------
def create_database():
    """Create the database and tables if they don't exist"""
    try:
        # First connect to server
        connection = connect_db_server()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Create database
        print("Creating database...")
        cursor.execute("CREATE DATABASE IF NOT EXISTS online_music_system")
        cursor.execute("USE online_music_system")
        
        # Create Users table
        print("Creating Users table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            first_name VARCHAR(50) NOT NULL,
            last_name VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password VARCHAR(64) NOT NULL,
            is_admin TINYINT(1) DEFAULT 0,
            is_active TINYINT(1) DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            secret_key VARCHAR(64)
        )
        """)
        
        # Create Artists table
        print("Creating Artists table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Artists (
            artist_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            bio TEXT,
            image_url VARCHAR(255)
        )
        """)
        
        # Create Albums table
        print("Creating Albums table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Albums (
            album_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            artist_id INT,
            release_year INT,
            cover_art MEDIUMBLOB,
            FOREIGN KEY (artist_id) REFERENCES Artists(artist_id) ON DELETE SET NULL
        )
        """)
        
        # Create Genres table
        print("Creating Genres table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Genres (
            genre_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE
        )
        """)
        
        # Create Songs table
        print("Creating Songs table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Songs (
            song_id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100) NOT NULL,
            artist_id INT,
            album_id INT,
            genre_id INT,
            duration INT,
            file_data LONGBLOB NOT NULL,
            file_type VARCHAR(10) NOT NULL,
            file_size INT NOT NULL,
            upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active TINYINT(1) NOT NULL DEFAULT 1,
            FOREIGN KEY (artist_id) REFERENCES Artists(artist_id) ON DELETE SET NULL,
            FOREIGN KEY (album_id) REFERENCES Albums(album_id) ON DELETE SET NULL,
            FOREIGN KEY (genre_id) REFERENCES Genres(genre_id) ON DELETE SET NULL
        )
        """)
        
        # Create Playlists table
        print("Creating Playlists table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Playlists (
            playlist_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
        )
        """)
        
        # Create Playlist_Songs junction table
        print("Creating Playlist_Songs table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Playlist_Songs (
            playlist_id INT NOT NULL,
            song_id INT NOT NULL,
            position INT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (playlist_id, song_id),
            FOREIGN KEY (playlist_id) REFERENCES Playlists(playlist_id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES Songs(song_id) ON DELETE CASCADE
        )
        """)
        
        # Create User_Favorites table
        print("Creating User_Favorites table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS User_Favorites (
            user_id INT NOT NULL,
            song_id INT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, song_id),
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES Songs(song_id) ON DELETE CASCADE
        )
        """)
        
        # Create Listening_History table
        print("Creating Listening_History table...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Listening_History (
            history_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            song_id INT NOT NULL,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
            FOREIGN KEY (song_id) REFERENCES Songs(song_id) ON DELETE CASCADE
        )
        """)
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("Database and tables created successfully!")
        return True
        
    except mysql.connector.Error as err:
        print(f"Error creating database: {err}")
        return False

# ------------------- Navigation Functions -------------------
def open_user_login():
    """Open the user login page"""
    try:
        subprocess.Popen(["python", "login_signup.py", "login"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open login page: {e}")

def open_user_signup():
    """Open the user signup page"""
    try:
        subprocess.Popen(["python", "login_signup.py", "signup"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open signup page: {e}")

def open_admin_login():
    """Open the admin login page"""
    try:
        subprocess.Popen(["python", "admin/admin_login.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open admin login page: {e}")

# ------------------- Splash Screen -------------------
def show_splash_screen():
    """Display a splash screen while setting up the database"""
    # Setup splash window
    splash_root = ctk.CTk()
    splash_root.title("Online Music System - Setup")
    splash_root.geometry("400x300")
    splash_root.overrideredirect(True)  # No window border
    
    # Center the window
    screen_width = splash_root.winfo_screenwidth()
    screen_height = splash_root.winfo_screenheight()
    x = (screen_width - 400) // 2
    y = (screen_height - 300) // 2
    splash_root.geometry(f"400x300+{x}+{y}")
    
    # Create a frame with rounded corners and purple color
    splash_frame = ctk.CTkFrame(splash_root, corner_radius=20, fg_color=COLORS["primary"])
    splash_frame.pack(fill="both", expand=True, padx=0, pady=0)
    
    # App title
    ctk.CTkLabel(
        splash_frame, 
        text="Online Music System", 
        font=("Arial", 28, "bold"),
        text_color="white"
    ).pack(pady=(40, 5))
    
    # App icon/logo
    ctk.CTkLabel(
        splash_frame, 
        text="🎵🐦", 
        font=("Arial", 50),
        text_color="white"
    ).pack(pady=10)
    
    # Loading text
    loading_label = ctk.CTkLabel(
        splash_frame, 
        text="Initializing...", 
        font=("Arial", 14),
        text_color="white"
    )
    loading_label.pack(pady=10)
    
    # Progress bar
    progress = ctk.CTkProgressBar(splash_frame, width=320)
    progress.pack(pady=10)
    progress.set(0)
    
    # Status message
    status_label = ctk.CTkLabel(
        splash_frame,
        text="",
        font=("Arial", 12),
        text_color="white"
    )
    status_label.pack(pady=5)
    
    # Function to run setup in steps
    def run_setup():
        # Initialize progress
        progress.set(0.1)
        loading_label.configure(text="Checking database...")
        splash_root.update_idletasks()
        time.sleep(0.5)
        
        # Create directories
        progress.set(0.3)
        loading_label.configure(text="Creating directories...")
        status_label.configure(text="")
        splash_root.update_idletasks()
        ensure_directories_exist()
        time.sleep(0.3)
        
        # Setup database
        progress.set(0.5)
        loading_label.configure(text="Setting up database...")
        splash_root.update_idletasks()
        
        setup_success = create_database()
        
        # Complete setup
        progress.set(1.0)
        
        if setup_success:
            loading_label.configure(text="Setup completed successfully!")
            status_label.configure(text="Starting application...")
        else:
            loading_label.configure(text="Setup completed with errors.")
            status_label.configure(text="See console for details. Starting application...")
        
        splash_root.update_idletasks()
        time.sleep(1.5)
        
        # Close splash and show landing page
        splash_root.destroy()
    
    # Start setup after a short delay
    splash_root.after(500, run_setup)
    
    # Start the splash screen
    splash_root.mainloop()

# ------------------- Landing Page -------------------
def create_landing_page():
    """Create and display the landing page"""
    global root
    
    # Set the appearance mode for landing page
    ctk.set_appearance_mode(UI_CONFIG["theme"])
    ctk.set_default_color_theme(UI_CONFIG["color_theme"])
    
    root = ctk.CTk()
    root.title(APP_CONFIG["name"])
    root.geometry("800x500")  # Slightly smaller than the main app
    root.resizable(False, False)

    # Main Frame with rounded corners
    main_frame = ctk.CTkFrame(root, corner_radius=20)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Left Side - Branding with purple color
    left_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["primary"], width=350, corner_radius=20)
    left_frame.pack(side="left", fill="both", expand=True)

    # Title on the left side
    title_label = ctk.CTkLabel(
        left_frame, 
        text="Online Music\nSystem",
        font=("Arial", 36, "bold"), 
        text_color="white"
    )
    title_label.place(relx=0.5, rely=0.3, anchor="center")

    # Description text below title
    desc_label = ctk.CTkLabel(
        left_frame, 
        text="Enjoy unlimited *ad-free music*\nanytime, anywhere. Access premium\nplaylists and high-quality audio\nstreaming.",
        font=("Arial", 14), 
        text_color="white", 
        justify="center"
    )
    desc_label.place(relx=0.5, rely=0.5, anchor="center")

    # Add music bird illustration
    ctk.CTkLabel(
        left_frame, 
        text="🎵🐦", 
        font=("Arial", 40), 
        text_color="white"
    ).place(relx=0.5, rely=0.75, anchor="center")

    # Right Side - Options
    right_frame = ctk.CTkFrame(main_frame, fg_color="white", width=350, corner_radius=0)
    right_frame.pack(side="right", fill="both", expand=True)

    # Create a container for the right side content with proper padding
    content_frame = ctk.CTkFrame(right_frame, fg_color="white")
    content_frame.pack(fill="both", expand=True, padx=40, pady=40)

    # Welcome title
    welcome_label = ctk.CTkLabel(
        content_frame, 
        text="Welcome!", 
        font=("Arial", 28, "bold"), 
        text_color=COLORS["primary"]
    )
    welcome_label.pack(anchor="center", pady=(20, 0))

    # Subtitle
    subtitle_label = ctk.CTkLabel(
        content_frame, 
        text="Choose an option to get started",
        font=("Arial", 14), 
        text_color="gray"
    )
    subtitle_label.pack(anchor="center", pady=(0, 40))

    # User Login button
    login_button = ctk.CTkButton(
        content_frame, 
        text="User Login", 
        font=("Arial", 16, "bold"),
        fg_color=COLORS["primary"], 
        hover_color=COLORS["primary_hover"], 
        text_color="white", 
        corner_radius=8, 
        height=50, 
        command=open_user_login
    )
    login_button.pack(fill="x", pady=(0, 15))

    # User Signup button
    signup_button = ctk.CTkButton(
        content_frame, 
        text="Create New Account", 
        font=("Arial", 16, "bold"),
        fg_color=COLORS["secondary"], 
        hover_color=COLORS["secondary_hover"], 
        text_color="white", 
        corner_radius=8, 
        height=50, 
        command=open_user_signup
    )
    signup_button.pack(fill="x", pady=(0, 15))

    # Admin Login button
    admin_button = ctk.CTkButton(
        content_frame, 
        text="Admin Login", 
        font=("Arial", 16, "bold"),
        fg_color=COLORS["card"], 
        hover_color=COLORS["content"], 
        text_color="white", 
        corner_radius=8, 
        height=50, 
        command=open_admin_login
    )
    admin_button.pack(fill="x", pady=(0, 15))

    # Version info
    version_label = ctk.CTkLabel(
        content_frame, 
        text=f"Version {APP_CONFIG['version']}", 
        font=("Arial", 12), 
        text_color="gray"
    )
    version_label.pack(side="bottom", pady=10)

# ------------------- Main Entry Point -------------------
if __name__ == "__main__":
    try:
        # Clear any existing sessions
        if os.path.exists("current_user.txt"):
            os.remove("current_user.txt")
            
        if os.path.exists("current_admin.txt"):
            os.remove("current_admin.txt")
            
        # Show splash screen
        show_splash_screen()
        
        # Display landing page
        create_landing_page()
        root.mainloop()
        
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        
        # Keep console open in case of error
        input("Press Enter to exit...")