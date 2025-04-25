"""
Login and signup functionality for the Online Music Player application.
This module handles:
- User login authentication
- New user registration
- Form validation
- Session management
- Forgot password functionality
"""

import os
import sys
import subprocess
import customtkinter as ctk
from tkinter import messagebox
import mysql.connector
import re

# Import from other modules
from db_config import UI_CONFIG, COLORS, DB_CONFIG
from db_utils import connect_db, hash_password, ensure_directories_exist, validate_secret_key, reset_password

# Global variables
root = None
login_frame = None
signup_frame = None

# ------------------- Validation Functions -------------------
def validate_email(email):
    """Simple email validation"""
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Password validation - at least 8 characters"""
    return len(password) >= 8

def validate_secret_key_input(secret_key):
    """Secret key validation - at least 6 characters"""
    return len(secret_key) >= 6

def get_password_strength(password):
    """Evaluate password strength and return (strength label, color)"""
    score = 0
    if len(password) >= 8:
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1
    
    if score <= 2:
        return "Weak", "red"
    elif score <= 4:
        return "Medium", "orange"
    else:
        return "Strong", "green"

# ------------------- Login Functions -------------------
def login_user(email_entry, password_entry):
    """Authenticate user and open home page if successful"""
    email = email_entry.get()
    password = password_entry.get()

    if not email or not password:
        messagebox.showwarning("Input Error", "Please enter both email and password.")
        return
    
    # Hash the password for security
    hashed_password = hash_password(password)

    try:
        connection = connect_db()
        if not connection:
            return
            
        cursor = connection.cursor()
        cursor.execute(
            "SELECT user_id, first_name, last_name FROM Users WHERE email = %s AND password = %s",
            (email, hashed_password)
        )
        user = cursor.fetchone()

        if user:
            user_id, first_name, last_name = user
            messagebox.showinfo("Success", f"Welcome {first_name} {last_name}!")
            
            # Create user files directory if not exists
            user_dir = f"temp/user_{user_id}"
            os.makedirs(user_dir, exist_ok=True)
            
            # Save user ID to a file for session persistence
            with open("current_user.txt", "w") as f:
                f.write(str(user_id))
                
            if 'root' in globals():
                root.destroy()
            open_home_page()
        else:
            messagebox.showerror("Login Failed", "Invalid Email or Password.")
    
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", str(err))
    finally:
        if 'connection' in locals() and connection is not None and connection.is_connected():
            cursor.close()
            connection.close()

def show_forgot_password_dialog():
    """Show a dialog for resetting the password, styled like login/signup pages"""
    dialog = ctk.CTkToplevel()
    dialog.title("Reset Password")
    dialog.geometry("700x600")
    dialog.resizable(True, True)
    dialog.minsize(600, 500)
    
    # Main Frame with rounded corners
    main_frame = ctk.CTkFrame(dialog, corner_radius=20)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Left Side - Branding with purple color
    left_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["primary"], width=350, corner_radius=20)
    left_frame.pack(side="left", fill="y")

    # Title on the left side
    ctk.CTkLabel(
        left_frame, 
        text="Online Music\nSystem",
        font=("Arial", 40, "bold"), 
        text_color="white"
    ).place(relx=0.5, rely=0.22, anchor="center")

    # Description text below title
    ctk.CTkLabel(
        left_frame, 
        text="Reset your password to\ncontinue enjoying unlimited\nad-free music.",
        font=("Arial", 16), 
        text_color="white", 
        justify="center"
    ).place(relx=0.5, rely=0.40, anchor="center")

    # Add music bird illustration
    ctk.CTkLabel(
        left_frame, 
        text="🎵🐦", 
        font=("Arial", 40), 
        text_color="white"
    ).place(relx=0.5, rely=0.75, anchor="center")

    # Right Side - Form
    right_frame = ctk.CTkFrame(main_frame, fg_color="white", width=350)
    right_frame.pack(side="right", fill="both", expand=True)

    # Scrollable content container
    content_frame = ctk.CTkScrollableFrame(right_frame, fg_color="white")
    content_frame.pack(fill="both", expand=True, padx=40, pady=40)

    # Title
    ctk.CTkLabel(
        content_frame,
        text="Reset Your Password",
        font=("Arial", 32, "bold"),
        text_color=COLORS["primary"]
    ).pack(anchor="w", pady=(0, 10))

    # Subtitle
    ctk.CTkLabel(
        content_frame,
        text="Enter your details to reset your password.",
        font=("Arial", 14),
        text_color="gray"
    ).pack(anchor="w", pady=(0, 30))

    # Email Address
    ctk.CTkLabel(
        content_frame,
        text="Email Address",
        font=("Arial", 16, "bold"),
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))
    
    email_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    email_frame.pack(fill="x", pady=(0, 20))
    
    email_entry = ctk.CTkEntry(
        email_frame,
        font=("Arial", 14),
        height=50,
        corner_radius=10,
        border_width=1,
        border_color="#DDDDDD",
        fg_color="white",
        text_color="black",
        placeholder_text="Enter your email"
    )
    email_entry.pack(fill="x", side="left", expand=True)
    
    ctk.CTkLabel(
        email_frame,
        text="✉️",
        font=("Arial", 16),
        fg_color="transparent"
    ).pack(side="right", padx=(0, 10))

    # Secret Key
    ctk.CTkLabel(
        content_frame,
        text="Secret Key",
        font=("Arial", 16, "bold"),
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))
    
    secret_key_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    secret_key_frame.pack(fill="x", pady=(0, 20))
    
    secret_key_entry = ctk.CTkEntry(
        secret_key_frame,
        font=("Arial", 14),
        height=50,
        corner_radius=10,
        border_width=1,
        border_color="#DDDDDD",
        fg_color="white",
        text_color="black",
        placeholder_text="Enter your secret key",
        show="*"
    )
    secret_key_entry.pack(fill="x", side="left", expand=True)
    
    secret_key_toggle = ctk.CTkButton(
        secret_key_frame,
        text="👁️",
        font=("Arial", 14),
        width=30,
        height=30,
        corner_radius=8,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white"
    )
    secret_key_toggle.pack(side="right", padx=(5, 10))
    
    def toggle_secret_key():
        if secret_key_entry.cget("show") == "*":
            secret_key_entry.configure(show="")
            secret_key_toggle.configure(text="🙈")
        else:
            secret_key_entry.configure(show="*")
            secret_key_toggle.configure(text="👁️")
    
    secret_key_toggle.configure(command=toggle_secret_key)
    
    # New Password
    ctk.CTkLabel(
        content_frame,
        text="New Password",
        font=("Arial", 16, "bold"),
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))
    
    new_password_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    new_password_frame.pack(fill="x", pady=(0, 20))
    
    new_password_entry = ctk.CTkEntry(
        new_password_frame,
        font=("Arial", 14),
        height=50,
        corner_radius=10,
        border_width=1,
        border_color="#DDDDDD",
        fg_color="white",
        text_color="black",
        placeholder_text="Enter new password",
        show="*"
    )
    new_password_entry.pack(fill="x", side="left", expand=True)
    
    new_password_toggle = ctk.CTkButton(
        new_password_frame,
        text="👁️",
        font=("Arial", 14),
        width=30,
        height=30,
        corner_radius=8,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white"
    )
    new_password_toggle.pack(side="right", padx=(5, 10))
    
    def toggle_new_password():
        if new_password_entry.cget("show") == "*":
            new_password_entry.configure(show="")
            new_password_toggle.configure(text="🙈")
        else:
            new_password_entry.configure(show="*")
            new_password_toggle.configure(text="👁️")
    
    new_password_toggle.configure(command=toggle_new_password)
    
    # Confirm New Password
    ctk.CTkLabel(
        content_frame,
        text="Confirm New Password",
        font=("Arial", 16, "bold"),
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))
    
    confirm_password_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    confirm_password_frame.pack(fill="x", pady=(0, 20))
    
    confirm_password_entry = ctk.CTkEntry(
        confirm_password_frame,
        font=("Arial", 14),
        height=50,
        corner_radius=10,
        border_width=1,
        border_color="#DDDDDD",
        fg_color="white",
        text_color="black",
        placeholder_text="Confirm new password",
        show="*"
    )
    confirm_password_entry.pack(fill="x", side="left", expand=True)
    
    confirm_password_toggle = ctk.CTkButton(
        confirm_password_frame,
        text="👁️",
        font=("Arial", 14),
        width=30,
        height=30,
        corner_radius=8,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white"
    )
    confirm_password_toggle.pack(side="right", padx=(5, 10))
    
    def toggle_confirm_password():
        if confirm_password_entry.cget("show") == "*":
            confirm_password_entry.configure(show="")
            confirm_password_toggle.configure(text="🙈")
        else:
            confirm_password_entry.configure(show="*")
            confirm_password_toggle.configure(text="👁️")
    
    confirm_password_toggle.configure(command=toggle_confirm_password)
    
    # Reset Password Button
    reset_button = ctk.CTkButton(
        content_frame,
        text="Reset Password",
        font=("Arial", 16, "bold"),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white",
        corner_radius=10,
        height=50,
        command=lambda: reset_password_action()
    )
    reset_button.pack(fill="x", pady=(20, 10))
    
    # Add arrow icon to the button
    ctk.CTkLabel(
        reset_button,
        text="→",
        font=("Arial", 18, "bold"),
        text_color="white"
    ).place(relx=0.9, rely=0.5, anchor="e")

    def reset_password_action():
        email = email_entry.get()
        secret_key = secret_key_entry.get()
        new_password = new_password_entry.get()
        confirm_password = confirm_password_entry.get()
        
        if not email or not secret_key or not new_password or not confirm_password:
            messagebox.showwarning("Input Error", "All fields are required.")
            return
        
        if not validate_email(email):
            messagebox.showwarning("Email Error", "Please enter a valid email address.")
            return
        
        if not validate_password(new_password):
            messagebox.showwarning("Password Error", "New password must be at least 8 characters long.")
            return
        
        if new_password != confirm_password:
            messagebox.showwarning("Password Error", "New passwords do not match.")
            return
        
        if validate_secret_key(email, secret_key):
            if reset_password(email, new_password):
                messagebox.showinfo("Success", "Password reset successfully! Please login with your new password.")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to reset password. Please try again.")
        else:
            messagebox.showerror("Error", "Invalid email or secret key.")

    # Back to Login Button
    back_button = ctk.CTkButton(
        content_frame,
        text="← Back to Login",
        font=("Arial", 14),
        fg_color="transparent",
        hover_color="#EEEEEE",
        text_color=COLORS["primary"],
        corner_radius=10,
        height=40,
        command=dialog.destroy
    )
    back_button.pack(anchor="w", pady=(10, 0))

# ------------------- Signup Functions -------------------
def signup_user(fullname_entry, email_entry, password_entry, confirm_password_entry, secret_key_entry):
    """Register a new user in the database"""
    full_name = fullname_entry.get()
    email = email_entry.get()
    password = password_entry.get()
    confirm_password = confirm_password_entry.get()
    secret_key = secret_key_entry.get()

    # Check if any fields are empty
    if not full_name or not email or not password or not confirm_password or not secret_key:
        messagebox.showwarning("Input Error", "All fields are required.")
        return

    # Validate email format
    if not validate_email(email):
        messagebox.showwarning("Email Error", "Please enter a valid email address.")
        return

    # Validate password strength
    if not validate_password(password):
        messagebox.showwarning("Password Error", "Password must be at least 8 characters long.")
        return

    # Check if passwords match
    if password != confirm_password:
        messagebox.showwarning("Password Error", "Passwords do not match.")
        return

    # Validate secret key
    if not validate_secret_key_input(secret_key):
        messagebox.showwarning("Secret Key Error", "Secret key must be at least 6 characters long.")
        return

    # Split full name into first and last name (assuming space separator)
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Hash the password and secret key
    hashed_password = hash_password(password)
    hashed_secret_key = hash_password(secret_key)

    try:
        connection = connect_db()
        if not connection:
            return
            
        cursor = connection.cursor()

        # Check if email already exists
        cursor.execute("SELECT user_id FROM Users WHERE email = %s", (email,))
        if cursor.fetchone():
            messagebox.showwarning("Registration Error", "This email is already registered.")
            return

        # Insert the user data into the database
        cursor.execute(
            "INSERT INTO Users (first_name, last_name, email, password, secret_key) VALUES (%s, %s, %s, %s, %s)",
            (first_name, last_name, email, hashed_password, hashed_secret_key)
        )

        # Get the new user ID
        user_id = cursor.lastrowid

        # Create default playlist for the user
        cursor.execute(
            "INSERT INTO Playlists (user_id, name, description) VALUES (%s, %s, %s)",
            (user_id, "Favorites", "My favorite songs")
        )

        connection.commit()
        messagebox.showinfo("Success", "User registered successfully!")
        
        # After successful registration, redirect to login page
        if 'root' in globals():
            root.destroy()
        open_login_page()

    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", str(err))
    finally:
        if 'connection' in locals() and connection and connection.is_connected():
            cursor.close()
            connection.close()

# ------------------- Navigation Functions -------------------
def open_home_page():
    """Open the home page after successful login"""
    try:
        subprocess.Popen(["python", "users/users_view.py", "home"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open home page: {e}")

def open_login_page():
    """Open the login page"""
    try:
        subprocess.Popen(["python", "login_signup.py", "login"])
        if root and root.winfo_exists():
            root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open login page: {e}")

def open_main_page():
    """Return to the main landing page"""
    try:
        subprocess.Popen(["python", "main.py"])
        if root and root.winfo_exists():
            root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open main page: {e}")

# ------------------- UI Creation Functions -------------------
def create_login_ui(parent_frame):
    """Create the login UI elements"""
    # Scrollable content frame
    content_frame = ctk.CTkScrollableFrame(parent_frame, fg_color="white")
    content_frame.pack(fill="both", expand=True, padx=40, pady=40)

    # Welcome Back! label
    ctk.CTkLabel(
        content_frame, 
        text="Welcome Back!", 
        font=("Arial", 32, "bold"), 
        text_color=COLORS["primary"]
    ).pack(anchor="w", pady=(0, 10))

    # Subtitle
    ctk.CTkLabel(
        content_frame, 
        text="Login to explore a world of non-stop music.",
        font=("Arial", 14), 
        text_color="gray"
    ).pack(anchor="w", pady=(0, 30))

    # Email Address label
    ctk.CTkLabel(
        content_frame, 
        text="Email Address", 
        font=("Arial", 16, "bold"), 
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))

    # Email entry with proper icon placement
    email_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    email_frame.pack(fill="x", pady=(0, 20))
    
    email_entry = ctk.CTkEntry(
        email_frame, 
        font=("Arial", 14), 
        height=50, 
        corner_radius=10,
        border_width=1, 
        border_color="#DDDDDD",
        fg_color="white", 
        text_color="black",
        placeholder_text="Enter your email"
    )
    email_entry.pack(fill="x", side="left", expand=True)
    
    ctk.CTkLabel(
        email_frame, 
        text="✉️", 
        font=("Arial", 16), 
        fg_color="transparent"
    ).pack(side="right", padx=(0, 10))

    # Password label
    ctk.CTkLabel(
        content_frame, 
        text="Password", 
        font=("Arial", 16, "bold"), 
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))

    # Password entry with proper icon placement
    password_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    password_frame.pack(fill="x", pady=(0, 20))
    
    password_entry = ctk.CTkEntry(
        password_frame, 
        font=("Arial", 14), 
        height=50, 
        corner_radius=10, 
        border_width=1, 
        border_color="#DDDDDD",
        fg_color="white", 
        text_color="black", 
        show="*",
        placeholder_text="Enter your password"
    )
    password_entry.pack(fill="x", side="left", expand=True)
    
    password_toggle = ctk.CTkButton(
        password_frame,
        text="👁️",
        font=("Arial", 14),
        width=30,
        height=30,
        corner_radius=8,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white"
    )
    password_toggle.pack(side="right", padx=(5, 10))
    
    def toggle_password():
        if password_entry.cget("show") == "*":
            password_entry.configure(show="")
            password_toggle.configure(text="🙈")
        else:
            password_entry.configure(show="*")
            password_toggle.configure(text="👁️")
    
    password_toggle.configure(command=toggle_password)
    
    # Remember Me & Forgot Password row
    remember_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    remember_frame.pack(fill="x", pady=(10, 20))

    # Remember me checkbox
    remember_var = ctk.BooleanVar()
    ctk.CTkCheckBox(
        remember_frame, 
        text="Remember me", 
        variable=remember_var, 
        text_color="#333333", 
        font=("Arial", 14),
        fg_color=COLORS["primary"], 
        border_color="#DDDDDD",
        checkbox_height=20, 
        checkbox_width=20
    ).pack(side="left")

    # Forgot password link
    forgot_pass = ctk.CTkLabel(
        remember_frame, 
        text="Forgot password?", 
        font=("Arial", 14), 
        text_color=COLORS["primary"],
        cursor="hand2"
    )
    forgot_pass.pack(side="right")
    forgot_pass.bind("<Button-1>", lambda e: show_forgot_password_dialog())

    # Login button
    login_button = ctk.CTkButton(
        content_frame, 
        text="Login", 
        font=("Arial", 16, "bold"),
        fg_color=COLORS["primary"], 
        hover_color=COLORS["primary_hover"], 
        text_color="white", 
        corner_radius=10, 
        height=50, 
        command=lambda: login_user(email_entry, password_entry)
    )
    login_button.pack(fill="x", pady=(0, 10))
    
    # Add arrow icon to the login button
    ctk.CTkLabel(
        login_button, 
        text="→", 
        font=("Arial", 18, "bold"), 
        text_color="white"
    ).place(relx=0.9, rely=0.5, anchor="e")

    # Signup button
    signup_button = ctk.CTkButton(
        content_frame, 
        text="Create New Account", 
        font=("Arial", 16, "bold"),
        fg_color=COLORS["secondary"], 
        hover_color=COLORS["secondary_hover"], 
        text_color="white", 
        corner_radius=10, 
        height=50, 
        command=show_signup_frame
    )
    signup_button.pack(fill="x", pady=(10, 20))

    # Back to main menu
    back_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    back_frame.pack(pady=(10, 0))
    
    back_label = ctk.CTkLabel(
        back_frame, 
        text="← Back to main menu", 
        font=("Arial", 14), 
        text_color=COLORS["primary"],
        cursor="hand2"
    )
    back_label.pack()
    back_label.bind("<Button-1>", lambda e: open_main_page())
    
    return email_entry, password_entry

def create_signup_ui(parent_frame):
    """Create the signup UI elements"""
    # Scrollable content frame
    content_frame = ctk.CTkScrollableFrame(parent_frame, fg_color="white")
    content_frame.pack(fill="both", expand=True, padx=40, pady=40)

    # Create an Account title
    ctk.CTkLabel(
        content_frame, 
        text="Create an Account", 
        font=("Arial", 32, "bold"), 
        text_color=COLORS["primary"]
    ).pack(anchor="w", pady=(0, 10))

    # Subtitle
    ctk.CTkLabel(
        content_frame, 
        text="Sign up to start your journey into the world of music.",
        font=("Arial", 14), 
        text_color="gray"
    ).pack(anchor="w", pady=(0, 30))

    # Full Name label
    ctk.CTkLabel(
        content_frame, 
        text="Full Name", 
        font=("Arial", 16, "bold"), 
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))

    # Full Name Entry with person icon
    fullname_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    fullname_frame.pack(fill="x", pady=(0, 20))

    fullname_entry = ctk.CTkEntry(
        fullname_frame, 
        font=("Arial", 14), 
        height=50, 
        corner_radius=10,
        border_width=1, 
        border_color="#DDDDDD",
        fg_color="white", 
        text_color="black",
        placeholder_text="Enter your full name"
    )
    fullname_entry.pack(fill="x", side="left", expand=True)

    ctk.CTkLabel(
        fullname_frame, 
        text="👤", 
        font=("Arial", 16), 
        fg_color="transparent"
    ).pack(side="right", padx=(0, 10))

    # Email Address label
    ctk.CTkLabel(
        content_frame, 
        text="Email Address", 
        font=("Arial", 16, "bold"), 
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))

    # Email Entry with envelope icon
    email_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    email_frame.pack(fill="x", pady=(0, 20))

    email_entry = ctk.CTkEntry(
        email_frame, 
        font=("Arial", 14), 
        height=50, 
        corner_radius=10,
        border_width=1, 
        border_color="#DDDDDD",
        fg_color="white", 
        text_color="black",
        placeholder_text="Enter your email"
    )
    email_entry.pack(fill="x", side="left", expand=True)

    ctk.CTkLabel(
        email_frame, 
        text="✉️", 
        font=("Arial", 16), 
        fg_color="transparent"
    ).pack(side="right", padx=(0, 10))

    # Password label
    ctk.CTkLabel(
        content_frame, 
        text="Password", 
        font=("Arial", 16, "bold"), 
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))

    # Password Entry with lock icon and toggle
    password_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    password_frame.pack(fill="x", pady=(0, 10))

    password_entry = ctk.CTkEntry(
        password_frame, 
        font=("Arial", 14), 
        height=50, 
        corner_radius=10,
        border_width=1, 
        border_color="#DDDDDD",
        fg_color="white", 
        text_color="black", 
        show="*",
        placeholder_text="Enter your password"
    )
    password_entry.pack(fill="x", side="left", expand=True)

    password_toggle = ctk.CTkButton(
        password_frame,
        text="👁️",
        font=("Arial", 14),
        width=30,
        height=30,
        corner_radius=8,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white"
    )
    password_toggle.pack(side="right", padx=(5, 10))
    
    ctk.CTkLabel(
        password_frame, 
        text="🔒", 
        font=("Arial", 16), 
        fg_color="transparent"
    ).pack(side="right", padx=(0, 5))

    def toggle_password():
        if password_entry.cget("show") == "*":
            password_entry.configure(show="")
            password_toggle.configure(text="🙈")
        else:
            password_entry.configure(show="*")
            password_toggle.configure(text="👁️")
    
    password_toggle.configure(command=toggle_password)

    # Password Strength Indicator
    strength_label = ctk.CTkLabel(
        content_frame,
        text="Password Strength: None",
        font=("Arial", 12),
        text_color="gray"
    )
    strength_label.pack(anchor="w", pady=(0, 10))

    def update_password_strength(event=None):
        password = password_entry.get()
        if not password:
            strength_label.configure(text="Password Strength: None", text_color="gray")
        else:
            strength, color = get_password_strength(password)
            strength_label.configure(text=f"Password Strength: {strength}", text_color=color)

    password_entry.bind("<KeyRelease>", update_password_strength)

    # Confirm Password label
    ctk.CTkLabel(
        content_frame, 
        text="Confirm Password", 
        font=("Arial", 16, "bold"), 
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))

    # Confirm Password Entry with lock icon and toggle
    confirm_password_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    confirm_password_frame.pack(fill="x", pady=(0, 20))

    confirm_password_entry = ctk.CTkEntry(
        confirm_password_frame, 
        font=("Arial", 14), 
        height=50, 
        corner_radius=10, 
        border_width=1, 
        border_color="#DDDDDD",
        fg_color="white", 
        text_color="black", 
        show="*",
        placeholder_text="Confirm your password"
    )
    confirm_password_entry.pack(fill="x", side="left", expand=True)

    confirm_password_toggle = ctk.CTkButton(
        confirm_password_frame,
        text="👁️",
        font=("Arial", 14),
        width=30,
        height=30,
        corner_radius=8,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white"
    )
    confirm_password_toggle.pack(side="right", padx=(5, 10))
    
    ctk.CTkLabel(
        confirm_password_frame, 
        text="🔒", 
        font=("Arial", 16), 
        fg_color="transparent"
    ).pack(side="right", padx=(0, 5))

    def toggle_confirm_password():
        if confirm_password_entry.cget("show") == "*":
            confirm_password_entry.configure(show="")
            confirm_password_toggle.configure(text="🙈")
        else:
            confirm_password_entry.configure(show="*")
            confirm_password_toggle.configure(text="👁️")
    
    confirm_password_toggle.configure(command=toggle_confirm_password)

    # Secret Key label
    ctk.CTkLabel(
        content_frame, 
        text="Secret Key", 
        font=("Arial", 16, "bold"), 
        text_color="#333333"
    ).pack(anchor="w", pady=(0, 5))

    # Secret Key Entry with key icon and toggle
    secret_key_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    secret_key_frame.pack(fill="x", pady=(0, 20))

    secret_key_entry = ctk.CTkEntry(
        secret_key_frame, 
        font=("Arial", 14), 
        height=50, 
        corner_radius=10, 
        border_width=1, 
        border_color="#DDDDDD",
        fg_color="white", 
        text_color="black", 
        show="*",
        placeholder_text="Enter a secret key for password recovery"
    )
    secret_key_entry.pack(fill="x", side="left", expand=True)

    secret_key_toggle = ctk.CTkButton(
        secret_key_frame,
        text="👁️",
        font=("Arial", 14),
        width=30,
        height=30,
        corner_radius=8,
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white"
    )
    secret_key_toggle.pack(side="right", padx=(5, 10))
    
    ctk.CTkLabel(
        secret_key_frame, 
        text="🔑", 
        font=("Arial", 16), 
        fg_color="transparent"
    ).pack(side="right", padx=(0, 5))

    def toggle_secret_key():
        if secret_key_entry.cget("show") == "*":
            secret_key_entry.configure(show="")
            secret_key_toggle.configure(text="🙈")
        else:
            secret_key_entry.configure(show="*")
            secret_key_toggle.configure(text="👁️")
    
    secret_key_toggle.configure(command=toggle_secret_key)

    # Sign Up button
    signup_button = ctk.CTkButton(
        content_frame, 
        text="Sign Up", 
        font=("Arial", 16, "bold"),
        fg_color=COLORS["primary"], 
        hover_color=COLORS["primary_hover"], 
        text_color="white", 
        corner_radius=10, 
        height=50, 
        command=lambda: signup_user(fullname_entry, email_entry, password_entry, confirm_password_entry, secret_key_entry)
    )
    signup_button.pack(fill="x", pady=(20, 10))

    # Add arrow icon to the signup button
    ctk.CTkLabel(
        signup_button, 
        text="→", 
        font=("Arial", 18, "bold"), 
        text_color="white"
    ).place(relx=0.9, rely=0.5, anchor="e")

    # Already have an account link
    login_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    login_frame.pack(pady=(10, 0))

    ctk.CTkLabel(
        login_frame, 
        text="Already have an account? ", 
        font=("Arial", 14), 
        text_color="#333333"
    ).pack(side="left")

    login_label = ctk.CTkLabel(
        login_frame, 
        text="Login", 
        font=("Arial", 14, "bold"), 
        text_color=COLORS["primary"], 
        cursor="hand2"
    )
    login_label.pack(side="left")
    login_label.bind("<Button-1>", lambda e: show_login_frame())
    
    # Back to main menu
    back_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    back_frame.pack(pady=(10, 0))
    
    back_label = ctk.CTkLabel(
        back_frame, 
        text="← Back to main menu", 
        font=("Arial", 14), 
        text_color=COLORS["primary"],
        cursor="hand2"
    )
    back_label.pack()
    back_label.bind("<Button-1>", lambda e: open_main_page())
    
    return fullname_entry, email_entry, password_entry, confirm_password_entry, secret_key_entry

def init_ui():
    """Initialize the UI"""
    global root, login_frame, signup_frame
    
    # Ensure temp directory exists
    ensure_directories_exist()
    
    # Setup CustomTkinter appearance
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    # Main window
    root = ctk.CTk()
    root.title("Online Music System - Login/Signup")
    root.geometry("700x600")
    root.minsize(600, 500)
    root.resizable(True, True)
    
    # Main Frame with rounded corners
    main_frame = ctk.CTkFrame(root, corner_radius=20)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Left Side - Branding with purple color
    left_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["primary"], width=350, corner_radius=20)
    left_frame.pack(side="left", fill="y")

    # Title on the left side
    ctk.CTkLabel(
        left_frame, 
        text="Online Music\nSystem",
        font=("Arial", 40, "bold"), 
        text_color="white"
    ).place(relx=0.5, rely=0.22, anchor="center")

    # Description text below title
    ctk.CTkLabel(
        left_frame, 
        text="Enjoy unlimited *ad-free music*\nanytime, anywhere. Access premium\nplaylists and high-quality audio\nstreaming.",
        font=("Arial", 16), 
        text_color="white", 
        justify="center"
    ).place(relx=0.5, rely=0.40, anchor="center")

    # Add music bird illustration
    ctk.CTkLabel(
        left_frame, 
        text="🎵🐦", 
        font=("Arial", 40), 
        text_color="white"
    ).place(relx=0.5, rely=0.75, anchor="center")

    # Right Side - Login/Signup Forms
    right_frame = ctk.CTkFrame(main_frame, fg_color="white", width=350)
    right_frame.pack(side="right", fill="both", expand=True)

    # Create login and signup frames
    login_frame = ctk.CTkFrame(right_frame, fg_color="white")
    signup_frame = ctk.CTkFrame(right_frame, fg_color="white")
    
    # Create content container with padding for both frames
    login_content = ctk.CTkFrame(login_frame, fg_color="white")
    login_content.pack(fill="both", expand=True)
    
    signup_content = ctk.CTkFrame(signup_frame, fg_color="white")
    signup_content.pack(fill="both", expand=True)
    
    # Create login UI elements
    email_entry, password_entry = create_login_ui(login_content)
    
    # Create signup UI elements
    fullname_entry, signup_email_entry, signup_password_entry, confirm_password_entry, secret_key_entry = create_signup_ui(signup_content)
    
    # Set the appropriate frame to show on startup based on command line argument
    mode = "login"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    
    if mode == "signup":
        show_signup_frame()
    else:
        show_login_frame()
        
    return root

def show_login_frame():
    """Show the login frame and hide the signup frame"""
    global login_frame, signup_frame
    if signup_frame and signup_frame.winfo_ismapped():
        signup_frame.pack_forget()
    login_frame.pack(fill="both", expand=True)

def show_signup_frame():
    """Show the signup frame and hide the login frame"""
    global login_frame, signup_frame
    if login_frame and login_frame.winfo_ismapped():
        login_frame.pack_forget()
    signup_frame.pack(fill="both", expand=True)

# ------------------- Main Entry Point -------------------
if __name__ == "__main__":
    try:
        # Initialize UI
        app = init_ui()
        app.mainloop()
    
    except Exception as e:
        import traceback
        print(f"Error: {e}")
        traceback.print_exc()
        input("Press Enter to exit...")