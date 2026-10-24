"""TalentGraph Agent core implementation.

Implements native OpenAI-compatible tool-calling loop, argument validation,
deterministic execution tracing, and evidence-backed response generation.
"""

import json
import re
import time
from typing import Any, Dict, List, Optional
from openai import OpenAI

from src.config import (
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    OPENAI_MODEL_NAME,
    TEMPERATURE,
    MAX_TOOL_ITERATIONS,
    is_live_api_configured,
)
from src.data_loader import DataLoader, default_data_loader
from src.tools import (
    TOOL_DEFINITIONS,
    execute_tool,
)
from src.validation import validate_tool_arguments, validate_grounding

SYSTEM_PROMPT = """You are TalentGraph Agent, an explainable AI career intelligence assistant for academic talent management.
Your purpose is to answer questions about student skills, projects, internship opportunities, and skill gaps using ONLY verified local data retrieved via tools.

STRICT OPERATIONAL GUARDRAILS:
1. TOOL GROUNDING: Never answer from prior knowledge or assumptions. Always select and invoke the appropriate tool to retrieve or calculate data.
2. MISSING DATA & RECORDS:
   - If a student is not found, state clearly: "Student <ID> was not found in the local database." Never invent fictional profiles.
   - If an internship search returns no matches, state clearly that no opportunities matched that skill.
   - If an attribute (such as GPA, address, or graduation honors) is missing or null in the student record, explicitly state that it is not stored in the database.
3. DETERMINISTIC CALCULATIONS:
   - Match percentages and skill overlap lists MUST strictly come from the `calculate_skill_match` tool.
   - Never perform mental math or invent percentage scores.
   - Always state that match percentages represent skill overlap, not a prediction of hiring success.
4. EVIDENCE CITATION:
   - Every factual response must cite the verified source records at the end of the answer (e.g., "Sources: students.json / S001, internships.json / I003").
5. LEARNING ROADMAPS:
   - When suggesting learning topics, only provide topics returned by `get_skill_gap`. Never invent courses, certifications, timelines, or qualifications.
"""


