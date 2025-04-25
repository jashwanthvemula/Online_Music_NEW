"""
User views for the Online Music Player application.
Handles all user-facing screens including:
- Home page
- Search page
- Playlist page
- Download page
- Recommendations page
"""

import os
import sys
import subprocess
import customtkinter as ctk
from tkinter import messagebox, filedialog, ttk
from pygame import mixer
import random
import time
import io

# Add parent directory to path so we can import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from other modules
from config import UI_CONFIG, COLORS, APP_CONFIG
from utils import connect_db, get_current_user, ensure_directories_exist, format_file_size, create_song_card

# Initialize mixer for music playback
mixer.init()

# Current song information
current_song = {
    "id": None,
    "title": "No song playing",
    "artist": "",
    "playing": False,
    "paused": False
}

# ------------------- Data Functions -------------------
def get_featured_songs(limit=3):
    """Get featured songs from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Get songs with most plays in listening history
        query = """
        SELECT s.song_id, s.title, a.name as artist_name, COUNT(lh.history_id) as play_count 
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Listening_History lh ON s.song_id = lh.song_id
        GROUP BY s.song_id
        ORDER BY play_count DESC
        LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        songs = cursor.fetchall()
        
        # If no songs with play history, get newest songs
        if not songs:
            query = """
            SELECT s.song_id, s.title, a.name as artist_name 
            FROM Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
            ORDER BY s.upload_date DESC
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            songs = cursor.fetchall()
            
        return songs
        
    except Exception as e:
        print(f"Error fetching featured songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_song_data(song_id):
    """Get binary song data from database"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor()
        
        query = """
        SELECT s.file_data, s.file_type, s.title, a.name as artist_name 
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        WHERE s.song_id = %s
        """
        cursor.execute(query, (song_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'data': result[0], 
                'type': result[1],
                'title': result[2],
                'artist': result[3]
            }
        return None
        
    except Exception as e:
        print(f"Error getting song data: {e}")
        return None
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_song_info(song_id):
    """Get song information from the database"""
    try:
        connection = connect_db()
        if not connection:
            return None
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT s.title, a.name as artist_name, s.duration, g.name as genre
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        WHERE s.song_id = %s
        """
        
        cursor.execute(query, (song_id,))
        return cursor.fetchone()
        
    except Exception as e:
        print(f"Error fetching song info: {e}")
        return None
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def record_listening_history(song_id):
    """Record that the current user listened to a song"""
    try:
        # Get current user ID
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
            
        connection = connect_db()
        if not connection:
            return
            
        cursor = connection.cursor()
        
        query = "INSERT INTO Listening_History (user_id, song_id) VALUES (%s, %s)"
        cursor.execute(query, (user_id, song_id))
        connection.commit()
        
    except Exception as e:
        print(f"Error recording listening history: {e}")
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def search_songs(query, search_type="all"):
    """Search for songs in the database"""
    try:
        if not query:
            return []
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        search_param = f"%{query}%"
        
        # Different queries based on search type
        if search_type == "song":
            query = """
            SELECT s.song_id, s.title, a.name as artist_name, al.title as album_name, 
                   g.name as genre, s.duration
            FROM Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
            LEFT JOIN Albums al ON s.album_id = al.album_id
            LEFT JOIN Genres g ON s.genre_id = g.genre_id
            WHERE s.title LIKE %s
            ORDER BY s.title
            """
            cursor.execute(query, (search_param,))
        
        elif search_type == "artist":
            query = """
            SELECT s.song_id, s.title, a.name as artist_name, al.title as album_name, 
                   g.name as genre, s.duration
            FROM Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
            LEFT JOIN Albums al ON s.album_id = al.album_id
            LEFT JOIN Genres g ON s.genre_id = g.genre_id
            WHERE a.name LIKE %s
            ORDER BY s.title
            """
            cursor.execute(query, (search_param,))
            
        elif search_type == "album":
            query = """
            SELECT s.song_id, s.title, a.name as artist_name, al.title as album_name, 
                   g.name as genre, s.duration
            FROM Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
            LEFT JOIN Albums al ON s.album_id = al.album_id
            LEFT JOIN Genres g ON s.genre_id = g.genre_id
            WHERE al.title LIKE %s
            ORDER BY s.title
            """
            cursor.execute(query, (search_param,))
            
        else:  # "all" - search everything
            query = """
            SELECT s.song_id, s.title, a.name as artist_name, al.title as album_name, 
                   g.name as genre, s.duration
            FROM Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
            LEFT JOIN Albums al ON s.album_id = al.album_id
            LEFT JOIN Genres g ON s.genre_id = g.genre_id
            WHERE s.title LIKE %s OR a.name LIKE %s OR al.title LIKE %s
            ORDER BY s.title
            """
            cursor.execute(query, (search_param, search_param, search_param))
        
        songs = cursor.fetchall()
        
        # Format durations to MM:SS
        for song in songs:
            minutes, seconds = divmod(song['duration'] or 0, 60)  # Handle None values
            song['duration_formatted'] = f"{minutes}:{seconds:02d}"
        
        return songs
        
    except Exception as e:
        print(f"Error searching songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_user_favorite_songs(limit=8):
    """Get the current user's favorite songs"""
    try:
        # Get current user ID
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Get songs the user has listened to most
        query = """
        SELECT s.song_id, s.title, a.name as artist_name, COUNT(lh.history_id) as play_count,
               g.name as genre_name, s.file_size, s.file_type
        FROM Listening_History lh
        JOIN Songs s ON lh.song_id = s.song_id
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        WHERE lh.user_id = %s
        GROUP BY s.song_id
        ORDER BY play_count DESC
        LIMIT %s
        """
        
        cursor.execute(query, (user_id, limit))
        songs = cursor.fetchall()
        
        # Format file sizes to human-readable format
        for song in songs:
            song['file_size_formatted'] = format_file_size(song['file_size'])
            
        return songs
        
    except Exception as e:
        print(f"Error getting user favorite songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_popular_songs(limit=8):
    """Get most popular songs from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Get songs with most plays in listening history
        query = """
        SELECT s.song_id, s.title, a.name as artist_name, COUNT(lh.history_id) as play_count, 
               g.name as genre_name, s.file_size, s.file_type
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        LEFT JOIN Listening_History lh ON s.song_id = lh.song_id
        GROUP BY s.song_id
        ORDER BY play_count DESC
        LIMIT %s
        """
        
        cursor.execute(query, (limit,))
        songs = cursor.fetchall()
        
        # If no songs with play history, get newest songs
        if not songs:
            query = """
            SELECT s.song_id, s.title, a.name as artist_name, s.file_size, s.file_type,
                   g.name as genre_name, 0 as play_count
            FROM Songs s
            JOIN Artists a ON s.artist_id = a.artist_id
            LEFT JOIN Genres g ON s.genre_id = g.genre_id
            ORDER BY s.upload_date DESC
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            songs = cursor.fetchall()
            
        # Format file sizes to human-readable format
        for song in songs:
            song['file_size_formatted'] = format_file_size(song['file_size'])
            
        return songs
        
    except Exception as e:
        print(f"Error fetching popular songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_recommended_songs(limit=8):
    """Get songs recommended based on user's listening history"""
    try:
        # Get current user ID
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
        
        # Get favorite genres and artists
        favorite_genres = get_favorite_genres()
        favorite_artists = get_favorite_artists()
        
        # No history yet, return random songs
        if not favorite_genres and not favorite_artists:
            return get_random_songs(limit)
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Get songs the user has already listened to
        cursor.execute(
            "SELECT song_id FROM Listening_History WHERE user_id = %s",
            (user_id,)
        )
        listened_songs = [row['song_id'] for row in cursor.fetchall()]
        
        # Build genre filter
        genre_filter = ""
        genre_params = []
        if favorite_genres:
            genre_ids = [g['genre_id'] for g in favorite_genres]
            placeholders = ", ".join(["%s"] * len(genre_ids))
            genre_filter = f"OR s.genre_id IN ({placeholders})"
            genre_params = genre_ids
        
        # Build artist filter
        artist_filter = ""
        artist_params = []
        if favorite_artists:
            artist_ids = [a['artist_id'] for a in favorite_artists]
            placeholders = ", ".join(["%s"] * len(artist_ids))
            artist_filter = f"OR s.artist_id IN ({placeholders})"
            artist_params = artist_ids
        
        # Exclude songs the user has already heard
        exclusion_filter = ""
        exclusion_params = []
        if listened_songs:
            placeholders = ", ".join(["%s"] * len(listened_songs))
            exclusion_filter = f"AND s.song_id NOT IN ({placeholders})"
            exclusion_params = listened_songs
        
        # If user hasn't listened to any songs, don't use the exclusion filter
        if not listened_songs:
            exclusion_filter = ""
            exclusion_params = []
        
        # Query for recommendations based on genres and artists
        query = f"""
        SELECT s.song_id, s.title, a.name as artist_name, g.name as genre_name
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        WHERE 1=0 {genre_filter} {artist_filter} {exclusion_filter}
        ORDER BY RAND()
        LIMIT %s
        """
        
        all_params = genre_params + artist_params + exclusion_params + [limit]
        cursor.execute(query, all_params)
        recommendations = cursor.fetchall()
        
        # If we don't have enough recommendations, fill with random songs
        if len(recommendations) < limit:
            remaining = limit - len(recommendations)
            
            # Get IDs of already recommended songs
            recommended_ids = [song['song_id'] for song in recommendations]
            
            # Add listened songs to the exclusion list
            excluded_songs = recommended_ids + listened_songs if listened_songs else recommended_ids
            
            # Get random songs excluding those already recommended or listened to
            random_songs = get_random_songs(remaining, excluded_songs)
            
            # Combine recommendations
            recommendations.extend(random_songs)
        
        return recommendations
        
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return get_random_songs(limit)  # Fallback to random songs
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_favorite_genres():
    """Get user's favorite genres based on listening history"""
    try:
        # Get current user ID
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT g.genre_id, g.name as genre_name, COUNT(lh.history_id) as count
        FROM Listening_History lh
        JOIN Songs s ON lh.song_id = s.song_id
        JOIN Genres g ON s.genre_id = g.genre_id
        WHERE lh.user_id = %s AND g.genre_id IS NOT NULL
        GROUP BY g.genre_id
        ORDER BY count DESC
        LIMIT 3
        """
        
        cursor.execute(query, (user_id,))
        genres = cursor.fetchall()
        
        return genres
        
    except Exception as e:
        print(f"Error getting favorite genres: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_favorite_artists():
    """Get user's favorite artists based on listening history"""
    try:
        # Get current user ID
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT a.artist_id, a.name as artist_name, COUNT(lh.history_id) as count
        FROM Listening_History lh
        JOIN Songs s ON lh.song_id = s.song_id
        JOIN Artists a ON s.artist_id = a.artist_id
        WHERE lh.user_id = %s
        GROUP BY a.artist_id
        ORDER BY count DESC
        LIMIT 3
        """
        
        cursor.execute(query, (user_id,))
        artists = cursor.fetchall()
        
        return artists
        
    except Exception as e:
        print(f"Error getting favorite artists: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_random_songs(limit=8, exclude_ids=None):
    """Get random songs from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        # Exclude songs if specified
        exclusion_filter = ""
        params = []
        
        if exclude_ids and len(exclude_ids) > 0:
            placeholders = ", ".join(["%s"] * len(exclude_ids))
            exclusion_filter = f"WHERE s.song_id NOT IN ({placeholders})"
            params = exclude_ids
        
        query = f"""
        SELECT s.song_id, s.title, a.name as artist_name, g.name as genre_name
        FROM Songs s
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        {exclusion_filter}
        ORDER BY RAND()
        LIMIT %s
        """
        
        params.append(limit)
        cursor.execute(query, params)
        songs = cursor.fetchall()
        
        # If no songs in database yet, return dummy data
        if not songs:
            songs = [
                {"song_id": 1, "title": "Blinding Lights", "artist_name": "The Weeknd", "genre_name": "Pop"},
                {"song_id": 2, "title": "Levitating", "artist_name": "Dua Lipa", "genre_name": "Pop"},
                {"song_id": 3, "title": "Believer", "artist_name": "Imagine Dragons", "genre_name": "Rock"},
                {"song_id": 4, "title": "Shape of You", "artist_name": "Ed Sheeran", "genre_name": "Pop"}
            ]
            # Shuffle and limit
            random.shuffle(songs)
            songs = songs[:limit]
        
        return songs
        
    except Exception as e:
        print(f"Error getting random songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def download_song(song_id):
    """Download a song to local storage"""
    try:
        # Get song data
        song_data = get_song_data(song_id)
        if not song_data:
            messagebox.showerror("Error", "Could not retrieve song data")
            return False
        
        # Format the filename
        filename = f"{song_data['artist']} - {song_data['title']}.{song_data['type']}"
        # Replace invalid filename characters
        filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        # Ask user for download location
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        save_path = filedialog.asksaveasfilename(
            initialdir=downloads_dir,
            initialfile=filename,
            defaultextension=f".{song_data['type']}",
            filetypes=[(f"{song_data['type'].upper()} files", f"*.{song_data['type']}"), ("All files", "*.*")]
        )
        
        if not save_path:  # User cancelled
            return False
        
        # Write song data to file
        with open(save_path, 'wb') as f:
            f.write(song_data['data'])
        
        messagebox.showinfo("Download Complete", f"Song has been downloaded to:\n{save_path}")
        return True
        
    except Exception as e:
        print(f"Error downloading song: {e}")
        messagebox.showerror("Error", f"Could not download song: {e}")
        return False

# ------------------- Music Player Functions -------------------
def play_song(song_id):
    """Play a song from its binary data in the database"""
    global current_song
    
    try:
        # Get song data from database
        song_data = get_song_data(song_id)
        if not song_data:
            messagebox.showerror("Error", "Could not retrieve song data")
            return False
            
        # Create a temporary file to play the song
        temp_dir = APP_CONFIG["temp_dir"]
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file = os.path.join(temp_dir, f"song_{song_id}.{song_data['type']}")
        
        # Write binary data to temp file
        with open(temp_file, 'wb') as f:
            f.write(song_data['data'])
            
        # Load and play the song
        mixer.music.load(temp_file)
        mixer.music.play()
        
        # Update current song info
        current_song = {
            "id": song_id,
            "title": song_data["title"],
            "artist": song_data["artist"],
            "playing": True,
            "paused": False
        }
        
        # Update UI elements
        update_now_playing_display()
        
        # Record in listening history
        record_listening_history(song_id)
        
        return True
        
    except Exception as e:
        print(f"Error playing song: {e}")
        messagebox.showerror("Error", f"Could not play song: {e}")
        return False

def toggle_play_pause():
    """Toggle between play and pause states"""
    global current_song
    
    if current_song["id"] is None:
        # No song loaded - try to play first featured song
        featured_songs = get_featured_songs(1)
        if featured_songs:
            play_song(featured_songs[0]['song_id'])
    elif current_song["paused"]:
        # Resume paused song
        mixer.music.unpause()
        current_song["paused"] = False
        current_song["playing"] = True
        update_now_playing_display()
    elif current_song["playing"]:
        # Pause playing song
        mixer.music.pause()
        current_song["paused"] = True
        current_song["playing"] = False
        update_now_playing_display()

def play_next_song():
    """Placeholder for playing next song"""
    messagebox.showinfo("Info", "Next song feature will be implemented with playlists")

def play_previous_song():
    """Placeholder for playing previous song"""
    messagebox.showinfo("Info", "Previous song feature will be implemented with playlists")

def update_now_playing_display():
    """Update the now playing display in the UI"""
    if 'now_playing_label' in globals():
        text = f"Now Playing: {current_song['title']} - {current_song['artist']}"
        now_playing_label.configure(text=text)
    
    if 'play_btn' in globals():
        if current_song["paused"]:
            play_btn.configure(text="▶️")
        else:
            play_btn.configure(text="⏸️")

# ------------------- UI Creation Functions -------------------
def create_sidebar(parent_frame, user, active_page="home"):
    """Create the sidebar navigation"""
    sidebar = ctk.CTkFrame(parent_frame, width=250, height=580, fg_color=COLORS["sidebar"], corner_radius=10)
    sidebar.pack(side="left", fill="y", padx=(10, 0), pady=10)

    # Sidebar Title
    title_label = ctk.CTkLabel(sidebar, text="Online Music\nSystem", font=("Arial", 20, "bold"), text_color="white")
    title_label.pack(pady=(25, 30))

    # Determine button colors based on active page
    page_colors = {
        "home": ["white", COLORS["text_secondary"], COLORS["text_secondary"], COLORS["text_secondary"], COLORS["text_secondary"]],
        "search": [COLORS["text_secondary"], "white", COLORS["text_secondary"], COLORS["text_secondary"], COLORS["text_secondary"]],
        "playlist": [COLORS["text_secondary"], COLORS["text_secondary"], "white", COLORS["text_secondary"], COLORS["text_secondary"]],
        "download": [COLORS["text_secondary"], COLORS["text_secondary"], COLORS["text_secondary"], "white", COLORS["text_secondary"]],
        "recommend": [COLORS["text_secondary"], COLORS["text_secondary"], COLORS["text_secondary"], COLORS["text_secondary"], "white"]
    }
    
    colors = page_colors.get(active_page, page_colors["home"])

    # Sidebar Menu Items with navigation commands
    home_btn = ctk.CTkButton(sidebar, text="🏠 Home", font=("Arial", 14), 
                          fg_color=COLORS["sidebar"], hover_color="#1E293B", text_color=colors[0],
                          anchor="w", corner_radius=0, height=40, command=lambda: show_home_view())
    home_btn.pack(fill="x", pady=5, padx=10)

    search_btn = ctk.CTkButton(sidebar, text="🔍 Search", font=("Arial", 14), 
                            fg_color=COLORS["sidebar"], hover_color="#1E293B", text_color=colors[1],
                            anchor="w", corner_radius=0, height=40, command=lambda: show_search_view())
    search_btn.pack(fill="x", pady=5, padx=10)

    playlist_btn = ctk.CTkButton(sidebar, text="🎵 Playlist", font=("Arial", 14), 
                              fg_color=COLORS["sidebar"], hover_color="#1E293B", text_color=colors[2],
                              anchor="w", corner_radius=0, height=40, command=lambda: show_playlist_view())
    playlist_btn.pack(fill="x", pady=5, padx=10)

    download_btn = ctk.CTkButton(sidebar, text="⬇️ Download", font=("Arial", 14), 
                              fg_color=COLORS["sidebar"], hover_color="#1E293B", text_color=colors[3],
                              anchor="w", corner_radius=0, height=40, command=lambda: show_download_view())
    download_btn.pack(fill="x", pady=5, padx=10)

    recommend_btn = ctk.CTkButton(sidebar, text="🎧 Recommend Songs", font=("Arial", 14), 
                                fg_color=COLORS["sidebar"], hover_color="#1E293B", text_color=colors[4],
                                anchor="w", corner_radius=0, height=40, command=lambda: show_recommend_view())
    recommend_btn.pack(fill="x", pady=5, padx=10)

    logout_btn = ctk.CTkButton(sidebar, text="🚪 Logout", font=("Arial", 14), 
                             fg_color=COLORS["sidebar"], hover_color="#1E293B", text_color=COLORS["text_secondary"],
                             anchor="w", corner_radius=0, height=40, command=lambda: open_login_page())
    logout_btn.pack(fill="x", pady=5, padx=10)

    # Now playing label
    global now_playing_label
    now_playing_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["sidebar"], height=40)
    now_playing_frame.pack(side="bottom", fill="x", pady=(0, 10), padx=10)
    
    now_playing_label = ctk.CTkLabel(now_playing_frame, 
                                   text="Now Playing: No song playing", 
                                   font=("Arial", 12), 
                                   text_color=COLORS["text_secondary"],
                                   wraplength=220)
    now_playing_label.pack(pady=5)

    # Music player controls at bottom of sidebar
    player_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["sidebar"], height=50)
    player_frame.pack(side="bottom", fill="x", pady=10, padx=10)

    # Control buttons with functionality
    prev_btn = ctk.CTkButton(player_frame, text="⏮️", font=("Arial", 18), 
                            fg_color=COLORS["sidebar"], hover_color="#1E293B", 
                            width=40, height=40, command=play_previous_song)
    prev_btn.pack(side="left", padx=10)

    global play_btn
    play_btn = ctk.CTkButton(player_frame, text="▶️", font=("Arial", 18), 
                           fg_color=COLORS["sidebar"], hover_color="#1E293B", 
                           width=40, height=40, command=toggle_play_pause)
    play_btn.pack(side="left", padx=10)

    next_btn = ctk.CTkButton(player_frame, text="⏭️", font=("Arial", 18), 
                           fg_color=COLORS["sidebar"], hover_color="#1E293B", 
                           width=40, height=40, command=play_next_song)
    next_btn.pack(side="left", padx=10)
    
    return sidebar

def create_header(parent_frame, title, user):
    """Create the header with title and user info"""
    header_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], height=40)
    header_frame.pack(fill="x", padx=20, pady=(20, 0))

    # Left side: Page title
    header_label = ctk.CTkLabel(header_frame, text=title, font=("Arial", 24, "bold"), text_color="white")
    header_label.pack(side="left")

    # Right side: Username
    user_label = ctk.CTkLabel(header_frame, 
                           text=f"Hello, {user['first_name']} {user['last_name']}!", 
                           font=("Arial", 14), text_color=COLORS["text_secondary"])
    user_label.pack(side="right")
    
    return header_frame

