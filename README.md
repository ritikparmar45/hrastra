# AI Candidate Information Reconciliation & Recruiter Decision Brief

> **AI Candidate Information Reconciliation Workflow** powered by OpenAI API (`gpt-6-astra`) with Groq development backend support (`groq/compound`).  
> Built for 50–300 employee recruitment agencies in North America and MENA to eliminate manual candidate verification fatigue and produce evidence-backed hiring decisions.

---

## 1. Business Problem
Recruiters in mid-sized recruitment agencies spend significant time manually cross-referencing candidate resumes against recruiter phone screen notes, application forms, and complex job descriptions.

When candidates present inflated claims on their CV or omit key job requirements, recruiters risk either:
- **Fast-tracking unverified candidates** into client interviews (damaging agency reputation).
- **Rejecting qualified candidates** due to ambiguous screening notes.

This workflow automates the **cross-source information reconciliation process** in seconds, producing an actionable **Recruiter Decision Brief**.

---

## 2. Why This Is Not Just Resume Screening
Traditional ATS tools and AI resume matchers simply compute keyword similarity between a CV and a Job Description. 

**This workflow is fundamentally different:**
- **Multi-Source Reconciliation:** It evaluates 3+ distinct sources simultaneously (Job Description, CV/Resume, and Recruiter Intake Notes).
- **Contradiction Detection:** It specifically flags discrepancies between what a candidate claims on paper vs. what they stated in intake conversations (e.g., claiming a full-time 3-year Lead position when notes reveal a 6-month contracting role).
- **Ambiguity & Gap Identification:** Distinguishes between proven qualifications, exaggerated team accomplishments, and unmentioned mandatory criteria.
- **Fact-vs-Inference Isolation:** Every key finding is bound to direct quotes and source references.

---

## 3. Workflow Architecture

```
                               ┌─────────────────────────────┐
                               │       Input Documents       │
                               │  - job_description.txt      │
                               │  - candidate_resume.pdf/.txt│
                               │  - candidate_notes.txt      │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │   src/extractor.py          │
                               │   (Text & pypdf Extractor)  │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │   src/prompts.py &          │
                               │   src/schemas.py            │
                               │   (Pydantic V2 Schema)      │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │     Inference API Engine    │
                               │  gpt-6-astra / groq-compound│
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                               ┌─────────────────────────────┐
                               │       Output Results        │
                               │  - output/decision_brief.md │
                               │  - output/decision_brief.json│
                               └─────────────────────────────┘
```

---

## 4. Setup Instructions

### Prerequisites
- Python 3.10 or higher
- OpenAI API Key (`OPENAI_API_KEY`) or Groq Dev Key (`GROQ_API_KEY`)

### Installation
1. Navigate to project directory:
   ```bash
   cd candidate-workflow
   ```

2. Install python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy environment template:
   ```bash
   cp .env.example .env
   ```

---

## 5. Environment Variables

Configure `.env` for your preferred provider:

- **For OpenAI (`gpt-6-astra`)**:
  ```env
  OPENAI_API_KEY=sk-proj-your-openai-api-key
  OPENAI_MODEL=gpt-6-astra
  ```

- **For Groq Dev Backend (Free Testing)**:
  ```env
  GROQ_API_KEY=gsk_your_groq_api_key
  GROQ_MODEL=groq/compound
  ```

---

## 6. How to Run

### Standard Execution
```bash
python src/main.py
```

### Update Brief with Follow-up Clarification Notes
```bash
python src/main.py --update
```

### Offline Local Demo Mode (Dry Run)
```bash
python src/main.py --dry-run
```

---

## 7. Example Output Format

Saved to `output/decision_brief.md` and `output/decision_brief.json`:

```markdown
# Recruiter Decision Brief: Candidate Reconciliation

**Candidate Name:** Alex Mercer  
**Target Position:** Senior Backend & Cloud Engineer  
**Recommended Action:** `ASK FOR INFORMATION`  

---

### Overall Assessment
The candidate has relevant experience but significant discrepancies between resume claims and intake statements. Key qualifications and certifications required by the job description are not fully met.

---

### 1. Strong Matches Against Requirements
- 6+ years of backend engineering experience with Python
- Experience with FastAPI and PostgreSQL
- AWS experience with Terraform, EKS, Lambda, S3, and RDS

### 2. Missing Information & Unverified Qualifications
- Active AWS Certified Solutions Architect (Professional level) certification
- Active Security Clearance or willingness for financial security vetting
- Demonstrated experience leading database optimization for 5M+ user workloads

### 3. Contradictions Between Sources
- ⚠️ Resume claims full-time Lead Cloud Architect (2021-2024), but intake notes confirm 6-month contractor role in 2023.
- ⚠️ Resume claims 10M+ DB scaling lead credit, but screening notes confirm candidate was 1 of 18 devs on team.

### 4. Potential Concerns & Red Flags
- 🚩 Limited timezone overlap with Gulf Standard Time (GST)
- 🚩 Missing Professional level AWS certification

### 5. Evidence & Source Quotes
| Finding / Conclusion | Source Document(s) | Quote or Factual Reference |
| :--- | :--- | :--- |
| Employment duration contradiction | Resume vs Recruiter Notes | `Alex clarified he was actually hired as a 6-month part-time contractor...` |

### 6. Recommended Next Action & Rationale
**Decision:** `ASK FOR INFORMATION`
**Rationale:** The candidate shows technical potential, but critical discrepancies require written clarification before scheduling an interview.

### 7. Tailored Interview Questions
1. Can you clarify your exact role and contract dates at Apex Cloud Technologies?
2. How do you plan to obtain the AWS Certified Solutions Architect (Professional) certification?
3. Are you willing to undergo MENA/US financial security vetting?
4. How do you ensure strict adherence to PCI-DSS security compliance standards?
5. Are you flexible with your work hours to provide overlapping hours with GST timezone?
```
