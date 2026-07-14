"""
Run the end-to-end ETL pipeline from a single entry point.

This script orchestrates the complete demo pipeline by executing the following stages:
1. Extract job posting metadata and highlighted skill mentions into CSV files.
2. Refresh the Excel skill standardization workbook to import the latest extracted skill mentions.
3. Extract validated tables from the skill standardization workbook into CSV files.
4. Create and populate the demo SQL Server database.

Requirements
------------
- Directory of annotated synthetic job posting documents
- Excel skill standardization workbook
- SQL Server instance accessible available on PATH

Output
------
- CSV file containing extracted job posting metadata
- CSV file containing extracted job posting skill mentions
- JSON file containing job posting extraction run summary
- CSV export of the RawSkillStandardization table 
- CSV export of the SkillTaxonomy table 
- CSV export of the SkillClassifications table
- JSON file containing skill standardization workbook extraction run summary
- SQL Server demo database containing staging and core schemas
"""

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pyodbc

from scripts.excel.refresh_workbook import refresh_workbook


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SQL_DIR = PROJECT_ROOT / "sql"

JOB_POSTING_EXTRACTION_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "extraction"
    / "job_posting_extraction.py"
)

JOB_POSTING_EXTRACTION_SUMMARY = (
    PROJECT_ROOT
    / "data"
    / "extracted_demo"
    / "job_posting_extraction_summary.json"
)

SKILL_STANDARD_WB_PATH = (
    PROJECT_ROOT
    / "data"
    / "source"
    / "skill_standardization_pipeline.xlsx"
)

SKILL_STANDARD_WB_EXTRACTION_SCRIPT = (
    PROJECT_ROOT
    / "scripts"
    / "extraction"
    / "skill_standardization_pipeline_extraction.py"
)

SKILL_STANDARD_WB_EXTRACTION_SUMMARY = (
    PROJECT_ROOT
    / "data"
    / "extracted_demo"
    / "skill_standardization_extraction_summary.json"
)



def print_step(message: str) -> None:
    print(f"\n=== {message} ===")


def check_sqlcmd() -> None:
    if shutil.which("sqlcmd") is None:
        print(
            "Error: sqlcmd was not found on your PATH.\n"
            "Please install the Microsoft SQL Server command-line tools "
            "and ensure 'sqlcmd' is available."
        )
        sys.exit(1)


def run_job_posting_extraction() -> None:

    subprocess.run(
        [sys.executable, str(JOB_POSTING_EXTRACTION_SCRIPT)],
        check=True,
        cwd=PROJECT_ROOT,
    )


def run_workbook_extraction() -> None:

    subprocess.run(
        [sys.executable, str(SKILL_STANDARD_WB_EXTRACTION_SCRIPT)],
        check=True,
        cwd=PROJECT_ROOT,
    )


def setup_database() -> None:
 
    SERVER_NAME = r"localhost\SQLEXPRESS"

    subprocess.run(
        [
            "sqlcmd",
            "-S",
            SERVER_NAME,
            "-E",
            "-i",
            "setup_demo_database.sql",
        ],
        check=True,
        cwd=SQL_DIR,
    )

    
def fetch_scalar(cursor, query) -> int:
    cursor.execute(query)
    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Failed to retrieve job posting count.")

    return row[0]


def main() -> None:
    print("========================================")
    print("Job Postings Analysis Demo Setup")
    print("========================================")

    check_sqlcmd()

    # ==============================
    # RUN JOB POSTING EXTRACTION
    # ==============================

    print_step("[1/4] Extracting synthetic job posting dataset...")
    run_job_posting_extraction()

    with open(
        JOB_POSTING_EXTRACTION_SUMMARY,
        encoding="utf-8",
    ) as file:
        jp_extraction_summary = json.load(file)

    total_files = jp_extraction_summary["total_files"]
    successful_files = jp_extraction_summary["successful_files"]
    rejected_files = jp_extraction_summary["rejected_files"]
    skills_extracted = jp_extraction_summary["skills_extracted"]


    # ==========================================
    # REFRESH SKILL STANDARDIZATION WORKBOOK
    # ==========================================

    print_step("[2/4] Refreshing skill standardization pipeline workbook...")
    refresh_workbook(SKILL_STANDARD_WB_PATH)


    # =================================================
    # RUN SKILL STANDARDIZATION WORKBOOK EXTRACTION
    # =================================================

    print_step("[3/4] Extracting skill standardization pipeline workbook tables...")
    run_workbook_extraction()

    with open(
        SKILL_STANDARD_WB_EXTRACTION_SUMMARY,
        encoding="utf-8",
    ) as file:
        standard_skills_extraction_summary = json.load(file)

    total_mappings = standard_skills_extraction_summary["total_mappings"]
    valid_mappings = standard_skills_extraction_summary["valid_mappings"]
    invalid_mappings = standard_skills_extraction_summary["invalid_mappings"]
    skill_taxonomy_records = standard_skills_extraction_summary["skill_taxonomy_records"]
    skill_classifications = standard_skills_extraction_summary["skill_classifications"]


    # =======================================
    # RUN DATABASE CREATION & LOAD SCRIPT
    # =======================================

    print_step("[4/4] Creating and loading demo database...")
    setup_database()

    with pyodbc.connect(
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=localhost\\SQLEXPRESS;"
        "Database=JobPostingsAnalysis_Demo;"
        "Trusted_Connection=yes;"
    ) as connection:
        cursor = connection.cursor()

    
    core_job_postings = fetch_scalar(
        cursor, 
        """SELECT COUNT(*) FROM core.job_postings;"""
    )

    core_companies = fetch_scalar(
        cursor,
        """SELECT COUNT(*) FROM core.companies;"""
    )

    core_locations = fetch_scalar(
        cursor,
        """SELECT COUNT(*) FROM core.locations;"""
    )

    core_skill_mentions = fetch_scalar(
        cursor,
        """SELECT COUNT(*) FROM core.skill_mentions;"""
    )

    core_standardized_skills = fetch_scalar(
        cursor,
        """SELECT COUNT(*) FROM core.standardized_skills;"""
    )

    core_skill_classifications = fetch_scalar(
        cursor,
        """SELECT COUNT(*) FROM core.skill_classifications;"""
    )


    # ==========================================
    # PIPELINE SUMMARY LOGGING
    # ==========================================

    print("\n[OK] Demo setup completed successfully.")

    print(f"\n{50 * '='}")
    print("PIPELINE SUMMARY")
    print(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    print(50 * "=")

    print("\nJob Posting Extraction")
    print("----------------------")
    print(f"Processed job postings : {successful_files} / {total_files}")
    print(f"Rejected files         : {rejected_files}")
    print(f"Skills extracted       : {skills_extracted}")


    print("\n\nSkill Standardization Workbook Extraction")
    print("-----------------------------------------")
    print(f"Valid mappings         : {valid_mappings} / {total_mappings}")
    print(f"Invalid mappings       : {invalid_mappings}")
    print(f"Skill taxonomy records : {skill_taxonomy_records}")
    print(f"Skill classifications  : {skill_classifications}")


    print("\n\nDatabase (Core schema)")
    print("----------------------")
    print(f"Job postings           : {core_job_postings}")
    print(f"Companies              : {core_companies}")
    print(f"Locations              : {core_locations}")
    print(f"Skill mentions         : {core_skill_mentions}")
    print(f"Standardized skills    : {core_standardized_skills}")
    print(f"Skill classifications  : {core_skill_classifications}")




if __name__ == "__main__":
    main()
