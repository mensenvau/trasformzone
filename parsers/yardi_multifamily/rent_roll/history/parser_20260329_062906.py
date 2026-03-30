import re
import pandas as pd
from datetime import datetime


def parse(file_path: str) -> pd.DataFrame:
    """
    Parses a rent roll Excel file into a clean pandas DataFrame.

    This function handles metadata extraction from the header, dynamic
    header detection, multi-level header merging, section title parsing,
    and data cleaning according to predefined rules.

    Args:
        file_path (str): The full path to the Excel file.

    Returns:
        pd.DataFrame: A cleaned and structured DataFrame with data
                      conforming to the specified schema.
    """
    try:
        # Using a context manager for file handling is good practice
        with open(file_path, 'rb') as f:
            df_raw = pd.read_excel(f, header=None, sheet_name=0)
    except FileNotFoundError:
        return pd.DataFrame()
    except Exception:
        # Fallback for other file reading issues
        return pd.DataFrame()

    # --- 1. Metadata Extraction ---
    property_name, property_id, as_of_date, period_date = None, None, None, None
    header_text_blob = df_raw.head(10).to_string()

    # Property Name and ID from a specific row format (e.g., 'Palm Bay Club (x28)')
    for i in range(min(5, len(df_raw))):
        cell_val = str(df_raw.iloc[i, 0])
        prop_match = re.search(r'^(.*?)\s*\((.*?)\)', cell_val, re.IGNORECASE)
        if prop_match:
            property_name = prop_match.group(1).strip()
            property_id = prop_match.group(2).strip()
            break

    # As Of Date (e.g., 'As Of = 03/09/2026')
    as_of_match = re.search(r'As\s*Of\s*[=:]\s*(\d{1,2}/\d{1,2}/\d{4})', header_text_blob, re.IGNORECASE)
    if as_of_match:
        try:
            as_of_date = pd.to_datetime(as_of_match.group(1), format='%m/%d/%Y', errors='coerce')
        except Exception:
            as_of_date = None

    # Period Date (e.g., 'Month Year = 03/2026')
    period_match = re.search(r'Month\s*Year\s*[=:]\s*(\d{1,2}/\d{4})', header_text_blob, re.IGNORECASE)
    if period_match:
        try:
            period_date = pd.to_datetime(period_match.group(1), format='%m/%Y', errors='coerce')
        except Exception:
            period_date = None

    # --- 2. Dynamic Header Detection ---
    header_row_index = -1
    expected_headers = ['unit', 'resident', 'market', 'actual', 'rent', 'balance']
    for i, row in df_raw.head(15).iterrows():
        row_str = ' '.join(str(s).lower() for s in row if pd.notna(s))
        if sum(h in row_str for h in expected_headers) >= 4:
            header_row_index = i
            break

    if header_row_index == -1:
        return pd.DataFrame()

    # --- 3. Data Loading and Header Combination ---
    df = pd.read_excel(file_path, header=[header_row_index, header_row_index + 1])

    def combine_columns(col):
        parts = [str(c) for c in col if 'Unnamed:' not in str(c)]
        return ' '.join(parts).strip()

    df.columns = [combine_columns(col) for col in df.columns]

    # --- 4. Data Cleaning & Structuring ---
    # STOP condition: "Summary Groups"
    stop_indices = df[df.iloc[:, 0].astype(str).str.contains("Summary Groups", na=False)].index
    if not stop_indices.empty:
        df = df.loc[:stop_indices.min() - 1]

    # Handle Section Titles (Resident_Status_Type)
    is_title_row = (df.isnull().sum(axis=1) >= df.shape[1] - 3) & (df.iloc[:, 0].notna())
    df['Resident_Status_Type'] = df.where(is_title_row).iloc[:, 0]
    df['Resident_Status_Type'] = df['Resident_Status_Type'].ffill()

    # SKIP condition: Filter out title rows and total rows
    df = df[~is_title_row].copy()
    df = df[~df.iloc[:, 0].astype(str).str.contains('Total', case=False, na=False)]
    df.dropna(how='all', inplace=True)

    # --- 5. Column Mapping & Final Schema ---
    rename_map = {
        'Unit': 'Unit',
        'Unit Type': 'Unit_Type',
        'Unit Sq Ft': 'Unit_Sq_Ft',
        'Name': 'Resident',
        'Market Rent': 'Market_Rent',
        'Actual Rent': 'Actual_Rent',
        'Resident Deposit': 'Resident_Deposit',
        'Other Deposit': 'Other_Deposit',
        'Move In': 'Move_In',
        'Lease Expiration': 'Lease_Expiration',
        'Move Out': 'Move_Out',
        'Balance': 'Balance',
    }
    df.rename(columns=rename_map, inplace=True)

    df['As_Of_Date'] = as_of_date
    df['Period_Date'] = period_date
    df['Property_Name'] = property_name
    df['Property_ID'] = property_id

    final_columns_config = {
        'Unit': 'string', 'Unit_Type': 'string', 'Unit_Sq_Ft': 'number',
        'Resident': 'string', 'Market_Rent': 'number', 'Actual_Rent': 'number',
        'Resident_Deposit': 'number', 'Other_Deposit': 'number', 'Move_In': 'date',
        'Lease_Expiration': 'date', 'Move_Out': 'date', 'Balance': 'number',
        'As_Of_Date': 'date', 'Period_Date': 'date', 'Property_Name': 'string',
        'Property_ID': 'string', 'Resident_Status_Type': 'string'
    }
    final_columns_order = list(final_columns_config.keys())

    for col in final_columns_order:
        if col not in df.columns:
            df[col] = None

    df = df[final_columns_order]
    df.dropna(subset=['Unit'], inplace=True)

    # --- 6. Type Casting & Formatting ---
    for col, col_type in final_columns_config.items():
        if col not in df.columns or df[col].isnull().all():
            continue
        try:
            if col_type == 'string':
                df[col] = df[col].astype(str).str.strip().replace('nan', None).replace('None', None)
            elif col_type == 'number':
                df[col] = pd.to_numeric(df[col], errors='coerce')
            elif col_type == 'date':
                df[col] = pd.to_datetime(df[col], errors='coerce')
        except Exception:
            df[col] = None

    df.reset_index(drop=True, inplace=True)

    return df