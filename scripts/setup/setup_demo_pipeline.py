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


    # =======================================
    # RUN DATABASE CREATION & LOAD SCRIPT
    # =======================================

    print_step("[4/4] Creating and loading demo database...")
    setup_database()


if __name__ == "__main__":
    main()