def create_home_frame(parent_frame, user):
    """Create the home page UI"""
    # Create header
    create_header(parent_frame, "Home", user)

    # ---------------- Hero Section ----------------
    hero_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    hero_frame.pack(fill="x", padx=20, pady=(40, 20))

    # Main title
    title_label = ctk.CTkLabel(hero_frame, text="Discover Music & Play Instantly", 
                              font=("Arial", 28, "bold"), text_color=COLORS["primary"])
    title_label.pack(anchor="w")

    # Subtitle
    subtitle_label = ctk.CTkLabel(hero_frame, 
                                 text="Explore top trending songs, curated playlists, and personalized recommendations.", 
                                 font=("Arial", 14), text_color=COLORS["text_secondary"])
    subtitle_label.pack(anchor="w", pady=(10, 20))

    # Action Buttons with navigation
    button_frame = ctk.CTkFrame(hero_frame, fg_color=COLORS["content"])
    button_frame.pack(anchor="w")

    # Trending button (just scrolls to featured songs for now)
    trending_btn = ctk.CTkButton(button_frame, text="🔥 Trending", font=("Arial", 14, "bold"), 
                                fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"], 
                                corner_radius=8, height=40, width=150)
    trending_btn.pack(side="left", padx=(0, 10))

    # Playlists button
    playlists_btn = ctk.CTkButton(button_frame, text="🎵 Playlists", font=("Arial", 14, "bold"), 
                                 fg_color=COLORS["success"], hover_color=COLORS["success_hover"], 
                                 corner_radius=8, height=40, width=150,
                                 command=lambda: show_playlist_view())
    playlists_btn.pack(side="left", padx=10)

    # Download button
    download_btn = ctk.CTkButton(button_frame, text="⬇️ Download", font=("Arial", 14, "bold"), 
                                fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], 
                                corner_radius=8, height=40, width=150,
                                command=lambda: show_download_view())
    download_btn.pack(side="left", padx=10)

    # ---------------- Featured Songs Section ----------------
    featured_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    featured_frame.pack(fill="x", padx=20, pady=20)

    # Section title
    featured_title = ctk.CTkLabel(featured_frame, text="🔥 Featured Songs", 
                                 font=("Arial", 18, "bold"), text_color=COLORS["primary"])
    featured_title.pack(anchor="w", pady=(0, 20))

    # Song cards container
    songs_frame = ctk.CTkFrame(featured_frame, fg_color=COLORS["content"])
    songs_frame.pack(fill="x")

    # Get featured songs from database
    featured_songs = get_featured_songs(3)
    
    # If database has no songs yet, use sample data
    if not featured_songs:
        featured_songs = [
            {"song_id": 1, "title": "Blinding\nLights", "artist_name": "The\nWeeknd"},
            {"song_id": 2, "title": "Levitating", "artist_name": "Dua Lipa"},
            {"song_id": 3, "title": "Shape of\nYou", "artist_name": "Ed\nSheeran"}
        ]
    
    # Create song cards for each featured song
    for song in featured_songs:
        song_card = create_song_card(
            songs_frame, 
            song["song_id"], 
            song["title"], 
            song["artist_name"],
            play_command=play_song
        )
        song_card.pack(side="left", padx=10)
    
    return parent_frame