class MockToolCallingLLM:
    """Deterministic tool-calling mock for unit testing and offline execution.

    Simulates an OpenAI-compatible model that issues tool calls and synthesizes
    grounded responses strictly following the local tool outputs.
    """

    def __init__(self, data_loader: DataLoader = default_data_loader):
        self.data_loader = data_loader

    def plan_tool_calls(self, question: str, iteration: int) -> Optional[List[Dict[str, Any]]]:
        """Inspect question and previous tool state to determine necessary tool calls."""
        q = question.lower()

        # Stop after 1-2 tool calls for mock
        if iteration > 0:
            return None

        # S999 or unknown student check
        if "s999" in q:
            return [{
                "id": "call_mock_s999",
                "function": {
                    "name": "get_student_profile",
                    "arguments": json.dumps({"student_id": "S999"}),
                },
            }]

        # Skill match or gap between student and internship
        student_match = re.search(r"\b(s00[1-6]|s\d{3})\b", q, re.IGNORECASE)
        internship_match = re.search(r"\b(i00[1-6]|i\d{3})\b", q, re.IGNORECASE)

        if "gap" in q or "learning" in q or "roadmap" in q or "recommend" in q:
            sid = student_match.group(1).upper() if student_match else "S001"
            iid = internship_match.group(1).upper() if internship_match else "I001"
            return [{
                "id": "call_mock_gap",
                "function": {
                    "name": "get_skill_gap",
                    "arguments": json.dumps({"student_id": sid, "internship_id": iid}),
                },
            }]

        if ("suitable" in q or "match" in q or "score" in q or "missing" in q) and student_match and internship_match:
            sid = student_match.group(1).upper()
            iid = internship_match.group(1).upper()
            return [{
                "id": "call_mock_match",
                "function": {
                    "name": "calculate_skill_match",
                    "arguments": json.dumps({"student_id": sid, "internship_id": iid}),
                },
            }]

        if "highest" in q and "overlap" in q:
            # Highest overlap for student across all internships
            sid = student_match.group(1).upper() if student_match else "S001"
            return [
                {
                    "id": f"call_mock_all_{i['internship_id']}",
                    "function": {
                        "name": "calculate_skill_match",
                        "arguments": json.dumps({"student_id": sid, "internship_id": i["internship_id"]}),
                    },
                }
                for i in self.data_loader.get_all_internships()
            ]

        # Search internships by skill
        if "internship" in q and ("requiring" in q or "search" in q or "find" in q or "for" in q):
            # Extract skill word
            skills = ["python", "docker", "react", "sql", "fastapi", "kubernetes", "pytorch", "typescript"]
            found_skill = next((s for s in skills if s in q), "Python")
            return [{
                "id": "call_mock_search",
                "function": {
                    "name": "search_internships",
                    "arguments": json.dumps({"skill": found_skill.capitalize()}),
                },
            }]

        # Student profile retrieval (e.g. skills, gpa, education)
        if student_match:
            sid = student_match.group(1).upper()
            return [{
                "id": "call_mock_profile",
                "function": {
                    "name": "get_student_profile",
                    "arguments": json.dumps({"student_id": sid}),
                },
            }]

        # Default fallback: search for python internships
        return [{
            "id": "call_mock_default",
            "function": {
                "name": "search_internships",
                "arguments": json.dumps({"skill": "Python"}),
            },
        }]

    def synthesize_final_answer(
        self,
        question: str,
        tool_results: List[Dict[str, Any]],
    ) -> str:
        """Synthesize a strictly grounded natural language answer from tool results."""
        q = question.lower()

        # Handle student not found
        for res in tool_results:
            if res.get("status") == "not_found" and "student" in res.get("error", "").lower():
                sid = res.get("student_id", "requested student")
                return (
                    f"Student {sid} was not found in the local database.\n\n"
                    f"Sources:\nstudents.json"
                )

        # Handle search internships
        for res in tool_results:
            if res.get("status") == "found" and "matched_internships" in res:
                items = res["matched_internships"]
                lines = [f"Found {len(items)} internship(s) requiring {res['query_skill']}:"]
                sources = []
                for it in items:
                    lines.append(f"- [{it['internship_id']}] {it['role']} at {it['company']} (Required: {', '.join(it['required_skills'])})")
                    sources.append(it["source"])
                lines.append(f"\nSources:\n{', '.join(sources)}")
                return "\n".join(lines)

            if res.get("status") == "empty":
                return (
                    f"No internships were found requiring the skill '{res.get('query_skill')}'.\n\n"
                    f"Sources:\ninternships.json"
                )

        # Handle highest overlap comparison
        calculated_results = [r for r in tool_results if r.get("status") == "calculated"]
        if len(calculated_results) > 1:
            best = max(calculated_results, key=lambda x: x.get("match_percentage", 0.0))
            return (
                f"For student {best['student_id']} ({best['student_name']}), the internship with the highest "
                f"skill-overlap score is **{best['internship_id']}** ({best['internship_role']} at {best['company']}) "
                f"with a score of **{best['match_percentage']}%**.\n\n"
                f"- Matched skills: {', '.join(best['matched_skills']) if best['matched_skills'] else 'None'}\n"
                f"- Missing skills: {', '.join(best['missing_skills']) if best['missing_skills'] else 'None'}\n\n"
                f"Note: {best['disclaimer']}\n\n"
                f"Sources:\n{', '.join(best['source_record_ids'])}"
            )

        # Handle single skill match
        for res in tool_results:
            if res.get("status") == "calculated":
                matched = ", ".join(res["matched_skills"]) if res["matched_skills"] else "None"
                missing = ", ".join(res["missing_skills"]) if res["missing_skills"] else "None"
                return (
                    f"Student {res['student_id']} ({res['student_name']}) matches Internship {res['internship_id']} "
                    f"({res['internship_role']} at {res['company']}) at **{res['match_percentage']}%** skill overlap.\n\n"
                    f"- Matched skills ({res['matched_count']}/{res['total_required_count']}): {matched}\n"
                    f"- Missing required skills: {missing}\n\n"
                    f"Note: {res['disclaimer']}\n\n"
                    f"Sources:\n{', '.join(res['source_record_ids'])}"
                )

        # Handle skill gap and learning topics
        for res in tool_results:
            if res.get("status") == "success" and "suggested_learning_topics" in res:
                missing = res.get("missing_required_skills", [])
                topics_dict = res.get("suggested_learning_topics", {})
                unmapped = res.get("unmapped_missing_skills", [])

                lines = [
                    f"Skill Gap Analysis for Student {res['student_id']} targeting {res['internship_id']} ({res['internship_role']} at {res['company']}):",
                    f"- Existing relevant skills: {', '.join(res['existing_relevant_skills']) if res['existing_relevant_skills'] else 'None'}",
                    f"- Missing required skills: {', '.join(missing) if missing else 'None'}",
                    "\nCurated Learning Recommendations:",
                ]
                for skill, topics in topics_dict.items():
                    lines.append(f"  • {skill}:")
                    for t in topics:
                        lines.append(f"    - {t}")

                if unmapped:
                    lines.append(f"\nNote: No curated learning roadmap is currently available in the database for: {', '.join(unmapped)}.")

                lines.append(f"\n{res['notes']}")
                lines.append(f"\nSources:\n{', '.join(res['source_record_ids'])}")
                return "\n".join(lines)

        # Handle student profile questions (skills, GPA, education)
        for res in tool_results:
            if res.get("status") == "found" and "skills" in res:
                sid = res["student_id"]
                name = res["name"]
                skills = ", ".join(res["skills"])
                edu = res.get("education", {})
                gpa = edu.get("gpa")

                if "gpa" in q:
                    if gpa is None:
                        return (
                            f"The GPA for student {sid} ({name}) is not stored in the database. "
                            f"Education on record: {edu.get('degree')} from {edu.get('institution')} ({edu.get('graduation_year')}).\n\n"
                            f"Sources:\n{res['source']}"
                        )
                    else:
                        return (
                            f"Student {sid} ({name}) has a recorded GPA of {gpa}.\n\n"
                            f"Sources:\n{res['source']}"
                        )

                # General profile / skills
                projects_summary = "; ".join([p["title"] for p in res.get("projects", [])])
                return (
                    f"Student {sid} ({name}) possesses the following verified skills:\n"
                    f"{skills}\n\n"
                    f"Education: {edu.get('degree')} at {edu.get('institution')} ({edu.get('graduation_year')})\n"
                    f"Projects: {projects_summary}\n\n"
                    f"Sources:\n{res['source']}"
                )

        return "I could not find verified records to answer this query based on local database information."


