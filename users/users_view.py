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
try:
    from db_config import UI_CONFIG, COLORS, APP_CONFIG
    from db_utils import connect_db, get_current_user, ensure_directories_exist, format_file_size, create_song_card
    USE_CONFIG = True
except ImportError:
    print("Warning: db_config.py or db_utils.py not found. Using fallback settings.")
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
        "name": "MusicFlow",
        "version": "2.0",
        "temp_dir": "temp",
        "reports_dir": "reports"
    }

# Initialize mixer for music playback
mixer.init()

# Set customtkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

sidebar = None
# Current song information
current_song = {
    "id": None,
    "title": "No song playing",
    "artist": "",
    "playing": False,
    "paused": False
}

# Song queue for navigation
song_queue = []
queue_index = -1
queue_context = None

# ------------------- Data Functions -------------------
def get_featured_songs(limit=3):
    """Get featured songs from the database"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
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
    """Search for songs in the database with preference for albums"""
    try:
        if not query:
            return []
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        search_param = f"%{query}%"
        
        # First check if there are any albums matching the query
        if search_type == "all":
            album_check_query = """
            SELECT COUNT(*) as album_count
            FROM Albums al
            WHERE al.title LIKE %s
            """
            cursor.execute(album_check_query, (search_param,))
            album_count = cursor.fetchone()['album_count']
            
            # If albums are found, switch search type to album
            if album_count > 0:
                search_type = "album"
        
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
            ORDER BY a.name, s.title
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
            ORDER BY al.title, s.title
            """
            cursor.execute(query, (search_param,))
            
        else:  # "all" without album matches
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
        
        for song in songs:
            minutes, seconds = divmod(song['duration'] or 0, 60)
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
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
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
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
        
        favorite_genres = get_favorite_genres()
        favorite_artists = get_favorite_artists()
        
        if not favorite_genres and not favorite_artists:
            return get_random_songs(limit)
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT song_id FROM Listening_History WHERE user_id = %s",
            (user_id,)
        )
        listened_songs = [row['song_id'] for row in cursor.fetchall()]
        
        genre_filter = ""
        genre_params = []
        if favorite_genres:
            genre_ids = [g['genre_id'] for g in favorite_genres]
            placeholders = ", ".join(["%s"] * len(genre_ids))
            genre_filter = f"OR s.genre_id IN ({placeholders})"
            genre_params = genre_ids
        
        artist_filter = ""
        artist_params = []
        if favorite_artists:
            artist_ids = [a['artist_id'] for a in favorite_artists]
            placeholders = ", ".join(["%s"] * len(artist_ids))
            artist_filter = f"OR s.artist_id IN ({placeholders})"
            artist_params = artist_ids
        
        exclusion_filter = ""
        exclusion_params = []
        if listened_songs:
            placeholders = ", ".join(["%s"] * len(listened_songs))
            exclusion_filter = f"AND s.song_id NOT IN ({placeholders})"
            exclusion_params = listened_songs
        
        if not listened_songs:
            exclusion_filter = ""
            exclusion_params = []
        
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
        
        if len(recommendations) < limit:
            remaining = limit - len(recommendations)
            recommended_ids = [song['song_id'] for song in recommendations]
            excluded_songs = recommended_ids + listened_songs if listened_songs else recommended_ids
            random_songs = get_random_songs(remaining, excluded_songs)
            recommendations.extend(random_songs)
        
        return recommendations
        
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return get_random_songs(limit)
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_favorite_genres():
    """Get user's favorite genres based on listening history"""
    try:
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
        
        if not songs:
            songs = [
                {"song_id": 1, "title": "Blinding Lights", "artist_name": "The Weeknd", "genre_name": "Pop"},
                {"song_id": 2, "title": "Levitating", "artist_name": "Dua Lipa", "genre_name": "Pop"},
                {"song_id": 3, "title": "Believer", "artist_name": "Imagine Dragons", "genre_name": "Rock"},
                {"song_id": 4, "title": "Shape of You", "artist_name": "Ed Sheeran", "genre_name": "Pop"}
            ]
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

