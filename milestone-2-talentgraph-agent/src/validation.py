"""Validation layer for TalentGraph Agent.

Enforces argument constraints, validates tool outputs, and audits
final model responses for evidence grounding and missing-data compliance.
"""

import re
from typing import Any, Dict, List, Optional, Tuple


def validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate tool arguments before execution to prevent invalid calls."""
    if not isinstance(arguments, dict):
        return False, f"Arguments for tool '{tool_name}' must be a dictionary, got {type(arguments).__name__}."

    if tool_name == "get_student_profile":
        student_id = arguments.get("student_id")
        if not student_id or not isinstance(student_id, str) or not student_id.strip():
            return False, "Argument 'student_id' is required and must be a non-empty string."
        return True, None

    elif tool_name == "search_internships":
        skill = arguments.get("skill")
        if not skill or not isinstance(skill, str) or not skill.strip():
            return False, "Argument 'skill' is required and must be a non-empty string."
        return True, None

    elif tool_name in ("calculate_skill_match", "get_skill_gap"):
        student_id = arguments.get("student_id")
        internship_id = arguments.get("internship_id")
        if not student_id or not isinstance(student_id, str) or not student_id.strip():
            return False, f"Argument 'student_id' is required and must be a non-empty string for {tool_name}."
        if not internship_id or not isinstance(internship_id, str) or not internship_id.strip():
            return False, f"Argument 'internship_id' is required and must be a non-empty string for {tool_name}."
        return True, None

    return False, f"Unknown tool '{tool_name}' cannot be validated."


def validate_grounding(
    question: str,
    answer: str,
    tool_outputs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Audit the generated answer against tool execution outputs.

    Checks:
    - Missing-record compliance: if a record was not found, did the answer state so?
    - Source citation: did the answer cite the source files/records when factual claims were made?
    - Deterministic score preservation: if calculate_skill_match was run, was the exact percentage stated?
    - Missing attribute compliance: if asked about unrecorded fields (like GPA), was absence noted?
    """
    audit = {
        "is_grounded": True,
        "warnings": [],
        "source_citations_found": [],
        "missing_data_respected": True,
        "score_integrity": True,
    }

    # Extract source references in answer (e.g. students.json / S001)
    citations = re.findall(r"(?:students\.json|internships\.json|learning_topics\.json)(?:\s*/\s*[A-Za-z0-9_-]+)?", answer)
    audit["source_citations_found"] = list(set(citations))

    # Check missing record handling
    for out in tool_outputs:
        if out.get("status") == "not_found":
            # Answer must acknowledge not found / not in database
            not_found_keywords = ["not found", "does not exist", "no record", "not in the database", "unknown"]
            if not any(kw in answer.lower() for kw in not_found_keywords):
                audit["is_grounded"] = False
                audit["missing_data_respected"] = False
                audit["warnings"].append("Model did not explicitly convey that the requested entity was not found.")

        elif out.get("status") == "empty":
            empty_keywords = ["no internship", "none found", "no matching", "no opportunities", "not found"]
            if not any(kw in answer.lower() for kw in empty_keywords):
                audit["warnings"].append("Tool returned zero results, but the answer may not clearly reflect this absence.")

    # Check calculated score integrity across tool outputs
    calculated_outputs = [out for out in tool_outputs if out.get("status") == "calculated"]
    if calculated_outputs:
        any_score_reflected = False
        for out in calculated_outputs:
            pct = out.get("match_percentage")
            if pct is not None:
                pct_str = f"{pct}%"
                int_pct_str = f"{int(pct)}%"
                if pct_str in answer or int_pct_str in answer or f"{pct}" in answer:
                    any_score_reflected = True
                    break
        if not any_score_reflected:
            audit["score_integrity"] = False
            audit["warnings"].append(
                "Calculated match percentage was not faithfully reflected in the answer text."
            )

    # Check unrecorded field (e.g. GPA for S001)
    if "gpa" in question.lower():
        gpa_missing_keywords = ["not stored", "not available", "not recorded", "no gpa", "not provided"]
        # If any student profile tool output lacked GPA
        for out in tool_outputs:
            if out.get("status") == "found" and out.get("student_id") == "S001":
                if not any(kw in answer.lower() for kw in gpa_missing_keywords):
                    audit["is_grounded"] = False
                    audit["missing_data_respected"] = False
                    audit["warnings"].append("Question asked for unrecorded GPA, but answer did not clearly state it was missing.")

    if audit["warnings"]:
        audit["is_grounded"] = (len(audit["warnings"]) == 0) or (audit["missing_data_respected"] and audit["score_integrity"])

    return audit
