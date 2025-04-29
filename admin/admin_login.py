"""
Admin login functionality for the Online Music Player application.
"""

import os
import sys
import subprocess
import customtkinter as ctk
from tkinter import messagebox
import mysql.connector
import re

# Add parent directory to path so we can import from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from other modules
from db_config import UI_CONFIG, COLORS
from db_utils import connect_db, hash_password, ensure_directories_exist, validate_secret_key, reset_password
from login_signup import validate_email, validate_password

def login_admin():
    """Authenticate admin and open admin dashboard if successful"""
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
            "SELECT user_id, first_name, last_name FROM Users WHERE email = %s AND password = %s AND is_admin = 1",
            (email, hashed_password)
        )
        admin = cursor.fetchone()
        print(admin)
        print(f"Admin login attempt: {email}, {hashed_password}")

        if admin:
            print(admin)
            admin_id, first_name, last_name = admin
            messagebox.showinfo("Success", f"Welcome Admin {first_name} {last_name}!")
            
            # Save admin ID to a file for session persistence
            with open("current_admin.txt", "w") as f:
                f.write(str(admin_id))
                
            root.destroy()
            open_admin_dashboard()
        else:
            messagebox.showerror("Login Failed", "Invalid Email or Password or Not an Admin Account.")
    
    except mysql.connector.Error as err:
        messagebox.showerror("Database Error", str(err))
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def show_forgot_password_dialog():
    """Show a dialog for resetting the admin password"""
    dialog = ctk.CTkToplevel()
    dialog.title("Reset Admin Password")
    dialog.geometry("400x500")
    dialog.resizable(False, False)
    
    # Title
    ctk.CTkLabel(
        dialog,
        text="Reset Admin Password",
        font=("Arial", 20, "bold"),
        text_color=COLORS["primary"]
    ).pack(pady=(20, 10))
    
    # Email Address
    ctk.CTkLabel(
        dialog,
        text="Email Address",
        font=("Arial", 14, "bold"),
        text_color="#333333"
    ).pack(anchor="w", padx=20, pady=(10, 5))
    
    # Email entry with icon in placeholder
    email_entry = ctk.CTkEntry(
        dialog,
        font=("Arial", 12),
        height=45,
        corner_radius=8,
        border_width=1,
        border_color="#DDDDDD",
        fg_color="white",
        text_color="black",
        placeholder_text="✉️ Enter your email"
    )
    email_entry.pack(fill="x", padx=20, pady=(0, 15))
    
    # Secret Key
    ctk.CTkLabel(
        dialog,
        text="Secret Key",
        font=("Arial", 14, "bold"),
        text_color="#333333"
    ).pack(anchor="w", padx=20, pady=(0, 5))
    
    # Secret Key entry with frame for toggle button
    secret_key_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    secret_key_frame.pack(fill="x", padx=20, pady=(0, 15))
    
    secret_key_entry = ctk.CTkEntry(
        secret_key_frame,
        font=("Arial", 12),
        height=45,
        corner_radius=8,
        border_width=1,
        border_color="#DDDDDD",
        fg_color="white",
        text_color="black",
        placeholder_text="🔑 Enter your secret key",
        show="*"
    )
    secret_key_entry.pack(fill="x", side="left", expand=True)
    
    # Secret key toggle button
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
    secret_key_toggle.place(relx=0.95, rely=0.5, anchor="e")
    
    # Define toggle function
    def toggle_secret_key():
        if secret_key_entry.cget("show") == "*":
            secret_key_entry.configure(show="")
            secret_key_toggle.configure(text="🙈")
        else:
            secret_key_entry.configure(show="*")
            secret_key_toggle.configure(text="👁️")
    
    # Assign command to toggle button
    secret_key_toggle.configure(command=toggle_secret_key)
    
    # New Password
    ctk.CTkLabel(
        dialog,
        text="New Password",
        font=("Arial", 14, "bold"),
        text_color="#333333"
    ).pack(anchor="w", padx=20, pady=(0, 5))
    
    # New Password entry with frame for toggle button
    new_password_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    new_password_frame.pack(fill="x", padx=20, pady=(0, 15))
    
    new_password_entry = ctk.CTkEntry(
        new_password_frame,
        font=("Arial", 12),
        height=45,
        corner_radius=8,
        border_width=1,
        border_color="#DDDDDD",
        fg_color="white",
        text_color="black",
        placeholder_text="🔒 Enter new password",
        show="*"
    )
    new_password_entry.pack(fill="x", side="left", expand=True)
    
    # New password toggle button
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
    new_password_toggle.place(relx=0.95, rely=0.5, anchor="e")
    
    # Define toggle function
    def toggle_new_password():
        if new_password_entry.cget("show") == "*":
            new_password_entry.configure(show="")
            new_password_toggle.configure(text="🙈")
        else:
            new_password_entry.configure(show="*")
            new_password_toggle.configure(text="👁️")
    
    # Assign command to toggle button
    new_password_toggle.configure(command=toggle_new_password)
    
    # Confirm New Password
    ctk.CTkLabel(
        dialog,
        text="Confirm New Password",
        font=("Arial", 14, "bold"),
        text_color="#333333"
    ).pack(anchor="w", padx=20, pady=(0, 5))
    
    # Confirm New Password entry with frame for toggle button
    confirm_password_frame = ctk.CTkFrame(dialog, fg_color="transparent")
    confirm_password_frame.pack(fill="x", padx=20, pady=(0, 15))
    
    confirm_password_entry = ctk.CTkEntry(
        confirm_password_frame,
        font=("Arial", 12),
        height=45,
        corner_radius=8,
        border_width=1,
        border_color="#DDDDDD",
        fg_color="white",
        text_color="black",
        placeholder_text="🔒 Confirm new password",
        show="*"
    )
    confirm_password_entry.pack(fill="x", side="left", expand=True)
    
    # Confirm password toggle button
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
    confirm_password_toggle.place(relx=0.95, rely=0.5, anchor="e")
    
    # Define toggle function
    def toggle_confirm_password():
        if confirm_password_entry.cget("show") == "*":
            confirm_password_entry.configure(show="")
            confirm_password_toggle.configure(text="🙈")
        else:
            confirm_password_entry.configure(show="*")
            confirm_password_toggle.configure(text="👁️")
    
    # Assign command to toggle button
    confirm_password_toggle.configure(command=toggle_confirm_password)
    
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
    
    # Reset Password Button
    reset_button = ctk.CTkButton(
        dialog,
        text="Reset Password",
        font=("Arial", 14, "bold"),
        fg_color=COLORS["primary"],
        hover_color=COLORS["primary_hover"],
        text_color="white",
        corner_radius=8,
        height=45,
        command=reset_password_action
    )
    reset_button.pack(fill="x", padx=20, pady=20)
    
    # Add arrow icon to the button
    ctk.CTkLabel(
        reset_button,
        text="→",
        font=("Arial", 16, "bold"),
        text_color="white"
    ).place(relx=0.9, rely=0.5, anchor="e")