def create_playlist(name, description=""):
    """Create a new playlist for the current user"""
    try:
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
            
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        query = "INSERT INTO Playlists (user_id, name, description) VALUES (%s, %s, %s)"
        cursor.execute(query, (user_id, name, description))
        connection.commit()
        
        return True
        
    except Exception as e:
        print(f"Error creating playlist: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_user_playlists():
    """Get all playlists for the current user"""
    try:
        with open("current_user.txt", "r") as f:
            user_id = f.read().strip()
            
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT playlist_id, name, description, created_at
        FROM Playlists
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        
        cursor.execute(query, (user_id,))
        playlists = cursor.fetchall()
        
        return playlists
        
    except Exception as e:
        print(f"Error fetching playlists: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def get_playlist_songs(playlist_id):
    """Get all songs in a specific playlist"""
    try:
        connection = connect_db()
        if not connection:
            return []
            
        cursor = connection.cursor(dictionary=True)
        
        query = """
        SELECT s.song_id, s.title, a.name as artist_name, g.name as genre_name
        FROM Playlist_Songs ps
        JOIN Songs s ON ps.song_id = s.song_id
        JOIN Artists a ON s.artist_id = a.artist_id
        LEFT JOIN Genres g ON s.genre_id = g.genre_id
        WHERE ps.playlist_id = %s
        ORDER BY ps.position
        """
        
        cursor.execute(query, (playlist_id,))
        songs = cursor.fetchall()
        
        return songs
        
    except Exception as e:
        print(f"Error fetching playlist songs: {e}")
        return []
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def add_song_to_playlist(playlist_id, song_id):
    """Add a song to a playlist"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        cursor.execute("SELECT MAX(position) FROM Playlist_Songs WHERE playlist_id = %s", (playlist_id,))
        max_position = cursor.fetchone()[0]
        position = (max_position or 0) + 1
        
        query = "INSERT INTO Playlist_Songs (playlist_id, song_id, position) VALUES (%s, %s, %s)"
        cursor.execute(query, (playlist_id, song_id, position))
        connection.commit()
        
        return True
        
    except Exception as e:
        print(f"Error adding song to playlist: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def remove_song_from_playlist(playlist_id, song_id):
    """Remove a song from a playlist"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        query = "DELETE FROM Playlist_Songs WHERE playlist_id = %s AND song_id = %s"
        cursor.execute(query, (playlist_id, song_id))
        connection.commit()
        
        return True
        
    except Exception as e:
        print(f"Error removing song from playlist: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def delete_playlist(playlist_id):
    """Delete a playlist"""
    try:
        connection = connect_db()
        if not connection:
            return False
            
        cursor = connection.cursor()
        
        query = "DELETE FROM Playlists WHERE playlist_id = %s"
        cursor.execute(query, (playlist_id,))
        connection.commit()
        
        return True
        
    except Exception as e:
        print(f"Error deleting playlist: {e}")
        return False
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

def download_song(song_id):
    """Download a song to local storage"""
    try:
        song_data = get_song_data(song_id)
        if not song_data:
            messagebox.showerror("Error", "Could not retrieve song data")
            return False
        
        filename = f"{song_data['artist']} - {song_data['title']}.{song_data['type']}"
        filename = filename.replace('/', '_').replace('\\', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        save_path = filedialog.asksaveasfilename(
            initialdir=downloads_dir,
            initialfile=filename,
            defaultextension=f".{song_data['type']}",
            filetypes=[(f"{song_data['type'].upper()} files", f"*.{song_data['type']}"), ("All files", "*.*")]
        )
        
        if not save_path:
            return False
        
        with open(save_path, 'wb') as f:
            f.write(song_data['data'])
        
        messagebox.showinfo("Download Complete", f"Song has been downloaded to:\n{save_path}")
        return True
        
    except Exception as e:
        print(f"Error downloading song: {e}")
        messagebox.showerror("Error", f"Could not download song: {e}")
        return False

# ------------------- Music Player Functions -------------------
def play_song(song_id, context=None, songs_list=None):
    """Play a song from its binary data in the database and manage queue"""
    global current_song, song_queue, queue_index, queue_context
    
    try:
        song_data = get_song_data(song_id)
        if not song_data:
            messagebox.showerror("Error", "Could not retrieve song data")
            return False
            
        # Update song queue based on context
        if context and songs_list:
            if queue_context != context or not song_queue:
                song_queue = songs_list
                queue_context = context
            queue_index = next((i for i, song in enumerate(song_queue) if song['song_id'] == song_id), -1)
        else:
            # If no context, maintain current queue or start with featured songs
            if not song_queue or queue_context != 'single':
                song_queue = get_featured_songs(3)
                queue_context = 'single'
            queue_index = next((i for i, song in enumerate(song_queue) if song['song_id'] == song_id), -1)
            if queue_index == -1:
                song_queue.append({'song_id': song_id, 'title': song_data['title'], 'artist_name': song_data['artist']})
                queue_index = len(song_queue) - 1
        
        temp_dir = APP_CONFIG["temp_dir"]
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file = os.path.join(temp_dir, f"song_{song_id}.{song_data['type']}")
        
        with open(temp_file, 'wb') as f:
            f.write(song_data['data'])
            
        mixer.music.load(temp_file)
        mixer.music.play()
        
        current_song = {
            "id": song_id,
            "title": song_data["title"],
            "artist": song_data["artist"],
            "playing": True,
            "paused": False
        }
        
        update_now_playing_display()
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
        featured_songs = get_featured_songs(1)
        if featured_songs:
            play_song(featured_songs[0]['song_id'], context='featured', songs_list=featured_songs)
    elif current_song["paused"]:
        mixer.music.unpause()
        current_song["paused"] = False
        current_song["playing"] = True
        update_now_playing_display()
    elif current_song["playing"]:
        mixer.music.pause()
        current_song["paused"] = True
        current_song["playing"] = False
        update_now_playing_display()

def play_next_song():
    """Play the next song in the queue"""
    global queue_index, song_queue
    
    if not song_queue or queue_index < 0:
        messagebox.showinfo("Info", "No songs in the queue.")
        return
    
    queue_index = min(queue_index + 1, len(song_queue) - 1)
    if queue_index < len(song_queue):
        play_song(song_queue[queue_index]['song_id'], context=queue_context, songs_list=song_queue)
    else:
        messagebox.showinfo("Info", "End of queue reached.")

def play_previous_song():
    """Play the previous song in the queue"""
    global queue_index, song_queue
    
    if not song_queue or queue_index < 0:
        messagebox.showinfo("Info", "No songs in the queue.")
        return
    
    queue_index = max(queue_index - 1, 0)
    play_song(song_queue[queue_index]['song_id'], context=queue_context, songs_list=song_queue)

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
def update_sidebar_active_page(active_page):
    """Update sidebar button colors to highlight the active page"""
    global sidebar, sidebar_buttons
    if sidebar is None or not sidebar_buttons:
        return
    
    for btn in sidebar_buttons:
        btn.configure(fg_color="transparent", text_color=COLORS["text"])
    
    page_index = {
        "home": 0,
        "search": 1,
        "playlist": 2,
        "download": 3,
        "recommend": 4,
        "trending": 0  # Trending uses home sidebar highlight
    }.get(active_page, 0)
    
    sidebar_buttons[page_index].configure(fg_color=COLORS["primary"], text_color=COLORS["text"])

def create_sidebar(parent_frame, user, active_page="home"):
    """Create the sidebar navigation"""
    global sidebar, sidebar_buttons, now_playing_label, play_btn
    if sidebar is not None:
        update_sidebar_active_page(active_page)
        return sidebar
    
    sidebar = ctk.CTkFrame(parent_frame, width=250, fg_color=COLORS["sidebar"], corner_radius=12)
    sidebar.pack(side="left", fill="y", padx=(10, 0), pady=10)
    sidebar.pack_propagate(False)
    
    ctk.CTkLabel(
        sidebar,
        text=APP_CONFIG["name"],
        font=("Inter", 20, "bold"),
        text_color=COLORS["primary"]
    ).pack(pady=(30, 20), padx=20)
    
    sidebar_buttons = []
    
    nav_items = [
        ("🏠 Home", show_home_view),
        ("🔍 Search", show_search_view),
        ("🎵 Playlists", show_playlist_view),
        ("⬇️ Downloads", show_download_view),
        ("🎧 Recommendations", show_recommend_view)
    ]
    
    for text, command in nav_items:
        btn = ctk.CTkButton(
            sidebar,
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
        sidebar_buttons.append(btn)
    
    ctk.CTkButton(
        sidebar,
        text="🚪 Logout",
        command=open_login_page,
        font=("Inter", 14),
        fg_color=COLORS["danger"],
        hover_color=COLORS["danger_hover"],
        height=40,
        corner_radius=8
    ).pack(side="bottom", fill="x", padx=10, pady=20)
    
    now_playing_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["sidebar"], corner_radius=8)
    now_playing_frame.pack(side="bottom", fill="x", pady=(0, 10), padx=10)
    
    now_playing_label = ctk.CTkLabel(
        now_playing_frame,
        text="Now Playing: No song playing",
        font=("Inter", 12),
        text_color=COLORS["text_secondary"],
        wraplength=220
    )
    now_playing_label.pack(pady=10)
    
    player_frame = ctk.CTkFrame(sidebar, fg_color=COLORS["sidebar"], corner_radius=8)
    player_frame.pack(side="bottom", fill="x", pady=10, padx=10)
    
    prev_btn = ctk.CTkButton(
        player_frame,
        text="⏮️",
        font=("Inter", 14),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        width=40,
        height=40,
        corner_radius=8,
        command=play_previous_song
    )
    prev_btn.pack(side="left", padx=5)
    
    play_btn = ctk.CTkButton(
        player_frame,
        text="▶️",
        font=("Inter", 14),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        width=40,
        height=40,
        corner_radius=8,
        command=toggle_play_pause
    )
    play_btn.pack(side="left", padx=5)
    
    next_btn = ctk.CTkButton(
        player_frame,
        text="⏭️",
        font=("Inter", 14),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        width=40,
        height=40,
        corner_radius=8,
        command=play_next_song
    )
    next_btn.pack(side="left", padx=5)
    
    update_sidebar_active_page(active_page)
    return sidebar

def create_header(parent_frame, title, user):
    """Create the header with title and user info"""
    header_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=8)
    header_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        header_frame,
        text=title,
        font=("Inter", 24, "bold"),
        text_color=COLORS["text"]
    ).pack(side="left")
    
    ctk.CTkLabel(
        header_frame,
        text=f"Hello, {user['first_name']} {user['last_name']}!",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    ).pack(side="right")

def create_home_frame(parent_frame, user):
    """Create the home page UI"""
    create_header(parent_frame, "Home", user)
    
    hero_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["card"], corner_radius=12)
    hero_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        hero_frame,
        text="Discover Music & Play Instantly",
        font=("Inter", 28, "bold"),
        text_color=COLORS["primary"]
    ).pack(anchor="w", padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        hero_frame,
        text="Explore top trending songs, curated playlists, and personalized recommendations.",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"],
        wraplength=600
    ).pack(anchor="w", padx=20, pady=(0, 20))
    
    button_frame = ctk.CTkFrame(hero_frame, fg_color="transparent")
    button_frame.pack(anchor="w", padx=20, pady=(0, 20))
    
    ctk.CTkButton(
        button_frame,
        text="🔥 Trending",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        corner_radius=8,
        height=40,
        width=150,
        command=show_trending_view
    ).pack(side="left", padx=(0, 10))
    
    ctk.CTkButton(
        button_frame,
        text="🎵 Playlists",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["success"],
        hover_color=COLORS["success_hover"],
        corner_radius=8,
        height=40,
        width=150,
        command=show_playlist_view
    ).pack(side="left", padx=10)
    
    ctk.CTkButton(
        button_frame,
        text="⬇️ Download",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        corner_radius=8,
        height=40,
        width=150,
        command=show_download_view
    ).pack(side="left", padx=10)
    
    featured_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    featured_frame.pack(fill="x", padx=20, pady=10)
    
    ctk.CTkLabel(
        featured_frame,
        text="🔥 Featured Songs",
        font=("Inter", 20, "bold"),
        text_color=COLORS["primary"]
    ).pack(anchor="w", padx=20, pady=(20, 10))
    
    songs_frame = ctk.CTkFrame(featured_frame, fg_color="transparent")
    songs_frame.pack(fill="x", padx=20)
    
    featured_songs = get_featured_songs(3)
    if not featured_songs:
        featured_songs = [
            {"song_id": 1, "title": "Blinding Lights", "artist_name": "The Weeknd"},
            {"song_id": 2, "title": "Levitating", "artist_name": "Dua Lipa"},
            {"song_id": 3, "title": "Shape of You", "artist_name": "Ed Sheeran"}
        ]
    
    for song in featured_songs:
        song_card = create_song_card(
            songs_frame,
            song["song_id"],
            song["title"],
            song["artist_name"],
            play_command=lambda sid=song["song_id"]: play_song(sid, context='featured', songs_list=featured_songs)
        )
        song_card.pack(side="left", padx=10)

