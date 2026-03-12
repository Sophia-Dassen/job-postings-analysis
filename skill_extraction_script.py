"""
Extracts metadata and highlighted skill phrases from multiple annotated job postings.

This script loops over a directory of annotated job posting (.docx) files, extracts 
job posting metadata from the header, highlighted hard and soft skill phrases from 
the job posting body, then writes the results to two separate CSV files.

Input: 
- Directory containing annotated Word documents with a consistent structure: 
  job posting metadata in the header and highlighted skill phrases in the posting excerpt.

Output: 
- CSV file containing extracted job posting metadata with the fields: 
  [job_id, company, job_title, location, source_platform, original_url, date_collected]
- CSV file containing extracted skill occurrences with the fields:
  [job_id, extracted_skill, observed_skill_type]

Notes:
- Highlight color determines the observed skill classification (hard vs soft).
- Duplicate skills per job posting are not allowed (goal: tracking skill presence, 
  not skill-mention frequency).
- Files missing any required job posting metadata (as defined in the metadata schema) are 
  rejected and logged. 
"""


from docx import Document
from docx.enum.text import WD_COLOR
import csv
import os
from datetime import datetime, timezone
import sys


# --- CONFIG ---
# Path to the directory containing all annotated job postings
DIR_PATH = "2_Annotated_Job_Postings"

# Output CSV files
JP_OUTPUT_PATH = "extracted_job_posting_metadata.csv"
SKILL_OUTPUT_PATH = "extracted_skills.csv"


# --- COLOR MAPPING ---
COLOR_TO_SKILL = {
    WD_COLOR.TURQUOISE: "hard",
    WD_COLOR.PINK: "soft"
}

# Schema used to extract and validate job posting metadata from source documents
# Each entry maps a source label to an output field and specifies whether it is required.
# --- METADATA FIELD DEFINITIONS ---
METADATA_FIELDS = [
    {"source_label": "Job ID", "output_field": "job_id", "mandatory": True},
    {"source_label": "Company", "output_field": "company", "mandatory": True},
    {"source_label": "Job Title", "output_field": "job_title", "mandatory": True},
    {"source_label": "Location", "output_field": "location", "mandatory": False},
    {"source_label": "Source Platform", "output_field": "source_platform", "mandatory": False},
    {"source_label": "Original URL", "output_field": "original_url", "mandatory": False},
    {"source_label": "Date collected", "output_field": "date_collected", "mandatory": False}
]


# --- HELPER STRUCTURES FOR METADATA LOOKUPS ---
LABELS_TO_FIELDS = {
    f["source_label"]: f["output_field"] for f in METADATA_FIELDS
}

REQUIRED_FIELDS = {
    f["output_field"] for f in METADATA_FIELDS
    if f["mandatory"]
}

JP_OUTPUT_FIELDS = [
    f["output_field"] for f in METADATA_FIELDS
]

SKILL_OUTPUT_FIELDS = [
    "job_id", 
    "extracted_skill", 
    "observed_skill_type"
]


def extract_metadata(doc, filename):
    """Extract job posting metadata from a Word .docx file.

    Args:
        doc (docx.document.Document): Document object representing the contents of a Word job posting file 
        filename (str): The file name of the job posting Word document used for warning logging

    Returns:
        dict: Dictionary of output field (key) and extracted metadata (value) pairs
    """
    
    metadata = {field: None for field in JP_OUTPUT_FIELDS}
    
    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()

        for label, field in LABELS_TO_FIELDS.items():
            label_prefix = f'{label}:'

            if text.startswith(label_prefix):
                value = text.removeprefix(label_prefix).strip()

                if metadata[field] is None:
                    metadata[field] = value
                else:
                    print(f"Warning: duplicate metadata '{field}' in {filename}")

                break # Stop looping over metadata labels if match is found and parse next paragraph
    return metadata


def get_missing_metadata(metadata):
    """Return a list of missing metadata fields in a job posting document."""
    return [
        field for field in REQUIRED_FIELDS 
        if not metadata[field]
    ]


