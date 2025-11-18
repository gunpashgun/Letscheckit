#!/usr/bin/env python3
"""Quick script to check download progress."""
import sys
import os

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.progress import print_download_progress

if __name__ == "__main__":
    print_download_progress()

