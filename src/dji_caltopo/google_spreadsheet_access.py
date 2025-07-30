from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
import datetime
import logging

logger = logging.getLogger("google_spreadsheet_access")
load_dotenv()
SERVICE_ACCOUNT_KEY_FILE = os.getenv("SERVICE_ACCOUNT_KEY_FILE")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
WORKSHEET_NAME = os.getenv("WORKSHEET_NAME", 'Form Responses 1')

def authenticate_google_sheets(key_file):
    try:
        scope = ['https://www.googleapis.com/auth/spreadsheets',
                 'https://www.googleapis.com/auth/drive']

        if not os.path.exists(key_file):
            print(f"Error: Service account key file not found at '{key_file}'")
            return None

        creds = ServiceAccountCredentials.from_json_keyfile_name(key_file, scope)
        client = gspread.authorize(creds)
        #print("Authentication successful!")
        return client
    except Exception as e:
        print(f"Authentication failed: {e}")
        return None

def open_spreadsheet_and_worksheet(client, spreadsheet_id, worksheet_name):
    if not client:
        return None, None
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        #print(f"Spreadsheet '{spreadsheet_id}' opened successfully.")

        worksheet = spreadsheet.worksheet(worksheet_name)
        logger.info(f"Worksheet '{worksheet_name}' selected successfully.")
        #print(f"Worksheet '{worksheet_name}' selected successfully.")
        return spreadsheet, worksheet
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Error: Spreadsheet with ID '{spreadsheet_id}' not found.")
        return None, None
    except gspread.exceptions.WorksheetNotFound:
        print(f"Error: Worksheet '{worksheet_name}' not found in '{spreadsheet_id}'.")
        return None, None
    except Exception as e:
        print(f"Error opening spreadsheet or worksheet: {e}")
        return None, None

def read_data(worksheet):
    if not worksheet:
        return []
    try:
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        print(f"Error reading data: {e}")
        return []

def write_data(worksheet):
    if not worksheet:
        return

    print("Attempting to Write Data to Spreadsheet...")
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_row_data = [timestamp, "New Python Entry", "Value C", "User Name"]
        worksheet.append_row(new_row_data)
        print(f"Appended new row: {new_row_data}")
    except Exception as e:
        print(f"Error writing data: {e}")

def delete_row_from_sheet(worksheet, row_number_to_delete):
    if not worksheet:
        return False
    
    if not isinstance(row_number_to_delete, int) or row_number_to_delete < 1:
        print(f"Invalid row number: {row_number_to_delete}. Must be a positive integer.")
        return False

    print(f"Attempting to Delete Row {row_number_to_delete}...")
    try:
        worksheet.delete_rows(row_number_to_delete)
        print(f"Successfully deleted row {row_number_to_delete}.")
        return True
    except gspread.exceptions.APIError as e:
        print(f"Google Sheets API Error deleting row {row_number_to_delete}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while deleting row {row_number_to_delete}: {e}")
        return False
    

def get_worksheet_data(key_file, spreadsheet_id, worksheet_name):
    client = authenticate_google_sheets(key_file)
    if client:
        _, worksheet = open_spreadsheet_and_worksheet(client, spreadsheet_id, worksheet_name)
        if worksheet:
            return worksheet    
    return None

def worksheet_to_dataframe(worksheet):

    #worksheet = get_worksheet_data(key_file, spreadsheet_id, worksheet_name)
    if worksheet:
            data = read_data(worksheet)
            if data:
                df = pd.DataFrame(data)
                return df
    return pd.DataFrame()

   

def find_expired_rows(df):
    if df.empty:
        print("DataFrame is empty. No expired rows to find.")
        return []

    if 'Timestamp' not in df.columns or 'Select service duration' not in df.columns:
        print("Required columns 'Timestamp' or 'Select service duration' not found in DataFrame.")
        return []

    try:
        # Convert 'Timestamp' column to datetime objects
        df['Timestamp_dt'] = pd.to_datetime(df['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce')

        # Define a mapping for duration strings to timedelta objects
        duration_map = {
            '1 second': pd.Timedelta(seconds=1), # Added '1 second' option
            '1 day': pd.Timedelta(days=1),
            '1 week': pd.Timedelta(weeks=1),
            '30 days': pd.Timedelta(days=30)
        }

        # Convert 'Select service duration' to timedelta objects
        # Use .get() with a default to handle potential missing keys gracefully
        df['Duration_td'] = df['Select service duration'].apply(lambda x: duration_map.get(x, pd.Timedelta(0)))

        # Calculate expiration time
        df['Expiration_Time'] = df['Timestamp_dt'] + df['Duration_td']

        # Get current time
        current_time = datetime.datetime.now()

        # Find rows where current time is past the expiration time
        expired_rows = df[current_time > df['Expiration_Time']]

        # Return the original DataFrame indices of the expired rows
        # Add 2 to the DataFrame index to get the 1-indexed Google Sheet row number
        # (assuming row 1 is headers, and DataFrame index 0 is sheet row 2)
        sheet_row_numbers = (expired_rows.index + 2).tolist()
        
        print(f"Found {len(sheet_row_numbers)} expired rows.")
        return sheet_row_numbers
    
    except Exception as e:
        print(f"Error finding expired rows: {e}")
        return []
    

# New function to remove expired rows safely
def remove_expired_rows(df, worksheet):
    expired_rows_to_delete = find_expired_rows(df)
    if not expired_rows_to_delete:
        print("No expired rows to delete.")
        return False

    # Sort row numbers in descending order to avoid index shifting issues
    expired_rows_to_delete.sort(reverse=True)
    print(f"Attempting to delete {len(expired_rows_to_delete)} expired rows.")

    for row_number in expired_rows_to_delete:
        if delete_row_from_sheet(worksheet, row_number):
            pass # print handled by delete_row_from_sheet
        else:
            print(f"Failed to delete row {row_number}.")
    return True

def get_worksheet_data_after_filtering(key_file, spreadsheet_id, worksheet_name):
    worksheet = get_worksheet_data(key_file, spreadsheet_id, worksheet_name)
    df = worksheet_to_dataframe(worksheet)
    if remove_expired_rows(df, worksheet):
        df = worksheet_to_dataframe(worksheet)
    return df
