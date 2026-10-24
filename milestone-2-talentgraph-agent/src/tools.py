"""Deterministic tools for TalentGraph Agent.

Implements verified retrieval, deterministic skill-overlap calculation,
and curated learning roadmap extraction with explicit missing-data handling.
"""

from typing import Any, Dict, List, Optional, Set
from src.data_loader import DataLoader, default_data_loader

# Documented and justified skill aliases for normalization
SKILL_ALIASES: Dict[str, str] = {
    "reactjs": "react",
    "react.js": "react",
    "postgres": "postgresql",
    "ml": "machine learning",
    "deeplearning": "deep learning",
    "ts": "typescript",
    "js": "javascript",
    "py": "python",
    "k8s": "kubernetes",
    "ci/cd": "ci/cd",
    "cicd": "ci/cd",
}


def normalize_skill(skill: str) -> str:
    """Normalize a skill name by trimming, lowercasing, and resolving canonical aliases."""
    cleaned = skill.strip().lower()
    return SKILL_ALIASES.get(cleaned, cleaned)


def get_student_profile(
    student_id: str,
    data_loader: DataLoader = default_data_loader,
) -> Dict[str, Any]:
    """Retrieve verified student profile from local JSON database.

    Returns structured record or structured not-found response if missing.
    """
    clean_id = (student_id or "").strip().upper()
    student = data_loader.get_student(clean_id)

    if not student:
        return {
            "status": "not_found",
            "error": f"Student with ID '{student_id}' was not found in the local database.",
            "student_id": clean_id,
            "source": "students.json",
        }

    # Extract verified fields exactly as stored
    return {
        "status": "found",
        "student_id": student.get("student_id"),
        "name": student.get("name"),
        "education": student.get("education"),
        "skills": student.get("skills", []),
        "projects": student.get("projects", []),
        "source": f"students.json / {student.get('student_id')}",
    }


def search_internships(
    skill: str,
    data_loader: DataLoader = default_data_loader,
) -> Dict[str, Any]:
    """Search internship opportunities requiring a specific skill.

    Returns list of matching opportunities or an explicit empty result.
    """
    if not skill or not skill.strip():
        return {
            "status": "invalid_argument",
            "error": "A non-empty skill name must be provided.",
            "source": "internships.json",
        }

    query_norm = normalize_skill(skill)
    internships = data_loader.get_all_internships()
    matches: List[Dict[str, Any]] = []

    for item in internships:
        req_skills_norm = [normalize_skill(s) for s in item.get("required_skills", [])]
        if query_norm in req_skills_norm:
            matches.append({
                "internship_id": item.get("internship_id"),
                "role": item.get("role"),
                "company": item.get("company"),
                "required_skills": item.get("required_skills", []),
                "description": item.get("description"),
                "source": f"internships.json / {item.get('internship_id')}",
            })

    if not matches:
        return {
            "status": "empty",
            "message": f"No internships found requiring skill '{skill}'.",
            "query_skill": skill,
            "matched_count": 0,
            "matched_internships": [],
            "source": "internships.json",
        }

    return {
        "status": "found",
        "query_skill": skill,
        "matched_count": len(matches),
        "matched_internships": matches,
        "source": "internships.json",
    }


def calculate_skill_match(
    student_id: str,
    internship_id: str,
    data_loader: DataLoader = default_data_loader,
) -> Dict[str, Any]:
    """Calculate deterministic skill overlap between student and internship.

    Formula: (matched required skills / total required skills) * 100
    Guaranteed zero-division safety and strictly computed in Python.
    """
    clean_sid = (student_id or "").strip().upper()
    clean_iid = (internship_id or "").strip().upper()

    student = data_loader.get_student(clean_sid)
    if not student:
        return {
            "status": "not_found",
            "error": f"Student with ID '{student_id}' does not exist in local database.",
            "source": "students.json",
        }

    internship = data_loader.get_internship(clean_iid)
    if not internship:
        return {
            "status": "not_found",
            "error": f"Internship with ID '{internship_id}' does not exist in local database.",
            "source": "internships.json",
        }

    student_skills_raw: List[str] = student.get("skills", [])
    required_skills_raw: List[str] = internship.get("required_skills", [])

    # Map normalized skill back to original display casing
    student_norm_map = {normalize_skill(s): s for s in student_skills_raw}
    internship_norm_map = {normalize_skill(s): s for s in required_skills_raw}

    student_norms: Set[str] = set(student_norm_map.keys())
    required_norms: Set[str] = set(internship_norm_map.keys())

    total_required = len(required_norms)
    matched_norms = required_norms.intersection(student_norms)
    missing_norms = required_norms - student_norms

    matched_skills = [s for s in required_skills_raw if normalize_skill(s) in matched_norms]
    missing_skills = [s for s in required_skills_raw if normalize_skill(s) in missing_norms]

    # Handle edge case: zero required skills without division by zero
    if total_required == 0:
        match_percentage = 100.0
        explanation = "The internship has no mandatory technical skills listed; baseline match is 100%."
    else:
        match_percentage = round((len(matched_norms) / total_required) * 100.0, 1)
        explanation = (
            f"Student {clean_sid} possesses {len(matched_skills)} of {total_required} required "
            f"skills ({', '.join(matched_skills) if matched_skills else 'none'}) "
            f"for internship {clean_iid} at {internship.get('company')}."
        )

    return {
        "status": "calculated",
        "student_id": clean_sid,
        "student_name": student.get("name"),
        "internship_id": clean_iid,
        "internship_role": internship.get("role"),
        "company": internship.get("company"),
        "match_percentage": match_percentage,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_required_count": total_required,
        "matched_count": len(matched_skills),
        "explanation": explanation,
        "source_record_ids": [
            f"students.json / {clean_sid}",
            f"internships.json / {clean_iid}",
        ],
        "disclaimer": (
            "This match percentage is a deterministic skill-overlap score based on required skills; "
            "it is not a statistical prediction of interview or hiring success."
        ),
    }


