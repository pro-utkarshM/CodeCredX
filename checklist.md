# CodeCredX Development Checklist

---

## Phase 0: Project Foundation

### Setup

* [x] Configure PocketFlow template
* [x] Set up virtual environment (`.venv`)
* [x] Install dependencies via `pip install -e .`
* [x] Add `.env` with GitHub & OpenAI keys

### Structure

* [x] Implement `main.py`, `flow.py`, and `nodes.py`
* [x] Create modular agents in `nodes/`
* [x] Set up `utils/` folder with helper functions

---

## Phase 1: Resume to URL Crawling Pipeline

### Resume Input Agent

* [ ] Accept resume as PDF, DOCX, or LinkedIn (planned)
* [x] Simulate resume as plain text (PoC stage)
* [x] Extract GitHub and project-related URLs using regex

### Depth-Aware Crawling

* [x] Implement Depth 0 (URLs only)
* [ ] Depth 1: README, metadata, and basic commit analysis
* [ ] Depth 2: Issues, pull requests, blog/demo links
* [ ] Depth 3 and beyond: External content like API docs, articles

---

## Phase 2: Project Verification Agents

### GitHubAnalyzerNode

* [x] Fetch metadata: name, description, stars, fork, topics
* [x] Download README.md from main/master branches
* [x] Skip invalid, private, or inaccessible repositories

### LLMSummarizerNode

* [ ] Use `call_llm()` to summarize projects
* [ ] Fallback to description if README is missing
* [ ] Store summary in project data

### ContributionAgent (future)

* [ ] Clone repository locally
* [ ] Analyze commit history using PyDriller or GitPython
* [ ] Calculate percentage authored by the candidate

### OriginalityAgent

* [ ] Compare against template/forked repos using SimHash or AST
* [ ] Penalize copied or unoriginal work

### TrustHeuristicAgent (meta-agent)

* [ ] Detect spammy, AI-generated, or inflated projects
* [ ] Flag projects with suspicious signals

---

## Phase 3: Scoring Engine

### Project-Level Scoring

* [ ] Compute originality score
* [ ] Compute contribution score
* [ ] Assess summary quality
* [ ] Combine into a normalized trust score (0 to 100)

### Candidate Aggregation

* [ ] Aggregate scores across multiple projects
* [ ] Normalize across roles and number of projects

---

## Phase 4: Elo-Based Ranking

### Skill Elo Scoring

* [ ] Initialize Elo from trust score
* [ ] Simulate pairwise comparisons
* [ ] Dynamically adjust ranks as new candidates enter

### Role-Specific Ranking Pools

* [ ] Create separate pools for frontend, backend, ML, blockchain, etc.
* [ ] Compare within relevant domain only

### Elo Reinforcement (future)

* [ ] Allow recruiter-validated outcomes to refine Elo
* [ ] Penalize low-effort repos over time

---

## Phase 5: Output and Reporting

### Candidate Reports

* [ ] Generate per-candidate summaries (JSON or Markdown)
* [ ] Include top projects, trust score, Elo score, and summary

### Recruiter Interface

* [ ] CLI to search and filter candidate reports
* [ ] Web dashboard (planned: Streamlit or Next.js)

---

## Phase 6: Testing and Edge Case Handling

* [ ] Test invalid GitHub links
* [ ] Handle missing README or stars
* [ ] Detect forked/archived repos
* [ ] Simulate GPT-generated or empty repos
* [ ] Validate robustness against edge cases

---

## Phase 7: Future Enhancements

| Feature                                       | Status  |
| --------------------------------------------- | ------- |
| Resume file ingestion (PDF/DOCX)              | Planned |
| GitHub OAuth login for real commit validation | Planned |
| LangGraph-based async agent orchestration     | Planned |
| Web dashboard for recruiters                  | Planned |
| Multi-agent CLI interface                     | Planned |
| Plugin architecture for scoring agent modules | Planned |

---

## Phase 8: Final Delivery

* [ ] End-to-end working CLI MVP
* [ ] Sample resume with real GitHub projects
* [ ] Final output in JSON and Markdown formats
* [ ] Public GitHub repo with README, architecture diagram, and examples
* [ ] CI pipeline using GitHub Actions (optional)

---
