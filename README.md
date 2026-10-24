# Skill First Labs — AI/ML Internship Shortlisting Assignment
> **Candidate Submission**  
> Streamlined, production-ready implementation for Milestone 1 and Milestone 2 with unified 1-command runner, 63 automated tests, and clean, focused executive reports.

---

## ⚡ Quick Start (1-Command Pipeline)

Run both milestones end-to-end with a single command from the project root:

```bash
# Run both Milestone 1 & Milestone 2 and generate clean HTML reports
python run.py

# Run all 63 unit tests across both milestones
python run.py --test
```

---

## Project Milestones

### [Milestone 1: CSS Insight Engine](milestone-1-css-insight-engine/)
*From Raw Stylesheets to Explainable Design Intelligence*
- **Directory:** [`milestone-1-css-insight-engine/`](milestone-1-css-insight-engine/)
- **Documentation:** [`milestone-1-css-insight-engine/README.md`](milestone-1-css-insight-engine/README.md)
- **Required Explanation (3–4 lines + edge case):** [`milestone-1-css-insight-engine/EXPLANATION.md`](milestone-1-css-insight-engine/EXPLANATION.md)
- **Executive HTML Report:** [`milestone-1-css-insight-engine/report.html`](milestone-1-css-insight-engine/report.html)
- **Automated Tests:** 31 passed (`pytest tests -v`)
- **Direct Run:** `python run_insight_engine.py` (analyzes sample CSS out-of-the-box with zero arguments)

---

### [Milestone 2: TalentGraph Agent](milestone-2-talentgraph-agent/)
*An Explainable AI Career Intelligence Assistant*
- **Directory:** [`milestone-2-talentgraph-agent/`](milestone-2-talentgraph-agent/)
- **Documentation:** [`milestone-2-talentgraph-agent/README.md`](milestone-2-talentgraph-agent/README.md)
- **Required Explanation (3–4 concise lines):** [`milestone-2-talentgraph-agent/EXPLANATION.md`](milestone-2-talentgraph-agent/EXPLANATION.md)
- **2-Minute Demo Script:** [`milestone-2-talentgraph-agent/DEMO_SCRIPT.md`](milestone-2-talentgraph-agent/DEMO_SCRIPT.md)
- **Consistency Lab Report:** [`milestone-2-talentgraph-agent/reports/consistency_report.html`](milestone-2-talentgraph-agent/reports/consistency_report.html)
- **Automated Tests:** 32 passed (`python -m pytest -v`)
- **Direct Run:** `python milestone-2-talentgraph-agent/main.py --demo`

---

## Summary of Execution Options

| Goal | Command |
| :--- | :--- |
| **Run Everything (M1 + M2)** | `python run.py` |
| **Run All 63 Tests** | `python run.py --test` |
| **Run Milestone 1 Analysis** | `python run_insight_engine.py` |
| **Run Milestone 2 Demo** | `python milestone-2-talentgraph-agent/main.py --demo` |
| **Run Milestone 2 Consistency Lab** | `python milestone-2-talentgraph-agent/evaluation/evaluate_consistency.py` |
