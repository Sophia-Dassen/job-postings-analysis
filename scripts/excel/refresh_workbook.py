"""
Refreshes all Power Query connections in the Excel
skill standardization pipeline workbook.
"""

import time
from pathlib import Path

import pythoncom
import pywintypes
import win32com.client


RPC_E_CALL_REJECTED = 0x80010001

def call_with_retry(operation, description, attempts=8, delay=0.5):
    """Retry a COM operation if Excel temporarily rejects the call."""

    for attempt in range(attempts):
        try:
            return operation()

        except pywintypes.com_error as exc:
            hresult = exc.args[0] & 0xFFFFFFFF

            if hresult != RPC_E_CALL_REJECTED or attempt == attempts - 1:
                raise

            wait_seconds = delay * (attempt + 1)

            print(
                f"Excel is busy during {description}. "
                f"Retrying in {wait_seconds:.1f}s "
                f"({attempt + 1}/{attempts - 1})..."
            )
            time.sleep(wait_seconds)


def refresh_workbook(WORKBOOK_PATH) -> None:
    """
    Open the workbook, refresh all Power Query connections,
    wait until refresh completes, save, and close.
    """

    pythoncom.CoInitialize()

    excel = None
    workbook = None
    refresh_succeeded = False

    try:
        # Create a separate Excel instance for this automation.
        excel = win32com.client.DispatchEx("Excel.Application")

        excel.Visible = False
        excel.DisplayAlerts = False
        excel.ScreenUpdating = False

        print("Opening Excel workbook...")

        workbook = call_with_retry(
            lambda: excel.Workbooks.Open(str(WORKBOOK_PATH)),
            "opening the workbook",
        )

        if workbook is None:
            raise RuntimeError("Failed to open the Excel workbook.")

        print("Refreshing workbook...")

        call_with_retry(
            workbook.RefreshAll,
            "starting the workbook refresh",
        )

        call_with_retry(
            excel.CalculateUntilAsyncQueriesDone,
            "waiting for asynchronous queries",
        )

        print("Saving workbook...")

        call_with_retry(
            workbook.Save,
            "saving the workbook",
        )

        refresh_succeeded = True
        print("Excel workbook refreshed successfully.")


    finally:

        # Cleanup must not mask the original refresh error.
        try:
            if workbook is not None:
                call_with_retry(
                    lambda: workbook.Close(
                        SaveChanges=refresh_succeeded
                    ),
                    "closing the workbook",
                )
        except Exception as exc:
            print(f"Warning: Could not close workbook cleanly: {exc}")

        try:
            if excel is not None:
                call_with_retry(
                    excel.Quit,
                    "quitting Excel",
                )
        except Exception as exc:
            print(f"Warning: Could not quit Excel cleanly: {exc}")

        pythoncom.CoUninitialize()
        
if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    WORKBOOK_PATH = (
        PROJECT_ROOT
        / "data"
        / "source"
        / "skill_standardization_pipeline.xlsx"
    )

    print(f"Project root: {PROJECT_ROOT}")
    print(f"Workbook path: {WORKBOOK_PATH}")
    print(f"Workbook exists: {WORKBOOK_PATH.is_file()}")

    if not WORKBOOK_PATH.is_file():
        raise FileNotFoundError(
            f"Workbook not found: {WORKBOOK_PATH}"
        )

    refresh_workbook(WORKBOOK_PATH)

