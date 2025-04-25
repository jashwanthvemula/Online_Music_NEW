"""
Navigation functions for the Admin section of the Online Music Player application.
"""

import os
import subprocess
from tkinter import messagebox

def open_admin_dashboard():
    """Open the admin dashboard"""
    try:
        subprocess.Popen(["python", "admin/admin_view.py"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open admin dashboard: {e}")

def open_manage_users():
    """Open the manage users page"""
    try:
        subprocess.Popen(["python", "admin/admin_view.py", "users"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open manage users page: {e}")

def open_manage_songs():
    """Open the manage songs page"""
    try:
        subprocess.Popen(["python", "admin/admin_view.py", "songs"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open manage songs page: {e}")

def open_manage_playlists():
    """Open the manage playlists page"""
    try:
        subprocess.Popen(["python", "admin/admin_view.py", "playlists"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open manage playlists page: {e}")

def open_reports():
    """Open the reports and analytics page"""
    try:
        subprocess.Popen(["python", "admin/admin_view.py", "reports"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open reports page: {e}")

def open_login_page():
    """Logout and open the login page"""
    try:
        # Remove admin session file
        if os.path.exists("current_admin.txt"):
            os.remove("current_admin.txt")
            
        subprocess.Popen(["python", "login_signup.py", "login"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to logout: {e}")

def open_admin_login_page():
    """Open the admin login page"""
    try:
        # Remove admin session
        if os.path.exists("current_admin.txt"):
            os.remove("current_admin.txt")
            
        subprocess.Popen(["python", "admin/admin_login.py"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open admin login: {e}")

def open_main_page():
    """Return to the main landing page"""
    try:
        # Remove admin session file
        if os.path.exists("current_admin.txt"):
            os.remove("current_admin.txt")
            
        subprocess.Popen(["python", "main.py"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open main page: {e}")