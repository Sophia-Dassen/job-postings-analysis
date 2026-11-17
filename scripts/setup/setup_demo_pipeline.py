"""
Run the end-to-end ETL pipeline from a single entry point.

This script orchestrates the complete demo pipeline by executing the following stages:
1. Extract job posting metadata and highlighted skill mentions into CSV files.
2. Verify that the Excel skill standardization workbookand is up-to-date and, if necessary, 
   prompt user to refresh it manually.
3. Extract validated tables from the skill standardization workbook into CSV files.
4. Set up or refresh the demo SQL Server database.

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
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pwinput
import pyodbc
from openpyxl import load_workbook

from scripts.extraction.job_posting_extraction import SKILL_OUTPUT_PATH
from scripts.extraction.skill_standardization_pipeline_extraction import (
    RAW_SKILLS_IMPORT_TABLE,
    SKILL_STANDARD_WORKBOOK_PATH,
    extract_excel_table,
    validate_table_fields,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SQL_DIR = PROJECT_ROOT / "sql"

# SQL Server configuration
SQL_SERVER = os.getenv(
    "SQL_SERVER",
    r"localhost\SQLEXPRESS",
).strip() or r"localhost\SQLEXPRESS"

# SQL Server authentication configuration
SQL_AUTH_MODE = os.getenv("SQL_AUTH_MODE", "trusted").strip().lower()
SQL_USERNAME = os.getenv("SQL_USERNAME", "").strip()

# ODBC driver configuration
SQL_ODBC_DRIVER = os.getenv(
    "SQL_ODBC_DRIVER",
    "ODBC Driver 17 for SQL Server",
).strip() or "ODBC Driver 17 for SQL Server"

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
    print(f"\n=== {message} ===\n")


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


def is_workbook_up_to_date() -> bool:

    while True:
        try:
            # Load workbook
            workbook = load_workbook(
                SKILL_STANDARD_WORKBOOK_PATH,
                data_only=True
            )
            break

        except PermissionError:
            print("Failed to access the workbook.\n"
                  "Please ensure Excel is closed and try again.")
            input("\nPress Enter to continue. ")
            print() 
            continue


    try:
        excel_table = extract_excel_table(
            workbook,
            sheet_name=RAW_SKILLS_IMPORT_TABLE["sheet_name"],
            table_name=RAW_SKILLS_IMPORT_TABLE["table_name"]
        )

        validated_table = validate_table_fields(
            extracted_table=excel_table,
            expected_fields=RAW_SKILLS_IMPORT_TABLE["expected_fields"],
            ignored_helper_fields=RAW_SKILLS_IMPORT_TABLE["ignored_helper_fields"]
        )

    finally:
        workbook.close()

    sort_columns = [
        "job_id",
        "extracted_skill",
        "observed_skill_type"
    ]

    sorted_table = (
        validated_table
        .sort_values(by=sort_columns)
        .reset_index(drop=True)
    )

    exported_skills_csv = pd.read_csv(SKILL_OUTPUT_PATH, header=0)
    
    sorted_csv = (
        exported_skills_csv
        .sort_values(by=sort_columns)
        .reset_index(drop=True)
    )

    return sorted_table.equals(sorted_csv)


def run_workbook_extraction() -> None:

    subprocess.run(
        [sys.executable, str(SKILL_STANDARD_WB_EXTRACTION_SCRIPT)],
        check=True,
        cwd=PROJECT_ROOT,
    )


def validate_sql_credentials(
    username: str,
    password: str
) -> None:

    connection_string = (
        f"Driver={{{SQL_ODBC_DRIVER}}};"
        f"Server={SQL_SERVER};"
        "Database=master;"
        f"UID={username};"
        f"PWD={password};"
    )

    connection = pyodbc.connect(connection_string, timeout=5)
    connection.close()


def get_sql_credentials() -> tuple[str | None, str | None]:

    if SQL_AUTH_MODE == "trusted":
        return None, None

    if SQL_AUTH_MODE == "sql":

        if not SQL_USERNAME:
            raise ValueError(
                "SQL_USERNAME must be configured when using SQL authentication."
            )

        while True:

            password = pwinput.pwinput(
                prompt="Enter your SQL Server password: ",
                mask="*"
            )

            if not password:
                print("Password cannot be empty. Please try again.")
                continue

            try:
                validate_sql_credentials(SQL_USERNAME, password)

            except pyodbc.Error as error:

                error_details = " ".join(str(arg) for arg in error.args)

                if "18456" in error_details or "28000" in error_details:
                    print(
                        "\nAuthentication failed. "
                        "Please check your password and try again.\n"
                    )
                    continue

                raise

            print("\nAuthentication successful.\n")
            
            return SQL_USERNAME, password

    raise ValueError(
        f"Unsupported SQL_AUTH_MODE: {SQL_AUTH_MODE!r}. "
        "Choose 'trusted' or 'sql'."
    )


def setup_or_refresh_database(
    action: str,
    username: str | None = None,
    password: str | None = None,
) -> None:

    script = None

    if action == "setup":
        script = "setup_demo_database.sql"
    elif action == "refresh":
        script = "refresh_demo_database.sql"
    else:
        raise ValueError(
            f"Incorrect action: {action}; must be either 'setup' or 'refresh'"
        )

    env = os.environ.copy()
    env["PROJECT_ROOT"] = PROJECT_ROOT.as_posix()

    command = [
        "sqlcmd",
        "-S", SQL_SERVER,
        "-b",
        "-i", script,
    ]

    if SQL_AUTH_MODE == "trusted":
        command.append("-E")

    elif SQL_AUTH_MODE == "sql":

        if not username or not password:
            raise ValueError(
                "Username and password are required "
                "when using SQL Server Authentication."
            )

        command.extend(["-U", username])
        env["SQLCMDPASSWORD"] = password

    else:
        raise ValueError(
            f"Unsupported SQL authentication mode: {SQL_AUTH_MODE}"
        )

    subprocess.run(
        command,
        check=True,
        cwd=SQL_DIR,
        env=env,
    )


def get_connection_string(
    database: str = "master",
    username: str | None = None,
    password: str | None = None,
) -> str:

    if database not in ["master", "JobPostingsAnalysis_Demo"]:
        raise ValueError(
            f"Unknown database: {database}; database must be either 'master' or 'JobPostingsAnalysis_Demo'"
        )

    connection_string = (
        f"Driver={{{SQL_ODBC_DRIVER}}};"
        f"Server={SQL_SERVER};"
        f"Database={database};"
    )

    if SQL_AUTH_MODE == "trusted":
        connection_string += "Trusted_Connection=yes;"

    elif SQL_AUTH_MODE == "sql":
        connection_string += (
            f"UID={username};"
            f"PWD={password};"
        )

    else:
        raise ValueError(
            f"Unsupported SQL authentication mode: {SQL_AUTH_MODE}"
        )

    return connection_string

    
def fetch_scalar(cursor, query) -> int:
    cursor.execute(query)
    row = cursor.fetchone()

    if row is None:
        raise RuntimeError("Failed to retrieve job posting count.")

    return row[0]


def main() -> None:
    print("========================================")
    print("Job Postings Analysis Demo Pipeline")
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
    
    print_step("[2/4] Verifying that Excel workbook data is up-to-date...")

    if is_workbook_up_to_date():
        print("Workbook is up-to-date.\n"
              "Resuming pipeline setup...")

    else:
        print("Workbook is not up-to-date; manual refresh needed.\n")
        print("Please follow the instructions below:")
        print(f"1/ Open the Excel workbook {SKILL_STANDARD_WORKBOOK_PATH}.")
        print("2/ Refresh all queries and connections to get the latest data.")
        print("3/ Save workbook and close Excel.")

        while True:
            input('\nPress Enter to continue. ')

            print("\nVerifying that Excel workbook data is up-to-date...\n")

            try:
                if is_workbook_up_to_date():
                    print("Workbook is up-to-date.\n"
                          "Resuming pipeline setup...")
                    break

                print(
                    "Workbook is still not up-to-date.\n"
                    "Please refresh all queries and connections, "
                    "save the workbook, and close Excel."
                )

            except PermissionError:
          
                print("Failed to access the workbook.\n"
                      "Please ensure Excel is closed and try again.")
                continue


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
    # RUN DATABASE SETUP OR REFRESH SCRIPT
    # =======================================

    username, password = get_sql_credentials()

    connection_string = get_connection_string("master", username, password)
    
    connection = pyodbc.connect(connection_string)

    try:
        cursor = connection.cursor()
        query = "IF DB_ID('JobPostingsAnalysis_Demo') IS NULL SELECT 0 ELSE SELECT 1;"

        cursor.execute(query)
        row = cursor.fetchone()

        if row is None:
            raise RuntimeError("Failed to retrieve database information.")

        if row[0] == 0:
            action = "setup"
            print_step("[4/4] Creating and loading demo database...")

        elif row[0] == 1:
            action = "refresh"
            print_step("[4/4] Refreshing demo database...")

        else:
            raise ValueError(
                f"Incorrect query result: {row[0]}; must be 0 or 1."
            )

    finally:
        connection.close()

    setup_or_refresh_database(action, username, password)


    connection_string = get_connection_string("JobPostingsAnalysis_Demo", username, password)
    
    connection = pyodbc.connect(connection_string)
    
    try:
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

    finally:
        connection.close()


    # ==========================================
    # PIPELINE SUMMARY LOGGING
    # ==========================================

    print(f"\n{50 * '-'}")
    
    print("\n[OK] Demo pipeline completed successfully.")

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
