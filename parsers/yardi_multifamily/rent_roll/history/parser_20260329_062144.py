import re
import pandas as pd
import numpy as np

def parse(file_path):
    """
    Reads and parses a rent roll Excel file into a pandas DataFrame.

    Args:
        file_path (str): The path to the Excel file.

    Returns:
        pandas.DataFrame: A DataFrame containing the parsed data.
    """
    try:
        raw_df = pd.read_excel(file_path, header=None, sheet_name=0)
    except FileNotFoundError:
        return pd.DataFrame()

    # --- Header Parsing ---
    property_name, property_id = None, None
    as_of_date, period_date = pd.NaT, pd.NaT

    # Property Name and ID from Row 1
    prop_string = str(raw_df.iloc[1, 0])
    match = re.match(r'^(.*?)\s*\((.*?)\)$', prop_string)
    if match:
        property_name = match.group(1).strip()
        property_id = match.group(2).strip()
    else:
        property_name = prop_string.strip()

    # As_Of_Date from Row 2
    try:
        as_of_date_str = str(raw_df.iloc[2, 0]).split('=')[-1].strip()
        as_of_date = pd.to_datetime(as_of_date_str, format='%m/%d/%Y', errors='coerce')
    except (IndexError, ValueError):
        pass

    # Period_Date from Row 3
    try:
        period_date_str = str(raw_df.iloc[3, 0]).split('=')[-1].strip()
        if '/' in period_date_str:
            month, year = period_date_str.split('/')
            formatted_date_str = f"{month}/01/{year}"
            period_date = pd.to_datetime(formatted_date_str, format='%m/%d/%Y', errors='coerce')
    except (IndexError, ValueError):
        pass

    # --- Data Body Parsing ---
    data_rows = []
    current_status_type = None
    
    # Find the starting row of the data table headers
    try:
        header_start_index = raw_df[raw_df[0] == 'Unit'].index[0]
        data_start_index = header_start_index + 2  # Data starts 2 rows after the first header line
    except IndexError:
        return pd.DataFrame() # No 'Unit' header found

    for row in raw_df.iloc[data_start_index:].itertuples(index=False):
        row_list = list(row)
        first_val_str = str(row_list[0]).strip()

        # STOP condition
        if 'Summary Groups' in first_val_str:
            break

        # SKIP condition for totals
        if first_val_str.lower().startswith('total'):
            continue
        
        # Check for empty rows
        if pd.isna(row_list[0]):
            continue

        # Check for Resident_Status_Type (category title) row
        # These rows have text in the first column and are mostly empty otherwise
        if pd.notna(row_list[0]) and pd.isna(row_list[1]) and pd.isna(row_list[2]):
            current_status_type = first_val_str
            continue

        # Process as a data row
        record = {
            'Unit': row_list[0],
            'Unit_Type': row_list[1],
            'Unit_Sq_Ft': row_list[2],
            'Resident': row_list[4], # Column 3 is a resident ID, Column 4 is the name
            'Market_Rent': row_list[5],
            'Actual_Rent': row_list[6],
            'Resident_Deposit': row_list[7],
            'Other_Deposit': row_list[8],
            'Move_In': row_list[9],
            'Lease_Expiration': row_list[10],
            'Move_Out': row_list[11],
            'Balance': row_list[12],
            'Resident_Status_Type': current_status_type
        }
        data_rows.append(record)

    if not data_rows:
        return pd.DataFrame()

    df = pd.DataFrame(data_rows)

    # --- Add Header Data and Clean ---
    df['As_Of_Date'] = as_of_date
    df['Period_Date'] = period_date
    df['Property_Name'] = property_name
    df['Property_ID'] = property_id

    # --- Type Conversion ---
    numeric_cols = [
        'Unit_Sq_Ft', 'Market_Rent', 'Actual_Rent', 'Resident_Deposit',
        'Other_Deposit', 'Balance'
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    date_cols = ['Move_In', 'Lease_Expiration', 'Move_Out', 'As_Of_Date', 'Period_Date']
    for col in date_cols:
        if col in df.columns: # Header dates might not exist
            df[col] = pd.to_datetime(df[col], errors='coerce')

    string_cols = [
        'Unit', 'Unit_Type', 'Resident', 'Property_Name', 'Property_ID', 'Resident_Status_Type'
    ]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).replace('nan', np.nan)
    
    # --- Finalize DataFrame Structure ---
    final_columns = [
        'Unit', 'Unit_Type', 'Unit_Sq_Ft', 'Resident', 'Market_Rent',
        'Actual_Rent', 'Resident_Deposit', 'Other_Deposit', 'Move_In',
        'Lease_Expiration', 'Move_Out', 'Balance', 'As_Of_Date',
        'Period_Date', 'Property_Name', 'Property_ID', 'Resident_Status_Type'
    ]

    for col in final_columns:
        if col not in df.columns:
            df[col] = np.nan

    return df[final_columns]