def create_search_frame(parent_frame, user):
    """Create the search page UI with enhanced artist search"""
    create_header(parent_frame, "Search Songs", user)
    
    search_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["card"], corner_radius=12)
    search_frame.pack(fill="x", padx=20, pady=(20, 10))
    
    search_type_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
    search_type_frame.pack(fill="x", padx=20, pady=(10, 10))
    
    search_type_var = ctk.StringVar(value="all")
    
    for text, value in [("All", "all"), ("Songs", "song"), ("Artists", "artist"), ("Albums", "album")]:
        ctk.CTkRadioButton(
            search_type_frame,
            text=text,
            variable=search_type_var,
            value=value,
            font=("Inter", 12),
            fg_color=COLORS["primary"],
            text_color=COLORS["text"]
        ).pack(side="left", padx=(0, 15))
    
    input_frame = ctk.CTkFrame(search_frame, fg_color="transparent")
    input_frame.pack(fill="x", padx=20, pady=10)
    
    search_entry = ctk.CTkEntry(
        input_frame,
        placeholder_text="Search for songs, artists, or albums...",
        font=("Inter", 14),
        text_color=COLORS["text"],
        fg_color=COLORS["content"],
        border_color=COLORS["primary"],
        height=40,
        corner_radius=8
    )
    search_entry.pack(side="left", fill="x", expand=True)
    
    def perform_search():
        for widget in songs_section.winfo_children():
            if widget != songs_title:
                widget.destroy()
        
        query = search_entry.get()
        if not query:
            recent_songs = get_featured_songs(6)
            display_search_results(recent_songs, "Recent Songs")
            return
        
        search_results = search_songs(query, search_type_var.get())
        if search_results:
            display_search_results(search_results, f"Search Results for '{query}'")
        else:
            ctk.CTkLabel(
                songs_section,
                text=f"No songs found for '{query}'",
                font=("Inter", 14),
                text_color=COLORS["text_secondary"]
            ).pack(pady=20)
    
    search_entry.bind("<Return>", lambda e: perform_search())
    
    ctk.CTkButton(
        input_frame,
        text="Search",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        corner_radius=8,
        height=40,
        width=100,
        command=perform_search
    ).pack(side="right", padx=(10, 0))
    
    global songs_section, songs_title
    songs_section = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    songs_section.pack(fill="both", expand=True, padx=20, pady=10)
    
    songs_title = ctk.CTkLabel(
        songs_section,
        text="Recent Songs 🎵",
        font=("Inter", 20, "bold"),
        text_color=COLORS["primary"]
    )
    songs_title.pack(anchor="w", padx=20, pady=(20, 10))
    
    def display_search_results(songs, section_subtitle=None):
        if section_subtitle:
            songs_title.configure(text=f"🔍 {section_subtitle}")
        
        if not songs:
            ctk.CTkLabel(
                songs_section,
                text="No songs available",
                font=("Inter", 14),
                text_color=COLORS["text_secondary"]
            ).pack(pady=20)
            return
        
        for song in songs:
            song_frame = ctk.CTkFrame(songs_section, fg_color=COLORS["card"], corner_radius=8, height=50)
            song_frame.pack(fill="x", pady=5)
            
            display_text = f"🎵 {song['artist_name']} - {song['title']}"
            if "album_name" in song and song["album_name"]:
                display_text += f" ({song['album_name']})"
            if "duration_formatted" in song:
                display_text += f" ({song['duration_formatted']})"
            
            song_label = ctk.CTkLabel(
                song_frame,
                text=display_text,
                font=("Inter", 14),
                text_color=COLORS["text"],
                anchor="w"
            )
            song_label.pack(side="left", padx=15, fill="y")
            
            ctk.CTkButton(
                song_frame,
                text="▶️",
                font=("Inter", 12),
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                width=40,
                height=40,
                corner_radius=8,
                command=lambda sid=song["song_id"]: play_song(sid, context='search', songs_list=songs)
            ).pack(side="right", padx=5)
            
            ctk.CTkButton(
                song_frame,
                text="➕ Playlist",
                font=("Inter", 12),
                fg_color=COLORS["secondary"],
                hover_color=COLORS["secondary_hover"],
                width=100,
                height=40,
                corner_radius=8,
                command=lambda sid=song["song_id"]: add_song_to_playlist_dialog(sid)
            ).pack(side="right", padx=5)
            
            song_label.bind("<Button-1>", lambda e, sid=song["song_id"]: play_song(sid, context='search', songs_list=songs))

    recent_songs = get_featured_songs(6)
    display_search_results(recent_songs, "Recent Songs")

