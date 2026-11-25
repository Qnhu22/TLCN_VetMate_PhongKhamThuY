"""Compatibility import: use the shared clinic mapping without duplicate tables."""
from app.models.clinic import Veterinarian

__all__ = ["Veterinarian"]
