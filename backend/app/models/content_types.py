"""Shared content type enum for analytics and analysis models."""

from __future__ import annotations

from enum import Enum


class ContentType(str, Enum):
    VIDEO = "VIDEO"
    IMAGE = "IMAGE"
    CAROUSEL = "CAROUSEL"
