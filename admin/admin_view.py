import os
import sys
import subprocess
import datetime
import customtkinter as ctk
from tkinter import messagebox, simpledialog, ttk, filedialog
import mysql.connector
import hashlib
import io
from PIL import Image, ImageTk
from mutagen.mp3 import MP3
from mutagen.flac import FLAC
from mutagen.wave import WAVE
import uuid
import re

# Import from other modules
try:
    from db_config import UI_CONFIG, COLORS, APP_CONFIG
    from db_utils import connect_db, hash_password, ensure_directories_exist, generate_report, open_file, get_admin_info, format_file_size
    USE_CONFIG = True
except ImportError:
    USE_CONFIG = False
    # Modernized color scheme
    COLORS = {
        "primary": "#8B5CF6",     # Vibrant purple
        "primary_hover": "#7C3AED",
        "secondary": "#3B82F6",   # Bright blue
        "secondary_hover": "#2563EB",
        "success": "#10B981",     # Emerald green
        "success_hover": "#059669",
        "danger": "#EF4444",      # Red
        "danger_hover": "#DC2626",
        "warning": "#F59E0B",     # Amber
        "warning_hover": "#D97706",
        "background": "#111827",  # Dark gray
        "sidebar": "#0F172A",     # Slate
        "content": "#1F2937",     # Gray
        "card": "#374151",        # Lighter gray
        "text": "#F3F4F6",        # Light gray
        "text_secondary": "#9CA3AF" # Gray
    }
    
    # Updated APP_CONFIG
    APP_CONFIG = {
        "name": "MusicFlow Admin",
        "version": "2.0",
        "temp_dir": "temp",
        "reports_dir": "reports"
    }

