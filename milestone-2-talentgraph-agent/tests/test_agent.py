"""Unit tests for TalentGraphAgent using deterministic mock execution."""

import pytest
from unittest.mock import MagicMock, patch
from src.agent import TalentGraphAgent, format_trace
from src.data_loader import DataLoader
from evaluation.evaluate_consistency import extract_normalized_facts, compare_runs


@pytest.fixture
def agent():
    """Create agent forced to deterministic mock mode for hermetic unit testing."""
    return TalentGraphAgent(data_loader=DataLoader(), force_mock=True)


def test_agent_existing_student_profile(agent):
    """Agent retrieves student S001 profile with tool trace and citations."""
    res = agent.query("What skills does student S001 have?")
    assert res["mode"] == "mock"
    assert len(res["trace"]) >= 1
    assert res["trace"][0]["tool"] == "get_student_profile"
    assert "Aarav Sharma" in res["final_answer"]
    assert "Python" in res["final_answer"]
    assert "students.json" in res["final_answer"]
    assert res["grounding_audit"]["is_grounded"] is True


def test_agent_unknown_student(agent):
    """Agent handles unknown student S999 without hallucinating."""
    res = agent.query("What do you know about student S999?")
    assert res["trace"][0]["tool"] == "get_student_profile"
    assert "not found" in res["final_answer"].lower()
    assert "students.json" in res["final_answer"]
    assert res["grounding_audit"]["missing_data_respected"] is True


def test_agent_search_internships(agent):
    """Agent searches internships requiring Python."""
    res = agent.query("Find internships requiring Python.")
    assert res["trace"][0]["tool"] == "search_internships"
    assert "internships.json" in res["final_answer"]
    assert "Apex AI Labs" in res["final_answer"] or "Quantum Analytics" in res["final_answer"]


def test_agent_skill_match_calculation(agent):
    """Agent calculates deterministic match score between S001 and I002."""
    res = agent.query("How suitable is student S001 for internship I002?")
    assert res["trace"][0]["tool"] == "calculate_skill_match"
    # S001 has Python, SQL, Pandas; lacks Data Visualization (3/4 = 75.0%)
    assert "75" in res["final_answer"]
    assert "students.json / S001" in res["final_answer"]
    assert "internships.json / I002" in res["final_answer"]
    assert res["grounding_audit"]["score_integrity"] is True


def test_agent_missing_required_skills(agent):
    """Agent identifies missing required skills for S001 targeting I001."""
    res = agent.query("Which required skills are missing for student S001 when applying for internship I001?")
    assert res["trace"][0]["tool"] == "calculate_skill_match"
    assert "Docker" in res["final_answer"]


def test_agent_highest_skill_overlap_multi_tool(agent):
    """Agent invokes multiple tool calls to compare internships for S001."""
    res = agent.query("Which internship has the highest skill-overlap score for student S001?")
    # Multiple tool calls executed across all internships
    assert len(res["trace"]) >= 5
    for step in res["trace"]:
        assert step["tool"] == "calculate_skill_match"
    assert "highest" in res["final_answer"].lower()
    assert "students.json" in res["final_answer"]


def test_agent_unrecorded_gpa_missing_attribute(agent):
    """Agent explicitly states GPA is not stored when asking about S001."""
    res = agent.query("What is the GPA of student S001 if GPA is not stored?")
    assert "not stored" in res["final_answer"].lower() or "not available" in res["final_answer"].lower()
    assert res["grounding_audit"]["missing_data_respected"] is True


def test_agent_skill_gap_and_learning_recommendations(agent):
    """Agent fetches curated learning topics for missing skills."""
    res = agent.query("Can you recommend learning topics for the missing skills of student S001 for internship I001?")
    assert res["trace"][0]["tool"] == "get_skill_gap"
    assert "Docker" in res["final_answer"]
    assert "Container" in res["final_answer"] or "Dockerfile" in res["final_answer"]
    assert "learning_topics.json" in res["final_answer"]


def test_agent_repeated_query_consistency(agent):
    """Running identical query twice yields identical normalized facts."""
    q = "How suitable is student S001 for internship I002?"
    res1 = agent.query(q)
    res2 = agent.query(q)

    facts1 = extract_normalized_facts(res1["final_answer"], res1["trace"])
    facts2 = extract_normalized_facts(res2["final_answer"], res2["trace"])
    comp = compare_runs(facts1, facts2, res1["final_answer"], res2["final_answer"])

    assert comp["facts_agreed"] is True
    assert comp["mismatches"] == []


def test_agent_format_trace():
    """Verify trace formatter outputs clear, readable text."""
    sample_trace = [{
        "iteration": 1,
        "tool": "get_student_profile",
        "arguments": {"student_id": "S001"},
        "result": {"status": "found", "student_id": "S001", "name": "Aarav"},
    }]
    formatted = format_trace(sample_trace)
    assert "[Step 1] Tool: get_student_profile" in formatted
    assert "S001" in formatted


def test_agent_api_error_handling():
    """Live tool loop catches API exceptions gracefully and records error in trace."""
    agent_live = TalentGraphAgent(force_mock=False)
    agent_live.use_live_api = True
    agent_live.client = MagicMock()
    agent_live.client.chat.completions.create.side_effect = Exception("Simulated connection timeout")

    res = agent_live.query("What skills does S001 have?")
    assert "API connection error" in res["final_answer"] or "timeout" in res["final_answer"].lower()
    assert any(step.get("event") == "api_error" for step in res["trace"])