def create_search_frame(parent_frame, user):
    """Create the search page UI"""
    # Create header
    create_header(parent_frame, "Search Songs", user)

    # ---------------- Search Bar ----------------
    search_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    search_frame.pack(fill="x", padx=20, pady=(30, 20))

    # Search type selection
    search_type_frame = ctk.CTkFrame(search_frame, fg_color=COLORS["content"])
    search_type_frame.pack(fill="x", pady=(0, 10))
    
    search_type_var = ctk.StringVar(value="all")
    
    # Search type options
    search_all_radio = ctk.CTkRadioButton(
        search_type_frame, 
        text="All", 
        variable=search_type_var, 
        value="all",
        fg_color=COLORS["primary"],
        text_color=COLORS["text_secondary"]
    )
    search_all_radio.pack(side="left", padx=(0, 20))
    
    search_songs_radio = ctk.CTkRadioButton(
        search_type_frame, 
        text="Songs", 
        variable=search_type_var, 
        value="song",
        fg_color=COLORS["primary"],
        text_color=COLORS["text_secondary"]
    )
    search_songs_radio.pack(side="left", padx=(0, 20))
    
    search_artists_radio = ctk.CTkRadioButton(
        search_type_frame, 
        text="Artists", 
        variable=search_type_var, 
        value="artist",
        fg_color=COLORS["primary"],
        text_color=COLORS["text_secondary"]
    )
    search_artists_radio.pack(side="left", padx=(0, 20))
    
    search_albums_radio = ctk.CTkRadioButton(
        search_type_frame, 
        text="Albums", 
        variable=search_type_var, 
        value="album",
        fg_color=COLORS["primary"],
        text_color=COLORS["text_secondary"]
    )
    search_albums_radio.pack(side="left")

    # Search entry with rounded corners
    search_entry = ctk.CTkEntry(search_frame, 
                              placeholder_text="Search for songs, artists, or albums...",
                              font=("Arial", 14), text_color="#FFFFFF",
                              fg_color=COLORS["card"], border_color="#2A2A4E", 
                              height=45, corner_radius=10)
    search_entry.pack(side="left", fill="x", expand=True)
    
    # Define the search function
    def perform_search():
        # Clear previous search results
        for widget in songs_section.winfo_children():
            if widget != songs_title:  # Keep the section title
                widget.destroy()
        
        # Get search query
        query = search_entry.get()
        
        if not query:
            # If no query, just show recent songs
            recent_songs = get_featured_songs(6)
            display_search_results(recent_songs, "Recent Songs")
            return
        
        # Perform the search
        search_results = search_songs(query, search_type_var.get())
        
        # Display results
        if search_results:
            display_search_results(search_results, f"Search Results for '{query}'")
        else:
            no_results_label = ctk.CTkLabel(
                songs_section, 
                text=f"No songs found for '{query}'", 
                font=("Arial", 14),
                text_color=COLORS["text_secondary"]
            )
            no_results_label.pack(pady=20)
    
    # Bind Enter key to search
    search_entry.bind("<Return>", lambda e: perform_search())
    
    # Search button
    search_button = ctk.CTkButton(
        search_frame, 
        text="Search", 
        font=("Arial", 14, "bold"),
        fg_color=COLORS["primary"], 
        hover_color=COLORS["primary_hover"], 
        corner_radius=10,
        command=perform_search,
        height=45,
        width=100
    )
    search_button.pack(side="right", padx=(10, 0))

    # ---------------- Songs Section ----------------
    global songs_section, songs_title
    songs_section = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    songs_section.pack(fill="both", expand=True, padx=20, pady=10)

    # Section title
    songs_title = ctk.CTkLabel(songs_section, text="Recent Songs 🎵", 
                             font=("Arial", 20, "bold"), text_color=COLORS["primary"])
    songs_title.pack(anchor="w", pady=(0, 15))
    
    # Function to display search results
    def display_search_results(songs, section_subtitle=None):
        """Display songs in the search results section"""
        # Update section subtitle if provided
        if section_subtitle:
            songs_title.configure(text=f"🔍 {section_subtitle}")
        
        if not songs:
            no_songs_label = ctk.CTkLabel(
                songs_section, 
                text="No songs available", 
                font=("Arial", 14),
                text_color=COLORS["text_secondary"]
            )
            no_songs_label.pack(pady=20)
            return
        
        # Create song rows
        for song in songs:
            # Create a frame for each song row
            song_frame = ctk.CTkFrame(songs_section, fg_color=COLORS["card"], corner_radius=10, height=50)
            song_frame.pack(fill="x", pady=5)
            
            # Format the song display text
            if "album_name" in song and song["album_name"]:
                display_text = f"🎵 {song['artist_name']} - {song['title']} ({song['album_name']})"
            else:
                display_text = f"🎵 {song['artist_name']} - {song['title']}"
            
            # Add duration if available
            if "duration_formatted" in song:
                display_text += f" ({song['duration_formatted']})"
            
            # Song name and info
            song_label = ctk.CTkLabel(
                song_frame, 
                text=display_text, 
                font=("Arial", 14), 
                text_color="white",
                anchor="w"
            )
            song_label.pack(side="left", padx=15, fill="y")
            
            # Play button
            play_icon = ctk.CTkLabel(
                song_frame, 
                text="▶️", 
                font=("Arial", 16), 
                text_color=COLORS["success"]
            )
            play_icon.pack(side="right", padx=15)
            
            # Add play song command
            song_id = song["song_id"]
            
            # Make the whole row clickable
            song_frame.bind("<Button-1>", lambda e, sid=song_id: play_song(sid))
            song_label.bind("<Button-1>", lambda e, sid=song_id: play_song(sid))
            play_icon.bind("<Button-1>", lambda e, sid=song_id: play_song(sid))
    
    # Show recent songs on initial load
    recent_songs = get_featured_songs(6)
    display_search_results(recent_songs, "Recent Songs")
    
    return parent_frame