# Set customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ------------------- Database Functions -------------------
if not USE_CONFIG:
    def connect_db():
        """Connect to the MySQL database"""
        try:
            connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="new_password",
                database="online_music_system"
            )
            return connection
        except mysql.connector.Error as err:
            messagebox.showerror("Database Connection Error", 
                                f"Failed to connect to database: {err}")
            return None

    def hash_password(password):
        """Hash a password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def ensure_directories_exist():
        """Ensure that necessary directories exist"""
        directories = ["temp", "uploads", "reports"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
    def format_file_size(size_bytes):
        """Format file size from bytes to human-readable format"""
        if not size_bytes:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB']
        size = float(size_bytes)
        unit_index = 0
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        
        return f"{size:.2f} {units[unit_index]}"
        
    def get_admin_info():
        """Get the current admin information"""
        try:
            if not os.path.exists("current_admin.txt"):
                messagebox.showerror("Error", "Admin session not found!")
                open_admin_login_page()
                return None
                
            with open("current_admin.txt", "r") as f:
                admin_id = f.read().strip()
                
            if not admin_id:
                messagebox.showerror("Error", "Admin ID not found!")
                open_admin_login_page()
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
                open_admin_login_page()
                return None
                
            return admin
            
        except Exception as e:
            print(f"Error getting admin info: {e}")
            return None
        finally:
            if 'connection' in locals() and connection.is_connected():
                cursor.close()
                connection.close()
                
    def generate_report(report_type, data, filename):
        """Generate a CSV report"""
        try:
            os.makedirs("reports", exist_ok=True)
            report_path = os.path.join("reports", filename)
            
            with open(report_path, 'w', newline='') as file:
                if data:
                    header = data[0].keys()
                    file.write(','.join([f'"{h}"' for h in header]) + '\n')
                    
                    for row in data:
                        values = []
                        for field in header:
                            value = row[field]
                            if isinstance(value, str):
                                value = f'"{value.replace("\"", "\"\"")}"'
                            elif value is None:
                                value = '""'
                            else:
                                value = str(value)
                            values.append(value)
                        file.write(','.join(values) + '\n')
            
            return report_path
        except Exception as e:
            print(f"Error generating report: {e}")
            return None
            
    def open_file(file_path):
        """Open a file with the default application"""
        try:
            if os.path.exists(file_path):
                if sys.platform == 'win32':
                    os.startfile(file_path)
                elif sys.platform == 'darwin':
                    subprocess.call(['open', file_path])
                else:
                    subprocess.call(['xdg-open', file_path])
                return True
            else:
                messagebox.showerror("Error", f"File not found: {file_path}")
                return False
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {e}")
            return False

# ------------------- System Statistics Functions -------------------
def get_system_stats():
    """Get system statistics for the dashboard"""
    try:
        connection = connect_db()
        if not connection:
            return {
                "total_users": 0,
                "total_songs": 0,
                "total_playlists": 0,
                "total_downloads": 0
            }
            
        cursor = connection.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM Users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Songs")
        total_songs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Playlists")
        total_playlists = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Listening_History")
        total_downloads = cursor.fetchone()[0]
        
        return {
            "total_users": total_users,
            "total_songs": total_songs,
            "total_playlists": total_playlists,
            "total_downloads": total_downloads
        }
        
    except mysql.connector.Error as e:
        print(f"Error getting system stats: {e}")
        return {
            "total_users": 0,
            "total_songs": 0,
            "total_playlists": 0,
            "total_downloads": 0
        }
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def get_recent_activities(limit=5):
    """Get recent system activities"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        user_query = """
        SELECT 'user_registered' as activity_type, 
               CONCAT(first_name, ' ', last_name) as item,
               created_at as timestamp
        FROM Users
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        song_query = """
        SELECT 'song_uploaded' as activity_type,
               CONCAT(s.title, ' - ', a.name) as item,
               s.upload_date as timestamp
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        ORDER BY s.upload_date DESC
        LIMIT %s
        """
        
        playlist_query = """
        SELECT 'playlist_created' as activity_type,
               p.name as item,
               p.created_at as timestamp
        FROM Playlists p
        ORDER BY p.created_at DESC
        LIMIT %s
        """
        
        download_query = """
        SELECT 'song_played' as activity_type,
               CONCAT(s.title, ' - ', a.name) as item,
               lh.played_at as timestamp
        FROM Listening_History lh
        JOIN Songs s ON lh.song_id = s.song_id
        JOIN Artists a ON s.artist_id = a.artist_id
        ORDER BY lh.played_at DESC
        LIMIT %s
        """
        
        cursor.execute(user_query, (limit,))
        users = cursor.fetchall()
        
        cursor.execute(song_query, (limit,))
        songs = cursor.fetchall()
        
        cursor.execute(playlist_query, (limit,))
        playlists = cursor.fetchall()
        
        cursor.execute(download_query, (limit,))
        downloads = cursor.fetchall()
        
        all_activities = users + songs + playlists + downloads
        all_activities.sort(key=lambda x: x["timestamp"], reverse=True)
        all_activities = all_activities[:limit]
        
        formatted_activities = []
        for activity in all_activities:
            activity_type = activity["activity_type"]
            item = activity["item"]
            timestamp = activity["timestamp"]
            
            time_diff = datetime.datetime.now() - timestamp
            if time_diff.days < 1:
                hours = time_diff.seconds // 3600
                minutes = (time_diff.seconds % 3600) // 60
                if hours > 0:
                    time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    time_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            elif time_diff.days == 1:
                time_str = "Yesterday"
            else:
                time_str = f"{time_diff.days} days ago"
            
            if activity_type == "user_registered":
                action = "👤 New user"
            elif activity_type == "song_uploaded":
                action = "🎵 New song"
            elif activity_type == "playlist_created":
                action = "📁 New playlist"
            elif activity_type == "song_played":
                action = "▶️ Song played"
            else:
                action = "🔄 Activity"
            
            formatted_activities.append((action, item, time_str))
        
        return formatted_activities
        
    except mysql.connector.Error as e:
        print(f"Error getting recent activities: {e}")
        return []
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- User Management Functions -------------------
def get_all_users():
    """Get all users from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT u.user_id, u.first_name, u.last_name, u.email, u.is_admin, u.created_at,
               COUNT(DISTINCT p.playlist_id) as playlist_count,
               COUNT(DISTINCT lh.history_id) as listening_count
        FROM Users u
        LEFT JOIN Playlists p ON u.user_id = p.user_id
        LEFT JOIN Listening_History lh ON u.user_id = lh.user_id
        GROUP BY u.user_id
        ORDER BY u.created_at DESC
        """
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        return users
        
    except mysql.connector.Error as e:
        print(f"Error fetching users: {e}")
        messagebox.showerror("Error", f"Failed to fetch users: {e}")
        return []
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
def delete_user(user_id):
    """Delete a user from the database"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        cursor.execute("SELECT is_admin FROM Users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            messagebox.showerror("Error", "Cannot delete an admin user.")
            return False
        
        cursor.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
        connection.commit()
        return True
        
    except mysql.connector.Error as e:
        print(f"Error deleting user: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def toggle_admin_status(user_id, current_status):
    """Toggle user's admin status"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        new_status = 0 if current_status else 1
        
        cursor.execute(
            "UPDATE Users SET is_admin = %s WHERE user_id = %s",
            (new_status, user_id)
        )
        connection.commit()
        return True
        
    except mysql.connector.Error as e:
        print(f"Error updating admin status: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def add_new_user(first_name, last_name, email, password, is_admin=0, is_active=1):
    """Add a new user to the database"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        cursor.execute("SELECT user_id FROM Users WHERE email = %s", (email,))
        if cursor.fetchone():
            messagebox.showerror("Error", "Email already exists.")
            return None
        
        hashed_password = hash_password(password)
        
        cursor.execute(
            "INSERT INTO Users (first_name, last_name, email, password, is_admin, is_active) VALUES (%s, %s, %s, %s, %s, %s)",
            (first_name, last_name, email, hashed_password, is_admin, is_active)
        )
        
        new_user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO Playlists (user_id, name, description) VALUES (%s, %s, %s)",
            (new_user_id, "Favorites", "My favorite songs")
        )
        
        connection.commit()
        return new_user_id
        
    except mysql.connector.Error as e:
        print(f"Error adding user: {e}")
        return None
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- Song Management Functions -------------------
def get_all_songs():
    """Get all songs from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT s.song_id, s.title, a.name as artist_name, al.title as album_name,
               g.name as genre_name, s.duration, s.is_active, s.file_size, s.file_type, s.upload_date
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Albums al ON s.album_id = al.album_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        ORDER BY s.upload_date DESC
        """
        
        cursor.execute(query)
        songs = cursor.fetchall()
        
        for song in songs:
            minutes, seconds = divmod(song['duration'] or 0, 60)
            song['duration_formatted'] = f"{minutes}:{seconds:02d}"
            song['file_size_formatted'] = format_file_size(song['file_size'])
            song['status'] = "Active" if song['is_active'] else "Inactive"
        
        return songs
        
    except mysql.connector.Error as e:
        print(f"Error fetching songs: {e}")
        messagebox.showerror("Error", f"Failed to fetch songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()
def delete_song(song_id):
    """Delete a song from the database"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        tables = [
            "Playlist_Songs",
            "User_Favorites",
            "Listening_History"
        ]
        
        for table in tables:
            cursor.execute(f"DELETE FROM {table} WHERE song_id = %s", (song_id,))
        
        cursor.execute("DELETE FROM Songs WHERE song_id = %s", (song_id,))
        connection.commit()
        return True
        
    except mysql.connector.Error as e:
        print(f"Error deleting song: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- Navigation Functions -------------------
def open_admin_login_page():
    """Open the admin login page"""
    try:
        if os.path.exists("current_admin.txt"):
            os.remove("current_admin.txt")
            
        subprocess.Popen(["python", "admin_login.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open admin login: {e}")

def open_login_page():
    """Logout and open the login page"""
    try:
        if os.path.exists("current_admin.txt"):
            os.remove("current_admin.txt")
            
        subprocess.Popen(["python", "main.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to logout: {e}")

def open_main_page():
    """Return to the main landing page"""
    try:
        if os.path.exists("current_admin.txt"):
            os.remove("current_admin.txt")
            
        subprocess.Popen(["python", "main.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open main page: {e}")

# ------------------- UI View Management Functions -------------------
def clear_content_frame():
    """Clear the content frame to load a new view"""
    for widget in content_frame.winfo_children():
        widget.destroy()

def show_dashboard_view():
    """Show the dashboard view"""
    clear_content_frame()
    admin = get_admin_info()
    if not admin:
        return
    create_dashboard_frame(content_frame, admin)

def show_users_view():
    """Show the user management view"""
    clear_content_frame()
    admin = get_admin_info()
    if not admin:
        return
    create_users_frame(content_frame, admin)

def show_songs_view():
    """Show the song management view"""
    clear_content_frame()
    admin = get_admin_info()
    if not admin:
        return
    create_songs_frame(content_frame, admin)

def show_playlist_view():
    """Show the playlist management view"""
    clear_content_frame()
    admin = get_admin_info()
    if not admin:
        return
    messagebox.showinfo("Coming Soon", "Playlist management view is under construction.")
    show_dashboard_view()

def show_reports_view():
    """Show the reports view"""
    clear_content_frame()
    admin = get_admin_info()
    if not admin:
        return
    create_reports_frame(content_frame, admin)

# ------------------- Dashboard UI Functions -------------------
def create_dashboard_frame(parent_frame, admin):
    """Create the modernized dashboard UI"""
    stats = get_system_stats()
    
    # Main container
    main_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Header
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        header_frame,
        text="Dashboard",
        font=("Inter", 28, "bold"),
        text_color=COLORS["text"]
    ).pack(side="left")
    
    ctk.CTkLabel(
        header_frame,
        text=f"{admin['first_name']} {admin['last_name']}",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    ).pack(side="right")
    
    ctk.CTkButton(
        header_frame,
        text="↻ Refresh",
        font=("Inter", 12),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        command=refresh_dashboard,
        width=120,
        height=32,
        corner_radius=8
    ).pack(side="right", padx=10)
    
    # Stats section
    stats_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["card"], corner_radius=12)
    stats_frame.pack(fill="x", padx=20, pady=20)
    
    ctk.CTkLabel(
        stats_frame,
        text="System Overview",
        font = ("Inter", 20, "bold"),
        text_color=COLORS["primary"]
    ).pack(anchor="w", padx=20, pady=(20, 10))
    
    # Stats grid
    stats_grid = ctk.CTkFrame(stats_frame, fg_color="transparent")
    stats_grid.pack(fill="x", padx=20, pady=10)
    
    stat_items = [
        ("Users", stats["total_users"], "👥", COLORS["success"]),
        ("Songs", stats["total_songs"], "🎵", COLORS["secondary"]),
        ("Playlists", stats["total_playlists"], "📁", COLORS["warning"]),
        ("Plays", stats["total_downloads"], "▶️", COLORS["danger"])
    ]
    
    global user_count_label, song_count_label, playlist_count_label, download_count_label
    user_count_label = None
    song_count_label = None
    playlist_count_label = None
    download_count_label = None
    
    for i, (title, value, icon, color) in enumerate(stat_items):
        card = ctk.CTkFrame(stats_grid, fg_color=COLORS["content"], corner_radius=8, border_width=1, border_color=COLORS["card"])
        card.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
        stats_grid.grid_columnconfigure(i, weight=1)
        
        ctk.CTkLabel(
            card,
            text=f"{icon} {title}",
            font=("Inter", 14, "bold"),
            text_color=COLORS["text"]
        ).pack(pady=(15, 5))
        
        label = ctk.CTkLabel(
            card,
            text=str(value),
            font=("Inter", 24, "bold"),
            text_color=color
        )
        label.pack(pady=5)
        
        if i == 0:
            user_count_label = label
        elif i == 1:
            song_count_label = label
        elif i == 2:
            playlist_count_label = label
        elif i == 3:
            download_count_label = label
    
    # Actions section
    # Recent activity section with improved UI and scrollability
    activity_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["card"], corner_radius=12)
    activity_frame.pack(fill="both", expand=True, padx=20, pady=20)

    activity_header = ctk.CTkFrame(activity_frame, fg_color="transparent")
    activity_header.pack(fill="x", padx=20, pady=(20, 10))

    ctk.CTkLabel(
        activity_header,
        text="Recent Activity",
        font=("Inter", 20, "bold"),
        text_color=COLORS["primary"]
    ).pack(side="left")

    refresh_btn = ctk.CTkButton(
        activity_header,
        text="↻ Refresh",
        font=("Inter", 12),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        command=refresh_dashboard,
        width=80,
        height=28,
        corner_radius=8
    )
    refresh_btn.pack(side="right")

    # Create a scrollable container for activities
    global activity_doc_frame
    activity_container = ctk.CTkFrame(activity_frame, fg_color="transparent")
    activity_container.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    # Make the activity frame scrollable
    activity_scroll = ctk.CTkScrollableFrame(
        activity_container, 
        fg_color=COLORS["content"],
        corner_radius=8,
        height=250  # Fixed height for better appearance
    )
    activity_scroll.pack(fill="both", expand=True)
    activity_doc_frame = activity_scroll

    activities = get_recent_activities(15)  # Increase limit to show more activities

    if not activities:
        ctk.CTkLabel(
            activity_doc_frame,
            text="No recent activities",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=20)
    else:
        for action, item, time in activities:
            activity_item = ctk.CTkFrame(activity_doc_frame, fg_color=COLORS["card"], corner_radius=8)
            activity_item.pack(fill="x", pady=5, padx=5, ipady=5)
            
            # Left side container for icon and action type
            left_container = ctk.CTkFrame(activity_item, fg_color="transparent")
            left_container.pack(side="left", padx=10, fill="y")
            
            # Draw a colored icon/badge based on activity type
            color = COLORS["primary"]
            if "New user" in action:
                color = COLORS["success"]
            elif "New song" in action:
                color = COLORS["secondary"]
            elif "New playlist" in action:
                color = COLORS["warning"]
            elif "Song played" in action:
                color = COLORS["danger"]
                
            icon_label = ctk.CTkLabel(
                left_container,
                text=action.split()[0],  # Just the icon part
                font=("Inter", 14, "bold"),
                text_color="white",
                fg_color=color,
                corner_radius=6,
                width=30,
                height=30
            )
            icon_label.pack(anchor="center", pady=2)
            
            # Middle container for activity details
            middle_container = ctk.CTkFrame(activity_item, fg_color="transparent")
            middle_container.pack(side="left", fill="both", expand=True, padx=5)
            
            activity_type = " ".join(action.split()[1:])  # The action without the icon
            
            # Activity type label
            ctk.CTkLabel(
                middle_container,
                text=activity_type,
                font=("Inter", 14, "bold"),
                text_color=COLORS["text"],
                anchor="w"
            ).pack(anchor="w", pady=(2, 0))
            
            # Item label with ellipsis for long text
            if len(item) > 40:
                item = item[:37] + "..."
                
            ctk.CTkLabel(
                middle_container,
                text=item,
                font=("Inter", 12),
                text_color=COLORS["text_secondary"],
                anchor="w"
            ).pack(anchor="w")
            
            # Right container for time
            time_label = ctk.CTkLabel(
                activity_item,
                text=time,
                font=("Inter", 12),
                text_color=COLORS["primary"],
                width=80  # Fixed width for alignment
            )
            time_label.pack(side="right", padx=10)

def refresh_dashboard():
    """Refresh the dashboard data"""
    stats = get_system_stats()
    
    user_count_label.configure(text=str(stats["total_users"]))
    song_count_label.configure(text=str(stats["total_songs"]))
    playlist_count_label.configure(text=str(stats["total_playlists"]))
    download_count_label.configure(text=str(stats["total_downloads"]))
    
    for widget in activity_doc_frame.winfo_children():
        widget.destroy()
    
    activities = get_recent_activities(15)  # Increased limit
    
    if not activities:
        ctk.CTkLabel(
            activity_doc_frame,
            text="No recent activities",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=20)
    else:
        for action, item, time in activities:
            activity_item = ctk.CTkFrame(activity_doc_frame, fg_color=COLORS["card"], corner_radius=8)
            activity_item.pack(fill="x", pady=5, padx=5, ipady=5)
            
            # Left side container for icon and action type
            left_container = ctk.CTkFrame(activity_item, fg_color="transparent")
            left_container.pack(side="left", padx=10, fill="y")
            
            # Draw a colored icon/badge based on activity type
            color = COLORS["primary"]
            if "New user" in action:
                color = COLORS["success"]
            elif "New song" in action:
                color = COLORS["secondary"]
            elif "New playlist" in action:
                color = COLORS["warning"]
            elif "Song played" in action:
                color = COLORS["danger"]
                
            icon_label = ctk.CTkLabel(
                left_container,
                text=action.split()[0],  # Just the icon part
                font=("Inter", 14, "bold"),
                text_color="white",
                fg_color=color,
                corner_radius=6,
                width=30,
                height=30
            )
            icon_label.pack(anchor="center", pady=2)
            
            # Middle container for activity details
            middle_container = ctk.CTkFrame(activity_item, fg_color="transparent")
            middle_container.pack(side="left", fill="both", expand=True, padx=5)
            
            activity_type = " ".join(action.split()[1:])  # The action without the icon
            
            # Activity type label
            ctk.CTkLabel(
                middle_container,
                text=activity_type,
                font=("Inter", 14, "bold"),
                text_color=COLORS["text"],
                anchor="w"
            ).pack(anchor="w", pady=(2, 0))
            
            # Item label with ellipsis for long text
            if len(item) > 40:
                item = item[:37] + "..."
                
            ctk.CTkLabel(
                middle_container,
                text=item,
                font=("Inter", 12),
                text_color=COLORS["text_secondary"],
                anchor="w"
            ).pack(anchor="w")
            
            # Right container for time
            time_label = ctk.CTkLabel(
                activity_item,
                text=time,
                font=("Inter", 12),
                text_color=COLORS["primary"],
                width=80  # Fixed width for alignment
            )
            time_label.pack(side="right", padx=10)

# ------------------- User Management UI Functions -------------------
def create_users_frame(parent_frame, admin):
    """Create the modernized user management UI"""
    main_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Header
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        header_frame,
        text="Manage Users",
        font=("Inter", 28, "bold"),
        text_color=COLORS["text"]
    ).pack(side="left")
    
    ctk.CTkLabel(
        header_frame,
        text=f"{admin['first_name']} {admin['last_name']}",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    ).pack(side="right")
    
    ctk.CTkButton(
        header_frame,
        text="← Back",
        font=("Inter", 12),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        command=show_dashboard_view,
        width=120,
        height=32,
        corner_radius=8
    ).pack(side="right", padx=10)
    
    # Actions
    actions_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    actions_frame.pack(fill="x", padx=20, pady=10)
    
    ctk.CTkButton(
        actions_frame,
        text="+ Add User",
        font=("Inter", 14),
        fg_color=COLORS["success"],
        hover_color=COLORS["success_hover"],
        command=handle_add_user,
        height=40,
        corner_radius=8
    ).pack(side="left", padx=(0, 10))
    
    ctk.CTkButton(
        actions_frame,
        text="🗑 Delete",
        font=("Inter", 14),
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        command=confirm_delete_user,
        height=40,
        corner_radius=8
    ).pack(side="left", padx=(0, 10))
    
    ctk.CTkButton(
        actions_frame,
        text="👑 Admin",
        font=("Inter", 14),
        fg_color=COLORS["warning"],
        hover_color=COLORS["warning_hover"],
        command=toggle_selected_admin_status,
        height=40,
        corner_radius=8
    ).pack(side="left", padx=(0, 10))
    
    ctk.CTkButton(
        actions_frame,
        text="↻ Refresh",
        font=("Inter", 14),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        command=refresh_user_list,
        height=40,
        corner_radius=8
    ).pack(side="right")
    
    # Users table
    table_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["card"], corner_radius=12)
    table_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Treeview",
        background=COLORS["content"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["content"],
        borderwidth=0,
        rowheight=30
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=("Inter", 12, "bold")
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["primary"])],
        foreground=[("selected", COLORS["text"])]
    )
    
    tree_scroll = ttk.Scrollbar(table_frame)
    tree_scroll.pack(side="right", fill="y")
    
