"""
AI Candidate Information Reconciliation & Recruiter Decision Brief.
CLI workflow executing text extraction, multi-source reconciliation via Groq API (llama-3.3-70b-versatile),
and structured markdown + JSON brief generation.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout/stderr encoding for Windows console compatibility
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Ensure project root is in Python path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Third-party imports
from groq import Groq, GroqError, APIError, AuthenticationError
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Internal imports
from src.extractor import load_input_documents, extract_text_from_file
from src.prompts import RECONCILIATION_SYSTEM_PROMPT, build_reconciliation_user_prompt
from src.schemas import CandidateDecisionBrief

console = Console()


def format_markdown_brief(brief: CandidateDecisionBrief) -> str:
    """Formats the Pydantic CandidateDecisionBrief into a clean, professional Markdown report."""
    md = f"""# Recruiter Decision Brief: Candidate Reconciliation

**Candidate Name:** {brief.candidate_name}  
**Target Position:** {brief.job_title}  
**Recommended Action:** `{brief.recommended_action.value}`  

---

### Overall Assessment
{brief.overall_assessment}

---

### 1. Strong Matches Against Requirements
"""
    if brief.strong_matches:
        for match in brief.strong_matches:
            md += f"- {match}\n"
    else:
        md += "- No clear strong matches identified.\n"

    md += "\n### 2. Missing Information & Unverified Qualifications\n"
    if brief.missing_information:
        for missing in brief.missing_information:
            md += f"- {missing}\n"
    else:
        md += "- No major missing qualifications noted.\n"

    md += "\n### 3. Contradictions Between Sources\n"
    if brief.contradictions:
        for contradiction in brief.contradictions:
            md += f"- ⚠️ {contradiction}\n"
    else:
        md += "- No direct contradictions detected.\n"

    md += "\n### 4. Potential Concerns & Red Flags\n"
    if brief.potential_concerns:
        for concern in brief.potential_concerns:
            md += f"- 🚩 {concern}\n"
    else:
        md += "- No critical red flags identified.\n"

    md += "\n### 5. Evidence & Source Quotes\n"
    md += "| Finding / Conclusion | Source Document(s) | Quote or Factual Reference |\n"
    md += "| :--- | :--- | :--- |\n"
    for item in brief.evidence:
        finding_clean = item.finding.replace('|', '\\|')
        source_clean = item.source.replace('|', '\\|')
        quote_clean = item.quote_or_reference.replace('|', '\\|')
        md += f"| {finding_clean} | {source_clean} | `{quote_clean}` |\n"

    md += f"\n### 6. Recommended Next Action & Rationale\n"
    md += f"**Decision:** `{brief.recommended_action.value}`\n\n"
    md += f"**Rationale:** {brief.action_rationale}\n"

    md += "\n### 7. Tailored Interview Questions (Targeting Gaps & Claims)\n"
    for idx, q in enumerate(brief.tailored_interview_questions, 1):
        clean_q = q.lstrip("0123456789. ")
        md += f"{idx}. {clean_q}\n"

    md += f"\n---\n*Report generated via Groq API ({os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')}) - Information Reconciliation Engine*\n"
    return md


def clean_json_response(raw_text: str) -> str:
    """Extracts the outermost valid JSON object between first '{' and last '}'."""
    if not raw_text:
        return "{}"
    cleaned = raw_text.strip()
    start_idx = cleaned.find('{')
    end_idx = cleaned.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return cleaned[start_idx:end_idx + 1]
    return cleaned



def run_workflow(input_dir: Path, output_dir: Path, include_followup: bool = False, dry_run: bool = False):
    """Executes the complete candidate reconciliation workflow using Groq API."""
    
    # Step 1: Load environment variables
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    model_name = os.getenv("GROQ_MODEL", "groq/compound")

    console.print(Panel.fit(
        f"[bold cyan]AI Candidate Information Reconciliation Workflow[/bold cyan]\n"
        f"[dim]Target: 50-300 Employee Recruitment Agencies | Powered by Groq API ({model_name})[/dim]",
        border_style="cyan"
    ))

    if not dry_run and (not api_key or api_key == "your_groq_api_key_here"):
        console.print("\n[bold red]❌ Error: GROQ_API_KEY is missing or unconfigured in .env file![/bold red]")
        console.print("[yellow]Please open .env and set a valid GROQ_API_KEY=gsk_... (or run with --dry-run to test offline)[/yellow]\n")
        sys.exit(1)

    # Step 2: Load input documents
    console.print(f"\n[bold yellow][1/4][/bold yellow] 📁 Scanning input directory: [cyan]{input_dir.resolve()}[/cyan]")
    try:
        docs = load_input_documents(input_dir)
    except Exception as e:
        console.print(f"[bold red]❌ File Loading Error:[/bold red] {e}")
        sys.exit(1)

    required_keys = ["job_description", "candidate_resume", "candidate_notes"]
    missing_docs = [k for k in required_keys if k not in docs]
    if missing_docs:
        console.print(f"[bold red]❌ Missing required input files:[/bold red] {', '.join(missing_docs)}")
        sys.exit(1)

    console.print("  [green]✓[/green] Job Description loaded (" + docs.get("job_description_filename", "txt") + ")")
    console.print("  [green]✓[/green] Candidate Resume loaded (" + docs.get("candidate_resume_filename", "pdf/txt") + ")")
    console.print("  [green]✓[/green] Candidate Notes loaded (" + docs.get("candidate_notes_filename", "txt") + ")")

    followup_content = None
    if include_followup:
        if "followup_notes" in docs:
            followup_content = docs["followup_notes"]
            console.print("  [green]✓[/green] Follow-up Notes detected & loaded (" + docs.get("followup_notes_filename", "txt") + ")")
        else:
            console.print("  [yellow]![/yellow] Update mode requested (--update), but no followup_notes file found.")

    # Step 3: Build Prompt & Call Groq API (or Dry Run)
    console.print(f"\n[bold yellow][2/4][/bold yellow] 🧠 Constructing prompt & connecting to Groq API ([cyan]{model_name}[/cyan])...")
    user_prompt = build_reconciliation_user_prompt(
        job_description=docs["job_description"],
        candidate_resume=docs["candidate_resume"],
        candidate_notes=docs["candidate_notes"],
        followup_notes=followup_content
    )

    console.print(f"[bold yellow][3/4][/bold yellow] ⚡ Reconciling multi-source data with structured JSON schema...")

    brief: CandidateDecisionBrief | None = None

    if dry_run:
        console.print("  [cyan]ℹ️ [DRY RUN MODE][/cyan] Simulating AI multi-source reconciliation for verification...")
        
        if followup_content:
            brief = CandidateDecisionBrief(
                candidate_name="Alex Mercer",
                job_title="Senior Backend & Cloud Engineer",
                overall_assessment="Alex Mercer demonstrates 6+ yrs of Python FastAPI experience. Recent HR verification confirmed contractor tenure, and candidate agreed to security clearance, GST hours, and scheduled AWS Professional exam.",
                recommended_action="INTERVIEW",
                strong_matches=[
                    "6+ yrs Python backend experience (FastAPI & Asyncio).",
                    "PostgreSQL query optimization & microservices architecture.",
                    "Agreed to 7:00 AM EST shift for 4-hr GST timezone overlap.",
                    "Signed financial security vetting consent form."
                ],
                missing_information=[
                    "AWS Professional Certification (exam scheduled for Oct 2026)."
                ],
                contradictions=[
                    "Resume listed 'Lead Cloud Architect (2021-2024)', but HR verified 'Contract Developer (May-Nov 2023)'."
                ],
                potential_concerns=[
                    "Initial resume title inflation during contract period."
                ],
                evidence=[
                    {
                        "finding": "Employment Title Verification",
                        "source": "Resume vs Follow-up HR Notes",
                        "quote_or_reference": "Resume: 'Lead Architect 2021-Present' vs HR: 'Contractor May-Nov 2023'"
                    },
                    {
                        "finding": "AWS Certification Status",
                        "source": "JD vs Follow-up Notes",
                        "quote_or_reference": "JD: 'Professional Cert Required' vs Notes: 'Exam scheduled Oct 2026'"
                    }
                ],
                action_rationale="Major timezone, security, and cert blockers resolved in follow-up. Proceed to technical interview.",
                tailored_interview_questions=[
                    "What technical scope did you own during your 6-month contract at Apex Cloud?",
                    "Which topics are you prioritizing for your upcoming AWS Professional exam?",
                    "How do you configure connection pooling in FastAPI for heavy PostgreSQL queries?",
                    "Describe a time you worked with DBAs to fix slow microservice API endpoints.",
                    "How will you manage daily 7:00 AM EST start times with the MENA team?"
                ]
            )
        else:
            brief = CandidateDecisionBrief(
                candidate_name="Alex Mercer",
                job_title="Senior Backend & Cloud Engineer",
                overall_assessment="Solid Python/FastAPI technical background, but direct reconciliation reveals discrepancies in job title/tenure, unverified DB scaling ownership, and missing mandatory certs.",
                recommended_action="ASK FOR INFORMATION",
                strong_matches=[
                    "6+ years Python microservices experience (FastAPI/Asyncio).",
                    "PostgreSQL query development and Docker deployment."
                ],
                missing_information=[
                    "AWS Certified Solutions Architect (Professional level) missing.",
                    "Active Security Clearance missing (candidate hesitant on background check).",
                    "Unconfirmed GST timezone overlap (preferred strict 9 AM - 5 PM EST)."
                ],
                contradictions=[
                    "Resume claims full-time 'Lead Cloud Architect (2021-2024)', but intake notes confirm 6-month contractor role in 2023."
                ],
                potential_concerns=[
                    "Ambiguous DB scaling claim: Listed sole credit for 10M+ DB scaling, but was 1 of 18 devs on team."
                ],
                evidence=[
                    {
                        "finding": "Employment Title Discrepancy",
                        "source": "Resume vs Screening Notes",
                        "quote_or_reference": "Resume: 'Lead Architect (2021-Present)' vs Notes: '6-month contractor in 2023'"
                    },
                    {
                        "finding": "AWS Certification Level Gap",
                        "source": "JD vs Resume",
                        "quote_or_reference": "JD: 'AWS Professional Required' vs Resume: 'Associate Level Only'"
                    },
                    {
                        "finding": "Database Scaling Scope",
                        "source": "Resume vs Notes",
                        "quote_or_reference": "Resume: 'Spearheaded 10M+ DB scaling' vs Notes: '1 of 18 devs; DBAs handled sharding'"
                    }
                ],
                action_rationale="Request written employment verification and cert timeline before scheduling client interview.",
                tailored_interview_questions=[
                    "Can you clarify your exact title and contract dates at Apex Cloud?",
                    "What was your direct code contribution to PostgreSQL queries versus the DBA team?",
                    "What is your timeline for obtaining the AWS Professional certification?",
                    "Are you willing to complete the required financial security clearance check?",
                    "Can you adjust your schedule to start earlier for GST timezone overlap?"
                ]
            )

    else:
        client = Groq(api_key=api_key)
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": RECONCILIATION_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            raw_json = response.choices[0].message.content
            cleaned_json = clean_json_response(raw_json)
            brief = CandidateDecisionBrief.model_validate_json(cleaned_json)

        except AuthenticationError:
            console.print("\n[bold red]❌ Authentication Error:[/bold red] Invalid GROQ_API_KEY provided in .env.")
            sys.exit(1)
        except GroqError as e:
            console.print(f"\n[bold red]❌ Groq API Execution Failure:[/bold red] {e}")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[bold red]❌ Validation or API Parsing Failure:[/bold red] {e}")
            sys.exit(1)


    if not brief:
        console.print("[bold red]❌ Error: Failed to generate candidate decision brief.[/bold red]")
        sys.exit(1)

    # Step 4: Save outputs
    console.print(f"\n[bold yellow][4/4][/bold yellow] 💾 Saving decision brief outputs to [cyan]{output_dir.resolve()}[/cyan]...")
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "decision_brief.json"
    md_path = output_dir / "decision_brief.md"

    # Save JSON
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(brief.model_dump_json(indent=2))

    # Save Markdown
    md_content = format_markdown_brief(brief)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Output Summary Table to Terminal
    console.print("\n[bold green]✅ CANDIDATE RECONCILIATION COMPLETE[/bold green]\n")

    summary_table = Table(title="Executive Summary", show_header=True, header_style="bold magenta")
    summary_table.add_column("Field", style="cyan", width=25)
    summary_table.add_column("Reconciled Finding", style="white")

    summary_table.add_row("Candidate Name", brief.candidate_name)
    summary_table.add_row("Target Position", brief.job_title)
    summary_table.add_row("Recommended Action", f"[bold green]{brief.recommended_action.value}[/bold green]")
    summary_table.add_row("Strong Matches", f"{len(brief.strong_matches)} items identified")
    summary_table.add_row("Contradictions", f"[yellow]{len(brief.contradictions)} discrepancy(ies) flagged[/yellow]")
    summary_table.add_row("Interview Questions", f"{len(brief.tailored_interview_questions)} tailored questions generated")

    console.print(summary_table)

    console.print("\n[bold cyan]OUTPUT FILES GENERATED:[/bold cyan]")
    console.print(f"  • JSON File: [link=file://{json_path.resolve()}]{json_path.resolve()}[/link]")
    console.print(f"  • Markdown Brief: [bold underline green]{md_path.resolve()}[/bold underline green]\n")


def main():
    parser = argparse.ArgumentParser(
        description="AI Candidate Information Reconciliation & Recruiter Decision Brief (Groq API)"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="input",
        help="Directory containing job description, resume, and notes files (default: input)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory where brief files will be saved (default: output)"
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Include follow-up clarification notes (followup_notes.txt) to update brief"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate AI reconciliation locally without requiring live API credentials"
    )

    args = parser.parse_args()
    
    project_root = Path(__file__).parent.parent
    input_path = project_root / args.input_dir
    output_path = project_root / args.output_dir

    run_workflow(input_path, output_path, include_followup=args.update, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
