# Generated: 20260329_063852
# Model: gemini-3-flash-preview
# Tokens: prompt=9641, output=1454, total=13409
# Examples: ResAnalytics_Rent_Roll_x05.xlsx, ResAnalytics_Rent_Roll_x06.xlsx
# GUID: A8BAFAA9-73A6-4BEE-ACDA-12DD3CAAA506 / test_message_id

import re
import pandas as pd

def parse(file_path):
    """Parses property rent roll files into a clean DataFrame."""
    if file_path.lower().endswith(('.xlsx', '.xls')):
        df_raw = pd.read_excel(file_path, header=None)
    else:
        try:
            df_raw = pd.read_csv(file_path, header=None, encoding='utf-8')
        except:
            df_raw = pd.read_csv(file_path, header=None, encoding='latin-1')

    prop_name, prop_id, as_of, period = None, None, None, None
    for i in range(min(15, len(df_raw))):
        row_str = ' '.join(df_raw.iloc[i].astype(str).values)
        if not prop_name:
            m = re.search(r'^Rent Roll\s+(.*?)\s*\((.*?)\)', row_str, re.I)
            if not m: m = re.search(r'^(.*?)\s*\((.*?)\)', row_str, re.I)
            if m: prop_name, prop_id = m.group(1).strip(), m.group(2).strip()
        if not as_of:
            m = re.search(r'As\s+Of\s*=\s*([\d/-]+)', row_str, re.I)
            if m: as_of = m.group(1).strip()
        if not period:
            m = re.search(r'Month\s+Year\s*=\s*([\d/-]+)', row_str, re.I)
            if m: period = m.group(1).strip()

    header_idx = -1
    for i in range(min(20, len(df_raw))):
        row_vals = [str(x).lower() for x in df_raw.iloc[i].values]
        if 'unit' in row_vals and 'resident' in row_vals:
            header_idx = i
            break

    data_rows = []
    current_status = None
    if header_idx != -1:
        for i in range(header_idx + 1, len(df_raw)):
            row = df_raw.iloc[i]
            row_vals_str = row.astype(str).tolist()
            
            if any("summary groups" in s.lower() for s in row_vals_str[:3]):
                break
            
            if any(s.strip().lower() in ['total', 'totals', 'subtotal'] for s in row_vals_str):
                continue
            
            non_empty = row.dropna()
            if len(non_empty) == 1 and isinstance(non_empty.iloc[0], str):
                current_status = str(non_empty.iloc[0]).strip()
                continue
            
            if pd.isna(row[0]) or str(row[0]).strip() == "" or "sq ft" in str(row[2]).lower():
                continue
                
            data_rows.append({
                'Unit': row[0],
                'Unit_Type': row[1],
                'Unit_Sq_Ft': row[2],
                'Resident': row[4],
                'Market_Rent': row[5],
                'Actual_Rent': row[6],
                'Resident_Deposit': row[7],
                'Other_Deposit': row[8],
                'Move_In': row[9],
                'Lease_Expiration': row[10],
                'Move_Out': row[11],
                'Balance': row[12],
                'Resident_Status_Type': current_status
            })

    df = pd.DataFrame(data_rows)
    if df.empty:
        df = pd.DataFrame(columns=['Unit', 'Unit_Type', 'Unit_Sq_Ft', 'Resident', 'Market_Rent', 'Actual_Rent', 'Resident_Deposit', 'Other_Deposit', 'Move_In', 'Lease_Expiration', 'Move_Out', 'Balance', 'As_Of_Date', 'Period_Date', 'Property_Name', 'Property_ID', 'Resident_Status_Type'])

    df['As_Of_Date'] = as_of
    df['Period_Date'] = period
    df['Property_Name'] = prop_name
    df['Property_ID'] = prop_id

    mapping = {
        'Unit': 'string', 'Unit_Type': 'string', 'Resident': 'string', 
        'Property_Name': 'string', 'Property_ID': 'string', 'Resident_Status_Type': 'string',
        'Unit_Sq_Ft': 'number', 'Market_Rent': 'number', 'Actual_Rent': 'number', 
        'Resident_Deposit': 'number', 'Other_Deposit': 'number', 'Balance': 'number',
        'Move_In': 'date', 'Lease_Expiration': 'date', 'Move_Out': 'date', 
        'As_Of_Date': 'date', 'Period_Date': 'date'
    }

    for col, dtype in mapping.items():
        if col not in df.columns: df[col] = None
        if dtype == 'number':
            df[col] = pd.to_numeric(df[col], errors='coerce')
        elif dtype == 'date':
            df[col] = pd.to_datetime(df[col], errors='coerce')
        else:
            df[col] = df[col].astype(str).str.strip().replace(['nan', 'NaN', 'None', 'NaT'], None)

    final_cols = [
        'Unit', 'Unit_Type', 'Unit_Sq_Ft', 'Resident', 'Market_Rent', 
        'Actual_Rent', 'Resident_Deposit', 'Other_Deposit', 'Move_In', 
        'Lease_Expiration', 'Move_Out', 'Balance', 'As_Of_Date', 
        'Period_Date', 'Property_Name', 'Property_ID', 'Resident_Status_Type'
    ]
    return df[final_cols].reset_index(drop=True)