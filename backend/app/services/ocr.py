from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Protocol


class OCRUnavailableError(RuntimeError):
    """Raised when the OCR binary or a requested language pack is unavailable."""


@dataclass
class OCRResult:
    text: str
    confidence: float | None
    engine: str
    languages: list[str]


class OCRProvider(Protocol):
    def extract(self, image_bytes: bytes, languages: str) -> OCRResult: ...


class TesseractOCRProvider:
    """Small local adapter; input/output use pipes so no user filename is executed."""

    def __init__(self, command: str | None = None, timeout_seconds: int = 90):
        self.command = command or os.getenv("TESSERACT_CMD", "tesseract")
        self.timeout_seconds = timeout_seconds

    def _available_languages(self) -> set[str]:
        binary = shutil.which(self.command) if os.path.sep not in self.command else self.command
        if not binary or not os.path.exists(binary):
            raise OCRUnavailableError("Tesseract OCR binary is not installed or not found in PATH.")
        try:
            result = subprocess.run(
                [binary, "--list-langs"], capture_output=True, text=True,
                timeout=10, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OCRUnavailableError("Tesseract could not be started.") from exc
        if result.returncode != 0:
            raise OCRUnavailableError("Tesseract language availability could not be checked.")
        return {line.strip() for line in result.stdout.splitlines()[1:] if line.strip()}

    def extract(self, image_bytes: bytes, languages: str = "ben+eng") -> OCRResult:
        requested = [item.strip() for item in languages.split("+") if item.strip()]
        if not image_bytes or not requested:
            raise ValueError("OCR requires image bytes and at least one language.")
        binary = shutil.which(self.command) if os.path.sep not in self.command else self.command
        available = self._available_languages()
        missing = sorted(set(requested) - available)
        if missing:
            raise OCRUnavailableError(
                "Tesseract language data missing: " + ", ".join(missing) + "."
            )
        if not binary:
            raise OCRUnavailableError("Tesseract OCR binary is not installed.")
        try:
            result = subprocess.run(
                [binary, "stdin", "stdout", "-l", "+".join(requested), "--psm", "3", "tsv"],
                input=image_bytes, capture_output=True, timeout=self.timeout_seconds, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("OCR timed out while processing this page.") from exc
        except OSError as exc:
            raise OCRUnavailableError("Tesseract OCR could not be executed.") from exc
        if result.returncode != 0:
            message = result.stderr.decode("utf-8", errors="replace")[:500]
            if "Error opening data file" in message or "Failed loading language" in message:
                raise OCRUnavailableError("Tesseract cannot load the configured language data.")
            raise RuntimeError("Tesseract OCR failed: " + (message or "unknown error"))

        lines = result.stdout.decode("utf-8", errors="replace").splitlines()
        words: list[str] = []
        confidences: list[float] = []
        if lines:
            for line in lines[1:]:
                columns = line.split("\t")
                if len(columns) < 12:
                    continue
                word = columns[11].strip()
                if word:
                    words.append(word)
                    try:
                        confidence = float(columns[10])
                        if confidence >= 0:
                            confidences.append(confidence)
                    except ValueError:
                        pass
        text = " ".join(words).strip()
        confidence_score = (sum(confidences) / len(confidences) / 100) if confidences else None
        return OCRResult(text=text, confidence=confidence_score, engine="tesseract", languages=requested)