def create_download_frame(parent_frame, user):
    """Create the download page UI"""
    # Create header
    create_header(parent_frame, "Download Songs", user)

    # ---------------- Download Your Favorite Songs ----------------
    favorite_songs_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    favorite_songs_frame.pack(fill="both", expand=True, padx=20, pady=(40, 0))

    # Section title - centered
    title_label = ctk.CTkLabel(favorite_songs_frame, text="Download Your Favorite Songs 🎵", 
                              font=("Arial", 24, "bold"), text_color=COLORS["primary"])
    title_label.pack(pady=(0, 5))

    # Subtitle - centered
    subtitle_label = ctk.CTkLabel(favorite_songs_frame, text="Select a song to download or upload your own.", 
                                 font=("Arial", 14), text_color=COLORS["text_secondary"])
    subtitle_label.pack(pady=(0, 20))

    # Tabview for different song sections
    tabs = ctk.CTkTabview(favorite_songs_frame, fg_color=COLORS["content"])
    tabs.pack(fill="both", expand=True)
    
    # Add tabs
    favorite_tab = tabs.add("Your Favorites")
    popular_tab = tabs.add("Popular Songs")
    
    # Function to select a song for download
    global selected_song, song_frames
    selected_song = {"id": None, "title": None, "artist": None}
    song_frames = []
    
    def select_song_for_download(song_id, title, artist, song_frame):
        """Select a song for download"""
        global selected_song, song_frames
        
        # Reset highlight on all frames
        for frame in song_frames:
            frame.configure(fg_color=COLORS["card"])
        
        # Highlight selected frame
        song_frame.configure(fg_color="#2A2A4E")
        
        # Update selected song info
        selected_song["id"] = song_id
        selected_song["title"] = title
        selected_song["artist"] = artist
    
    # Function to display songs in tabs
    def display_songs_in_tab(tab, songs):
        """Display songs in a tab"""
        if not songs:
            no_songs_label = ctk.CTkLabel(
                tab, 
                text="No songs available", 
                font=("Arial", 14), 
                text_color=COLORS["text_secondary"]
            )
            no_songs_label.pack(pady=30)
            return
        
        # Create song frames for each song
        for song in songs:
            song_frame = ctk.CTkFrame(tab, fg_color=COLORS["card"], corner_radius=10, height=50)
            song_frame.pack(fill="x", pady=5, ipady=5)
            
            # Prevent frame from resizing
            song_frame.pack_propagate(False)
            
            # Song icon and title - left side
            song_icon = "🎵"
            song_label = ctk.CTkLabel(
                song_frame, 
                text=f"{song_icon} {song['artist_name']} - {song['title']}", 
                font=("Arial", 14), 
                text_color="white",
                anchor="w"
            )
            song_label.pack(side="left", padx=20)
            
            # File size and type - right side
            if 'file_size_formatted' in song and 'file_type' in song:
                file_info = ctk.CTkLabel(
                    song_frame, 
                    text=f"{song['file_size_formatted']} ({song['file_type']})", 
                    font=("Arial", 12), 
                    text_color=COLORS["text_secondary"]
                )
                file_info.pack(side="right", padx=(0, 20))
            
            # Play button - right side
            play_btn = ctk.CTkButton(
                song_frame, 
                text="▶️", 
                font=("Arial", 14), 
                fg_color="#1E293B",
                hover_color="#2A3749",
                width=30, height=30,
                command=lambda sid=song['song_id']: play_song(sid)
            )
            play_btn.pack(side="right", padx=5)
            
            # Make frame selectable
            song_frame.bind(
                "<Button-1>", 
                lambda e, sid=song['song_id'], title=song['title'], artist=song['artist_name'], frame=song_frame: 
                    select_song_for_download(sid, title, artist, frame)
            )
            song_label.bind(
                "<Button-1>", 
                lambda e, sid=song['song_id'], title=song['title'], artist=song['artist_name'], frame=song_frame: 
                    select_song_for_download(sid, title, artist, frame)
            )
            
            # Add to list of song frames
            song_frames.append(song_frame)
    
    # Display favorite songs tab
    favorite_songs = get_user_favorite_songs()
    display_songs_in_tab(favorite_tab, favorite_songs)
    
    # Display popular songs tab
    popular_songs = get_popular_songs()
    display_songs_in_tab(popular_tab, popular_songs)
    
    # Button frame at the bottom
    button_frame = ctk.CTkFrame(favorite_songs_frame, fg_color=COLORS["content"])
    button_frame.pack(pady=25)
    
    # Function to download selected song
    def download_selected_song():
        """Download the selected song"""
        if not selected_song["id"]:
            messagebox.showwarning("Warning", "Please select a song to download")
            return
        
        # Download the song
        download_song(selected_song["id"])
    
    # Function to handle file upload (placeholder)
    def handle_upload_song():
        """Handle song upload (placeholder)"""
        messagebox.showinfo("Upload Song", "This functionality will be implemented in a future update.")
    
    # Download button
    download_button = ctk.CTkButton(button_frame, text="⬇️ Download Selected", font=("Arial", 14, "bold"), 
                                   fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], 
                                   corner_radius=5, height=40, width=210, 
                                   command=download_selected_song)
    download_button.pack(side="left", padx=10)

    # Upload button
    upload_button = ctk.CTkButton(button_frame, text="⬆️ Upload New Song", font=("Arial", 14, "bold"), 
                                 fg_color=COLORS["secondary"], hover_color=COLORS["secondary_hover"], 
                                 corner_radius=5, height=40, width=210,
                                 command=handle_upload_song)
    upload_button.pack(side="left", padx=10)
    
    return parent_frame
