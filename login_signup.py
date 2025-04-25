"""
Login and signup functionality for the Online Music Player application.
This module handles:
- User login authentication
- New user registration
- Form validation
- Session management
"""

import os
import sys
import subprocess
import customtkinter as ctk
from tkinter import messagebox
import mysql.connector
import re

# Import from other modules
from config import UI_CONFIG, COLORS, DB_CONFIG
from utils import connect_db, hash_password, ensure_directories_exist

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

# ------------------- Signup Functions -------------------
def signup_user(fullname_entry, email_entry, password_entry, confirm_password_entry):
    """Register a new user in the database"""
    full_name = fullname_entry.get()
    email = email_entry.get()
    password = password_entry.get()
    confirm_password = confirm_password_entry.get()

    # Check if any fields are empty
    if not full_name or not email or not password or not confirm_password:
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

    # Split full name into first and last name (assuming space separator)
    name_parts = full_name.split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    # Hash the password
    hashed_password = hash_password(password)

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
            "INSERT INTO Users (first_name, last_name, email, password) VALUES (%s, %s, %s, %s)",
            (first_name, last_name, email, hashed_password)
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
    # Welcome Back! label
    welcome_label = ctk.CTkLabel(parent_frame, text="Welcome Back!", 
                                font=("Arial", 28, "bold"), text_color=COLORS["primary"])
    welcome_label.pack(anchor="w", pady=(5, 0))

    # Subtitle
    subtitle_label = ctk.CTkLabel(parent_frame, text="Login to explore a world of non-stop music.",
                                 font=("Arial", 12), text_color="gray")
    subtitle_label.pack(anchor="w", pady=(0, 30))

    # Email Address label
    email_label = ctk.CTkLabel(parent_frame, text="Email Address", 
                              font=("Arial", 14, "bold"), text_color="#333333")
    email_label.pack(anchor="w", pady=(0, 5))

    # Email entry with proper icon placement
    email_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    email_frame.pack(fill="x", pady=(0, 15))
    
    email_entry = ctk.CTkEntry(email_frame, font=("Arial", 12), 
                              height=45, corner_radius=8,
                              border_width=1, border_color="#DDDDDD",
                              fg_color="white", text_color="black")
    email_entry.pack(fill="x", side="left", expand=True)
    
    email_icon = ctk.CTkLabel(email_frame, text="✉️", font=("Arial", 14), fg_color="transparent")
    email_icon.pack(side="right", padx=(0, 10))

    # Password label
    password_label = ctk.CTkLabel(parent_frame, text="Password", 
                                 font=("Arial", 14, "bold"), text_color="#333333")
    password_label.pack(anchor="w", pady=(5, 5))

    # Password entry with proper icon placement
    password_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    password_frame.pack(fill="x", pady=(0, 15))
    
    password_entry = ctk.CTkEntry(password_frame, font=("Arial", 12), 
                                 height=45, corner_radius=8, 
                                 border_width=1, border_color="#DDDDDD",
                                 fg_color="white", text_color="black", 
                                 show="*")
    password_entry.pack(fill="x", side="left", expand=True)
    
    password_icon = ctk.CTkLabel(password_frame, text="🔒", font=("Arial", 14), fg_color="transparent")
    password_icon.pack(side="right", padx=(0, 10))

    # Remember Me & Forgot Password row - proper spacing
    remember_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    remember_frame.pack(fill="x", pady=(5, 20))

    # Remember me checkbox
    remember_var = ctk.BooleanVar()
    remember_check = ctk.CTkCheckBox(remember_frame, text="Remember me", 
                                    variable=remember_var, 
                                    text_color="#333333", font=("Arial", 12),
                                    fg_color=COLORS["primary"], border_color="#DDDDDD",
                                    checkbox_height=20, checkbox_width=20)
    remember_check.pack(side="left")

    # Forgot password link
    forgot_pass = ctk.CTkLabel(remember_frame, text="Forgot password?", 
                              font=("Arial", 12), text_color="gray",
                              cursor="hand2")
    forgot_pass.pack(side="right")

    # Login button with login icon
    login_button = ctk.CTkButton(parent_frame, text="Login", 
                                font=("Arial", 14, "bold"),
                                fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], 
                                text_color="white", corner_radius=8, 
                                height=45, command=lambda: login_user(email_entry, password_entry))
    login_button.pack(fill="x", pady=(10, 25))
    
    # Add an arrow icon to the login button (simulating the icon in the image)
    login_icon_label = ctk.CTkLabel(login_button, text="→", font=("Arial", 16, "bold"), text_color="white")
    login_icon_label.place(relx=0.9, rely=0.5, anchor="e")

    # Don't have an account text
    signup_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    signup_frame.pack(pady=0)

    account_label = ctk.CTkLabel(signup_frame, text="Don't have an account? ", 
                                font=("Arial", 12), text_color="#333333")
    account_label.pack(side="left")

    # "Sign up" in purple and bold
    signup_label = ctk.CTkLabel(signup_frame, text="Sign up", 
                               font=("Arial", 12, "bold"), 
                               text_color=COLORS["primary"], cursor="hand2")
    signup_label.pack(side="left")
    signup_label.bind("<Button-1>", lambda e: show_signup_frame())
    
    # Go back to main menu
    back_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    back_frame.pack(pady=(20, 0))
    
    back_label = ctk.CTkLabel(back_frame, text="← Back to main menu", 
                             font=("Arial", 12), text_color=COLORS["primary"],
                             cursor="hand2")
    back_label.pack()
    back_label.bind("<Button-1>", lambda e: open_main_page())
    
    return email_entry, password_entry

