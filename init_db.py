import logging
import os
from database import init_db
from auth import set_initial_password
from config_manager import load_config

# Load config to find DB path
config = load_config()
DB_PATH = config.get('database_path', 'folder_watcher.db')

# Ensure parent directory for DB exists if it doesn't exist
db_dir = os.path.dirname(DB_PATH)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir)
    logging.info(f"Created directory for database: {db_dir}")


# Initialize DB schema
init_db(DB_PATH)

# Set initial admin credentials
# WARNING: Hardcoding credentials is bad practice for production.
# Consider using environment variables or a more secure setup method.
ADMIN_USER = "admin"
INITIAL_PASSWORD = "Admin12#$%" # As per requirements
logging.info(f"Setting initial password for user '{ADMIN_USER}'. Use the UI or another method to change this immediately!")
set_initial_password(DB_PATH, ADMIN_USER, INITIAL_PASSWORD)

print(f"Database '{DB_PATH}' initialized and admin user set.")
print("IMPORTANT: Change the default admin password!")