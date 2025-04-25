"""
Admin views for the Online Music Player application.
Includes:
- Dashboard
- User Management
- Song Management
- Playlist Management
- Reports
"""

import os
import sys
import subprocess
import datetime
import customtkinter as ctk
from tkinter import messagebox, simpledialog, ttk, filedialog
import mysql.connector
import hashlib

# Add parent directory to path so we can import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from other modules
from config import UI_CONFIG, COLORS, APP_CONFIG
from utils import connect_db, get_admin_info, hash_password, ensure_directories_exist, generate_report, open_file

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
        
        # Get user count
        cursor.execute("SELECT COUNT(*) FROM Users")
        total_users = cursor.fetchone()[0]
        
        # Get song count
        cursor.execute("SELECT COUNT(*) FROM Songs")
        total_songs = cursor.fetchone()[0]
        
        # Get playlist count
        cursor.execute("SELECT COUNT(*) FROM Playlists")
        total_playlists = cursor.fetchone()[0]
        
        # Approximate downloads (listening history entries)
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
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_recent_activities(limit=4):
    """Get recent system activities"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Get recent user registrations
        user_query = """
        SELECT 'user_registered' as activity_type, 
               CONCAT(first_name, ' ', last_name) as item,
               created_at as timestamp
        FROM Users
        ORDER BY created_at DESC
        LIMIT %s
        """
        
        # Get recent song uploads
        song_query = """
        SELECT 'song_uploaded' as activity_type,
               CONCAT(s.title, ' - ', a.name) as item,
               s.upload_date as timestamp
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        ORDER BY s.upload_date DESC
        LIMIT %s
        """
        
        # Get recent playlist creations
        playlist_query = """
        SELECT 'playlist_created' as activity_type,
               p.name as item,
               p.created_at as timestamp
        FROM Playlists p
        ORDER BY p.created_at DESC
        LIMIT %s
        """
        
        # Get recent listening activity (downloads)
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
        
        # Execute all queries
        cursor.execute(user_query, (limit,))
        users = cursor.fetchall()
        
        cursor.execute(song_query, (limit,))
        songs = cursor.fetchall()
        
        cursor.execute(playlist_query, (limit,))
        playlists = cursor.fetchall()
        
        cursor.execute(download_query, (limit,))
        downloads = cursor.fetchall()
        
        # Combine all activities
        all_activities = users + songs + playlists + downloads
        
        # Sort by timestamp (most recent first)
        all_activities.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Limit to requested number
        all_activities = all_activities[:limit]
        
        # Format activities for display
        formatted_activities = []
        for activity in all_activities:
            activity_type = activity["activity_type"]
            item = activity["item"]
            timestamp = activity["timestamp"]
            
            # Calculate relative time
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
            
            # Format action based on activity type
            if activity_type == "user_registered":
                action = "👤 New user registered"
            elif activity_type == "song_uploaded":
                action = "🎵 New song uploaded"
            elif activity_type == "playlist_created":
                action = "📁 Playlist created"
            elif activity_type == "song_played":
                action = "⬇️ Song played"
            else:
                action = "🔄 System activity"
            
            formatted_activities.append((action, item, time_str))
        
        return formatted_activities
        
    except mysql.connector.Error as e:
        print(f"Error getting recent activities: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
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
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def delete_user(user_id):
    """Delete a user from the database"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Check if this is an admin user
        cursor.execute("SELECT is_admin FROM Users WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        
        if result and result[0] == 1:
            messagebox.showerror("Error", "Cannot delete an admin user.")
            return False
        
        # The foreign key constraints with ON DELETE CASCADE should
        # automatically delete related records in other tables
        cursor.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
        
        connection.commit()
        return True
        
    except mysql.connector.Error as e:
        print(f"Error deleting user: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def toggle_admin_status(user_id, current_status):
    """Toggle user's admin status"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        # Toggle the admin status
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
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def add_new_user(first_name, last_name, email, password, is_admin=0):
    """Add a new user to the database"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT user_id FROM Users WHERE email = %s", (email,))
        if cursor.fetchone():
            messagebox.showerror("Error", "A user with this email already exists.")
            return None
        
        # Hash the password
        hashed_password = hash_password(password)
        
        # Insert user
        cursor.execute(
            "INSERT INTO Users (first_name, last_name, email, password, is_admin) VALUES (%s, %s, %s, %s, %s)",
            (first_name, last_name, email, hashed_password, is_admin)
        )
        
        # Get new user ID
        new_user_id = cursor.lastrowid
        
        # Create default playlist for user
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
        if 'connection' in locals() and connection and connection.is_connected():
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
               g.name as genre_name, s.duration, s.file_size, s.file_type, s.upload_date
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Albums al ON s.album_id = al.album_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        ORDER BY s.upload_date DESC
        """
        
        cursor.execute(query)
        songs = cursor.fetchall()
        
        return songs
        
    except mysql.connector.Error as e:
        print(f"Error fetching songs: {e}")
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
        
        # First delete from related tables to avoid foreign key constraints
        tables = [
            "Playlist_Songs",
            "User_Favorites",
            "Listening_History"
        ]
        
        for table in tables:
            cursor.execute(f"DELETE FROM {table} WHERE song_id = %s", (song_id,))
        
        # Now delete the song itself
        cursor.execute("DELETE FROM Songs WHERE song_id = %s", (song_id,))
        
        connection.commit()
        return True
        
    except mysql.connector.Error as e:
        print(f"Error deleting song: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- Report Generation Functions -------------------
def generate_user_report():
    """Generate a report of all users"""
    users = get_all_users()
    
    # Format data for report
    report_data = []
    for user in users:
        report_data.append({
            'User ID': user['user_id'],
            'First Name': user['first_name'],
            'Last Name': user['last_name'],
            'Email': user['email'],
            'Admin': 'Yes' if user['is_admin'] else 'No',
            'Created At': user['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
            'Playlists Count': user['playlist_count'],
            'Listening Count': user['listening_count']
        })
    
    # Generate and save the report
    filename = "users_report.csv"
    report_path = generate_report("users", report_data, filename)
    
    if report_path:
        messagebox.showinfo("Report Generated", f"User report has been saved to: {report_path}")
        return report_path
    else:
        messagebox.showerror("Error", "Failed to generate user report.")
        return None

def generate_song_report():
    """Generate a report of all songs"""
    songs = get_all_songs()
    
    # Format data for report
    report_data = []
    for song in songs:
        # Format duration to MM:SS
        minutes, seconds = divmod(song['duration'] or 0, 60)
        duration_formatted = f"{minutes}:{seconds:02d}"
        
        report_data.append({
            'Song ID': song['song_id'],
            'Title': song['title'],
            'Artist': song['artist_name'],
            'Album': song['album_name'] or 'N/A',
            'Genre': song['genre_name'] or 'N/A',
            'Duration': duration_formatted,
            'File Type': song['file_type'],
            'File Size (bytes)': song['file_size'],
            'Upload Date': song['upload_date'].strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # Generate and save the report
    filename = "songs_report.csv"
    report_path = generate_report("songs", report_data, filename)
    
    if report_path:
        messagebox.showinfo("Report Generated", f"Song report has been saved to: {report_path}")
        return report_path
    else:
        messagebox.showerror("Error", "Failed to generate song report.")
        return None

def generate_activity_report():
    """Generate a report of recent activities"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor(dictionary=True)
        
        # Query for more comprehensive activity report
        query = """
        SELECT 
            'User Registration' as activity_type,
            CONCAT(first_name, ' ', last_name) as description,
            created_at as timestamp
        FROM 
            Users
        UNION ALL
        SELECT 
            'Song Upload' as activity_type,
            CONCAT(s.title, ' by ', a.name) as description,
            s.upload_date as timestamp
        FROM 
            Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
        UNION ALL
        SELECT 
            'Playlist Creation' as activity_type,
            CONCAT(p.name, ' by ', u.first_name, ' ', u.last_name) as description,
            p.created_at as timestamp
        FROM 
            Playlists p
            JOIN Users u ON p.user_id = u.user_id
        UNION ALL
        SELECT 
            'Song Played' as activity_type,
            CONCAT(s.title, ' by ', a.name, ' - played by ', u.first_name, ' ', u.last_name) as description,
            lh.played_at as timestamp
        FROM 
            Listening_History lh
            JOIN Songs s ON lh.song_id = s.song_id
            JOIN Artists a ON s.artist_id = a.artist_id
            JOIN Users u ON lh.user_id = u.user_id
        ORDER BY 
            timestamp DESC
        LIMIT 
            500
        """
        
        cursor.execute(query)
        activities = cursor.fetchall()
        
        # Format data for report
        report_data = []
        for activity in activities:
            report_data.append({
                'Activity Type': activity['activity_type'],
                'Description': activity['description'],
                'Timestamp': activity['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Generate and save the report
        filename = "activity_report.csv"
        report_path = generate_report("activity", report_data, filename)
        
        if report_path:
            messagebox.showinfo("Report Generated", f"Activity report has been saved to: {report_path}")
            return report_path
        else:
            messagebox.showerror("Error", "Failed to generate activity report.")
            return None
        
    except mysql.connector.Error as e:
        print(f"Error generating activity report: {e}")
        return None
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- UI Functions -------------------
def create_dashboard_frame(parent_frame, admin):
    """Create the dashboard UI"""
    # Get system stats
    stats = get_system_stats()
    
    # Header with username
    header_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], height=40)
    header_frame.pack(fill="x", padx=20, pady=(20, 0))

    # Left side: Admin Dashboard
    dashboard_label = ctk.CTkLabel(header_frame, text="Admin Dashboard", 
                                  font=("Arial", 24, "bold"), text_color="white")
    dashboard_label.pack(side="left")

    # Right side: Admin Name
    admin_label = ctk.CTkLabel(header_frame, 
                             text=f"Hello, {admin['first_name']} {admin['last_name']}!", 
                             font=("Arial", 14), text_color=COLORS["text_secondary"])
    admin_label.pack(side="right")

    # Refresh button on header
    refresh_btn = ctk.CTkButton(header_frame, text="🔄 Refresh", font=("Arial", 12), 
                              fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"], 
                              text_color="white", corner_radius=5, 
                              width=100, height=30, command=refresh_dashboard)
    refresh_btn.pack(side="right", padx=15)

    # ---------------- Quick Overview Section ----------------
    overview_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    overview_frame.pack(fill="x", padx=20, pady=(40, 20))

    # Section title
    overview_title = ctk.CTkLabel(overview_frame, text="Quick Overview 📊", 
                                 font=("Arial", 20, "bold"), text_color=COLORS["primary"])
    overview_title.pack(anchor="w", pady=(0, 15))

    # Stats grid container
    stats_frame = ctk.CTkFrame(overview_frame, fg_color=COLORS["content"])
    stats_frame.pack(fill="x")

    # Stats cards
    stat_colors = [
        ("👥 Total Users", "#16A34A"),  # Green
        ("🎵 Total Songs", "#2563EB"),  # Blue
        ("📁 Playlists Created", "#FACC15"),  # Yellow
        ("⬇️ Total Plays", "#DC2626")  # Red
    ]

    # Create global references to stat labels for updating
    global user_count_label, song_count_label, playlist_count_label, download_count_label
    user_count_label = None
    song_count_label = None
    playlist_count_label = None
    download_count_label = None

    # Create stats cards
    for i, (name, color) in enumerate(stat_colors):
        stat_card = ctk.CTkFrame(stats_frame, fg_color=COLORS["card"], corner_radius=10, width=160, height=90)
        stat_card.pack(side="left", padx=10, expand=True)
        stat_card.pack_propagate(False)  # Keep fixed size
        
        # Center the content vertically
        stat_icon = ctk.CTkLabel(stat_card, text=name, font=("Arial", 12, "bold"), text_color="white")
        stat_icon.pack(pady=(20, 5))
        
        # Get the correct stat value
        if i == 0:  # Users
            stat_value = stats["total_users"]
            user_count_label = ctk.CTkLabel(stat_card, text=str(stat_value), font=("Arial", 22, "bold"), text_color=color)
            user_count_label.pack()
        elif i == 1:  # Songs
            stat_value = stats["total_songs"]
            song_count_label = ctk.CTkLabel(stat_card, text=str(stat_value), font=("Arial", 22, "bold"), text_color=color)
            song_count_label.pack()
        elif i == 2:  # Playlists
            stat_value = stats["total_playlists"]
            playlist_count_label = ctk.CTkLabel(stat_card, text=str(stat_value), font=("Arial", 22, "bold"), text_color=color)
            playlist_count_label.pack()
        elif i == 3:  # Downloads/Plays
            stat_value = stats["total_downloads"]
            download_count_label = ctk.CTkLabel(stat_card, text=str(stat_value), font=("Arial", 22, "bold"), text_color=color)
            download_count_label.pack()

    # ---------------- Manage Actions Section ----------------
    actions_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    actions_frame.pack(fill="x", padx=20, pady=(20, 0))

    # Section title
    actions_title = ctk.CTkLabel(actions_frame, text="Manage System ⚙️", 
                                font=("Arial", 20, "bold"), text_color=COLORS["primary"])
    actions_title.pack(anchor="w", pady=(0, 15))

    # Action buttons container
    buttons_frame = ctk.CTkFrame(actions_frame, fg_color=COLORS["content"])
    buttons_frame.pack(fill="x")

    # Action buttons with commands
    manage_users_action = ctk.CTkButton(buttons_frame, text="👥 Manage Users", 
                                       font=("Arial", 14, "bold"), 
                                       fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], 
                                       text_color="white", height=50, corner_radius=8,
                                       command=lambda: show_users_view())
    manage_users_action.pack(side="left", padx=10, expand=True)

    manage_songs_action = ctk.CTkButton(buttons_frame, text="🎵 Manage Songs", 
                                       font=("Arial", 14, "bold"), 
                                       fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"], 
                                       text_color="white", height=50, corner_radius=8,
                                       command=lambda: show_songs_view())
    manage_songs_action.pack(side="left", padx=10, expand=True)

    manage_playlists_action = ctk.CTkButton(buttons_frame, text="📁 Manage Playlists", 
                                          font=("Arial", 14, "bold"), 
                                          fg_color=COLORS["success"], hover_color=COLORS["success_hover"], 
                                          text_color="white", height=50, corner_radius=8,
                                          command=lambda: show_playlists_view())
    manage_playlists_action.pack(side="left", padx=10, expand=True)

    # ---------------- Recent Activity Section ----------------
    activity_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    activity_frame.pack(fill="both", expand=True, padx=20, pady=(20, 20))

    # Section title
    activity_title = ctk.CTkLabel(activity_frame, text="Recent Activity 📝", 
                                 font=("Arial", 20, "bold"), text_color=COLORS["primary"])
    activity_title.pack(anchor="w", pady=(0, 15))

    # Activity list container
    global activity_list_frame
    activity_list_frame = ctk.CTkFrame(activity_frame, fg_color=COLORS["card"], corner_radius=10)
    activity_list_frame.pack(fill="both", expand=True)

    # Get recent activities
    activities = get_recent_activities()

    # Display activities
    if not activities:
        no_activity_label = ctk.CTkLabel(
            activity_list_frame, 
            text="No recent activities found", 
            font=("Arial", 12), 
            text_color=COLORS["text_secondary"]
        )
        no_activity_label.pack(pady=20)
    else:
        for action, item, time in activities:
            activity_item = ctk.CTkFrame(activity_list_frame, fg_color=COLORS["card"], height=40)
            activity_item.pack(fill="x", padx=10, pady=5)
            
            action_label = ctk.CTkLabel(activity_item, text=action, font=("Arial", 12, "bold"), text_color="white")
            action_label.pack(side="left", padx=10)
            
            item_label = ctk.CTkLabel(activity_item, text=item, font=("Arial", 12), text_color=COLORS["text_secondary"])
            item_label.pack(side="left", padx=10)
            
            time_label = ctk.CTkLabel(activity_item, text=time, font=("Arial", 12), text_color=COLORS["primary"])
            time_label.pack(side="right", padx=10)
    
    return parent_frame

def create_users_frame(parent_frame, admin):
    """Create the user management UI"""
    # Header
    header_frame = ctk.CTkFrame(parent_frame, height=60, fg_color=COLORS["card"])
    header_frame.pack(fill="x", padx=10, pady=10)
    
    # Title
    ctk.CTkLabel(
        header_frame, 
        text="Manage Users", 
        font=("Arial", 24, "bold"),
        text_color=COLORS["primary"]
    ).pack(side="left", padx=20)
    
    # Admin name
    ctk.CTkLabel(
        header_frame,
        text=f"Admin: {admin['first_name']} {admin['last_name']}",
        font=("Arial", 14)
    ).pack(side="right", padx=20)
    
    # Back button
    back_btn = ctk.CTkButton(
        header_frame,
        text="← Back to Dashboard",
        command=lambda: show_dashboard_view(),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        height=32
    )
    back_btn.pack(side="right", padx=20)
    
    # Content area
    content_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    # Action buttons
    action_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["content"], height=50)
    action_frame.pack(fill="x", padx=20, pady=20)
    
    # Add user button
    add_btn = ctk.CTkButton(
        action_frame,
        text="+ Add New User",
        command=lambda: handle_add_user(),
        fg_color=COLORS["success"],
        hover_color=COLORS["success_hover"],
        height=40
    )
    add_btn.pack(side="left", padx=(0, 10))
    
    # Delete user button
    delete_btn = ctk.CTkButton(
        action_frame,
        text="🗑️ Delete Selected User",
        command=lambda: confirm_delete_user(),
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        height=40
    )
    delete_btn.pack(side="left", padx=(0, 10))
    
    # Toggle admin button
    toggle_admin_btn = ctk.CTkButton(
        action_frame,
        text="👑 Toggle Admin Status",
        command=lambda: toggle_selected_admin_status(),
        fg_color=COLORS["warning"],
        hover_color=COLORS["warning_hover"],
        text_color="black",
        height=40
    )
    toggle_admin_btn.pack(side="left")
    
    # Refresh button
    refresh_btn = ctk.CTkButton(
        action_frame,
        text="🔄 Refresh List",
        command=lambda: refresh_user_list(),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        height=40
    )
    refresh_btn.pack(side="right")
    
    # Users list with scrollbar
    users_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["card"])
    users_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    # Create Treeview with ttk.Scrollbar
    tree_frame = ctk.CTkFrame(users_frame)
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Create a custom style for the Treeview
    style = ttk.Style()
    style.theme_use("default")
    
    # Configure colors for dark mode
    style.configure(
        "Treeview",
        background=COLORS["card"],
        foreground="white",
        fieldbackground=COLORS["card"],
        borderwidth=0
    )
    style.map(
        "Treeview", 
        background=[("selected", COLORS["primary"])],
        foreground=[("selected", "white")]
    )
    
    # Add scrollbar
    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")
    
    # Create Treeview with columns
    global users_tree
    users_tree = ttk.Treeview(
        tree_frame,
        columns=("id", "name", "email", "admin", "created", "playlists", "history", "user_id"),
        show="headings",
        height=20,
        yscrollcommand=tree_scroll.set
    )
    users_tree.pack(fill="both", expand=True)
    
    # Configure scrollbar
    tree_scroll.config(command=users_tree.yview)
    
    # Format columns
    users_tree.heading("id", text="#")
    users_tree.heading("name", text="Name")
    users_tree.heading("email", text="Email")
    users_tree.heading("admin", text="Admin")
    users_tree.heading("created", text="Created")
    users_tree.heading("playlists", text="Playlists")
    users_tree.heading("history", text="Plays")
    users_tree.heading("user_id", text="ID")
    
    # Set column widths and alignment
    users_tree.column("id", width=40, anchor="center")
    users_tree.column("name", width=180, anchor="w")
    users_tree.column("email", width=200, anchor="w")
    users_tree.column("admin", width=80, anchor="center")
    users_tree.column("created", width=100, anchor="center")
    users_tree.column("playlists", width=80, anchor="center")
    users_tree.column("history", width=80, anchor="center")
    users_tree.column("user_id", width=50, anchor="center")
    
    # Statistics footer
    stats_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["content"], height=30)
    stats_frame.pack(fill="x", padx=20, pady=(0, 10))
    
    global stats_label
    stats_label = ctk.CTkLabel(
        stats_frame,
        text="Loading users...",
        font=("Arial", 12),
        text_color=COLORS["text_secondary"]
    )
    stats_label.pack(side="left")

    # Generate report button
    report_btn = ctk.CTkButton(
        stats_frame,
        text="📊 Generate Report",
        command=lambda: generate_and_open_user_report(),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        height=30
    )
    report_btn.pack(side="right")
    
    # Initial load of users
    refresh_user_list()
    
    return parent_frame

