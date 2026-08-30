from __future__ import annotations


class GoogleRoutesError(Exception):
    """Raised when Google Routes API returns an error or unexpected payload."""

class GoogleMapsError(Exception):
    """Raised when Google Maps Platform APIs return an error or unexpected payload."""

class GoogleAPIError(Exception):
    """Raised when Google Platform APIs return an error or unexpected payload."""

class OverpassError(Exception):
    """Raised when Open Street Maps APIs return an error or unexpected payload."""

class OpenaiAPIError(Exception):
    """Raised when Open Street Maps APIs return an error or unexpected payload."""

class TTSNotReadyError(RuntimeError):
    """Raised when the TTS model is not loaded / available."""

class AudioConversionError(RuntimeError):
    """Raised when There is an error in audio conversion"""