class TalentGraphAgent:
    """Agentic AI Career Intelligence Assistant with tool execution tracing."""

    def __init__(
        self,
        data_loader: DataLoader = default_data_loader,
        force_mock: bool = False,
    ):
        self.data_loader = data_loader
        self.use_live_api = is_live_api_configured() and not force_mock
        self.mock_llm = MockToolCallingLLM(data_loader=data_loader)

        if self.use_live_api:
            self.client: Optional[OpenAI] = OpenAI(
                api_key=OPENAI_API_KEY,
                base_url=OPENAI_BASE_URL,
            )
        else:
            self.client = None

    def query(self, question: str) -> Dict[str, Any]:
        """Execute the agentic tool-calling loop for a user question."""
        start_time = time.time()
        trace: List[Dict[str, Any]] = []
        collected_tool_outputs: List[Dict[str, Any]] = []

        if self.use_live_api and self.client:
            final_answer = self._run_live_tool_loop(question, trace, collected_tool_outputs)
            mode = "live"
        else:
            final_answer = self._run_mock_tool_loop(question, trace, collected_tool_outputs)
            mode = "mock"

        duration = round(time.time() - start_time, 3)

        # Audit grounding and missing-data compliance
        grounding_audit = validate_grounding(question, final_answer, collected_tool_outputs)

        return {
            "question": question,
            "final_answer": final_answer,
            "trace": trace,
            "grounding_audit": grounding_audit,
            "tool_iterations": len(trace),
            "execution_time_seconds": duration,
            "mode": mode,
        }

    def _run_live_tool_loop(
        self,
        question: str,
        trace: List[Dict[str, Any]],
        collected_tool_outputs: List[Dict[str, Any]],
    ) -> str:
        """Execute real OpenAI-compatible tool calling loop with live model."""
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        for iteration in range(MAX_TOOL_ITERATIONS):
            try:
                response = self.client.chat.completions.create(
                    model=OPENAI_MODEL_NAME,
                    messages=messages,
                    tools=TOOL_DEFINITIONS,
                    tool_choice="auto",
                    temperature=TEMPERATURE,
                )
            except Exception as e:
                # Handle API failures gracefully
                trace.append({
                    "iteration": iteration + 1,
                    "event": "api_error",
                    "error": str(e),
                })
                # Fallback to local deterministic resolution
                return f"Unable to complete live model request due to API connection error: {str(e)}."

            choice = response.choices[0]
            message = choice.message

            # If no tool calls requested, model provided final grounded answer
            if not message.tool_calls:
                return message.content or "No response generated."

            # Append assistant message with tool calls to conversation history
            messages.append(message)

            # Process each requested tool call
            for tool_call in message.tool_calls:
                func_name = tool_call.function.name
                call_id = tool_call.id

                try:
                    raw_args = json.loads(tool_call.function.arguments)
                except Exception:
                    raw_args = {}

                # Validate tool arguments
                is_valid, validation_err = validate_tool_arguments(func_name, raw_args)
                if not is_valid:
                    result = {
                        "status": "argument_validation_error",
                        "error": validation_err,
                    }
                else:
                    # Execute deterministic Python tool
                    result = execute_tool(func_name, raw_args, data_loader=self.data_loader)

                collected_tool_outputs.append(result)

                # Record execution trace
                trace.append({
                    "iteration": iteration + 1,
                    "tool": func_name,
                    "arguments": raw_args,
                    "result": result,
                })

                # Append tool result back to the conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": json.dumps(result),
                })

        return "Agent reached maximum tool iterations without generating a final response."

    def _run_mock_tool_loop(
        self,
        question: str,
        trace: List[Dict[str, Any]],
        collected_tool_outputs: List[Dict[str, Any]],
    ) -> str:
        """Execute deterministic mock tool calling loop."""
        for iteration in range(MAX_TOOL_ITERATIONS):
            planned_calls = self.mock_llm.plan_tool_calls(question, iteration)
            if not planned_calls:
                break

            for call in planned_calls:
                func_name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])

                is_valid, val_err = validate_tool_arguments(func_name, args)
                if not is_valid:
                    result = {"status": "argument_validation_error", "error": val_err}
                else:
                    result = execute_tool(func_name, args, data_loader=self.data_loader)

                collected_tool_outputs.append(result)
                trace.append({
                    "iteration": iteration + 1,
                    "tool": func_name,
                    "arguments": args,
                    "result": result,
                })

        return self.mock_llm.synthesize_final_answer(question, collected_tool_outputs)


def format_trace(trace: List[Dict[str, Any]]) -> str:
    """Format tool execution trace for readable terminal or log output."""
    if not trace:
        return "  (No tool calls made)"

    lines = []
    for step in trace:
        iteration = step.get("iteration", 1)
        tool = step.get("tool", "unknown")
        args = step.get("arguments", {})
        result = step.get("result", {})
        status = result.get("status", "unknown")

        lines.append(f"  [Step {iteration}] Tool: {tool}")
        lines.append(f"    Arguments: {json.dumps(args)}")
        lines.append(f"    Status:    {status}")

        if "match_percentage" in result:
            lines.append(f"    Result:    Match={result['match_percentage']}% | Matched={result.get('matched_skills')} | Missing={result.get('missing_skills')}")
        elif "matched_count" in result:
            lines.append(f"    Result:    Found {result['matched_count']} matching internship(s)")
        elif "error" in result:
            lines.append(f"    Result:    {result['error']}")
        else:
            summary = {k: v for k, v in result.items() if k not in ("education", "projects")}
            lines.append(f"    Result:    {summary}")

    return "\n".join(lines)
