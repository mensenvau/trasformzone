import re
import numpy as np
import pandas as pd

def parse(file_path):
    # Read the entire sheet without header interpretation to manually parse header info and data
    df_raw_full = pd.read_excel(file_path, header=None, sheet_name=0)

    # --- Extract Header-level Information ---
    property_name = None
    property_id = None
    as_of_date = None
    period_date = None

    # Row 1 (index 1): Property Name and ID (e.g., 'Marin at Harvard (x05)')
    if len(df_raw_full) > 1 and pd.notna(df_raw_full.iloc[1, 0]):
        prop_info = str(df_raw_full.iloc[1, 0])
        match = re.match(r'(.+?)\s*\((x\d+)\)', prop_info)
        if match:
            property_name = match.group(1).strip()
            property_id = match.group(2).strip()

    # Row 2 (index 2): As Of Date (e.g., 'As Of = 03/16/2026')
    if len(df_raw_full) > 2 and pd.notna(df_raw_full.iloc[2, 0]):
        as_of_str = str(df_raw_full.iloc[2, 0])
        match = re.search(r'(\d{2}/\d{2}/\d{4})', as_of_str)
        if match:
            try:
                as_of_date = pd.to_datetime(match.group(1), format='%m/%d/%Y')
            except ValueError:
                as_of_date = pd.NaT # Not a Time (pandas equivalent of NaN for datetime)

    # Row 3 (index 3): Period Date (e.g., 'Month Year = 03/2026')
    if len(df_raw_full) > 3 and pd.notna(df_raw_full.iloc[3, 0]):
        period_str = str(df_raw_full.iloc[3, 0])
        match = re.search(r'(\d{2}/\d{4})', period_str)
        if match:
            # Assume day is 01 for Month/Year format (MM/YYYY)
            try:
                period_date = pd.to_datetime(f"01/{match.group(1)}", format='%d/%m/%Y')
            except ValueError:
                period_date = pd.NaT

    # --- Prepare Data DataFrame ---
    # The actual data rows start from row 6 (0-indexed).
    # The classification titles (e.g., 'Current/Notice/Vacant Residents') are also in these data rows.
    df_data = df_raw_full.iloc[6:].copy()

    # Define the mapping from raw file column index (0-indexed) to YAML column name
    # This mapping also handles dropping the 'Resident' ID column (index 3) and mapping 'Name' to 'Resident'
    raw_col_index_to_yaml_name = {
        0: 'Unit',
        1: 'Unit_Type',
        2: 'Unit_Sq_Ft', # Combines 'Unit' header from row 4 and 'Sq Ft' sub-header from row 5
        3: 'Resident_ID_TEMP_DROP', # This is Resident ID (e.g., t1181860), not in YAML
        4: 'Resident',   # This is Resident Name (e.g., Valerie A Cayo), maps to YAML 'Resident'
        5: 'Market_Rent', # Combines 'Market' header from row 4 and 'Rent' sub-header from row 5
        6: 'Actual_Rent', # Combines 'Actual' header from row 4 and 'Rent' sub-header from row 5
        7: 'Resident_Deposit', # Combines 'Resident' header from row 4 and 'Deposit' sub-header from row 5
        8: 'Other_Deposit', # Combines 'Other' header from row 4 and 'Deposit' sub-header from row 5
        9: 'Move_In',
        10: 'Lease_Expiration', # Combines 'Lease' header from row 4 and 'Expiration' sub-header from row 5
        11: 'Move_Out',
        12: 'Balance'
    }

    # Rename columns based on the mapping and handle columns to drop
    # Create a new list of column names, using mapped names or placeholders for unmapped/unwanted columns
    new_cols = [raw_col_index_to_yaml_name.get(i, f'UNMAPPED_COL_{i}') for i in range(len(df_data.columns))]
    df_data.columns = new_cols

    # Drop columns that were placeholders for columns not needed or unmapped
    df_data = df_data.drop(columns=[col for col in df_data.columns if col.startswith(('UNMAPPED_COL_', 'Resident_ID_TEMP_DROP'))], errors='ignore')

    # --- Apply STOP Condition ---
    # "If you encounter a row where the first few columns contain "Summary Groups", STOP reading any further rows for data."
    # Use the 'Unit' column for this check as it's typically the first data column.
    # We check if the string representation contains "Summary Groups"
    stop_idx = df_data[df_data['Unit'].astype(str).str.contains("Summary Groups", case=False, na=False)].index
    if not stop_idx.empty:
        df_data = df_data.loc[:stop_idx[0]-1] # Slice up to the row before "Summary Groups"

    # --- Apply SKIP Condition ---
    # "Skip any intermediate rows that represent Totals, Subtotals, or where a cell value explicitly says "Total" or "Totals"."
    # Check if 'Unit' column contains 'Total' or 'Totals'
    df_data = df_data[~df_data['Unit'].astype(str).str.contains(r'Total(s)?', case=False, na=False, regex=True)]

    # --- Handle Resident_Status_Type (Classification Category Title) ---
    # Initialize Resident_Status_Type with NaN
    df_data['Resident_Status_Type'] = np.nan

    # Identify classification rows: these have text in 'Unit' column but are missing key data values
    # A classification row typically has text in 'Unit', but numeric/date columns like 'Unit_Sq_Ft', 'Market_Rent', 'Resident' are NaN
    is_classification_row = (
        df_data['Unit'].notna() &
        df_data['Unit_Sq_Ft'].isna() &
        df_data['Resident'].isna() &
        df_data['Market_Rent'].isna()
    )

    # Fill the 'Resident_Status_Type' for identified classification rows with their 'Unit' value
    df_data.loc[is_classification_row, 'Resident_Status_Type'] = df_data.loc[is_classification_row, 'Unit'].astype(str)

    # Forward fill the Resident_Status_Type to all subsequent data rows until the next classification or end of data
    df_data['Resident_Status_Type'] = df_data['Resident_Status_Type'].ffill()

    # Remove the classification title rows from the main DataFrame as they are not data rows
    df_data = df_data[~is_classification_row]

    # --- Apply Global Header Values (Broadcast to all rows) ---
    df_data['Property_Name'] = property_name
    df_data['Property_ID'] = property_id
    df_data['As_Of_Date'] = as_of_date
    df_data['Period_Date'] = period_date

    # Define the final list of columns and their types as per YAML configuration
    final_columns_config = [
        {'name': 'Unit', 'type': 'string'},
        {'name': 'Unit_Type', 'type': 'string'},
        {'name': 'Unit_Sq_Ft', 'type': 'number'},
        {'name': 'Resident', 'type': 'string'},
        {'name': 'Market_Rent', 'type': 'number'},
        {'name': 'Actual_Rent', 'type': 'number'},
        {'name': 'Resident_Deposit', 'type': 'number'},
        {'name': 'Other_Deposit', 'type': 'number'},
        {'name': 'Move_In', 'type': 'date'},
        {'name': 'Lease_Expiration', 'type': 'date'},
        {'name': 'Move_Out', 'type': 'date'},
        {'name': 'Balance', 'type': 'number'},
        {'name': 'As_Of_Date', 'type': 'date'},
        {'name': 'Period_Date', 'type': 'date'},
        {'name': 'Property_Name', 'type': 'string'},
        {'name': 'Property_ID', 'type': 'string'},
        {'name': 'Resident_Status_Type', 'type': 'string'}
    ]
    final_column_names = [col['name'] for col in final_columns_config]
    
    # Reindex the DataFrame to ensure all final columns are present and in the specified order.
    # Missing columns will be added with NaN values.
    df = df_data.reindex(columns=final_column_names)

    # --- Type Conversion ---
    for col_config in final_columns_config:
        col_name = col_config['name']
        col_type = col_config['type']

        if col_name in df.columns: # Ensure column exists before attempting conversion
            if col_type == 'string':
                # Convert to string, then replace 'nan' string (from np.nan) or 'None' string with actual None
                df[col_name] = df[col_name].astype(str).replace({'nan': None, 'None': None})
            elif col_type == 'number':
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            elif col_type == 'date':
                # pd.to_datetime can handle various formats including YYYY-MM-DD HH:MM:SS,
                # and will set NaT for unparseable values.
                df[col_name] = pd.to_datetime(df[col_name], errors='coerce')

    return df