def create_trending_frame(parent_frame, user):
    """Create the trending songs page UI"""
    create_header(parent_frame, "Trending Songs", user)
    
    songs_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    songs_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        songs_frame,
        text="Trending Songs 🔥",
        font=("Inter", 24, "bold"),
        text_color=COLORS["primary"]
    ).pack(pady=(20, 10))
    
    ctk.CTkLabel(
        songs_frame,
        text="Discover the most popular songs right now.",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    ).pack(pady=(0, 20))
    
    trending_songs = get_popular_songs(10)
    
    if not trending_songs:
        ctk.CTkLabel(
            songs_frame,
            text="No trending songs available",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=30)
    else:
        for song in trending_songs:
            song_frame = ctk.CTkFrame(songs_frame, fg_color=COLORS["card"], corner_radius=8, height=50)
            song_frame.pack(fill="x", pady=5, ipady=5)
            song_frame.pack_propagate(False)
            
            display_text = f"🎵 {song['artist_name']} - {song['title']}"
            if song.get('genre_name'):
                display_text += f" ({song['genre_name']})"
            if 'file_size_formatted' in song and 'file_type' in song:
                display_text += f" ({song['file_size_formatted']} - {song['file_type']})"
            
            ctk.CTkLabel(
                song_frame,
                text=display_text,
                font=("Inter", 14),
                text_color=COLORS["text"],
                anchor="w"
            ).pack(side="left", padx=20)
            
            ctk.CTkButton(
                song_frame,
                text="▶️ Play",
                font=("Inter", 12),
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                width=80,
                height=40,
                corner_radius=8,
                command=lambda sid=song["song_id"]: play_song(sid, context='trending', songs_list=trending_songs)
            ).pack(side="right", padx=5)
            
            ctk.CTkButton(
                song_frame,
                text="➕ Playlist",
                font=("Inter", 12),
                fg_color=COLORS["secondary"],
                hover_color=COLORS["secondary_hover"],
                width=100,
                height=40,
                corner_radius=8,
                command=lambda sid=song["song_id"]: add_song_to_playlist_dialog(sid)
            ).pack(side="right", padx=5)
            
            song_frame.bind("<Button-1>", lambda e, sid=song["song_id"]: play_song(sid, context='trending', songs_list=trending_songs))