# Users table
    global users_tree
    users_tree = ttk.Treeview(
        table_frame,
        columns=("id", "name", "email", "admin", "status", "created", "playlists", "history", "user_id"),
        show="headings",
        yscrollcommand=tree_scroll.set
    )
    users_tree.pack(fill="both", expand=True, padx=10, pady=10)

    tree_scroll.config(command=users_tree.yview)

    users_tree.heading("id", text="#")
    users_tree.heading("name", text="Name")
    users_tree.heading("email", text="Email")
    users_tree.heading("admin", text="Admin")
    users_tree.heading("status", text="Status")
    users_tree.heading("created", text="Created")
    users_tree.heading("playlists", text="Playlists")
    users_tree.heading("history", text="Plays")
    users_tree.heading("user_id", text="ID")

    users_tree.column("id", width=50, anchor="center")
    users_tree.column("name", width=200, anchor="w")
    users_tree.column("email", width=250, anchor="w")
    users_tree.column("admin", width=80, anchor="center")
    users_tree.column("status", width=80, anchor="center")
    users_tree.column("created", width=120, anchor="center")
    users_tree.column("playlists", width=80, anchor="center")
    users_tree.column("history", width=80, anchor="center")
    users_tree.column("user_id", width=80, anchor="center")
        
    # Footer
    footer_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    footer_frame.pack(fill="x", padx=20, pady=(0, 20))
    
    global stats_label
    stats_label = ctk.CTkLabel(
        footer_frame,
        text="Loading users...",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    )
    stats_label.pack(side="left")
    # Add this after the Admin button
    ctk.CTkButton(
        actions_frame,
        text="🔄 Status",
        font=("Inter", 14),
        fg_color=COLORS["success"],
        hover_color=COLORS["success_hover"],
        command=toggle_selected_active_status,
        height=40,
        corner_radius=8
    ).pack(side="left", padx=(0, 10))
    
    ctk.CTkButton(
        footer_frame,
        text="📊 Report",
        font=("Inter", 14),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        command=generate_and_open_user_report,
        height=32,
        corner_radius=8
    ).pack(side="right")
    
    refresh_user_list()
