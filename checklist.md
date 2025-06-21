# CodeCredX Development Checklist

---

## Phase 0: Project Foundation

### Setup
- [x] Configure PocketFlow template  
- [x] Set up virtual environment (.venv)  
- [x] Install dependencies via `pip install -e .`  
- [x] Add `.env` with GitHub & OpenAI keys  

### Structure
- [x] Implement `main.py`, `flow.py`, and `nodes.py`  
- [x] Create modular agents in `nodes/`  
- [x] Set up `utils/` folder with helper functions  

---

## Phase 1: Resume to URL Crawling Pipeline

### Resume Input Agent
- [x] Accept resume as PDF (DOCX & LinkedIn planned)  
- [x] Simulate resume as plain text (fallback implemented)  
- [x] Extract GitHub and project-related URLs via regex + LLM  

### Depth-Aware Crawling
- [x] Depth 0: URLs only  
- [x] Depth 1: README, metadata, basic analysis  
- [ ] Depth 2: Issues, pull requests, blog/demo links  
- [ ] Depth 3+: External content like API docs, articles  

---

## Phase 2: Project Verification Agents

### GitHubAnalyzerNode
- [x] Fetch metadata: name, description, stars, forks, topics  
- [x] Download `README.md` from main/master branches  
- [x] Skip invalid/private/inaccessible repos  

### LLMSummarizerNode
- [x] Summarize project using `call_llm()`  
- [x] Fallback to description if README is missing  
- [x] Store summary in project data  

### ContributionAgent
- [ ] Clone repository locally  
- [ ] Analyze commit history (PyDriller/GitPython)  
- [x] Simulate author contribution percentage  

### OriginalityAgent
- [ ] Compare with forks/templates (SimHash/AST)  
- [x] Simulate originality score based on fork status  

### TrustHeuristicAgent (meta-agent)
- [ ] Detect spammy/AI-generated/inflated projects  
- [x] Simulate flags based on README and summary  

---

## Phase 3: Scoring Engine

### Project-Level Scoring
- [x] Compute originality score  
- [x] Compute contribution score  
- [x] Assess summary quality  
- [x] Normalize into a trust score (0–100)  

### Candidate Aggregation
- [x] Average trust score across projects  
- [ ] Normalize for roles and project count  

---

## Phase 4: Elo-Based Ranking

### Skill Elo Scoring
- [x] Initialize Elo from trust score  
- [ ] Simulate pairwise comparisons  
- [ ] Dynamically adjust ranks for new candidates  

### Role-Specific Ranking Pools
- [x] Placeholder for "General" pool  
- [ ] Compare candidates within domain only  

### Elo Reinforcement (future)
- [ ] Recruiter feedback adjusts Elo  
- [ ] Penalize low-effort repos over time  

---

## Phase 5: Output and Reporting

### Candidate Reports
- [x] Generate Markdown summary per candidate  
- [x] Include top projects, trust score, Elo score  

### Recruiter Interface
- [x] CLI output with filtering  
- [ ] Web dashboard (Streamlit/Next.js planned)  

---

## Phase 6: Testing and Edge Case Handling

- [x] Invalid GitHub links  
- [x] Missing README or stars  
- [x] Forked/archived repositories  
- [x] GPT-generated or empty repos  
- [x] Robustness against edge cases  

---

## Phase 7: Future Enhancements

| Feature                                 | Status                  |
|-----------------------------------------|--------------------------|
| Resume file ingestion (PDF/DOCX)        | PDF/TXT implemented, DOCX planned |
| GitHub OAuth for commit validation      | Planned              |
| LangGraph-based agent orchestration     | Planned              |
| Web dashboard for recruiters            | Planned              |
| Multi-agent CLI interface               | Planned              |
| Plugin architecture for scoring agents  | Planned              |

---

## Phase 8: Final Delivery

- [x] End-to-end working CLI MVP  
- [x] Sample resume input with real GitHub projects  
- [x] Output in JSON + Markdown formats  
- [ ] Public GitHub repo with README, architecture diagram, and examples  
- [ ] CI pipeline using GitHub Actions (optional)  