def add_song_to_playlist_dialog(song_id):
    """Open a dialog to select a playlist to add the song to"""
    dialog = ctk.CTkToplevel()
    dialog.title("Add to Playlist")
    dialog.geometry("350x450")
    dialog.configure(fg_color=COLORS["content"])
    
    ctk.CTkLabel(
        dialog,
        text="Select Playlist",
        font=("Inter", 16, "bold"),
        text_color=COLORS["text"]
    ).pack(pady=20)
    
    playlists = get_user_playlists()
    playlist_var = ctk.StringVar()
    
    if playlists:
        ctk.CTkOptionMenu(
            dialog,
            variable=playlist_var,
            values=[p["name"] for p in playlists],
            font=("Inter", 14),
            fg_color=COLORS["primary"],
            button_color=COLORS["primary_hover"],
            button_hover_color=COLORS["primary"],
            text_color=COLORS["text"],
            width=250,
            height=40
        ).pack(pady=10)
    else:
        ctk.CTkLabel(
            dialog,
            text="No playlists available",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=20)
    
    def add_to_selected_playlist():
        if not playlists:
            messagebox.showwarning("Warning", "No playlists available. Please create a playlist first.")
            return
        
        playlist_name = playlist_var.get()
        if not playlist_name:
            messagebox.showwarning("Warning", "Please select a playlist.")
            return
        
        playlist_id = next(p["playlist_id"] for p in playlists if p["name"] == playlist_name)
        
        if add_song_to_playlist(playlist_id, song_id):
            messagebox.showinfo("Success", "Song added to playlist!")
            dialog.destroy()
        else:
            messagebox.showerror("Error", "Failed to add song to playlist.")
    
    ctk.CTkButton(
        dialog,
        text="Add to Playlist",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        corner_radius=8,
        height=40,
        command=add_to_selected_playlist
    ).pack(pady=20)
    
    ctk.CTkLabel(
        dialog,
        text="Or create a new playlist:",
        font=("Inter", 14),
        text_color=COLORS["text"]
    ).pack(pady=(20, 10))
    
    new_playlist_entry = ctk.CTkEntry(
        dialog,
        placeholder_text="New playlist name",
        font=("Inter", 14),
        text_color=COLORS["text"],
        fg_color=COLORS["card"],
        border_color=COLORS["primary"],
        height=40,
        width=250
    )
    new_playlist_entry.pack(pady=10)
    
    def create_and_add_to_playlist():
        playlist_name = new_playlist_entry.get().strip()
        if not playlist_name:
            messagebox.showwarning("Warning", "Please enter a playlist name.")
            return
        
        if create_playlist(playlist_name):
            new_playlists = get_user_playlists()
            new_playlist_id = next(p["playlist_id"] for p in new_playlists if p["name"] == playlist_name)
            if add_song_to_playlist(new_playlist_id, song_id):
                messagebox.showinfo("Success", f"Created playlist '{playlist_name}' and added song!")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to add song to new playlist.")
        else:
            messagebox.showerror("Error", "Failed to create playlist.")
    
    ctk.CTkButton(
        dialog,
        text="Create & Add",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        corner_radius=8,
        height=40,
        command=create_and_add_to_playlist
    ).pack(pady=10)