def get_skill_gap(
    student_id: str,
    internship_id: str,
    data_loader: DataLoader = default_data_loader,
) -> Dict[str, Any]:
    """Identify missing required skills and map them to curated local learning topics.

    Never invents unverified courses, timelines, or qualifications.
    """
    match_result = calculate_skill_match(student_id, internship_id, data_loader)
    if match_result.get("status") != "calculated":
        return match_result

    missing_skills: List[str] = match_result.get("missing_skills", [])
    suggested_learning_topics: Dict[str, List[str]] = {}
    unmapped_missing_skills: List[str] = []

    for skill in missing_skills:
        topics = data_loader.get_topics_for_skill(skill)
        if topics:
            suggested_learning_topics[skill] = topics
        else:
            unmapped_missing_skills.append(skill)

    return {
        "status": "success",
        "student_id": match_result.get("student_id"),
        "student_name": match_result.get("student_name"),
        "internship_id": match_result.get("internship_id"),
        "internship_role": match_result.get("internship_role"),
        "company": match_result.get("company"),
        "existing_relevant_skills": match_result.get("matched_skills", []),
        "missing_required_skills": missing_skills,
        "suggested_learning_topics": suggested_learning_topics,
        "unmapped_missing_skills": unmapped_missing_skills,
        "notes": (
            "Learning topics are derived strictly from local curated mappings. "
            "No fictional courses or external certifications have been fabricated."
        ),
        "source_record_ids": [
            *match_result.get("source_record_ids", []),
            "learning_topics.json",
        ],
    }


# Standard OpenAI Tool Definition Schemas
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_student_profile",
            "description": "Retrieve verified student profile (skills, education, projects) by student ID from local database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "Unique identifier of the student (e.g. 'S001', 'S002').",
                    }
                },
                "required": ["student_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_internships",
            "description": "Search local internship database for open opportunities requiring a specific technical skill.",
            "parameters": {
                "type": "object",
                "properties": {
                    "skill": {
                        "type": "string",
                        "description": "Technical skill name to filter internships by (e.g. 'Python', 'Docker', 'React').",
                    }
                },
                "required": ["skill"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_skill_match",
            "description": "Calculate deterministic skill overlap percentage and identify matched and missing skills between a student and an internship.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "Student ID (e.g. 'S001').",
                    },
                    "internship_id": {
                        "type": "string",
                        "description": "Internship ID (e.g. 'I001', 'I002').",
                    },
                },
                "required": ["student_id", "internship_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_skill_gap",
            "description": "Identify missing required skills for an internship and retrieve curated learning topics from the local curriculum database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "student_id": {
                        "type": "string",
                        "description": "Student ID (e.g. 'S001').",
                    },
                    "internship_id": {
                        "type": "string",
                        "description": "Internship ID (e.g. 'I001', 'I003').",
                    },
                },
                "required": ["student_id", "internship_id"],
                "additionalProperties": False,
            },
        },
    },
]

# Tool dispatcher registry
AVAILABLE_TOOLS = {
    "get_student_profile": get_student_profile,
    "search_internships": search_internships,
    "calculate_skill_match": calculate_skill_match,
    "get_skill_gap": get_skill_gap,
}


def execute_tool(
    name: str,
    arguments: Dict[str, Any],
    data_loader: DataLoader = default_data_loader,
) -> Dict[str, Any]:
    """Safely execute a tool by name with provided arguments and injected data loader."""
    if name not in AVAILABLE_TOOLS:
        return {
            "status": "error",
            "error": f"Tool '{name}' is not recognized. Available tools: {list(AVAILABLE_TOOLS.keys())}",
        }

    tool_fn = AVAILABLE_TOOLS[name]
    try:
        # Pass data_loader if accepted
        return tool_fn(**arguments, data_loader=data_loader)
    except TypeError:
        # Fallback if arguments don't support custom data_loader
        return tool_fn(**arguments)
    except Exception as exc:
        return {
            "status": "execution_error",
            "error": f"Exception raised while executing {name}: {str(exc)}",
        }
