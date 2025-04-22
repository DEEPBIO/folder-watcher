# This file makes Python treat the directory as a package.
# You can optionally import functions here for easier access.
from .reader import get_config, get_task_specific_config, get_database_path

__all__ = ['get_config', 'get_task_specific_config', 'get_database_path']