def extract_skills(doc, job_id):
    """Extract highlighted skill phrases from an annotated job posting (.docx) file.

    Args:
        doc (docx.document.Document): Document object representing the contents of a Word job posting file
        job_id (str): Job ID metadata of the job posting document

    Returns:
        list[dict]: Each dictionary contains keys ("job_id", "extracted_skill", "observed_skill_type")
    """

    skill_rows = []
    extracted_skills = set() # Track extracted skills to prevent duplicates per job posting

    def add_skill_from_buffer(skill_buffer, observed_skill_type):
        skill_text = skill_buffer.strip()
        if skill_text and skill_text not in extracted_skills:
            skill_rows.append({
                "job_id": job_id, 
                "extracted_skill": skill_text, 
                "observed_skill_type": observed_skill_type
            })
            extracted_skills.add(skill_text)

    for paragraph in doc.paragraphs:
        skill_buffer = ""
        observed_skill_type = None

        for run in paragraph.runs:
            # Collect contiguous highlighted text into skill buffer
            if run.font.highlight_color is not None:
                skill_buffer += run.text
                observed_skill_type = COLOR_TO_SKILL.get(run.font.highlight_color, "invalid")
            # Extract skill from buffer when highlighting stops
            else: 
                add_skill_from_buffer(skill_buffer, observed_skill_type)
                skill_buffer = ""
                observed_skill_type = None

        # Extract skill from buffer if highlighting continues until the end of paragraph 
        add_skill_from_buffer(skill_buffer, observed_skill_type)
    
    return skill_rows


def log_extraction_summary(total_files, rejected_files, OUTPUT_FILE_ROWS):
    """Print extraction run summary log with extraction metrics, exceptions, and outputs.

    Args:
        total_files (int): Counter of total job posting files
        rejected_files (dict[str, str]): Mapping of rejected filename to rejection reason
        OUTPUT_FILE_ROWS (list[tuple[str, list]]): Mapping of output file paths to extracted rows
    """
    successful_files = total_files - len(rejected_files)

    total_skills = 0
    for file, rows in OUTPUT_FILE_ROWS:
        if file == SKILL_OUTPUT_PATH:
            total_skills = len(rows)

    DIVIDER = "-" * 50
    
    print("\n" + DIVIDER)
    print("Extraction run summary")
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(DIVIDER)

    print(f"Job postings processed : {successful_files} / {total_files}")
    print(f"Skills extracted       : {total_skills}")
    print(f"Rejected files         : {len(rejected_files)}")

    if rejected_files:
        print("\nRejected files:")
        for file, reason in rejected_files.items():
            print(f"- {file}")
            print(f"  Reason: {reason}")
    else:
        print("\nNo rejected files.")

    print("\nOutputs:")
    for file, rows in OUTPUT_FILE_ROWS:
        print(f"- {file} ({len(rows)} rows)")

    print(DIVIDER)


def write_csv(path: str, rows: list[dict], fieldnames: list[str]):
    """Write a list of dictionaries to a CSV file."""
    
    with open(path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file, 
            fieldnames=fieldnames,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def main():

    total_files = 0  
    rejected_files = {}

    # Lists for extracted job posting metadata and extracted skills
    all_jp_metadata_rows = []
    all_skill_rows = []

    # Helper structure mapping destination files to extracted rows 
    OUTPUT_FILE_ROWS = [
        (JP_OUTPUT_PATH, all_jp_metadata_rows), 
        (SKILL_OUTPUT_PATH, all_skill_rows)
    ]

    # Batch job posting processing 
    for filename in os.listdir(DIR_PATH):
    
        if not filename.lower().endswith(".docx"):
            continue # skip non-Word files
        total_files += 1

        
        # --- OPEN DOCUMENT ---
        doc_path = os.path.join(DIR_PATH, filename)
        doc = Document(doc_path)
        print(f'Processing file: {filename}')


        # --- EXTRACT JOB POSTING METADATA ---
        metadata = extract_metadata(doc, filename)

        # --- VALIDATE METADATA ---
        missing_metadata = get_missing_metadata(metadata)

        if missing_metadata:        
            rejected_files[filename] = (
                f"Missing required metadata: {', '.join(missing_metadata)}"
            )
            print(f"Failed to process file due to missing metadata: {', '.join(missing_metadata)}")
            continue # Proceed to next job posting
        
        all_jp_metadata_rows.append(metadata)


        # --- EXTRACT SKILLS ---
        skills = extract_skills(doc, metadata["job_id"])
        all_skill_rows.extend(skills)


    # --- WRITE EXTRACTED ROWS TO CSV FILES ---
    write_csv(JP_OUTPUT_PATH, all_jp_metadata_rows, JP_OUTPUT_FIELDS)
    write_csv(SKILL_OUTPUT_PATH, all_skill_rows, SKILL_OUTPUT_FIELDS)


    # --- FINAL EXTRACTION SUMMARY LOGGING ---
    log_extraction_summary(
        total_files, 
        rejected_files, 
        OUTPUT_FILE_ROWS
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