def create_songs_frame(parent_frame, admin):
    """Create the song management UI"""
    # Header
    header_frame = ctk.CTkFrame(parent_frame, height=60, fg_color=COLORS["card"])
    header_frame.pack(fill="x", padx=10, pady=10)
    
    # Title
    ctk.CTkLabel(
        header_frame, 
        text="Manage Songs", 
        font=("Arial", 24, "bold"),
        text_color=COLORS["primary"]
    ).pack(side="left", padx=20)
    
    # Admin name
    ctk.CTkLabel(
        header_frame,
        text=f"Admin: {admin['first_name']} {admin['last_name']}",
        font=("Arial", 14)
    ).pack(side="right", padx=20)
    
    # Back button
    back_btn = ctk.CTkButton(
        header_frame,
        text="← Back to Dashboard",
        command=lambda: show_dashboard_view(),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        height=32
    )
    back_btn.pack(side="right", padx=20)
    
    # Content area
    content_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    # Action buttons
    action_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["content"], height=50)
    action_frame.pack(fill="x", padx=20, pady=20)
    
    # Upload button
    upload_btn = ctk.CTkButton(
        action_frame,
        text="+ Upload New Song",
        command=lambda: handle_upload_song(),
        fg_color=COLORS["success"],
        hover_color=COLORS["success_hover"],
        height=40
    )
    upload_btn.pack(side="left", padx=(0, 10))
    
    # Delete button
    delete_btn = ctk.CTkButton(
        action_frame,
        text="🗑️ Delete Selected Song",
        command=lambda: confirm_delete_song(),
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        height=40
    )
    delete_btn.pack(side="left")
    
    # Refresh button
    refresh_btn = ctk.CTkButton(
        action_frame,
        text="🔄 Refresh List",
        command=lambda: refresh_song_list(),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        height=40
    )
    refresh_btn.pack(side="right")
    
    # Songs list with scrollbar
    songs_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["card"])
    songs_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
    
    # Create Treeview with ttk.Scrollbar
    tree_frame = ctk.CTkFrame(songs_frame)
    tree_frame.pack(fill="both", expand=True, padx=10, pady=10)
    
    # Create a custom style for the Treeview
    style = ttk.Style()
    style.theme_use("default")
    
    # Configure colors for dark mode
    style.configure(
        "Treeview",
        background=COLORS["card"],
        foreground="white",
        fieldbackground=COLORS["card"],
        borderwidth=0
    )
    style.map(
        "Treeview", 
        background=[("selected", COLORS["primary"])],
        foreground=[("selected", "white")]
    )
    
    # Add scrollbar
    tree_scroll = ttk.Scrollbar(tree_frame)
    tree_scroll.pack(side="right", fill="y")
    
    # Create Treeview with columns
    global songs_tree
    songs_tree = ttk.Treeview(
        tree_frame,
        columns=("id", "title", "artist", "genre", "duration", "size", "song_id"),
        show="headings",
        height=20,
        yscrollcommand=tree_scroll.set
    )
    songs_tree.pack(fill="both", expand=True)
    
    # Configure scrollbar
    tree_scroll.config(command=songs_tree.yview)
    
    # Format columns
    songs_tree.heading("id", text="#")
    songs_tree.heading("title", text="Title")
    songs_tree.heading("artist", text="Artist")
    songs_tree.heading("genre", text="Genre")
    songs_tree.heading("duration", text="Duration")
    songs_tree.heading("size", text="Size")
    songs_tree.heading("song_id", text="ID")
    
    # Set column widths and alignment
    songs_tree.column("id", width=50, anchor="center")
    songs_tree.column("title", width=250, anchor="w")
    songs_tree.column("artist", width=150, anchor="w")
    songs_tree.column("genre", width=100, anchor="w")
    songs_tree.column("duration", width=80, anchor="center")
    songs_tree.column("size", width=80, anchor="e")
    songs_tree.column("song_id", width=50, anchor="center")
    
    # Statistics footer
    stats_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["content"], height=30)
    stats_frame.pack(fill="x", padx=20, pady=(0, 10))
    
    global song_stats_label
    song_stats_label = ctk.CTkLabel(
        stats_frame,
        text="Loading songs...",
        font=("Arial", 12),
        text_color=COLORS["text_secondary"]
    )
    song_stats_label.pack(side="left")
    
    # Generate report button
    report_btn = ctk.CTkButton(
        stats_frame,
        text="📊 Generate Report",
        command=lambda: generate_and_open_song_report(),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        height=30
    )
    report_btn.pack(side="right")
    
    # Initial load of songs
    refresh_song_list()
    
    return parent_frame

