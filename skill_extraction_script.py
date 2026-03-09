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
- Files with a missing Job ID are rejected and logged. 
"""


from docx import Document
from docx.enum.text import WD_COLOR
import csv
import os
from datetime import datetime, timezone


# --- CONFIG ---
# Path to the directory containing all annotated job postings
DIR_PATH = "2_Annotated_Job_Postings"

# Output CSV files
JP_OUTPUT_PATH = "extracted_job_posting_metadata.csv"
SKILL_OUTPUT_PATH = "extracted_skills.csv"

# Lists for extracted job posting metadata and extracted skills
all_jp_metadata_rows = []
all_skill_rows = []


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

OUTPUT_FIELDS = [
    f["output_field"] for f in METADATA_FIELDS
]


total_files = 0  
rejected_files = {}

# Batch job posting processing 
for filename in os.listdir(DIR_PATH):
    
    if not filename.lower().endswith(".docx"):
        continue # skip non-Word files
    total_files += 1


    # --- OPEN DOCUMENT ---
    doc_path = os.path.join(DIR_PATH, filename)
    doc = Document(doc_path)
    print(f'Processing file: {filename}')

    
    metadata = {field: None for field in OUTPUT_FIELDS}

    # --- EXTRACT JOB POSTING METADATA ---
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
    

    # Reject file if required metadata is missing and skip skill extraction
    missing_metadata = [
        field for field in REQUIRED_FIELDS 
        if not metadata[field]
    ]            

    if missing_metadata:        
        rejected_files[filename] = (
            f"Missing required metadata: {', '.join(missing_metadata)}"
        )
        print(f"Failed to process file due to missing metadata: {', '.join(missing_metadata)}")
        continue # Skip skill extraction and proceed to next job posting
    else:
        all_jp_metadata_rows.append(metadata)


    # Track extracted skills to prevent duplicates per job posting
    extracted_skills = set()


    # --- EXTRACT SKILLS ---
    for paragraph in doc.paragraphs:
        buffer = ""
        observed_skill_type = None

        for run in paragraph.runs:
            if run.font.highlight_color is not None:
                buffer += run.text
                observed_skill_type = COLOR_TO_SKILL.get(run.font.highlight_color, "invalid")
            else: 
                skill_text = buffer.strip()
                if skill_text and skill_text not in extracted_skills:
                    all_skill_rows.append({
                        "job_id": metadata["job_id"], 
                        "extracted_skill": skill_text, 
                        "observed_skill_type": observed_skill_type
                    })
                    extracted_skills.add(skill_text)
                
                buffer = ""
                observed_skill_type = None

        # flush at end of paragraph
        skill_text = buffer.strip()
        if skill_text and skill_text not in extracted_skills:
            all_skill_rows.append({
                "job_id": metadata["job_id"], 
                "extracted_skill": skill_text, 
                "observed_skill_type": observed_skill_type
            })
            extracted_skills.add(skill_text)


# --- WRITE JOB POSTING METADATA TO CSV ---
with open(JP_OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["job_id", "company", "job_title", "location", "source_platform", "original_url", "date_collected"]
    )
    writer.writeheader()
    writer.writerows(all_jp_metadata_rows)


# --- WRITE SKILLS TO CSV ---
with open(SKILL_OUTPUT_PATH, mode="w", newline="", encoding="utf-8") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["job_id", "extracted_skill", "observed_skill_type"]
    )
    writer.writeheader()
    writer.writerows(all_skill_rows)


# --- FINAL EXTRACTION SUMMARY LOGGING ---
DIVIDER = "-" * 50
successful_files = total_files - len(rejected_files)
UTC_timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
OUTPUT_FILES = {
    JP_OUTPUT_PATH: all_jp_metadata_rows, 
    SKILL_OUTPUT_PATH: all_skill_rows
}

print("\n" + DIVIDER)
print(f"Extraction run summary")
print(f"Timestamp: {UTC_timestamp}")
print(DIVIDER)

print(f'Job postings processed : {successful_files} / {total_files}')
print(f'Skills extracted       : {len(all_skill_rows)}')
print(f'Rejected files         : {len(rejected_files)}')

if rejected_files:
    print('\nRejected files:')
    for file, reason in rejected_files.items():
        print(f'- {file}')
        print(f'  Reason: {reason}')
else:
    print('\nNo rejected files.')

print("\nOutputs:")
for file, rows in OUTPUT_FILES.items():
    print(f"- {file} ({len(rows)} rows)")

print(DIVIDER)
