import re
import numpy as np
import pandas as pd

def parse(file_path):
    xl = pd.ExcelFile(file_path, engine='openpyxl')
    sheet = xl.sheet_names[0]
    raw = pd.read_excel(file_path, sheet_name=sheet, header=None, engine='openpyxl')
    
    property_name = None
    property_id = None
    as_of_date = None
    period_date = None
    
    for i in range(min(5, len(raw))):
        row_str = ' '.join([str(v) for v in raw.iloc[i].values if pd.notna(v)])
        
        match_prop = re.search(r'^(.+?)\s*\((\w+)\)', row_str)
        if match_prop and property_name is None:
            property_name = match_prop.group(1).strip()
            property_id = match_prop.group(2).strip()
        
        match_asof = re.search(r'As\s*Of\s*=?\s*(\d{1,2}/\d{1,2}/\d{4})', row_str)
        if match_asof:
            as_of_date = pd.to_datetime(match_asof.group(1), format='%m/%d/%Y', errors='coerce')
        
        match_period = re.search(r'Month\s*Year\s*=?\s*(\d{1,2}/\d{4})', row_str)
        if match_period:
            period_date = pd.to_datetime(match_period.group(1), format='%m/%Y', errors='coerce')
    
    header_row = None
    for i in range(min(10, len(raw))):
        row_vals = [str(v).strip().lower() for v in raw.iloc[i].values if pd.notna(v)]
        if 'unit' in row_vals and any('rent' in v for v in row_vals):
            header_row = i
            break
    
    if header_row is None:
        header_row = 0
    
    df = pd.read_excel(file_path, sheet_name=sheet, header=header_row, engine='openpyxl')
    df.columns = df.columns.astype(str).str.strip()
    
    column_mapping = {
        'Unit': 'Unit',
        'Unit Type': 'Unit_Type',
        'Unit Sq Ft': 'Unit_Sq_Ft',
        'Resident': 'Resident',
        'Market Rent': 'Market_Rent',
        'Actual Rent': 'Actual_Rent',
        'Resident Deposit': 'Resident_Deposit',
        'Other Deposit': 'Other_Deposit',
        'Move In': 'Move_In',
        'Lease Expiration': 'Lease_Expiration',
        'Move Out': 'Move_Out',
        'Balance': 'Balance',
    }
    
    df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
    
    stop_mask = df.apply(lambda row: any('summary groups' in str(v).lower() for v in row.values if pd.notna(v)), axis=1)
    if stop_mask.any():
        stop_idx = stop_mask.idxmax()
        df = df.loc[:stop_idx - 1]
    
    skip_mask = df.apply(lambda row: any(str(v).strip().lower() in ('total', 'totals', 'subtotal') for v in row.values if pd.notna(v)), axis=1)
    df = df[~skip_mask]
    
    resident_status = None
    status_list = []
    for _, row in df.iterrows():
        non_null_count = row.notna().sum()
        first_val = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
        if non_null_count <= 2 and first_val and not first_val.replace('.', '').isdigit():
            resident_status = first_val
            status_list.append(None)
        else:
            status_list.append(resident_status)
    
    df['Resident_Status_Type'] = status_list
    df = df[df['Resident_Status_Type'].notna()]
    
    if 'Unit' in df.columns:
        df = df[df['Unit'].notna() & (df['Unit'].astype(str).str.strip() != '')]
    
    df['Property_Name'] = property_name
    df['Property_ID'] = property_id
    df['As_Of_Date'] = as_of_date
    df['Period_Date'] = period_date
    
    date_cols = ['Move_In', 'Lease_Expiration', 'Move_Out', 'As_Of_Date', 'Period_Date']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    
    numeric_cols = ['Unit_Sq_Ft', 'Market_Rent', 'Actual_Rent', 'Resident_Deposit', 'Other_Deposit', 'Balance']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    all_columns = ['Unit', 'Unit_Type', 'Unit_Sq_Ft', 'Resident', 'Market_Rent', 'Actual_Rent', 'Resident_Deposit', 'Other_Deposit', 'Move_In', 'Lease_Expiration', 'Move_Out', 'Balance', 'As_Of_Date', 'Period_Date', 'Property_Name', 'Property_ID', 'Resident_Status_Type']
    for col in all_columns:
        if col not in df.columns:
            df[col] = None
    
    return df[all_columns].reset_index(drop=True)