def create_reports_frame(parent_frame, admin):
    """Create the reports UI"""
    # Header
    header_frame = ctk.CTkFrame(parent_frame, height=60, fg_color=COLORS["card"])
    header_frame.pack(fill="x", padx=10, pady=10)
    
    # Title
    ctk.CTkLabel(
        header_frame, 
        text="Reports & Analytics", 
        font=("Arial", 24, "bold"),
        text_color=COLORS["primary"]
    ).pack(side="left", padx=20)
    
    # Admin name
    ctk.CTkLabel(
        header_frame,
        text=f"Admin: {admin['first_name']} {admin['last_name']}",
        font=("Arial", 14)
    ).pack(side="right", padx=20)
    
    # Back button
    back_btn = ctk.CTkButton(
        header_frame,
        text="← Back to Dashboard",
        command=lambda: show_dashboard_view(),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        height=32
    )
    back_btn.pack(side="right", padx=20)
    
    # Content area
    content_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    content_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    # Title
    ctk.CTkLabel(
        content_frame,
        text="Generate and Download Reports",
        font=("Arial", 20, "bold"),
        text_color="white"
    ).pack(pady=(20, 10))
    
    # Description
    ctk.CTkLabel(
        content_frame,
        text="Generate CSV reports for system data and analysis",
        font=("Arial", 14),
        text_color=COLORS["text_secondary"]
    ).pack(pady=(0, 30))
    
    # Reports container
    reports_container = ctk.CTkFrame(content_frame, fg_color=COLORS["content"])
    reports_container.pack(fill="both", expand=True, padx=40)
    
    # Grid of report options
    reports = [
        {
            "title": "User Report", 
            "description": "List of all users with their activity data",
            "icon": "👤",
            "command": generate_and_open_user_report
        },
        {
            "title": "Song Report", 
            "description": "List of all songs in the system",
            "icon": "🎵",
            "command": generate_and_open_song_report
        },
        {
            "title": "Activity Report", 
            "description": "Recent system activities (registrations, uploads, etc.)",
            "icon": "📊",
            "command": generate_and_open_activity_report
        }
    ]
    
    for i, report in enumerate(reports):
        report_card = ctk.CTkFrame(reports_container, fg_color=COLORS["card"], corner_radius=10)
        report_card.pack(fill="x", pady=10, ipady=20)
        
        # Icon
        icon_label = ctk.CTkLabel(report_card, text=report["icon"], font=("Arial", 30))
        icon_label.pack(side="left", padx=20)
        
        # Info container
        info_frame = ctk.CTkFrame(report_card, fg_color=COLORS["card"])
        info_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        # Title
        ctk.CTkLabel(
            info_frame, 
            text=report["title"], 
            font=("Arial", 16, "bold"), 
            text_color="white"
        ).pack(anchor="w")
        
        # Description
        ctk.CTkLabel(
            info_frame, 
            text=report["description"], 
            font=("Arial", 12), 
            text_color=COLORS["text_secondary"]
        ).pack(anchor="w", pady=(5, 0))
        
        # Generate button
        generate_btn = ctk.CTkButton(
            report_card,
            text="Generate Report",
            command=report["command"],
            font=("Arial", 14),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            height=36,
            width=160
        )
        generate_btn.pack(side="right", padx=20)
    
    # Note about reports
    note_frame = ctk.CTkFrame(content_frame, fg_color=COLORS["content"])
    note_frame.pack(fill="x", padx=20, pady=20)
    
    ctk.CTkLabel(
        note_frame,
        text="Note: Reports are saved in the 'reports' folder and will open automatically after generation.",
        font=("Arial", 12, "italic"),
        text_color=COLORS["text_secondary"]
    ).pack()
    
    return parent_frame