def create_recommend_frame(parent_frame, user):
    """Create the recommendations page UI"""
    # Create header
    create_header(parent_frame, "Recommended Songs", user)

    # ---------------- Songs You Might Like ----------------
    songs_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    songs_frame.pack(fill="both", expand=True, padx=20, pady=(40, 0))

    # Section title - centered
    title_label = ctk.CTkLabel(songs_frame, text="Songs You Might Like 🎵", 
                              font=("Arial", 24, "bold"), text_color=COLORS["primary"])
    title_label.pack(pady=(0, 5))

    # Subtitle with personalized text based on listening history
    subtitle_text = "Discover music based on your listening history." 
    listening_history = get_user_favorite_songs(limit=1)
    if not listening_history:
        subtitle_text = "Start listening to songs to get personalized recommendations."
        
    subtitle_label = ctk.CTkLabel(songs_frame, text=subtitle_text, 
                                 font=("Arial", 14), text_color=COLORS["text_secondary"])
    subtitle_label.pack(pady=(0, 20))
    
    # Song list container
    recommended_songs_frame = ctk.CTkFrame(songs_frame, fg_color=COLORS["content"])
    recommended_songs_frame.pack(fill="both", expand=True)
    
    # Get recommended songs
    recommended_songs = get_recommended_songs(8)
    
    if not recommended_songs:
        no_songs_label = ctk.CTkLabel(
            recommended_songs_frame, 
            text="No recommended songs available", 
            font=("Arial", 14),
            text_color=COLORS["text_secondary"]
        )
        no_songs_label.pack(pady=30)
    else:
        # Display songs
        for song in recommended_songs:
            # Create song row
            song_frame = ctk.CTkFrame(recommended_songs_frame, fg_color=COLORS["card"], corner_radius=10, height=50)
            song_frame.pack(fill="x", pady=5, ipady=5)
            
            # Make sure the frame stays at desired height
            song_frame.pack_propagate(False)
            
            # Get display text with icon
            song_icon = "🎵"
            display_text = f"{song_icon} {song['artist_name']} - {song['title']}"
            if song.get('genre_name'):
                display_text += f" ({song['genre_name']})"
            
            # Song label with icon
            song_label = ctk.CTkLabel(song_frame, text=display_text, font=("Arial", 14), text_color="white")
            song_label.pack(side="left", padx=20)
            
            # Play button
            play_btn = ctk.CTkButton(song_frame, text="▶️ Play", font=("Arial", 12), 
                                   fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], 
                                   width=80, height=30,
                                   command=lambda sid=song["song_id"]: play_song(sid))
            play_btn.pack(side="right", padx=20)
            
            # Make frame clickable
            song_frame.bind("<Button-1>", lambda e, sid=song["song_id"]: play_song(sid))
            song_label.bind("<Button-1>", lambda e, sid=song["song_id"]: play_song(sid))
    
    # Refresh button at the bottom
    button_frame = ctk.CTkFrame(songs_frame, fg_color=COLORS["content"])
    button_frame.pack(pady=25)
    
    def refresh_recommendations():
        """Refresh the recommendations"""
        # Clear the content frame and recreate it
        clear_content_frame()
        create_recommend_frame(content_frame, user_info)
        messagebox.showinfo("Refreshed", "Recommendations have been updated!")
    
    refresh_button = ctk.CTkButton(button_frame, text="⟳ Refresh", font=("Arial", 14, "bold"), 
                                  fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], 
                                  corner_radius=5, height=40, width=140,
                                  command=refresh_recommendations)
    refresh_button.pack()
    
    return parent_frame

