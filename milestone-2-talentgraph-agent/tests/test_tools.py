"""Unit tests for deterministic tools in TalentGraph Agent."""

import pytest
from pathlib import Path
from src.data_loader import DataLoader
from src.tools import (
    get_student_profile,
    search_internships,
    calculate_skill_match,
    get_skill_gap,
    normalize_skill,
    execute_tool,
)

# Test fixture using the actual test datasets
@pytest.fixture
def loader():
    return DataLoader()


# -------------------------------------------------------------------------
# TOOL 1: get_student_profile
# -------------------------------------------------------------------------

def test_get_student_profile_existing(loader):
    """Existing student S001 returns verified profile without invention."""
    res = get_student_profile("S001", data_loader=loader)
    assert res["status"] == "found"
    assert res["student_id"] == "S001"
    assert res["name"] == "Aarav Sharma"
    assert "Python" in res["skills"]
    assert "students.json / S001" in res["source"]


def test_get_student_profile_case_insensitive(loader):
    """Student ID lookup is case-insensitive and trims whitespace."""
    res = get_student_profile("  s002  ", data_loader=loader)
    assert res["status"] == "found"
    assert res["student_id"] == "S002"
    assert res["name"] == "Priya Patel"


def test_get_student_profile_unknown_student(loader):
    """Unknown student ID S999 returns structured not-found without hallucination."""
    res = get_student_profile("S999", data_loader=loader)
    assert res["status"] == "not_found"
    assert "S999" in res["error"]
    assert res["source"] == "students.json"


# -------------------------------------------------------------------------
# TOOL 2: search_internships
# -------------------------------------------------------------------------

def test_search_internships_existing_skill(loader):
    """Searching for 'Python' returns multiple matching internships."""
    res = search_internships("Python", data_loader=loader)
    assert res["status"] == "found"
    assert res["matched_count"] >= 3
    for it in res["matched_internships"]:
        assert any(normalize_skill(s) == "python" for s in it["required_skills"])


def test_search_internships_skill_alias_normalization(loader):
    """Alias 'ML' normalizes to 'machine learning' and finds matching internships."""
    res = search_internships("ML", data_loader=loader)
    assert res["status"] == "found"
    assert any(it["internship_id"] == "I001" for it in res["matched_internships"])


def test_search_internships_unknown_skill_empty(loader):
    """Searching for non-existent skill returns structured empty result."""
    res = search_internships("NonExistentSkillXYZ", data_loader=loader)
    assert res["status"] == "empty"
    assert res["matched_count"] == 0
    assert res["matched_internships"] == []
    assert "No internships found" in res["message"]


def test_search_internships_empty_argument(loader):
    """Empty skill string returns invalid_argument status."""
    res = search_internships("", data_loader=loader)
    assert res["status"] == "invalid_argument"


# -------------------------------------------------------------------------
# TOOL 3: calculate_skill_match
# -------------------------------------------------------------------------

def test_calculate_skill_match_valid(loader):
    """S001 vs I001: S001 has Python, ML, Scikit-Learn; lacks Docker. Overlap = 75%."""
    res = calculate_skill_match("S001", "I001", data_loader=loader)
    assert res["status"] == "calculated"
    assert res["student_id"] == "S001"
    assert res["internship_id"] == "I001"
    assert res["match_percentage"] == 75.0
    assert "Docker" in res["missing_skills"]
    assert "Python" in res["matched_skills"]
    assert res["source_record_ids"] == ["students.json / S001", "internships.json / I001"]
    assert "deterministic skill-overlap" in res["disclaimer"]


def test_calculate_skill_match_no_overlap(loader):
    """S004 (Frontend React/TS) vs I005 (DevOps Linux/Docker/K8s/AWS/CI/CD) -> 0% overlap."""
    res = calculate_skill_match("S004", "I005", data_loader=loader)
    assert res["status"] == "calculated"
    assert res["match_percentage"] == 0.0
    assert len(res["matched_skills"]) == 0
    assert len(res["missing_skills"]) == 5


def test_calculate_skill_match_unknown_student(loader):
    """Skill match with non-existent student returns structured error."""
    res = calculate_skill_match("S999", "I001", data_loader=loader)
    assert res["status"] == "not_found"
    assert "S999" in res["error"]


def test_calculate_skill_match_unknown_internship(loader):
    """Skill match with non-existent internship returns structured error."""
    res = calculate_skill_match("S001", "I999", data_loader=loader)
    assert res["status"] == "not_found"
    assert "I999" in res["error"]


def test_calculate_skill_match_zero_division_safety():
    """Custom data loader with 0 required skills yields safe 100% baseline."""
    class CustomLoader(DataLoader):
        def get_student(self, sid):
            return {"student_id": "S100", "name": "Test", "skills": ["Python"]}
        def get_internship(self, iid):
            return {"internship_id": "I100", "company": "TestCo", "required_skills": []}

    res = calculate_skill_match("S100", "I100", data_loader=CustomLoader())
    assert res["status"] == "calculated"
    assert res["match_percentage"] == 100.0


# -------------------------------------------------------------------------
# TOOL 4: get_skill_gap
# -------------------------------------------------------------------------

def test_get_skill_gap_curated_topics(loader):
    """S001 lacks Docker for I001; retrieves curated Docker learning topics."""
    res = get_skill_gap("S001", "I001", data_loader=loader)
    assert res["status"] == "success"
    assert "Docker" in res["missing_required_skills"]
    assert "Docker" in res["suggested_learning_topics"]
    docker_topics = res["suggested_learning_topics"]["Docker"]
    assert len(docker_topics) >= 3
    assert any("Dockerfile" in t for t in docker_topics)
    assert "learning_topics.json" in res["source_record_ids"]


def test_get_skill_gap_unmapped_skill():
    """Missing skill with no entry in learning_topics is explicitly reported."""
    class CustomLoader(DataLoader):
        def get_student(self, sid):
            return {"student_id": "S100", "name": "Test", "skills": []}
        def get_internship(self, iid):
            return {"internship_id": "I100", "company": "Co", "required_skills": ["ObscureSkill99"]}
        def get_topics_for_skill(self, skill):
            return None

    res = get_skill_gap("S100", "I100", data_loader=CustomLoader())
    assert res["status"] == "success"
    assert "ObscureSkill99" in res["unmapped_missing_skills"]


# -------------------------------------------------------------------------
# execute_tool dispatcher
# -------------------------------------------------------------------------

def test_execute_tool_dispatcher(loader):
    """Dispatcher successfully routes valid tool calls."""
    res = execute_tool("get_student_profile", {"student_id": "S001"}, data_loader=loader)
    assert res["status"] == "found"

    err = execute_tool("non_existent_tool", {}, data_loader=loader)
    assert err["status"] == "error"