def create_download_frame(parent_frame, user):
    """Create the download page UI"""
    create_header(parent_frame, "Download Songs", user)
    
    favorite_songs_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    favorite_songs_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        favorite_songs_frame,
        text="Download Your Favorite Songs 🎵",
        font=("Inter", 24, "bold"),
        text_color=COLORS["primary"]
    ).pack(pady=(20, 10))
    
    ctk.CTkLabel(
        favorite_songs_frame,
        text="Select a song to download or upload your own.",
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    ).pack(pady=(0, 20))
    
    tabs = ctk.CTkTabview(favorite_songs_frame, fg_color=COLORS["card"], corner_radius=8)
    tabs.pack(fill="both", expand=True)
    
    favorite_tab = tabs.add("Your Favorites")
    popular_tab = tabs.add("Popular Songs")
    
    global selected_song, song_frames
    selected_song = {"id": None, "title": None, "artist": None}
    song_frames = []
    
    def select_song_for_download(song_id, title, artist, song_frame):
        global selected_song, song_frames
        for frame in song_frames:
            frame.configure(fg_color=COLORS["card"])
        song_frame.configure(fg_color=COLORS["primary"])
        selected_song["id"] = song_id
        selected_song["title"] = title
        selected_song["artist"] = artist
    
    def display_songs_in_tab(tab, songs):
        if not songs:
            ctk.CTkLabel(
                tab,
                text="No songs available",
                font=("Inter", 14),
                text_color=COLORS["text_secondary"]
            ).pack(pady=30)
            return
        
        for song in songs:
            song_frame = ctk.CTkFrame(tab, fg_color=COLORS["card"], corner_radius=8, height=50)
            song_frame.pack(fill="x", pady=5, ipady=5)
            song_frame.pack_propagate(False)
            
            ctk.CTkLabel(
                song_frame,
                text=f"🎵 {song['artist_name']} - {song['title']}",
                font=("Inter", 14),
                text_color=COLORS["text"],
                anchor="w"
            ).pack(side="left", padx=20)
            
            if 'file_size_formatted' in song and 'file_type' in song:
                ctk.CTkLabel(
                    song_frame,
                    text=f"{song['file_size_formatted']} ({song['file_type']})",
                    font=("Inter", 12),
                    text_color=COLORS["text_secondary"]
                ).pack(side="right", padx=(0, 20))
            
            ctk.CTkButton(
                song_frame,
                text="▶️",
                font=("Inter", 12),
                fg_color=COLORS["success"],
                hover_color=COLORS["success_hover"],
                width=40,
                height=40,
                corner_radius=8,
                command=lambda sid=song['song_id']: play_song(sid, context='download', songs_list=songs)
            ).pack(side="right", padx=5)
            
            ctk.CTkButton(
                song_frame,
                text="➕ Playlist",
                font=("Inter", 12),
                fg_color=COLORS["secondary"],
                hover_color=COLORS["secondary_hover"],
                width=100,
                height=40,
                corner_radius=8,
                command=lambda sid=song['song_id']: add_song_to_playlist_dialog(sid)
            ).pack(side="right", padx=5)
            
            song_frame.bind(
                "<Button-1>",
                lambda e, sid=song['song_id'], title=song['title'], artist=song['artist_name'], frame=song_frame:
                    select_song_for_download(sid, title, artist, frame)
            )
            song_frames.append(song_frame)
    
    favorite_songs = get_user_favorite_songs()
    display_songs_in_tab(favorite_tab, favorite_songs)
    
    popular_songs = get_popular_songs()
    display_songs_in_tab(popular_tab, popular_songs)
    
    button_frame = ctk.CTkFrame(favorite_songs_frame, fg_color="transparent")
    button_frame.pack(pady=20)
    
    def download_selected_song():
        if not selected_song["id"]:
            messagebox.showwarning("Warning", "Please select a song to download")
            return
        download_song(selected_song["id"])
    
    def handle_upload_song():
        messagebox.showinfo("Upload Song", "This functionality will be implemented in a future update.")
    
    ctk.CTkButton(
        button_frame,
        text="⬇️ Download Selected",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        corner_radius=8,
        height=40,
        width=210,
        command=download_selected_song
    ).pack(side="left", padx=10)
    
    ctk.CTkButton(
        button_frame,
        text="⬆️ Upload New Song",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["secondary"],
        hover_color=COLORS["secondary_hover"],
        corner_radius=8,
        height=40,
        width=210,
        command=handle_upload_song
    ).pack(side="left", padx=10)

