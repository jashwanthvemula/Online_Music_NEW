"""
Navigation functions for the User section of the Online Music Player application.
"""

import os
import subprocess
from tkinter import messagebox

def open_home_page():
    """Open the home page"""
    try:
        subprocess.Popen(["python", "users/users_view.py", "home"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open home page: {e}")

def open_search_page():
    """Open the search page"""
    try:
        subprocess.Popen(["python", "users/users_view.py", "search"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open search page: {e}")

def open_playlist_page():
    """Open the playlist page"""
    try:
        subprocess.Popen(["python", "users/users_view.py", "playlist"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open playlist page: {e}")

def open_download_page():
    """Open the download page"""
    try:
        subprocess.Popen(["python", "users/users_view.py", "download"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open download page: {e}")

def open_recommend_page():
    """Open the recommendations page"""
    try:
        subprocess.Popen(["python", "users/users_view.py", "recommend"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open recommendations page: {e}")

def open_login_page():
    """Logout and open the login page"""
    try:
        # Stop any playing music if needed
        
        # Remove current user file
        if os.path.exists("current_user.txt"):
            os.remove("current_user.txt")
            
        subprocess.Popen(["python", "login_signup.py", "login"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to logout: {e}")

def open_main_page():
    """Return to the main landing page"""
    try:
        # Remove current user file if exists
        if os.path.exists("current_user.txt"):
            os.remove("current_user.txt")
            
        subprocess.Popen(["python", "main.py"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open main page: {e}")