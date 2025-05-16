#!/usr/bin/env python3

from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import logging
from database import get_db_connection # Use the centralized db connection

def set_initial_password(db_path, username, password):
    """Sets or updates the password for a user. Used by init_db script."""
    conn = get_db_connection(db_path)
    try:
        hashed_password = generate_password_hash(password)
        # Check if user exists
        user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if user:
            # Update existing user's password
            conn.execute('UPDATE users SET password_hash = ? WHERE username = ?', (hashed_password, username))
            logging.info(f"Password updated for user '{username}'.")
        else:
            # Insert new user
            conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, hashed_password))
            logging.info(f"Initial user '{username}' created.")
        conn.commit()
    except sqlite3.Error as e:
        logging.error(f"Database error setting password for {username}: {e}")
        conn.rollback()
    finally:
        conn.close()

def verify_user(db_path, username, password):
    """Verifies username and password."""
    conn = get_db_connection(db_path)
    user = conn.execute('SELECT password_hash FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()

    if user and check_password_hash(user['password_hash'], password):
        logging.info(f"User '{username}' verified successfully.")
        return True
    else:
        logging.warning(f"Failed login attempt for user '{username}'.")
        return False