def create_recommend_frame(parent_frame, user):
    """Create the recommendations page UI"""
    create_header(parent_frame, "Recommended Songs", user)
    
    songs_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    songs_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        songs_frame,
        text="Songs You Might Like 🎵",
        font=("Inter", 24, "bold"),
        text_color=COLORS["primary"]
    ).pack(pady=(20, 10))
    
    subtitle_text = "Discover music based on your listening history."
    if not get_user_favorite_songs(limit=1):
        subtitle_text = "Start listening to songs to get personalized recommendations."
    
    ctk.CTkLabel(
        songs_frame,
        text=subtitle_text,
        font=("Inter", 14),
        text_color=COLORS["text_secondary"]
    ).pack(pady=(0, 20))
    
    recommended_songs_frame = ctk.CTkFrame(songs_frame, fg_color="transparent")
    recommended_songs_frame.pack(fill="both", expand=True)
    
    recommended_songs = get_recommended_songs(8)
    
    if not recommended_songs:
        ctk.CTkLabel(
            recommended_songs_frame,
            text="No recommended songs available",
            font=("Inter", 14),
            text_color=COLORS["text_secondary"]
        ).pack(pady=30)
    else:
        for song in recommended_songs:
            song_frame = ctk.CTkFrame(recommended_songs_frame, fg_color=COLORS["card"], corner_radius=8, height=50)
            song_frame.pack(fill="x", pady=5, ipady=5)
            song_frame.pack_propagate(False)
            
            display_text = f"🎵 {song['artist_name']} - {song['title']}"
            if song.get('genre_name'):
                display_text += f" ({song['genre_name']})"
            
            ctk.CTkLabel(
                song_frame,
                text=display_text,
                font=("Inter", 14),
                text_color=COLORS["text"],
                anchor="w"
            ).pack(side="left", padx=20)
            
            ctk.CTkButton(
                song_frame,
                text="▶️ Play",
                font=("Inter", 12),
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                width=80,
                height=40,
                corner_radius=8,
                command=lambda sid=song["song_id"]: play_song(sid, context='recommend', songs_list=recommended_songs)
            ).pack(side="right", padx=5)
            
            ctk.CTkButton(
                song_frame,
                text="➕ Playlist",
                font=("Inter", 12),
                fg_color=COLORS["secondary"],
                hover_color=COLORS["secondary_hover"],
                width=100,
                height=40,
                corner_radius=8,
                command=lambda sid=song["song_id"]: add_song_to_playlist_dialog(sid)
            ).pack(side="right", padx=5)
            
            song_frame.bind("<Button-1>", lambda e, sid=song["song_id"]: play_song(sid, context='recommend', songs_list=recommended_songs))
    
    button_frame = ctk.CTkFrame(songs_frame, fg_color="transparent")
    button_frame.pack(pady=20)
    
    def refresh_recommendations():
        clear_content_frame()
        create_recommend_frame(content_frame, user)
        messagebox.showinfo("Refreshed", "Recommendations have been updated!")
    
    ctk.CTkButton(
        button_frame,
        text="⟳ Refresh",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        corner_radius=8,
        height=40,
        width=140,
        command=refresh_recommendations
    ).pack()

