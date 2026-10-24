"""Unit tests for validation layer in TalentGraph Agent."""

import pytest
from src.validation import validate_tool_arguments, validate_grounding


def test_validate_tool_arguments_get_student_profile():
    """Verify argument validation for get_student_profile."""
    # Valid
    ok, err = validate_tool_arguments("get_student_profile", {"student_id": "S001"})
    assert ok is True
    assert err is None

    # Missing student_id
    ok, err = validate_tool_arguments("get_student_profile", {})
    assert ok is False
    assert "student_id" in err

    # Empty string
    ok, err = validate_tool_arguments("get_student_profile", {"student_id": "   "})
    assert ok is False

    # Invalid type
    ok, err = validate_tool_arguments("get_student_profile", {"student_id": 123})
    assert ok is False


def test_validate_tool_arguments_search_internships():
    """Verify argument validation for search_internships."""
    ok, err = validate_tool_arguments("search_internships", {"skill": "Python"})
    assert ok is True

    ok, err = validate_tool_arguments("search_internships", {"skill": ""})
    assert ok is False

    ok, err = validate_tool_arguments("search_internships", {})
    assert ok is False


def test_validate_tool_arguments_calculate_skill_match():
    """Verify argument validation for calculate_skill_match."""
    ok, err = validate_tool_arguments("calculate_skill_match", {"student_id": "S001", "internship_id": "I001"})
    assert ok is True

    ok, err = validate_tool_arguments("calculate_skill_match", {"student_id": "S001"})
    assert ok is False

    ok, err = validate_tool_arguments("calculate_skill_match", {"student_id": "", "internship_id": "I001"})
    assert ok is False


def test_validate_grounding_audit_success():
    """Grounded answer with citations and verified score passes audit."""
    answer = (
        "Student S001 matches Internship I001 at 75.0% skill overlap.\n"
        "Sources: students.json / S001, internships.json / I001"
    )
    tool_outputs = [{
        "status": "calculated",
        "match_percentage": 75.0,
        "student_id": "S001",
        "internship_id": "I001",
    }]
    audit = validate_grounding("How suitable is S001 for I001?", answer, tool_outputs)
    assert audit["is_grounded"] is True
    assert audit["score_integrity"] is True
    assert len(audit["source_citations_found"]) >= 2


def test_validate_grounding_missing_record_compliance():
    """Audit flags answer that ignores not_found status."""
    bad_answer = "Student S999 is a wonderful engineer with 5 years experience."
    tool_outputs = [{"status": "not_found", "student_id": "S999"}]
    audit = validate_grounding("Tell me about S999", bad_answer, tool_outputs)
    assert audit["missing_data_respected"] is False
    assert audit["is_grounded"] is False


def test_validate_grounding_unrecorded_gpa():
    """Audit flags answer if GPA was requested for S001 but answer claimed a fictional GPA."""
    hallucinated_answer = "Student S001 has a GPA of 3.9."
    tool_outputs = [{
        "status": "found",
        "student_id": "S001",
        "education": {"degree": "B.Tech"},
    }]
    audit = validate_grounding("What is the GPA of student S001?", hallucinated_answer, tool_outputs)
    assert audit["missing_data_respected"] is False
    assert audit["is_grounded"] is False

    compliant_answer = "The GPA for student S001 is not stored in the database."
    audit2 = validate_grounding("What is the GPA of student S001?", compliant_answer, tool_outputs)
    assert audit2["missing_data_respected"] is True
