# TALENTGRAPH AGENT — 2-Minute Demonstration Video Script

> **Video Duration:** 2 minutes (120 seconds)  
> **Speaker Role:** Senior AI Engineer / Candidate  
> **Target Audience:** Hiring Team at Skill First Labs  
> **Goal:** Demonstrate real native LLM tool calling, deterministic calculation, explainable career intelligence, missing-data handling, and consistency evaluation.

---

### [00:00 – 00:20] 1. Project Introduction & Problem Statement
- **Visual:** Terminal title banner showing `TALENTGRAPH AGENT | Explainable AI Career Intelligence Assistant`.
- **Narration:**
  > *"Hello! This is TalentGraph Agent, built for Milestone 2 of the Skill First Labs AI/ML internship assignment. Instead of relying on a language model's ungrounded memory, TalentGraph Agent is an explainable career intelligence assistant that uses verified local datasets and deterministic tools to answer questions about student capabilities, internship suitability, and skill gap roadmaps."*

---

### [00:20 – 00:35] 2. Architecture & Native Tool-Calling Loop
- **Visual:** Display architecture flow diagram or code snippet showing `TalentGraphAgent` query loop (`User Question → Tool Selection → Argument Validation → Python Execution → Tool Response → Grounded Synthesis`).
- **Narration:**
  > *"Rather than hardcoded if/else routing or complex frameworks like LangChain, TalentGraph implements a clean, native OpenAI-compatible tool loop. The LLM selects tools and passes structured JSON arguments, which Python validates and executes deterministically. The model only receives verified facts, guaranteeing that every response is backed by source record IDs."*

---

### [00:35 – 00:55] 3. Student Profile & Skill Matching Demo
- **Visual:** Run in CLI:
  ```bash
  python main.py "How suitable is student S001 for internship I002?"
  ```
- **Terminal Output Displayed:**
  ```text
  --- TOOL EXECUTION TRACE ---
    [Step 1] Tool: calculate_skill_match
      Arguments: {"student_id": "S001", "internship_id": "I002"}
      Status:    calculated
      Result:    Match=75.0% | Matched=['Python', 'SQL', 'Pandas'] | Missing=['Data Visualization']
  --- GROUNDED ANSWER ---
  Student S001 (Aarav Sharma) matches Internship I002 (Data Science & Analytics Intern at Quantum Analytics) at 75.0% skill overlap.
  - Matched skills (3/4): Python, SQL, Pandas
  - Missing required skills: Data Visualization
  Note: This match percentage is a deterministic skill-overlap score based on required skills; not a hiring prediction.
  Sources: students.json / S001, internships.json / I002
  ```
- **Narration:**
  > *"Watch this live execution trace: when asked about suitability, the agent invokes `calculate_skill_match`. The 75% score is calculated entirely in Python—not by LLM arithmetic. It identifies the 3 overlapping skills, the 1 missing skill ('Data Visualization'), and cites the exact source files `students.json / S001` and `internships.json / I002`."*

---

### [00:55 – 01:15] 4. Missing Data & Hallucination Guardrails
- **Visual:** Run two questions demonstrating guardrails:
  ```bash
  python main.py "What do you know about student S999?"
  python main.py "What is the GPA of student S001 if GPA is not stored?"
  ```
- **Terminal Output Displayed:**
  ```text
  [Step 1] Tool: get_student_profile -> Status: not_found
  Student S999 was not found in the local database. Sources: students.json

  [Step 1] Tool: get_student_profile -> Status: found (GPA is unrecorded)
  The GPA for student S001 (Aarav Sharma) is not stored in the database.
  Sources: students.json / S001
  ```
- **Narration:**
  > *"Here is how we handle missing data. When asked about unknown student S999, the tool returns a structured `not_found`, and the agent explicitly states the student does not exist. Similarly, student S001's record does not include a GPA. Instead of hallucinating a plausible number like 3.8, the agent respects the schema and states that GPA is not recorded."*

---

### [01:15 – 01:45] 5. Consistency Lab & Evaluation Report
- **Visual:** Run:
  ```bash
  python evaluation/evaluate_consistency.py
  ```
  Switch browser window to open `reports/consistency_report.html`.
- **Narration:**
  > *"Our signature differentiating feature is the Consistency Lab. It evaluates repeatability by executing each test question twice at temperature zero, extracting normalized structured facts—including student IDs, percentages, matched skills, and missing-data flags. Rather than relying on fragile exact text equality, it checks semantic and factual agreement. As you can see on the generated dashboard, all 8 questions achieved 100% factual agreement across runs."*

---

### [01:45 – 02:00] 6. Automated Tests & Summary
- **Visual:** Run in terminal:
  ```bash
  python -m pytest -v
  ```
  Highlight `32 passed in 1.88s`.
- **Narration:**
  > *"All 32 automated unit tests pass in under 2 seconds, verifying edge cases, zero-division safety, and argument validation. TalentGraph Agent stands out through robust software engineering, explainable decisions, and honest guardrails. Thank you!"*
