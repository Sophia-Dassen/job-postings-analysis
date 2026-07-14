"""
Refreshes all Power Query connections in the Excel
skill standardization pipeline workbook.
"""

from pathlib import Path

import pythoncom
import win32com.client.gencache


def refresh_workbook(WORKBOOK_PATH) -> None:
    """
    Open the workbook, refresh all Power Query connections,
    wait until refresh completes, save, and close.
    """

    pythoncom.CoInitialize()

    excel = None
    workbook = None

    try:
        excel = win32com.client.gencache.EnsureDispatch("Excel.Application")

        excel.Visible = False
        excel.DisplayAlerts = False
        excel.ScreenUpdating = False

        print("Opening Excel workbook...")

        workbook = excel.Workbooks.Open(str(WORKBOOK_PATH))

        print("Refreshing workbook...")

        workbook.RefreshAll()

        excel.CalculateUntilAsyncQueriesDone()

        print("Saving workbook...")

        workbook.Save()

        print("Closing Excel...")

        workbook.Close(SaveChanges=True)

    finally:

        if excel is not None:
            excel.Quit()

        pythoncom.CoUninitialize()

    print("Excel workbook refreshed successfully.")