def create_playlist_frame(parent_frame, user):
    """Create the playlist page UI with creation and management features"""
    create_header(parent_frame, "Playlists", user)
    
    main_content_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
    main_content_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))
    
    ctk.CTkLabel(
        main_content_frame,
        text="Your Playlists 🎵",
        font=("Inter", 24, "bold"),
        text_color=COLORS["primary"]
    ).pack(pady=(20, 10))
    
    create_frame = ctk.CTkFrame(main_content_frame, fg_color=COLORS["card"], corner_radius=8)
    create_frame.pack(fill="x", pady=10)
    
    playlist_name_entry = ctk.CTkEntry(
        create_frame,
        placeholder_text="Enter playlist name",
        font=("Inter", 14),
        text_color=COLORS["text"],
        fg_color=COLORS["content"],
        border_color=COLORS["primary"],
        height=40,
        width=300
    )
    playlist_name_entry.pack(side="left", padx=10)
    
    def create_new_playlist():
        playlist_name = playlist_name_entry.get().strip()
        if not playlist_name:
            messagebox.showwarning("Warning", "Please enter a playlist name.")
            return
        
        if create_playlist(playlist_name):
            messagebox.showinfo("Success", f"Playlist '{playlist_name}' created!")
            clear_content_frame()
            create_playlist_frame(parent_frame, user)
        else:
            messagebox.showerror("Error", "Failed to create playlist.")
    
    ctk.CTkButton(
        create_frame,
        text="Create Playlist",
        font=("Inter", 14, "bold"),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        corner_radius=8,
        height=40,
        command=create_new_playlist
    ).pack(side="left", padx=10)
    
    playlists_frame = ctk.CTkFrame(main_content_frame, fg_color="transparent")
    playlists_frame.pack(fill="both", expand=True)
    
    playlists = get_user_playlists()
    
    if not playlists:
        ctk.CTkLabel(
            playlists_frame,
            text="No playlists created yet. Create one above!",
            font=("Inter", 16),
            text_color=COLORS["text_secondary"]
        ).pack(pady=20)
    else:
        for playlist in playlists:
            playlist_frame = ctk.CTkFrame(playlists_frame, fg_color=COLORS["card"], corner_radius=8)
            playlist_frame.pack(fill="x", pady=5)
            
            ctk.CTkLabel(
                playlist_frame,
                text=f"📋 {playlist['name']}",
                font=("Inter", 16, "bold"),
                text_color=COLORS["text"]
            ).pack(side="left", padx=10)
            
            ctk.CTkButton(
                playlist_frame,
                text="View Songs",
                font=("Inter", 12),
                fg_color=COLORS["primary"],
                hover_color=COLORS["primary_hover"],
                width=100,
                height=40,
                corner_radius=8,
                command=lambda pid=playlist["playlist_id"]: show_playlist_songs(pid)
            ).pack(side="right", padx=5)
            
            ctk.CTkButton(
                playlist_frame,
                text="🗑️",
                font=("Inter", 12),
                fg_color=COLORS["danger"],
                hover_color=COLORS["danger_hover"],
                width=40,
                height=40,
                corner_radius=8,
                command=lambda pid=playlist["playlist_id"]: delete_playlist_and_refresh(pid)
            ).pack(side="right", padx=5)
    
    def show_playlist_songs(playlist_id):
        clear_content_frame()
        create_header(parent_frame, "Playlist Songs", user)
        
        songs_frame = ctk.CTkFrame(parent_frame, fg_color=COLORS["content"], corner_radius=12)
        songs_frame.pack(fill="both", expand=True, padx=20, pady=(20, 10))
        
        playlist = next(p for p in playlists if p["playlist_id"] == playlist_id)
        ctk.CTkLabel(
            songs_frame,
            text=f"Songs in {playlist['name']} 🎵",
            font=("Inter", 24, "bold"),
            text_color=COLORS["primary"]
        ).pack(pady=(20, 10))
        
        songs = get_playlist_songs(playlist_id)
        
        if not songs:
            ctk.CTkLabel(
                songs_frame,
                text="No songs in this playlist. Add some from the Search page!",
                font=("Inter", 16),
                text_color=COLORS["text_secondary"]
            ).pack(pady=20)
        else:
            for song in songs:
                song_frame = ctk.CTkFrame(songs_frame, fg_color=COLORS["card"], corner_radius=8, height=50)
                song_frame.pack(fill="x", pady=5)
                
                ctk.CTkLabel(
                    song_frame,
                    text=f"🎵 {song['artist_name']} - {song['title']}",
                    font=("Inter", 14),
                    text_color=COLORS["text"]
                ).pack(side="left", padx=10)
                
                ctk.CTkButton(
                    song_frame,
                    text="▶️",
                    font=("Inter", 12),
                    fg_color=COLORS["success"],
                    hover_color=COLORS["success_hover"],
                    width=40,
                    height=40,
                    corner_radius=8,
                    command=lambda sid=song["song_id"]: play_song(sid, context=f'playlist_{playlist_id}', songs_list=songs)
                ).pack(side="right", padx=5)
                
                ctk.CTkButton(
                    song_frame,
                    text="🗑️",
                    font=("Inter", 12),
                    fg_color=COLORS["danger"],
                    hover_color=COLORS["danger_hover"],
                    width=40,
                    height=40,
                    corner_radius=8,
                    command=lambda sid=song["song_id"]: remove_song_and_refresh(playlist_id, sid)
                ).pack(side="right", padx=5)
        
        ctk.CTkButton(
            songs_frame,
            text="Back to Playlists",
            font=("Inter", 14, "bold"),
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            corner_radius=8,
            height=40,
            command=show_playlist_view
        ).pack(pady=20)
    
    def delete_playlist_and_refresh(playlist_id):
        if delete_playlist(playlist_id):
            messagebox.showinfo("Success", "Playlist deleted!")
            clear_content_frame()
            create_playlist_frame(parent_frame, user)
        else:
            messagebox.showerror("Error", "Failed to delete playlist.")
    
    def remove_song_and_refresh(playlist_id, song_id):
        if remove_song_from_playlist(playlist_id, song_id):
            messagebox.showinfo("Success", "Song removed from playlist!")
            clear_content_frame()
            show_playlist_songs(playlist_id)
        else:
            messagebox.showerror("Error", "Failed to remove song.")

# ------------------- Navigation Functions -------------------
def open_login_page():
    """Logout and open the login page"""
    try:
        if mixer.music.get_busy():
            mixer.music.stop()
            
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
    update_sidebar_active_page("home")
    create_home_frame(content_frame, user_info)

def show_search_view():
    """Show the search view"""
    clear_content_frame()
    update_sidebar_active_page("search")
    create_search_frame(content_frame, user_info)

def show_playlist_view():
    """Show the playlist view"""
    clear_content_frame()
    update_sidebar_active_page("playlist")
    create_playlist_frame(content_frame, user_info)

def show_download_view():
    """Show the download view"""
    clear_content_frame()
    update_sidebar_active_page("download")
    create_download_frame(content_frame, user_info)

def show_recommend_view():
    """Show the recommendations view"""
    clear_content_frame()
    update_sidebar_active_page("recommend")
    create_recommend_frame(content_frame, user_info)

def show_trending_view():
    """Show the trending songs view"""
    clear_content_frame()
    update_sidebar_active_page("trending")
    create_trending_frame(content_frame, user_info)

# ------------------- Initialize App -------------------
if __name__ == "__main__":
    try:
        user_info = get_current_user()
        if not user_info:
            open_login_page()
            exit()

        ensure_directories_exist()
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        root = ctk.CTk()
        root.title(f"{APP_CONFIG['name']} - User Interface")
        root.geometry("1200x700")
        
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")
        
        main_frame = ctk.CTkFrame(root, fg_color=COLORS["background"], corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        view_to_show = "home"
        if len(sys.argv) > 1:
            view_to_show = sys.argv[1].lower()
            
        create_sidebar(main_frame, user_info, view_to_show)
        
        global content_frame
        content_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["background"], corner_radius=12)
        content_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
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
        
        root.mainloop()
        
    except Exception as e:
        print(f"Error initializing application: {e}")
        messagebox.showerror("Error", f"Failed to start application: {e}")
        exit()