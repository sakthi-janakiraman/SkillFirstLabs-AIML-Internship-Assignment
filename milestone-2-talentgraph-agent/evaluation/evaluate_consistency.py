"""Consistency Lab - Evaluates repeatability of TalentGraph Agent responses.

Runs identical questions twice under temperature 0, extracts normalized structured
facts, checks factual agreement, identifies any mismatches, and produces detailed
JSON and standalone HTML evaluation reports.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Add parent directory to path so script runs directly or as a module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agent import TalentGraphAgent
from src.data_loader import default_data_loader
from evaluation.console_template import render_intelligence_lab_html
from src.config import (
    BASE_DIR,
    REPORTS_DIR,
    TEST_QUESTIONS_FILE,
    TEMPERATURE,
    OPENAI_MODEL_NAME,
    is_live_api_configured,
)


def extract_normalized_facts(answer: str, trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Extract normalized factual entities and outcomes from answer and tool trace."""
    # 1. Student IDs
    sids_in_answer = set(re.findall(r"\bS\d{3}\b", answer, re.IGNORECASE))
    sids_in_trace = {
        step.get("arguments", {}).get("student_id", "").upper()
        for step in trace
        if step.get("arguments", {}).get("student_id")
    }
    student_ids = sorted(list(sids_in_answer.union(sids_in_trace)))

    # 2. Internship IDs
    iids_in_answer = set(re.findall(r"\bI\d{3}\b", answer, re.IGNORECASE))
    iids_in_trace = {
        step.get("arguments", {}).get("internship_id", "").upper()
        for step in trace
        if step.get("arguments", {}).get("internship_id")
    }
    internship_ids = sorted(list(iids_in_answer.union(iids_in_trace)))

    # 3. Match percentages
    pcts_in_answer = [float(p) for p in re.findall(r"(\d+(?:\.\d+)?)\s*%", answer)]
    pcts_in_trace = [
        float(step["result"]["match_percentage"])
        for step in trace
        if step.get("result", {}).get("match_percentage") is not None
    ]
    all_percentages = sorted(list(set(pcts_in_answer + pcts_in_trace)))

    # 4. Matched and Missing skills from tool traces
    matched_skills: Set[str] = set()
    missing_skills: Set[str] = set()
    for step in trace:
        res = step.get("result", {})
        if "matched_skills" in res:
            matched_skills.update(s.lower() for s in res["matched_skills"])
        if "missing_skills" in res:
            missing_skills.update(s.lower() for s in res["missing_skills"])
        if "missing_required_skills" in res:
            missing_skills.update(s.lower() for s in res["missing_required_skills"])

    # 5. Missing data status
    ans_lower = answer.lower()
    is_unknown_student = any(kw in ans_lower for kw in ["not found", "unknown student", "does not exist"])
    is_unrecorded_gpa = any(kw in ans_lower for kw in ["not stored", "not available", "no gpa", "not recorded"])
    is_empty_search = any(kw in ans_lower for kw in ["no internships", "none found", "no matching"])

    tools_called = [step.get("tool") for step in trace if step.get("tool")]

    return {
        "student_ids": student_ids,
        "internship_ids": internship_ids,
        "match_percentages": all_percentages,
        "matched_skills": sorted(list(matched_skills)),
        "missing_skills": sorted(list(missing_skills)),
        "missing_data_status": {
            "unknown_student": is_unknown_student,
            "unrecorded_gpa": is_unrecorded_gpa,
            "empty_search": is_empty_search,
        },
        "tools_called": tools_called,
    }


def compare_runs(facts1: Dict[str, Any], facts2: Dict[str, Any], text1: str, text2: str) -> Dict[str, Any]:
    """Compare normalized facts between two identical runs and record any mismatches."""
    mismatches: List[str] = []

    # Student IDs comparison
    if facts1["student_ids"] != facts2["student_ids"]:
        mismatches.append(f"Student IDs mismatch: Run1={facts1['student_ids']} vs Run2={facts2['student_ids']}")

    # Internship IDs comparison
    if facts1["internship_ids"] != facts2["internship_ids"]:
        mismatches.append(f"Internship IDs mismatch: Run1={facts1['internship_ids']} vs Run2={facts2['internship_ids']}")

    # Match percentages comparison
    if facts1["match_percentages"] != facts2["match_percentages"]:
        mismatches.append(f"Match percentages mismatch: Run1={facts1['match_percentages']} vs Run2={facts2['match_percentages']}")

    # Matched skills comparison
    if facts1["matched_skills"] != facts2["matched_skills"]:
        mismatches.append(f"Matched skills mismatch: Run1={facts1['matched_skills']} vs Run2={facts2['matched_skills']}")

    # Missing skills comparison
    if facts1["missing_skills"] != facts2["missing_skills"]:
        mismatches.append(f"Missing skills mismatch: Run1={facts1['missing_skills']} vs Run2={facts2['missing_skills']}")

    # Missing data status comparison
    if facts1["missing_data_status"] != facts2["missing_data_status"]:
        mismatches.append(f"Missing data status mismatch: Run1={facts1['missing_data_status']} vs Run2={facts2['missing_data_status']}")

    # Tools called comparison
    tool_sequence_match = (facts1["tools_called"] == facts2["tools_called"])
    if not tool_sequence_match:
        mismatches.append(f"Tool calling mismatch: Run1={facts1['tools_called']} vs Run2={facts2['tools_called']}")

    # Exact text match
    exact_text_match = (text1.strip() == text2.strip())
    facts_agreed = (len(mismatches) == 0)

    return {
        "facts_agreed": facts_agreed,
        "exact_text_match": exact_text_match,
        "tool_sequence_match": tool_sequence_match,
        "mismatches": mismatches,
    }


