"""
Adds the project root to sys.path so pytest resolves `src.*` imports correctly.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