def open_admin_dashboard():
    """Open the admin dashboard after successful login"""
    try:
        subprocess.Popen(["python", "admin/admin_view.py"])
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open admin dashboard: {e}")

def open_user_login():
    """Open the regular user login page"""
    try:
        subprocess.Popen(["python", "login_signup.py", "login"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open login page: {e}")

def open_main_page():
    """Return to the main landing page"""
    try:
        subprocess.Popen(["python", "main.py"])
        root.destroy()
    except Exception as e:
        messagebox.showerror("Error", f"Unable to open main page: {e}")

# Main application setup
try:
    # Create temp directory for temporary files if it doesn't exist
    ensure_directories_exist()
    
    # Main window
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.title("Online Music System - Admin Login")
    root.geometry("700x500")
    root.resizable(False, False)

    # Main Frame with rounded corners
    main_frame = ctk.CTkFrame(root, corner_radius=20)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Left Side - Branding
    left_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["primary"], width=350, height=480, corner_radius=20)
    left_frame.pack(side="left", fill="both")

    # Title on the left side
    title_label = ctk.CTkLabel(left_frame, text="Admin\nControl Panel",
                              font=("Arial", 36, "bold"), text_color="white")
    title_label.place(relx=0.5, rely=0.22, anchor="center")

    # Description text below title
    desc_label = ctk.CTkLabel(left_frame, text="Manage your online music system.\nAdd songs, manage users,\nview statistics and more.",
                              font=("Arial", 14), text_color="white", justify="center")
    desc_label.place(relx=0.5, rely=0.40, anchor="center")

    # Add admin icon
    ctk.CTkLabel(left_frame, text="👨‍💼", font=("Arial", 40), text_color="white").place(relx=0.5, rely=0.75, anchor="center")

    # Right Side - Login Form
    right_frame = ctk.CTkFrame(main_frame, fg_color="white", width=350, height=480, corner_radius=0)
    right_frame.pack(side="right", fill="both", expand=True)

    # Create a container for the right side content with proper padding
    content_frame = ctk.CTkFrame(right_frame, fg_color="white")
    content_frame.pack(fill="both", expand=True, padx=40, pady=40)

    # Admin Login title
    welcome_label = ctk.CTkLabel(content_frame, text="Admin Login", 
                                font=("Arial", 28, "bold"), text_color=COLORS["primary"])
    welcome_label.pack(anchor="w", pady=(5, 0))

    # Subtitle
    subtitle_label = ctk.CTkLabel(content_frame, text="Login with admin credentials to manage the system.",
                                 font=("Arial", 12), text_color="gray")
    subtitle_label.pack(anchor="w", pady=(0, 30))

    # Email Address label
    email_label = ctk.CTkLabel(content_frame, text="Email Address", 
                              font=("Arial", 14, "bold"), text_color="#333333")
    email_label.pack(anchor="w", pady=(0, 5))

    # Email entry with icon in placeholder
    global email_entry
    email_entry = ctk.CTkEntry(content_frame, 
                              font=("Arial", 12), 
                              height=45, 
                              corner_radius=8,
                              border_width=1, 
                              border_color="#DDDDDD",
                              fg_color="white", 
                              text_color="black",
                              placeholder_text="✉️ admin@music.com")
    email_entry.pack(fill="x", pady=(0, 15))

    # Password label
    password_label = ctk.CTkLabel(content_frame, text="Password", 
                                 font=("Arial", 14, "bold"), text_color="#333333")
    password_label.pack(anchor="w", pady=(5, 5))

    # Password entry with frame for toggle button
    password_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    password_frame.pack(fill="x", pady=(0, 15))
    
    global password_entry
    password_entry = ctk.CTkEntry(password_frame, 
                                 font=("Arial", 12), 
                                 height=45, 
                                 corner_radius=8, 
                                 border_width=1, 
                                 border_color="#DDDDDD",
                                 fg_color="white", 
                                 text_color="black", 
                                 show="*",
                                 placeholder_text="🔒 admin123")
    password_entry.pack(fill="x", side="left", expand=True)
    
    # Password toggle button
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
    password_toggle.place(relx=0.95, rely=0.5, anchor="e")
    
    # Define toggle function
    def toggle_password():
        if password_entry.cget("show") == "*":
            password_entry.configure(show="")
            password_toggle.configure(text="🙈")
        else:
            password_entry.configure(show="*")
            password_toggle.configure(text="👁️")
    
    # Assign command to toggle button
    password_toggle.configure(command=toggle_password)

    # Forgot Password link
    forgot_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    forgot_frame.pack(fill="x", pady=(5, 20))

    forgot_pass = ctk.CTkLabel(forgot_frame, text="Forgot password?", 
                              font=("Arial", 12), text_color=COLORS["primary"],
                              cursor="hand2")
    forgot_pass.pack(side="right")
    forgot_pass.bind("<Button-1>", lambda e: show_forgot_password_dialog())

    # Login button with login icon
    login_button = ctk.CTkButton(content_frame, text="Admin Login", 
                                font=("Arial", 14, "bold"),
                                fg_color=COLORS["primary"], hover_color=COLORS["primary_hover"], 
                                text_color="white", corner_radius=8, 
                                height=45, command=login_admin)
    login_button.pack(fill="x", pady=(10, 25))
    
    # Add an arrow icon to the login button
    login_icon_label = ctk.CTkLabel(login_button, text="→", font=("Arial", 16, "bold"), text_color="white")
    login_icon_label.place(relx=0.9, rely=0.5, anchor="e")

    # Regular user login link
    user_login_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    user_login_frame.pack(pady=0)

    user_login_label = ctk.CTkLabel(user_login_frame, text="Not an admin? ", 
                                   font=("Arial", 12), text_color="#333333")
    user_login_label.pack(side="left")

    login_label = ctk.CTkLabel(user_login_frame, text="User Login", 
                              font=("Arial", 12, "bold"), 
                              text_color=COLORS["primary"], cursor="hand2")
    login_label.pack(side="left")
    login_label.bind("<Button-1>", lambda e: open_user_login())
    
    # Back to main menu
    back_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
    back_frame.pack(pady=(20, 0))
    
    back_label = ctk.CTkLabel(back_frame, text="← Back to main menu", 
                             font=("Arial", 12), text_color=COLORS["primary"],
                             cursor="hand2")
    back_label.pack()
    back_label.bind("<Button-1>", lambda e: open_main_page())

    # Start the main loop
    root.mainloop()

except Exception as e:
    import traceback
    print(f"Error: {e}")
    traceback.print_exc()
    input("Press Enter to exit...")