# ------------------- Helper Functions -------------------
def refresh_dashboard():
    """Refresh the dashboard data"""
    # Update stats
    stats = get_system_stats()
    
    # Update stat values
    user_count_label.configure(text=str(stats["total_users"]))
    song_count_label.configure(text=str(stats["total_songs"]))
    playlist_count_label.configure(text=str(stats["total_playlists"]))
    download_count_label.configure(text=str(stats["total_downloads"]))
    
    # Update recent activities
    # First, clear existing activities
    for widget in activity_list_frame.winfo_children():
        widget.destroy()
    
    # Get fresh activities
    activities = get_recent_activities()
    
    # Display activities
    if not activities:
        no_activity_label = ctk.CTkLabel(
            activity_list_frame, 
            text="No recent activities found", 
            font=("Arial", 12), 
            text_color=COLORS["text_secondary"]
        )
        no_activity_label.pack(pady=20)
    else:
        for action, item, time in activities:
            activity_item = ctk.CTkFrame(activity_list_frame, fg_color=COLORS["card"], height=40)
            activity_item.pack(fill="x", padx=10, pady=5)
            
            action_label = ctk.CTkLabel(activity_item, text=action, font=("Arial", 12, "bold"), text_color="white")
            action_label.pack(side="left", padx=10)
            
            item_label = ctk.CTkLabel(activity_item, text=item, font=("Arial", 12), text_color=COLORS["text_secondary"])
            item_label.pack(side="left", padx=10)
            
            time_label = ctk.CTkLabel(activity_item, text=time, font=("Arial", 12), text_color=COLORS["primary"])
            time_label.pack(side="right", padx=10)

