"""Database connectivity helpers for the UFDR forensic project."""

from .connection import get_connection

__all__ = ["get_connection"]