def toggle_song_active_status(song_id, current_status):
    """Toggle song's active status"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        new_status = 0 if current_status else 1
        
        cursor.execute(
            "UPDATE Songs SET is_active = %s WHERE song_id = %s",
            (new_status, song_id)
        )
        connection.commit()
        return True
        
    except mysql.connector.Error as e:
        print(f"Error updating song active status: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def toggle_selected_song_status():
    """Toggle active status for the selected song"""
    selected = songs_tree.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a song.")
        return
    
    song_id = songs_tree.item(selected, 'values')[-1]
    song_title = songs_tree.item(selected, 'values')[1]
    # Get current status from the tree - we need to add this column to the tree first
    current_status = songs_tree.item(selected, 'values')[6] == "Active" 
    
    action = "deactivate" if current_status else "activate"
    confirm = messagebox.askyesno(
        "Confirm",
        f"Do you want to {action} song '{song_title}'?\n\n"
        f"{'Users will NOT see this song anymore.' if current_status else 'Users will be able to see this song.'}"
    )
    
    if confirm:
        if toggle_song_active_status(song_id, current_status):
            status = "deactivated" if current_status else "activated"
            messagebox.showinfo("Success", f"Song '{song_title}' has been {status}.")
            refresh_song_list()
        else:
            messagebox.showerror("Error", f"Failed to {action} song '{song_title}'.")

def refresh_user_list():
    """Refresh the user list display"""
    for item in users_tree.get_children():
        users_tree.delete(item)
    
    users = get_all_users()
    
    for i, user in enumerate(users, 1):
        admin_status = "Yes" if user["is_admin"] else "No"
        active_status = "Active" if user["is_active"] else "Inactive"
        created_date = user["created_at"].strftime("%Y-%m-%d")
        users_tree.insert(
            "", "end",
            values=(
                i,
                f"{user['first_name']} {user['last_name']}",
                user["email"],
                admin_status,
                active_status,
                created_date,
                user["playlist_count"],
                user["listening_count"],
                user["user_id"]
            )
        )
    
    stats_label.configure(text=f"Total Users: {len(users_tree.get_children())}")

def confirm_delete_user():
    """Confirm and delete selected user"""
    selected = users_tree.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a user.")
        return
    
    user_id = users_tree.item(selected, 'values')[-1]
    user_name = users_tree.item(selected, 'values')[1]
    
    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Delete user '{user_name}'? This action is irreversible."
    )
    
    if confirm:
        if delete_user(user_id):
            messagebox.showinfo("Success", f"User '{user_name}' deleted.")
            refresh_user_list()
        else:
            messagebox.showerror("Error", f"Failed to delete user '{user_name}'.")

def toggle_selected_admin_status():
    """Toggle admin status for selected user"""
    selected = users_tree.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a user.")
        return
    
    user_id = users_tree.item(selected, 'values')[-1]
    user_name = users_tree.item(selected, 'values')[1]
    current_status = users_tree.item(selected, 'values')[3] == "Yes"
    
    action = "remove admin privileges from" if current_status else "grant admin privileges to"
    confirm = messagebox.askyesno(
        "Confirm",
        f"{action.capitalize()} '{user_name}'?"
    )
    
    if confirm:
        if toggle_admin_status(user_id, current_status):
            status = "removed from" if current_status else "granted to"
            messagebox.showinfo("Success", f"Admin privileges {status} '{user_name}'.")
            refresh_user_list()
        else:
            messagebox.showerror("Error", f"Failed to update admin status for '{user_name}'.")

def handle_add_user():
    """Display dialog to add a new user"""
    dialog = ctk.CTkToplevel(root)
    dialog.title("Add User")
    dialog.geometry("400x500")
    dialog.transient(root)
    dialog.grab_set()
    
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    ctk.CTkLabel(
        dialog,
        text="Add New User",
        font=("Inter", 20, "bold"),
        text_color=COLORS["text"]
    ).pack(pady=20)
    
    # Form fields
    fields = [
        ("First Name", ctk.StringVar()),
        ("Last Name", ctk.StringVar()),
        ("Email", ctk.StringVar()),
        ("Password", ctk.StringVar()),
        ("Confirm Password", ctk.StringVar())
    ]
    
    entries = {}
    for label, var in fields:
        frame = ctk.CTkFrame(dialog, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(
            frame,
            text=label,
            font=("Inter", 12),
            width=100,
            text_color=COLORS["text"]
        ).pack(side="left")
        
        entry = ctk.CTkEntry(
            frame,
            textvariable=var,
            width=200,
            font=("Inter", 12),
            show="*" if "Password" in label else ""
        )
        entry.pack(side="left", padx=5)
        entries[label] = entry
    
    admin_var = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(
        dialog,
        text="Grant Admin Privileges",
        variable=admin_var,
        font=("Inter", 12),
        text_color=COLORS["text"]
    ).pack(pady=15)
    
    def do_add_user():
        first_name = fields[0][1].get().strip()
        last_name = fields[1][1].get().strip()
        email = fields[2][1].get().strip()
        password = fields[3][1].get()
        confirm_password = fields[4][1].get()
        is_admin = 1 if admin_var.get() else 0
        
        if not all([first_name, last_name, email, password]):
            messagebox.showwarning("Warning", "All fields are required.")
            return
            
        if password != confirm_password:
            messagebox.showwarning("Warning", "Passwords do not match.")
            return
            
        if len(password) < 8:
            messagebox.showwarning("Warning", "Password must be at least 8 characters.")
            return
            
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, email):
            messagebox.showwarning("Warning", "Invalid email address.")
            return
        
        new_user_id = add_new_user(first_name, last_name, email, password, is_admin)
        if new_user_id:
            messagebox.showinfo("Success", f"User '{first_name} {last_name}' added.")
            dialog.destroy()
            refresh_user_list()
        else:
            messagebox.showerror("Error", "Failed to add user.")
    
    ctk.CTkButton(
        dialog,
        text="Add User",
        font=("Inter", 14),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        command=do_add_user,
        height=40,
        corner_radius=8
    ).pack(pady=20)

def generate_and_open_user_report():
    """Generate a user report and open it"""
    users = get_all_users()
    
    report_data = [
        {
            'User ID': user['user_id'],
            'First Name': user['first_name'],
            'Last Name': user['last_name'],
            'Email': user['email'],
            'Admin': 'Yes' if user['is_admin'] else 'No',
            'Created At': user['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
            'Playlists': user['playlist_count'],
            'Plays': user['listening_count']
        } for user in users
    ]
    timestamp= datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"admin_user_{timestamp}.csv"
    report_path = generate_report("users", report_data, filename)
    
    if report_path:
        messagebox.showinfo("Success", f"Report saved to: {report_path}")
        open_file(report_path)
    else:
        messagebox.showerror("Error", "Failed to generate report.")

# ------------------- Song Management UI Functions -------------------
def create_songs_frame(parent_frame, admin):
    """Create the modernized song management UI"""
    main_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Header
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        header_frame,
        text="Manage Songs",
        font=("Inter", 28, "bold"),
        text_color=COLORS["text"]
    ).pack(side="left")
    
    ctk.CTkLabel(
        header_frame,
        text=f"{admin['first_name']} {admin['last_name']}",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    ).pack(side="right")
    
    ctk.CTkButton(
        header_frame,
        text="← Back",
        font=("Inter", 12),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        command=show_dashboard_view,
        width=120,
        height=32,
        corner_radius=8
    ).pack(side="right", padx=10)
    
    # Actions
    actions_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    actions_frame.pack(fill="x", padx=20, pady=10)
    
    ctk.CTkButton(
        actions_frame,
        text="+ Upload Song",
        font=("Inter", 14),
        fg_color=COLORS["success"],
        hover_color=COLORS["success_hover"],
        command=handle_upload_song,
        height=40,
        corner_radius=8
    ).pack(side="left", padx=(0, 10))
    
    ctk.CTkButton(
        actions_frame,
        text="🗑 Delete",
        font=("Inter", 14),
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        command=confirm_delete_song,
        height=40,
        corner_radius=8
    ).pack(side="left", padx=(0, 10))
    
    # New button for toggling song active status
    ctk.CTkButton(
        actions_frame,
        text="🔄 Toggle Status",
        font=("Inter", 14),
        fg_color=COLORS["warning"],
        hover_color=COLORS["warning_hover"],
        command=toggle_selected_song_status,
        height=40,
        corner_radius=8
    ).pack(side="left", padx=(0, 10))
    
    ctk.CTkButton(
        actions_frame,
        text="↻ Refresh",
        font=("Inter", 14),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        command=refresh_song_list,
        height=40,
        corner_radius=8
    ).pack(side="right")
    
    # Songs table
    table_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["card"], corner_radius=12)
    table_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    style = ttk.Style()
    style.theme_use("default")
    style.configure(
        "Treeview",
        background=COLORS["content"],
        foreground=COLORS["text"],
        fieldbackground=COLORS["content"],
        borderwidth=0,
        rowheight=30
    )
    style.configure(
        "Treeview.Heading",
        background=COLORS["card"],
        foreground=COLORS["text"],
        font=("Inter", 12, "bold")
    )
    style.map(
        "Treeview",
        background=[("selected", COLORS["primary"])],
        foreground=[("selected", COLORS["text"])]
    )
    
    tree_scroll = ttk.Scrollbar(table_frame)
    tree_scroll.pack(side="right", fill="y")
    
    global songs_tree
    songs_tree = ttk.Treeview(
        table_frame,
        columns=("id", "title", "artist", "genre", "duration", "size", "status", "song_id"),
        show="headings",
        yscrollcommand=tree_scroll.set
    )
    songs_tree.pack(fill="both", expand=True, padx=10, pady=10)
    
    tree_scroll.config(command=songs_tree.yview)
    
    songs_tree.heading("id", text="#")
    songs_tree.heading("title", text="Title")
    songs_tree.heading("artist", text="Artist")
    songs_tree.heading("genre", text="Genre")
    songs_tree.heading("duration", text="Duration")
    songs_tree.heading("size", text="Size")
    songs_tree.heading("status", text="Status")
    songs_tree.heading("song_id", text="ID")
    
    songs_tree.column("id", width=50, anchor="center")
    songs_tree.column("title", width=250, anchor="w")
    songs_tree.column("artist", width=180, anchor="w")
    songs_tree.column("genre", width=120, anchor="w")
    songs_tree.column("duration", width=80, anchor="center")
    songs_tree.column("size", width=100, anchor="e")
    songs_tree.column("status", width=80, anchor="center")
    songs_tree.column("song_id", width=80, anchor="center")
    
    # Footer
    footer_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    footer_frame.pack(fill="x", padx=20, pady=(0, 20))
    
    global song_stats_label
    song_stats_label = ctk.CTkLabel(
        footer_frame,
        text="Loading songs...",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    )
    song_stats_label.pack(side="left")
    
    ctk.CTkButton(
        footer_frame,
        text="📊 Report",
        font=("Inter", 14),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        command=generate_and_open_song_report,
        height=32,
        corner_radius=8
    ).pack(side="right")
    
    refresh_song_list()

def refresh_song_list():
    """Refresh the song list display"""
    for item in songs_tree.get_children():
        songs_tree.delete(item)
    
    songs = get_all_songs()
    active_count = 0
    inactive_count = 0
    
    for i, song in enumerate(songs, 1):
        if song.get('is_active', 1):
            active_count += 1
        else:
            inactive_count += 1
            
        songs_tree.insert(
            "", "end",
            values=(
                i,
                song["title"],
                song["artist_name"],
                song["genre_name"] or "N/A",
                song["duration_formatted"],
                song["file_size_formatted"],
                song["status"],
                song["song_id"]
            )
        )
    
    song_stats_label.configure(text=f"Total Songs: {len(songs)} (Active: {active_count}, Inactive: {inactive_count})")

def confirm_delete_song():
    """Confirm and delete selected song"""
    selected = songs_tree.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a song.")
        return
    
    song_id = songs_tree.item(selected, 'values')[-1]
    song_title = songs_tree.item(selected, 'values')[1]
    
    confirm = messagebox.askyesno(
        "Confirm Delete",
        f"Delete song '{song_title}'? This action is irreversible."
    )
    
    if confirm:
        if delete_song(song_id):
            messagebox.showinfo("Success", f"Song '{song_title}' deleted.")
            refresh_song_list()
        else:
            messagebox.showerror("Error", f"Failed to delete song '{song_title}'.")

def handle_upload_song():
    """Handle the song upload process"""
    file_path = filedialog.askopenfilename(
        title="Select Song",
        filetypes=[("Audio Files", "*.mp3 *.wav *.flac"), ("All files", "*.*")]
    )
    
    if not file_path:
        return
    
    if not os.path.exists(file_path):
        messagebox.showerror("Error", "File does not exist.")
        return
    
    try:
        with open(file_path, 'rb') as f:
            f.read(1)
    except Exception as e:
        messagebox.showerror("Error", f"Cannot access file: {e}")
        return
    
    default_title = os.path.splitext(os.path.basename(file_path))[0]
    
    dialog = ctk.CTkToplevel(root)
    dialog.title("Upload Song")
    dialog.geometry("450x600")
    dialog.transient(root)
    dialog.grab_set()
    
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (width // 2)
    y = (dialog.winfo_screenheight() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    ctk.CTkLabel(
        dialog,
        text="Upload Song",
        font=("Inter", 20, "bold"),
        text_color=COLORS["text"]
    ).pack(pady=20)
    
    # Form fields
    title_var = ctk.StringVar(value=default_title)
    album_var = ctk.StringVar()
    
    # Title
    title_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    title_frame.pack(fill="x", padx=20, pady=5)
    ctk.CTkLabel(title_frame, text="Title:", font=("Inter", 12), width=100).pack(side="left")
    ctk.CTkEntry(title_frame, textvariable=title_var, width=250, font=("Inter", 12)).pack(side="left")
    
    # Artist
    artists = get_artists()
    artist_names = [artist["name"] for artist in artists] or ["Unknown Artist"]
    artist_ids = [artist["artist_id"] for artist in artists] or [1]
    artist_var = ctk.StringVar(value=artist_names[0] if artist_names else "")
    
    artist_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    artist_frame.pack(fill="x", padx=20, pady=5)
    ctk.CTkLabel(artist_frame, text="Artist:", font=("Inter", 12), width=100).pack(side="left")
    artist_menu = ctk.CTkOptionMenu(
        artist_frame,
        variable=artist_var,
        values=artist_names,
        width=250,
        font=("Inter", 12)
    )
    artist_menu.pack(side="left")
    
    def add_artist():
        name = simpledialog.askstring("New Artist", "Enter artist name:")
        if name and name.strip():
            new_id = add_new_artist(name.strip())
            if new_id:
                artist_names.append(name)
                artist_ids.append(new_id)
                artist_menu.configure(values=artist_names)
                artist_var.set(name)
                messagebox.showinfo("Success", f"Artist '{name}' added.")
    
    ctk.CTkButton(
        artist_frame,
        text="+",
        width=40,
        font=("Inter", 12),
        command=add_artist,
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"]
    ).pack(side="left", padx=5)
    
    # Genre
    genres = get_genres()
    genre_names = [genre["name"] for genre in genres] or ["Unknown Genre"]
    genre_ids = [genre["genre_id"] for genre in genres] or [1]
    genre_var = ctk.StringVar(value=genre_names[0] if genre_names else "")
    
    genre_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    genre_frame.pack(fill="x", padx=20, pady=5)
    ctk.CTkLabel(genre_frame, text="Genre:", font=("Inter", 12), width=100).pack(side="left")
    genre_menu = ctk.CTkOptionMenu(
        genre_frame,
        variable=genre_var,
        values=genre_names,
        width=250,
        font=("Inter", 12)
    )
    genre_menu.pack(side="left")
    
    def add_genre():
        name = simpledialog.askstring("New Genre", "Enter genre name:")
        if name and name.strip():
            new_id = add_new_genre(name.strip())
            if new_id:
                genre_names.append(name)
                genre_ids.append(new_id)
                genre_menu.configure(values=genre_names)
                genre_var.set(name)
                messagebox.showinfo("Success", f"Genre '{name}' added.")
    
    ctk.CTkButton(
        genre_frame,
        text="+",
        width=40,
        font=("Inter", 12),
        command=add_genre,
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"]
    ).pack(side="left", padx=5)
    
    # Album
    album_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    album_frame.pack(fill="x", padx=20, pady=5)
    ctk.CTkLabel(album_frame, text="Album:", font=("Inter", 12), width=100).pack(side="left")
    ctk.CTkEntry(album_frame, textvariable=album_var, width=250, font=("Inter", 12)).pack(side="left")
    
    # File info
    file_size = os.path.getsize(file_path)
    file_type = os.path.splitext(file_path)[1][1:].lower()
    
    file_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    file_frame.pack(fill="x", padx=20, pady=10)
    ctk.CTkLabel(
        file_frame,
        text=f"File: {os.path.basename(file_path)}",
        font=("Inter", 12),
        text_color=COLORS["text"]
    ).pack(anchor="w")
    ctk.CTkLabel(
        file_frame,
        text=f"Type: {file_type.upper()} | Size: {format_file_size(file_size)}",
        font=("Inter", 12),
        text_color=COLORS["text_secondary"]
    ).pack(anchor="w")
    
    def do_upload():
        title = title_var.get().strip()
        if not title:
            messagebox.showwarning("Warning", "Please enter a title.")
            return
        
        artist_name = artist_var.get()
        if artist_name not in artist_names:
            messagebox.showwarning("Warning", "Please select a valid artist.")
            return
        artist_id = artist_ids[artist_names.index(artist_name)]
        
        genre_name = genre_var.get()
        if genre_name not in genre_names:
            messagebox.showwarning("Warning", "Please select a valid genre.")
            return
        genre_id = genre_ids[genre_names.index(genre_name)]
        
        album_name = album_var.get().strip()
        album_id = None
        if album_name:
            album_id = get_or_create_album(album_name, artist_id)
            if not album_id:
                messagebox.showerror("Error", "Failed to process album.")
                return
        
        progress_label = ctk.CTkLabel(
            dialog,
            text="Uploading...",
            font=("Inter", 12),
            text_color=COLORS["text_secondary"]
        )
        progress_label.pack(pady=10)
        dialog.config(cursor="wait")
        dialog.update()
        
        try:
            song_id = upload_song(file_path, title, artist_id, genre_id, album_id)
            
            if song_id:
                messagebox.showinfo("Success", f"Song '{title}' uploaded.")
                dialog.destroy()
                refresh_song_list()
            else:
                # The upload_song function already shows error messages
                dialog.config(cursor="")
                progress_label.destroy()
                dialog.update()
        except Exception as e:
            messagebox.showerror("Error", f"Upload failed: {e}")
            dialog.config(cursor="")
            progress_label.destroy()
            dialog.update()
    
    # Button frame for better organization
    button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    button_frame.pack(fill="x", padx=20, pady=20)
    
    # Upload button
    ctk.CTkButton(
        button_frame,
        text="Upload",
        font=("Inter", 14),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        command=do_upload,
        height=40,
        corner_radius=8
    ).pack(fill="x", pady=(0, 10))
    
    # Cancel button
    ctk.CTkButton(
        button_frame,
        text="Cancel",
        font=("Inter", 14),
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        command=dialog.destroy,
        height=40,
        corner_radius=8
    ).pack(fill="x")

def upload_song(file_path, title, artist_id, genre_id=None, album_id=None):
    """Upload a song to the database with duplicate detection"""
    try:
        if not os.path.exists(file_path):
            messagebox.showerror("Error", "File not found.")
            return None
        
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(file_path)[1][1:].lower()
        
        if file_type not in ['mp3', 'wav', 'flac']:
            messagebox.showerror("Error", f"Unsupported file type: {file_type}.")
            return None
        
        # First database connection - just for checking duplicates
        duplicate_exists = False
        duplicate_title = ""
        
        # Use a separate try-except block for the duplicate check
        try:
            check_conn = connect_db()
            if check_conn:
                check_cursor = check_conn.cursor(dictionary=True)
                check_cursor.execute(
                    "SELECT song_id, title FROM Songs WHERE title = %s AND artist_id = %s",
                    (title, artist_id)
                )
                existing_song = check_cursor.fetchone()
                
                if existing_song:
                    duplicate_exists = True
                    duplicate_title = existing_song["title"]
                
                check_cursor.close()
                check_conn.close()
        except mysql.connector.Error as e:
            print(f"Error checking for duplicates: {e}")
            # Continue with upload even if duplicate check fails
        
        # If duplicate found, ask for confirmation
        if duplicate_exists:
            confirm = messagebox.askyesno(
                "Duplicate Song",
                f"A song with title '{duplicate_title}' by this artist already exists. Upload anyway?",
                icon='warning'
            )
            if not confirm:
                return None
                
        # Process audio file
        duration = 180
        try:
            if file_type == 'mp3':
                audio = MP3(file_path)
                duration = int(audio.info.length)
            elif file_type == 'flac':
                audio = FLAC(file_path)
                duration = int(audio.info.length)
            elif file_type == 'wav':
                audio = WAVE(file_path)
                duration = int(audio.info.length)
        except Exception as e:
            print(f"Warning: Could not get duration: {e}")
        
        # Read file data
        with open(file_path, 'rb') as file:
            file_data = file.read()
        
        max_size = 100 * 1024 * 1024
        if file_size > max_size:
            messagebox.showerror("Error", f"File too large: {format_file_size(file_size)}.")
            return None
        
        # Second database connection - just for inserting the song
        insert_conn = connect_db()
        if not insert_conn:
            return None
            
        try:
            insert_cursor = insert_conn.cursor()
            
            query = """
            INSERT INTO Songs (title, artist_id, genre_id, album_id, duration, file_data, file_type, file_size, upload_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (title, artist_id, genre_id, album_id, duration, file_data, file_type, file_size, datetime.datetime.now())
            insert_cursor.execute(query, values)
            insert_conn.commit()
            
            new_song_id = insert_cursor.lastrowid
            insert_cursor.close()
            insert_conn.close()
            
            return new_song_id
        except mysql.connector.Error as e:
            if insert_conn:
                insert_conn.close()
            raise e
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        messagebox.showerror("Error", f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", f"Upload failed: {e}")
        return None

def generate_and_open_user_report():
    """Generate a user report and open it"""
    users = get_all_users()
    
    report_data = [
        {
            'User ID': user['user_id'],
            'First Name': user['first_name'],
            'Last Name': user['last_name'],
            'Email': user['email'],
            'Admin': 'Yes' if user['is_admin'] else 'No',
            'Created At': user['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
            'Playlists': user['playlist_count'],
            'Plays': user['listening_count']
        } for user in users
    ]
    
    # Updated filename format
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report-{timestamp}-users.csv"
    report_path = generate_report("users", report_data, filename)
    
    if report_path:
        messagebox.showinfo("Success", f"Report saved to: {report_path}")
        open_file(report_path)
    else:
        messagebox.showerror("Error", "Failed to generate report.")

def generate_and_open_song_report():
    """Generate a song report and open it"""
    songs = get_all_songs()
    
    report_data = [
        {
            'Song ID': song['song_id'],
            'Title': song['title'],
            'Artist': song['artist_name'],
            'Album': song.get('album_name', 'N/A'),
            'Genre': song.get('genre_name', 'N/A'),
            'Duration': song['duration_formatted'],
            'File Type': song.get('file_type', 'N/A'),
            'File Size': song['file_size_formatted'],
            'Upload Date': song['upload_date'].strftime('%Y-%m-%d %H:%M:%S')
        } for song in songs
    ]
    
    # Updated filename format
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"admin-songs-{timestamp}.csv"
    report_path = generate_report("songs", report_data, filename)
    
    if report_path:
        messagebox.showinfo("Success", f"Report saved to: {report_path}")
        open_file(report_path)
    else:
        messagebox.showerror("Error", "Failed to generate report.")
def generate_and_open_activity_report():
    """Generate an activity report and open it"""
    activities = get_recent_activities(limit=100)
    
    report_data = [
        {
            'Activity Type': activity[0],
            'Item': activity[1],
            'Time': activity[2]
        } for activity in activities
    ]
    
    # Updated filename format
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report-{timestamp}-activity.csv"
    report_path = generate_report("activity", report_data, filename)
    
    if report_path:
        messagebox.showinfo("Success", f"Report saved to: {report_path}")
        open_file(report_path)
    else:
        messagebox.showerror("Error", "Failed to generate report.")

# ------------------- Artist and Genre Functions -------------------
def get_artists():
    """Get list of artists from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT artist_id, name FROM Artists ORDER BY name")
        return cursor.fetchall()
        
    except mysql.connector.Error as e:
        print(f"Error fetching artists: {e}")
        return []
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def add_new_artist(name):
    """Add a new artist to the database"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        cursor.execute("SELECT artist_id FROM Artists WHERE name = %s", (name,))
        existing = cursor.fetchone()
        if existing:
            return existing[0]
            
        cursor.execute("INSERT INTO Artists (name) VALUES (%s)", (name,))
        connection.commit()
        return cursor.lastrowid
        
    except mysql.connector.Error as e:
        print(f"Error adding artist: {e}")
        return None
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def get_genres():
    """Get list of genres from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT genre_id, name FROM Genres ORDER BY name")
        return cursor.fetchall()
        
    except mysql.connector.Error as e:
        print(f"Error fetching genres: {e}")
        return []
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def add_new_genre(name):
    """Add a new genre to the database"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        cursor.execute("SELECT genre_id FROM Genres WHERE name = %s", (name,))
        existing = cursor.fetchone()
        if existing:
            return existing[0]
            
        cursor.execute("INSERT INTO Genres (name) VALUES (%s)", (name,))
        connection.commit()
        return cursor.lastrowid
        
    except mysql.connector.Error as e:
        print(f"Error adding genre: {e}")
        return None
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def get_or_create_album(album_name, artist_id):
    """Get album ID or create a new album"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        cursor.execute(
            "SELECT album_id FROM Albums WHERE title = %s AND artist_id = %s",
            (album_name, artist_id)
        )
        existing = cursor.fetchone()
        if existing:
            return existing[0]
            
        cursor.execute(
            "INSERT INTO Albums (title, artist_id) VALUES (%s, %s)",
            (album_name, artist_id)
        )
        connection.commit()
        return cursor.lastrowid
        
    except mysql.connector.Error as e:
        print(f"Error adding album: {e}")
        return None
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- Reports UI Functions -------------------
# Continuation from Reports UI Functions

def create_reports_frame(parent_frame, admin):
    """Create the modernized reports UI"""
    main_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Header
    header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
    header_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        header_frame,
        text="Reports & Analytics",
        font=("Inter", 28, "bold"),
        text_color=COLORS["text"]
    ).pack(side="left")
    
    ctk.CTkLabel(
        header_frame,
        text=f"{admin['first_name']} {admin['last_name']}",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    ).pack(side="right")
    
    ctk.CTkButton(
        header_frame,
        text="← Back",
        font=("Inter", 12),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        command=show_dashboard_view,
        width=120,
        height=32,
        corner_radius=8
    ).pack(side="right", padx=10)
    
    # Reports section
    reports_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["card"], corner_radius=12)
    reports_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    ctk.CTkLabel(
        reports_frame,
        text="Available Reports",
        font=("Inter", 20, "bold"),
        text_color=COLORS["primary"]
    ).pack(anchor="w", padx=20, pady=(20, 10))
    
    # Report buttons grid
    reports_grid = ctk.CTkFrame(reports_frame, fg_color="transparent")
    reports_grid.pack(fill="x", padx=20, pady=10)
    
    report_buttons = [
        ("Users Report", generate_and_open_user_report, COLORS["primary"]),
        ("Songs Report", generate_and_open_song_report, COLORS["secondary"]),
        #("Activity Report", generate_and_open_activity_report, COLORS["success"])
    ]
    
    for i, (text, command, color) in enumerate(report_buttons):
        btn = ctk.CTkButton(
            reports_grid,
            text=text,
            command=command,
            font=("Inter", 14),
            fg_color=color,
            #hover_color=COLORS[f"{color[1:]}_hover"] if color != COLORS["primary"] else COLORS["primary_hover"],
            height=48,
            corner_radius=8
        )
        btn.grid(row=i, column=0, padx=10, pady=10, sticky="ew")
        reports_grid.grid_columnconfigure(0, weight=1)
    
    # Report history section
    history_frame = ctk.CTkFrame(reports_frame, fg_color=COLORS["content"], corner_radius=8)
    history_frame.pack(fill="x", padx=20, pady=20)
    
    ctk.CTkLabel(
        history_frame,
        text="Recent Reports",
        font=("Inter", 16, "bold"),
        text_color=COLORS["text"]
    ).pack(anchor="w", padx=15, pady=(15, 5))
    
    try:
        reports_dir = APP_CONFIG["reports_dir"]
        report_files = sorted(
            [f for f in os.listdir(reports_dir) if f.endswith('.csv')],
            key=lambda x: os.path.getmtime(os.path.join(reports_dir, x)),
            reverse=True
        )[:5]
        
        if not report_files:
            ctk.CTkLabel(
                history_frame,
                text="No reports generated yet",
                font=("Inter", 14),
                text_color=COLORS["text_secondary"]
            ).pack(pady=20)
        else:
            for report in report_files:
                report_item = ctk.CTkFrame(history_frame, fg_color=COLORS["card"], corner_radius=8)
                report_item.pack(fill="x", pady=5)
                
                ctk.CTkLabel(
                    report_item,
                    text=report,
                    font=("Inter", 14),
                    text_color=COLORS["text"]
                ).pack(side="left", padx=15, pady=10)
                
                ctk.CTkButton(
                    report_item,
                    text="Open",
                    font=("Inter", 12),
                    fg_color=COLORS["secondary"],
                    hover_color=COLORS["secondary_hover"],
                    command=lambda r=report: open_file(os.path.join(reports_dir, r)),
                    width=80,
                    height=28,
                    corner_radius=8
                ).pack(side="right", padx=15)
                
    except Exception as e:
        print(f"Error listing reports: {e}")
        ctk.CTkLabel(
            history_frame,
            text="Unable to load report history",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=20)

def generate_and_open_activity_report():
    """Generate an activity report and open it"""
    activities = get_recent_activities(limit=100)
    
    report_data = [
        {
            'Activity Type': activity[0],
            'Item': activity[1],
            'Time': activity[2]
        } for activity in activities
    ]
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"admin_activity_{timestamp}.csv"
    report_path = generate_report("activity", report_data, filename)
    
    if report_path:
        messagebox.showinfo("Success", f"Report saved to: {report_path}")
        open_file(report_path)
    else:
        messagebox.showerror("Error", "Failed to generate report.")
def toggle_active_status(user_id, current_status):
    """Toggle user's active status"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        new_status = 0 if current_status else 1
        
        cursor.execute(
            "UPDATE Users SET is_active = %s WHERE user_id = %s",
            (new_status, user_id)
        )
        connection.commit()
        return True
        
    except mysql.connector.Error as e:
        print(f"Error updating active status: {e}")
        return False
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
def toggle_selected_active_status():
    """Toggle active status for selected user"""
    selected = users_tree.selection()
    if not selected:
        messagebox.showwarning("Warning", "Please select a user.")
        return
    
    user_id = users_tree.item(selected, 'values')[-1]
    user_name = users_tree.item(selected, 'values')[1]
    current_status = users_tree.item(selected, 'values')[4] == "Active"
    
    action = "deactivate" if current_status else "activate"
    confirm = messagebox.askyesno(
        "Confirm",
        f"Do you want to {action} user '{user_name}'?"
    )
    
    if confirm:
        if toggle_active_status(user_id, current_status):
            status = "deactivated" if current_status else "activated"
            messagebox.showinfo("Success", f"User '{user_name}' has been {status}.")
            refresh_user_list()
        else:
            messagebox.showerror("Error", f"Failed to {action} user '{user_name}'.")
def get_all_users():
    """Get all users from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT u.user_id, u.first_name, u.last_name, u.email, u.is_admin, u.is_active, u.created_at,
               COUNT(DISTINCT p.playlist_id) as playlist_count,
               COUNT(DISTINCT lh.history_id) as listening_count
        FROM Users u
        LEFT JOIN Playlists p ON u.user_id = p.user_id
        LEFT JOIN Listening_History lh ON u.user_id = lh.user_id
        GROUP BY u.user_id
        ORDER BY u.created_at DESC
        """
        
        cursor.execute(query)
        users = cursor.fetchall()
        
        return users
        
    except mysql.connector.Error as e:
        print(f"Error fetching users: {e}")
        messagebox.showerror("Error", f"Failed to fetch users: {e}")
        return []
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- Main Application Setup -------------------
def create_main_window():
    """Create the main application window with modernized UI"""
    # global root, content_frame
    
    # root = ctk.CTk()
    # root.title(f"{APP_CONFIG['name']} v{APP_CONFIG['version']}")
    # root.geometry("1200x700")
    global root, content_frame
    
    root = ctk.CTk()
    root.title(f"{APP_CONFIG['name']} v{APP_CONFIG['version']}")
    
    # Maximize the window
    root.state('zoomed')
    
    # # Center window
    # root.update_idletasks()
    # width = root.winfo_width()
    # height = root.winfo_height()
    # x = (root.winfo_screenwidth() // 2) - (width // 2)
    # y = (root.winfo_screenheight() // 2) - (height // 2)
    # root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Main frame
    main_frame = ctk.CTkFrame(root, fg_color=COLORS["background"])
    main_frame.pack(fill="both", expand=True)
    
    # Sidebar
    sidebar_frame = ctk.CTkFrame(
        main_frame,
        fg_color=COLORS["sidebar"],
        width=250,
        corner_radius=0
    )
    sidebar_frame.pack(side="left", fill="y")
    sidebar_frame.pack_propagate(False)
    
    # Sidebar header
    ctk.CTkLabel(
        sidebar_frame,
        text=APP_CONFIG["name"],
        font=("Inter", 20, "bold"),
        text_color=COLORS["primary"]
    ).pack(pady=(30, 20), padx=20)
    
    # Navigation buttons
    nav_buttons = [
        ("🏠 Dashboard", show_dashboard_view, COLORS["primary"]),
        ("👥 Users", show_users_view, COLORS["primary"]),
        ("🎵 Songs", show_songs_view, COLORS["primary"]),
        #("📁 Playlists", show_playlist_view, COLORS["primary"]),
        ("📊 Reports", show_reports_view, COLORS["primary"])
    ]
    
    for text, command, color in nav_buttons:
        btn = ctk.CTkButton(
            sidebar_frame,
            text=text,
            command=command,
            font=("Inter", 14),
            fg_color="transparent",
            hover_color=COLORS["primary_hover"],
            text_color=COLORS["text"],
            anchor="w",
            height=40,
            corner_radius=8
        )
        btn.pack(fill="x", padx=10, pady=5)
    
    # Sidebar footer
    ctk.CTkButton(
        sidebar_frame,
        text="🚪 Logout",
        command=open_login_page,
        font=("Inter", 14),
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        height=40,
        corner_radius=8
    ).pack(side="bottom", fill="x", padx=10, pady=20)
    
    # Content frame
    content_frame = ctk.CTkFrame(
        main_frame,
        fg_color=COLORS["background"],
        corner_radius=0
    )
    content_frame.pack(side="left", fill="both", expand=True)
    
    # Verify admin and show dashboard
    admin = get_admin_info()
    if admin:
        show_dashboard_view()
    else:
        root.destroy()
        return
    
    root.mainloop()

# ------------------- Entry Point -------------------
if __name__ == "__main__":
    ensure_directories_exist()
    create_main_window()