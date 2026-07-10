"""Content-type visual analysis strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ....models.content_analysis import MediaSource
from ..backends import VisualBackend
from ..context import VisualAnalysisContext


class ContentTypeVisualStrategy(ABC):
    """Analyzes one content format — register new types without editing the service."""

    @abstractmethod
    def analyze(
        self,
        media: MediaSource,
        context: VisualAnalysisContext,
        backend: VisualBackend,
    ) -> str:
        """Return JSON matching VisualPassOutput for this content type."""