def create_signup_ui(parent_frame):
    """Create the signup UI elements"""
    # Create an Account title
    title_label = ctk.CTkLabel(parent_frame, text="Create an Account", 
                              font=("Arial", 28, "bold"), text_color=COLORS["primary"])
    title_label.pack(anchor="w", pady=(0, 0))

    # Subtitle
    subtitle_label = ctk.CTkLabel(parent_frame, text="Sign up to start your journey into the world of music.",
                                 font=("Arial", 12), text_color="gray")
    subtitle_label.pack(anchor="w", pady=(0, 25))

    # Full Name label
    fullname_label = ctk.CTkLabel(parent_frame, text="Full Name", 
                                 font=("Arial", 14, "bold"), text_color="#333333")
    fullname_label.pack(anchor="w", pady=(0, 5))

    # Full Name Entry with person icon
    fullname_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    fullname_frame.pack(fill="x", pady=(0, 15))

    fullname_entry = ctk.CTkEntry(fullname_frame, font=("Arial", 12), 
                                 height=45, corner_radius=8,
                                 border_width=1, border_color="#DDDDDD",
                                 fg_color="white", text_color="black")
    fullname_entry.pack(fill="x", side="left", expand=True)

    person_icon = ctk.CTkLabel(fullname_frame, text="👤", font=("Arial", 14), fg_color="transparent")
    person_icon.pack(side="right", padx=(0, 10))

    # Email Address label
    email_label = ctk.CTkLabel(parent_frame, text="Email Address", 
                              font=("Arial", 14, "bold"), text_color="#333333")
    email_label.pack(anchor="w", pady=(0, 5))

    # Email Entry with envelope icon
    email_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    email_frame.pack(fill="x", pady=(0, 15))

    email_entry = ctk.CTkEntry(email_frame, font=("Arial", 12), 
                              height=45, corner_radius=8,
                              border_width=1, border_color="#DDDDDD",
                              fg_color="white", text_color="black")
    email_entry.pack(fill="x", side="left", expand=True)

    email_icon = ctk.CTkLabel(email_frame, text="✉️", font=("Arial", 14), fg_color="transparent")
    email_icon.pack(side="right", padx=(0, 10))

    # Password label
    password_label = ctk.CTkLabel(parent_frame, text="Password", 
                                 font=("Arial", 14, "bold"), text_color="#333333")
    password_label.pack(anchor="w", pady=(0, 5))

    # Password Entry with lock icon
    password_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    password_frame.pack(fill="x", pady=(0, 15))

    password_entry = ctk.CTkEntry(password_frame, font=("Arial", 12), 
                                 height=45, corner_radius=8, 
                                 border_width=1, border_color="#DDDDDD",
                                 fg_color="white", text_color="black", 
                                 show="*")
    password_entry.pack(fill="x", side="left", expand=True)

    password_icon = ctk.CTkLabel(password_frame, text="🔒", font=("Arial", 14), fg_color="transparent")
    password_icon.pack(side="right", padx=(0, 10))

    # Confirm Password label
    confirm_password_label = ctk.CTkLabel(parent_frame, text="Confirm Password", 
                                         font=("Arial", 14, "bold"), text_color="#333333")
    confirm_password_label.pack(anchor="w", pady=(0, 5))

    # Confirm Password Entry with lock icon
    confirm_password_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    confirm_password_frame.pack(fill="x", pady=(0, 15))

    confirm_password_entry = ctk.CTkEntry(confirm_password_frame, font=("Arial", 12), 
                                         height=45, corner_radius=8, 
                                         border_width=1, border_color="#DDDDDD",
                                         fg_color="white", text_color="black", 
                                         show="*")
    confirm_password_entry.pack(fill="x", side="left", expand=True)

    confirm_password_icon = ctk.CTkLabel(confirm_password_frame, text="🔒", font=("Arial", 14), fg_color="transparent")
    confirm_password_icon.pack(side="right", padx=(0, 10))

    # Sign Up button with arrow icon (to match login button)
    signup_button = ctk.CTkButton(parent_frame, text="Sign Up", 
                                 font=("Arial", 14, "bold"),
                                 fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], 
                                 text_color="white", corner_radius=8, 
                                 height=45, 
                                 command=lambda: signup_user(fullname_entry, email_entry, password_entry, confirm_password_entry))
    signup_button.pack(fill="x", pady=(10, 20))

    # Add an arrow icon to the signup button (matching login)
    signup_icon_label = ctk.CTkLabel(signup_button, text="→", font=("Arial", 16, "bold"), text_color="white")
    signup_icon_label.place(relx=0.9, rely=0.5, anchor="e")

    # Already have an account text
    login_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    login_frame.pack(pady=0)

    account_label = ctk.CTkLabel(login_frame, text="Already have an account? ", 
                                font=("Arial", 12), text_color="#333333")
    account_label.pack(side="left")

    login_label = ctk.CTkLabel(login_frame, text="Login", 
                              font=("Arial", 12, "bold"), 
                              text_color=COLORS["primary"], cursor="hand2")
    login_label.pack(side="left")
    login_label.bind("<Button-1>", lambda e: show_login_frame())
    
    # Go back to main menu
    back_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
    back_frame.pack(pady=(20, 0))
    
    back_label = ctk.CTkLabel(back_frame, text="← Back to main menu", 
                             font=("Arial", 12), text_color=COLORS["primary"],
                             cursor="hand2")
    back_label.pack()
    back_label.bind("<Button-1>", lambda e: open_main_page())
    
    return fullname_entry, email_entry, password_entry, confirm_password_entry