def refresh_user_list():
    """Refresh the user list display"""
    # Clear the treeview
    for item in users_tree.get_children():
        users_tree.delete(item)
    
    # Get updated users
    users = get_all_users()
    
    # Add users to treeview
    for i, user in enumerate(users, 1):
        # Format admin status
        admin_status = "Yes" if user["is_admin"] else "No"
        
        # Format created date
        created_date = user["created_at"].strftime("%Y-%m-%d")
        
        users_tree.insert(
            "", "end", 
            values=(
                i,
                f"{user['first_name']} {user['last_name']}",
                user["email"],
                admin_status,
                created_date,
                user["playlist_count"],
                user["listening_count"],
                user["user_id"]
            )
        )
    
    # Update stats
    stats_label.configure(text=f"Total Users: {len(users_tree.get_children())}")

def refresh_song_list():
    """Refresh the song list display"""
    # Clear the treeview
    for item in songs_tree.get_children():
        songs_tree.delete(item)
    
    # Get updated songs
    songs = get_all_songs()
    
    # Add songs to treeview
    for i, song in enumerate(songs, 1):
        # Format durations to MM:SS
        minutes, seconds = divmod(song['duration'] or 0, 60)
        duration_formatted = f"{minutes}:{seconds:02d}"
        
        # Format file size
        file_size = ""
        if song['file_size']:
            # Get size in KB or MB
            size = song['file_size']
            if size > 1024 * 1024:  # MB
                file_size = f"{size / (1024 * 1024):.1f} MB"
            else:  # KB
                file_size = f"{size / 1024:.1f} KB"
        
        songs_tree.insert(
            "", "end", 
            values=(
                i,
                song["title"], 
                song["artist_name"], 
                song["genre_name"] or "", 
                duration_formatted, 
                file_size,
                song["song_id"]
            )
        )
    
    # Update stats
    song_stats_label.configure(text=f"Total Songs: {len(songs_tree.get_children())}")

