"""AI categorization. Depends on no other PRS package.

Two interchangeable suggesters share the ``ICategorySuggester`` interface:

* ``GeminiSuggester`` - calls a real AI API (needs ``GEMINI_API_KEY``).
* ``KeywordSuggester`` - TEMPORARY FALLBACK. It matches hard-coded keywords
  and is NOT an AI model. It is used only when no API key is configured.

Only the visit-note text is ever passed in, never patient details.
"""
import json
import os
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

CATEGORIES = ("Respiratory", "Digestive", "Musculoskeletal", "General/Other")
AI_TIMEOUT_SECONDS = 5
MIN_CONFIDENCE = 0.5


@dataclass(frozen=True)
class Suggestion:
    """A category proposed for a note. It is a suggestion, never a diagnosis."""

    category: str
    confidence: float
    source: str  # human-readable name of the engine that produced it


class ICategorySuggester(ABC):
    """Common interface for anything that can suggest a note category."""

    @abstractmethod
    def suggest(self, note_text: str) -> Optional[Suggestion]:
        """Return a Suggestion, or None if unavailable, slow or unsure."""


class GeminiSuggester(ICategorySuggester):
    """Calls Google's Gemini ``generateContent`` API with a 5 second timeout.

    The API key travels in the ``x-goog-api-key`` header (never in the URL)
    and only the note text is sent. The model name can be overridden with the
    ``GEMINI_MODEL`` environment variable.
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    DEFAULT_MODEL = "gemini-3.5-flash-lite"  # fast model; must reply in 5 s

    def __init__(self, api_key: str, model: Optional[str] = None) -> None:
        self._api_key = api_key
        self._model = model or os.environ.get(
            "GEMINI_MODEL", self.DEFAULT_MODEL)

    def suggest(self, note_text: str) -> Optional[Suggestion]:
        """Ask the model for a category; return None on any failure."""
        prompt = (
            "Classify this visit note into exactly one of these labels: "
            + ", ".join(CATEGORIES)
            + ". The label is for filing only and is not a diagnosis. "
              'Reply with JSON only: {"category": "...", "confidence": 0.0}'
              "\n\nNote: " + note_text
        )
        body = json.dumps({
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.BASE_URL}/{self._model}:generateContent",
            data=body,
            headers={"Content-Type": "application/json",
                     "x-goog-api-key": self._api_key})
        try:
            with urllib.request.urlopen(
                    request, timeout=AI_TIMEOUT_SECONDS) as response:
                reply = json.load(response)
            parts = reply["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts
                           if not p.get("thought"))
            data = json.loads(text)
            category = data["category"]
            confidence = float(data["confidence"])
        except Exception:  # network error, timeout, bad JSON, HTTP error
            return None
        if category not in CATEGORIES or confidence < MIN_CONFIDENCE:
            return None
        return Suggestion(category, confidence,
                          f"AI model (Gemini: {self._model})")


class KeywordSuggester(ICategorySuggester):
    """TEMPORARY FALLBACK - hard-coded keywords. This is NOT an AI model."""

    KEYWORDS = {
        "Respiratory": ("cough", "breath", "wheez", "asthma", "chest",
                        "lung", "congestion", "sore throat"),
        "Digestive": ("nausea", "vomit", "stomach", "abdominal", "diarrhea",
                      "constipation", "heartburn"),
        "Musculoskeletal": ("back pain", "joint", "knee", "shoulder",
                            "muscle", "sprain", "fracture"),
    }

    def suggest(self, note_text: str) -> Optional[Suggestion]:
        """Return the category with the most keyword hits, or None."""
        text = note_text.lower()
        scores = {category: sum(word in text for word in words)
                  for category, words in self.KEYWORDS.items()}
        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return None
        return Suggestion(best, 0.6, "KEYWORD FALLBACK (temporary, not AI)")


def build_suggester() -> ICategorySuggester:
    """Use the real AI when an API key is set, else the keyword fallback."""
    api_key = os.environ.get("GEMINI_API_KEY")
    return GeminiSuggester(api_key) if api_key else KeywordSuggester()
