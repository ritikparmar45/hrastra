"""
Data schemas for Candidate Information Reconciliation and Recruiter Decision Brief.
Uses Pydantic V2 to enforce structured AI responses via OpenAI API.
"""

from enum import Enum
from typing import List, Literal
from pydantic import BaseModel, Field


class RecommendedAction(str, Enum):
    INTERVIEW = "INTERVIEW"
    ASK_FOR_INFORMATION = "ASK FOR INFORMATION"
    REJECT = "REJECT"
    MANUAL_REVIEW = "MANUAL REVIEW"


class EvidenceItem(BaseModel):
    finding: str = Field(
        ...,
        description="The specific claim, match, contradiction, or gap conclusion."
    )
    source: str = Field(
        ...,
        description="Source document or comparison pair (e.g. 'Candidate Resume', 'Candidate Notes', 'Resume vs Recruiter Notes')."
    )
    quote_or_reference: str = Field(
        ...,
        description="Direct quote or specific factual reference supporting this finding."
    )


class CandidateDecisionBrief(BaseModel):
    candidate_name: str = Field(
        ...,
        description="Full name of the candidate evaluated."
    )
    job_title: str = Field(
        ...,
        description="Target job position title from the Job Description."
    )
    overall_assessment: str = Field(
        ...,
        description="High-level 2-3 sentence executive summary reconciling candidate fit and key findings."
    )
    recommended_action: RecommendedAction = Field(
        ...,
        description="Recommended next step: INTERVIEW, ASK FOR INFORMATION, REJECT, or MANUAL REVIEW."
    )
    strong_matches: List[str] = Field(
        default_factory=list,
        description="List of strong, verified alignments between candidate experience/skills and key job requirements."
    )
    missing_information: List[str] = Field(
        default_factory=list,
        description="List of required qualifications, certifications, or details absent across provided documents."
    )
    contradictions: List[str] = Field(
        default_factory=list,
        description="Direct discrepancies or conflicting statements between CV, candidate notes, and JD."
    )
    potential_concerns: List[str] = Field(
        default_factory=list,
        description="Potential red flags, unexplained employment gaps, exaggerated claims, or risk factors."
    )
    evidence: List[EvidenceItem] = Field(
        default_factory=list,
        description="Factual evidence items supporting each major match, contradiction, or concern finding."
    )
    action_rationale: str = Field(
        ...,
        description="Clear operational rationale explaining why the recommended action was chosen."
    )
    tailored_interview_questions: List[str] = Field(
        ...,
        description="Exactly 5 tailored interview questions specifically targeted at probing identified gaps, contradictions, or unverified claims."
    )