def confirm_delete_user():
    """Confirm and delete selected user"""
    selected = users_tree.selection()
    if not selected:
        messagebox.showwarning("Selection Required", "Please select a user to delete.")
        return
    
    # Get the user ID from the selected item
    user_id = users_tree.item(selected, 'values')[-1]  # Last column contains user_id
    user_name = users_tree.item(selected, 'values')[1]  # Second column contains name
    
    # Confirmation dialog
    confirm = messagebox.askyesno(
        "Confirm Delete", 
        f"Are you sure you want to delete the user '{user_name}'?\n\nThis will delete ALL data associated with this user, including playlists and listening history.\n\nThis action cannot be undone."
    )
    
    if confirm:
        if delete_user(user_id):
            messagebox.showinfo("Success", f"User '{user_name}' deleted successfully!")
            refresh_user_list()
        else:
            messagebox.showerror("Error", f"Failed to delete user '{user_name}'.")

def toggle_selected_admin_status():
    """Toggle admin status for selected user"""
    selected = users_tree.selection()
    if not selected:
        messagebox.showwarning("Selection Required", "Please select a user to modify.")
        return
    
    # Get the user info from the selected item
    user_id = users_tree.item(selected, 'values')[-1]  # Last column contains user_id
    user_name = users_tree.item(selected, 'values')[1]  # Second column contains name
    current_status = users_tree.item(selected, 'values')[3] == "Yes"  # Fourth column is admin status
    
    # New status message
    new_status_msg = "remove admin privileges from" if current_status else "grant admin privileges to"
    
    # Confirmation dialog
    confirm = messagebox.askyesno(
        "Confirm Admin Status Change", 
        f"Are you sure you want to {new_status_msg} '{user_name}'?"
    )
    
    if confirm:
        if toggle_admin_status(user_id, current_status):
            status_msg = "removed from" if current_status else "granted to"
            messagebox.showinfo("Success", f"Admin privileges {status_msg} '{user_name}' successfully!")