def init_ui():
    """Initialize the UI"""
    global root, login_frame, signup_frame
    
    # Ensure temp directory exists
    ensure_directories_exist()
    
    # Setup CustomTkinter appearance
    ctk.set_appearance_mode("light")  # Light mode
    ctk.set_default_color_theme("blue")

    # Main window
    root = ctk.CTk()
    root.title("Online Music System - Login/Signup")
    root.geometry("700x500")  # Default size
    root.resizable(False, False)
    
    # Main Frame with rounded corners
    main_frame = ctk.CTkFrame(root, corner_radius=20)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Left Side - Branding with purple color
    left_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["primary"], width=350, height=480, corner_radius=20)
    left_frame.pack(side="left", fill="both")

    # Title on the left side
    title_label = ctk.CTkLabel(left_frame, text="Online Music\nSystem",
                              font=("Arial", 36, "bold"), text_color="white")
    title_label.place(relx=0.5, rely=0.22, anchor="center")

    # Description text below title
    desc_label = ctk.CTkLabel(left_frame, 
                             text="Enjoy unlimited *ad-free music*\nanytime, anywhere. Access premium\nplaylists and high-quality audio\nstreaming.",
                             font=("Arial", 14), text_color="white", justify="center")
    desc_label.place(relx=0.5, rely=0.40, anchor="center")

    # Add music bird illustration
    bird_label = ctk.CTkLabel(left_frame, text="🎵🐦", font=("Arial", 40), text_color="white")
    bird_label.place(relx=0.5, rely=0.75, anchor="center")

    # Right Side - Login/Signup Forms
    right_frame = ctk.CTkFrame(main_frame, fg_color="white", width=350, height=480, corner_radius=0)
    right_frame.pack(side="right", fill="both", expand=True)

    # Create login and signup frames
    login_frame = ctk.CTkFrame(right_frame, fg_color="white")
    signup_frame = ctk.CTkFrame(right_frame, fg_color="white")
    
    # Create content container with padding for both frames
    login_content = ctk.CTkFrame(login_frame, fg_color="white")
    login_content.pack(fill="both", expand=True, padx=40, pady=40)
    
    signup_content = ctk.CTkFrame(signup_frame, fg_color="white")
    signup_content.pack(fill="both", expand=True, padx=40, pady=40)
    
    # Create login UI elements
    email_entry, password_entry = create_login_ui(login_content)
    
    # Create signup UI elements
    fullname_entry, signup_email_entry, signup_password_entry, confirm_password_entry = create_signup_ui(signup_content)
    
    # Set the appropriate frame to show on startup based on command line argument
    mode = "login"  # Default mode
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
        input("Press Enter to exit...")  # This keeps the console open