def create_playlist_frame(parent_frame, user):
    """Create the playlist page UI (placeholder)"""
    # Create header
    create_header(parent_frame, "Playlists", user)
    
    # Placeholder content
    placeholder_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"])
    placeholder_frame.pack(fill="both", expand=True, padx=20, pady=(40, 20))
    
    # Title
    title_label = ctk.CTkLabel(placeholder_frame, text="Playlist Feature Coming Soon", 
                              font=("Arial", 24, "bold"), text_color=COLORS["primary"])
    title_label.pack(pady=(40, 10))
    
    # Message
    message_label = ctk.CTkLabel(placeholder_frame, 
                               text="We're working on implementing playlist functionality. Stay tuned!", 
                               font=("Arial", 16),
                               text_color=COLORS["text_secondary"])
    message_label.pack(pady=10)
    
    # Icon
    icon_label = ctk.CTkLabel(placeholder_frame, text="🎵 + 📋 = ❤️", font=("Arial", 40))
    icon_label.pack(pady=30)
    
    # Button to return to home
    home_button = ctk.CTkButton(placeholder_frame, text="Return to Home", 
                              font=("Arial", 14, "bold"),
                              fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"],
                              corner_radius=5, height=40, width=160,
                              command=lambda: show_home_view())
    home_button.pack(pady=20)
    
    return parent_frame

