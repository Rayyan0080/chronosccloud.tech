"""
Trajectory Insight Analysis Module

Provides trajectory analysis capabilities for flight plans including:
- Conflict detection
- Hotspot identification
- Violation detection
- Solution generation
"""

from .analyzer import analyze

__all__ = ["analyze"]

