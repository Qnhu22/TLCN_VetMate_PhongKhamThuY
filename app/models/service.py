"""Compatibility import: use the shared clinic mapping without duplicate tables."""
from app.models.clinic import Service

__all__ = ["Service"]