# ------------------- Navigation Functions -------------------
def open_login_page():
    """Logout and open the login page"""
    try:
        # Stop any playing music
        if mixer.music.get_busy():
            mixer.music.stop()
            
        # Remove current user file
        if os.path.exists("current_user.txt"):
            os.remove("current_user.txt")
            
        subprocess.Popen(["python", "login_signup.py", "login"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to logout: {e}")

# ------------------- View Management -------------------
def clear_content_frame():
    """Clear all widgets from the content frame"""
    for widget in content_frame.winfo_children():
        widget.destroy()

def show_home_view():
    """Show the home view"""
    clear_content_frame()
    create_sidebar(main_frame, user_info, "home")
    create_home_frame(content_frame, user_info)

def show_search_view():
    """Show the search view"""
    clear_content_frame()
    create_sidebar(main_frame, user_info, "search")
    create_search_frame(content_frame, user_info)

def show_playlist_view():
    """Show the playlist view"""
    clear_content_frame()
    create_sidebar(main_frame, user_info, "playlist")
    create_playlist_frame(content_frame, user_info)

def show_download_view():
    """Show the download view"""
    clear_content_frame()
    create_sidebar(main_frame, user_info, "download")
    create_download_frame(content_frame, user_info)

def show_recommend_view():
    """Show the recommendations view"""
    clear_content_frame()
    create_sidebar(main_frame, user_info, "recommend")
    create_recommend_frame(content_frame, user_info)

# ------------------- Initialize App -------------------
if __name__ == "__main__":
    try:
        # Get current user info
        user_info = get_current_user()
        if not user_info:
            # Redirect to login if not logged in
            open_login_page()
            exit()

        # Ensure all directories exist
        ensure_directories_exist()

        # ---------------- Initialize App ----------------
        ctk.set_appearance_mode(UI_CONFIG["theme"])  # Dark mode
        ctk.set_default_color_theme(UI_CONFIG["color_theme"])  # Default theme

        root = ctk.CTk()
        root.title(f"{APP_CONFIG['name']} - User Interface")
        root.geometry(UI_CONFIG["default_window_size"])
        root.resizable(True, True)

        # ---------------- Main Frame ----------------
        main_frame = ctk.CTkFrame(root, fg_color=COLORS["background"], corner_radius=15)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ---------------- Create Sidebar ----------------
        view_to_show = "home"  # Default view
        if len(sys.argv) > 1:
            view_to_show = sys.argv[1].lower()
            
        # Create sidebar with active page highlighted
        create_sidebar(main_frame, user_info, view_to_show)

        # ---------------- Main Content ----------------
        content_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["content"], corner_radius=10)
        content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # Show the appropriate view based on command line argument
        if view_to_show == "search":
            create_search_frame(content_frame, user_info)
        elif view_to_show == "playlist":
            create_playlist_frame(content_frame, user_info)
        elif view_to_show == "download":
            create_download_frame(content_frame, user_info)
        elif view_to_show == "recommend":
            create_recommend_frame(content_frame, user_info)
        else:
            create_home_frame(content_frame, user_info)

        # ---------------- Run Application ----------------
        root.mainloop()
        
    except Exception as e:
        import traceback
        print(f"Error in users_view.py: {e}")
        traceback.print_exc()
        messagebox.showerror("Error", f"An error occurred: {e}")
        input("Press Enter to exit...")  #