"""Data loader module for TalentGraph Agent.

Safely loads and caches local JSON datasets for students, internships,
and learning roadmaps.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from src.config import STUDENTS_FILE, INTERNSHIPS_FILE, LEARNING_TOPICS_FILE


class DataLoader:
    """Manages loading and querying of local JSON databases."""

    def __init__(
        self,
        students_path: Path = STUDENTS_FILE,
        internships_path: Path = INTERNSHIPS_FILE,
        learning_topics_path: Path = LEARNING_TOPICS_FILE,
    ):
        self.students_path = Path(students_path)
        self.internships_path = Path(internships_path)
        self.learning_topics_path = Path(learning_topics_path)

        self._students_cache: Optional[List[Dict[str, Any]]] = None
        self._internships_cache: Optional[List[Dict[str, Any]]] = None
        self._learning_topics_cache: Optional[Dict[str, List[str]]] = None

    def reload(self) -> None:
        """Clear cached datasets and force reloading from disk."""
        self._students_cache = None
        self._internships_cache = None
        self._learning_topics_cache = None

    def get_all_students(self) -> List[Dict[str, Any]]:
        """Return all student records."""
        if self._students_cache is None:
            if not self.students_path.exists():
                raise FileNotFoundError(f"Students dataset missing at: {self.students_path}")
            with open(self.students_path, "r", encoding="utf-8") as f:
                self._students_cache = json.load(f)
        return self._students_cache

    def get_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Find a student record by ID (case-insensitive)."""
        clean_id = student_id.strip().upper()
        for s in self.get_all_students():
            if s.get("student_id", "").strip().upper() == clean_id:
                return s
        return None

    def get_all_internships(self) -> List[Dict[str, Any]]:
        """Return all internship records."""
        if self._internships_cache is None:
            if not self.internships_path.exists():
                raise FileNotFoundError(f"Internships dataset missing at: {self.internships_path}")
            with open(self.internships_path, "r", encoding="utf-8") as f:
                self._internships_cache = json.load(f)
        return self._internships_cache

    def get_internship(self, internship_id: str) -> Optional[Dict[str, Any]]:
        """Find an internship record by ID (case-insensitive)."""
        clean_id = internship_id.strip().upper()
        for i in self.get_all_internships():
            if i.get("internship_id", "").strip().upper() == clean_id:
                return i
        return None

    def get_all_learning_topics(self) -> Dict[str, List[str]]:
        """Return the dictionary of skill-to-topics mappings."""
        if self._learning_topics_cache is None:
            if not self.learning_topics_path.exists():
                raise FileNotFoundError(f"Learning topics missing at: {self.learning_topics_path}")
            with open(self.learning_topics_path, "r", encoding="utf-8") as f:
                self._learning_topics_cache = json.load(f)
        return self._learning_topics_cache

    def get_topics_for_skill(self, skill: str) -> Optional[List[str]]:
        """Retrieve curated learning topics for a given skill (case-insensitive)."""
        clean_skill = skill.strip().lower()
        topics_map = self.get_all_learning_topics()
        for key, topics in topics_map.items():
            if key.strip().lower() == clean_skill:
                return topics
        return None


# Global singleton instance for convenient access across tools
default_data_loader = DataLoader()
