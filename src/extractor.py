"""
Document Text Extraction Module.
Supports plain text (.txt) and PDF (.pdf) documents using pypdf.
Includes text cleaning and robust error handling.
"""

import os
from pathlib import Path
from pypdf import PdfReader


def clean_text(text: str) -> str:
    """Standardizes whitespace and strips non-printable control characters."""
    if not text:
        return ""
    # Normalize newline characters
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove multiple consecutive blank lines while preserving paragraph spacing
    lines = [line.strip() for line in text.split('\n')]
    cleaned = '\n'.join(line for line in lines if line)
    return cleaned


def extract_text_from_file(file_path: str | Path) -> str:
    """
    Extracts text from a given file path (.txt or .pdf).
    
    Args:
        file_path: Absolute or relative path to target document.
        
    Returns:
        Cleaned text string extracted from the file.
        
    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If file extension is unsupported or extraction fails.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found at: {path.resolve()}")

    suffix = path.suffix.lower()
    
    try:
        if suffix == '.txt' or suffix == '.md':
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                raw_text = f.read()
                return clean_text(raw_text)

        elif suffix == '.pdf':
            reader = PdfReader(str(path))
            extracted_pages = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    extracted_pages.append(page_text)
            
            raw_text = "\n\n".join(extracted_pages)
            if not raw_text.strip():
                raise ValueError(f"PDF at '{path.name}' appears to contain no extractable text (it may be scanned/image-only).")
            return clean_text(raw_text)

        else:
            raise ValueError(f"Unsupported file format '{suffix}'. Supported formats: .txt, .pdf, .md")

    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise RuntimeError(f"Error reading file '{path.name}': {str(e)}") from e


def load_input_documents(input_dir: str | Path) -> dict[str, str]:
    """
    Scans the input directory and loads job description, resume, candidate notes, and optional follow-up notes.
    Flexibly matches .txt or .pdf extensions.
    """
    dir_path = Path(input_dir)
    if not dir_path.exists():
        raise FileNotFoundError(f"Input directory does not exist: {dir_path.resolve()}")

    documents = {}
    
    # Document matching patterns
    patterns = {
        "job_description": ["job_description", "jd", "job_desc"],
        "candidate_resume": ["candidate_resume", "resume", "cv"],
        "candidate_notes": ["candidate_notes", "recruiter_notes", "notes", "application_notes"],
        "followup_notes": ["followup_notes", "followup", "update_notes"]
    }

    # Scan directory files
    dir_files = list(dir_path.glob("*"))
    
    for key, aliases in patterns.items():
        matched_file = None
        for file in dir_files:
            stem = file.stem.lower()
            if any(alias == stem or alias in stem for alias in aliases):
                matched_file = file
                break
        
        if matched_file:
            documents[key] = extract_text_from_file(matched_file)
            documents[f"{key}_filename"] = matched_file.name

    return documents