def run_consistency_evaluation(
    questions_file: Path = TEST_QUESTIONS_FILE,
    output_json: Optional[Path] = None,
    output_html: Optional[Path] = None,
    force_mock: bool = False,
) -> Dict[str, Any]:
    """Execute consistency evaluation across test questions."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_json is None:
        output_json = REPORTS_DIR / "consistency_report.json"
    if output_html is None:
        output_html = REPORTS_DIR / "consistency_report.html"

    with open(questions_file, "r", encoding="utf-8") as f:
        questions = json.load(f)

    agent = TalentGraphAgent(force_mock=force_mock)
    is_live = agent.use_live_api
    mode_label = "Live OpenAI API" if is_live else "Deterministic Mock Engine"

    print("=" * 70)
    print("TALENTGRAPH AGENT - CONSISTENCY LAB EVALUATION")
    print("=" * 70)
    print(f"Mode:              {mode_label}")
    print(f"Model:             {OPENAI_MODEL_NAME}")
    print(f"Temperature:       {TEMPERATURE}")
    print(f"Total Questions:   {len(questions)}")
    print(f"Questions File:    {questions_file}")
    print("-" * 70)

    results: List[Dict[str, Any]] = []
    factual_agreements = 0
    exact_text_matches = 0
    tool_agreements = 0

    # Reconfigure stdout to utf-8 if supported on Windows
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    for idx, item in enumerate(questions, 1):
        qid = item.get("id", f"Q{idx}")
        category = item.get("category", "general")
        q_text = item["question"]

        print(f"[{idx}/{len(questions)}] Running {qid} ({category}): \"{q_text}\"")

        # Run 1
        t0 = time.time()
        res1 = agent.query(q_text)
        run1_time = round(time.time() - t0, 3)

        # Run 2
        t1 = time.time()
        res2 = agent.query(q_text)
        run2_time = round(time.time() - t1, 3)

        # Extract normalized facts
        facts1 = extract_normalized_facts(res1["final_answer"], res1["trace"])
        facts2 = extract_normalized_facts(res2["final_answer"], res2["trace"])

        # Compare runs
        comp = compare_runs(facts1, facts2, res1["final_answer"], res2["final_answer"])

        if comp["facts_agreed"]:
            factual_agreements += 1
            status_symbol = "[AGREED]"
        else:
            status_symbol = "[MISMATCH]"

        text_symbol = "[TEXT MATCH]" if comp["exact_text_match"] else "[TEXT VARIES]"
        print(f"    -> Run 1 ({run1_time}s) | Run 2 ({run2_time}s) | {status_symbol} | {text_symbol}")

        if comp["mismatches"]:
            for m in comp["mismatches"]:
                print(f"       ! {m}")

        if comp["exact_text_match"]:
            exact_text_matches += 1
        if comp["tool_sequence_match"]:
            tool_agreements += 1

        results.append({
            "id": qid,
            "category": category,
            "question": q_text,
            "run_1": {
                "answer": res1["final_answer"],
                "trace": res1["trace"],
                "execution_time_seconds": run1_time,
                "extracted_facts": facts1,
                "grounding_audit": res1["grounding_audit"],
            },
            "run_2": {
                "answer": res2["final_answer"],
                "trace": res2["trace"],
                "execution_time_seconds": run2_time,
                "extracted_facts": facts2,
                "grounding_audit": res2["grounding_audit"],
            },
            "comparison": comp,
        })

    # Summary calculation
    total_q = len(questions)
    fact_rate = round((factual_agreements / total_q) * 100, 1) if total_q else 0.0
    text_rate = round((exact_text_matches / total_q) * 100, 1) if total_q else 0.0
    tool_rate = round((tool_agreements / total_q) * 100, 1) if total_q else 0.0

    report = {
        "metadata": {
            "project": "TalentGraph Agent - Consistency Lab",
            "timestamp": datetime.now().isoformat(),
            "execution_mode": mode_label,
            "model": OPENAI_MODEL_NAME,
            "temperature": TEMPERATURE,
            "total_questions": total_q,
        },
        "metrics": {
            "factual_agreement_rate_pct": fact_rate,
            "exact_text_match_rate_pct": text_rate,
            "tool_sequence_agreement_rate_pct": tool_rate,
            "factual_agreements_count": factual_agreements,
            "exact_text_matches_count": exact_text_matches,
            "mismatches_detected": total_q - factual_agreements,
        },
        "evaluation_notes": (
            "Consistency evaluation tests factual stability across repeated inferences under temperature 0. "
            "Because temperature 0 eliminates sampling variance but does not eliminate floating-point concurrency "
            "or alternate phrasing in LLMs, our evaluation normalizes structured facts (IDs, percentages, skills, "
            "and missing-data flags) to evaluate semantic and factual consistency."
        ),
        "detailed_results": results,
    }

    # Save JSON report
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Generate standalone HTML dashboard
    generate_html_report(report, output_html)

    print("-" * 70)
    print("EVALUATION SUMMARY:")
    print(f"  Factual Agreement Rate:       {fact_rate}% ({factual_agreements}/{total_q})")
    print(f"  Tool Calling Agreement Rate:  {tool_rate}% ({tool_agreements}/{total_q})")
    print(f"  Exact Text Match Rate:        {text_rate}% ({exact_text_matches}/{total_q})")
    print(f"  JSON Report Saved:            {output_json}")
    print(f"  HTML Dashboard Saved:         {output_html}")
    print("=" * 70)

    return report


def generate_html_report(report_data: Dict[str, Any], output_path: Path) -> None:
    """Generate The Intelligence Operations Lab standalone HTML application."""
    html_content = render_intelligence_lab_html(report_data)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)


if __name__ == "__main__":
    run_consistency_evaluation()
