# Generated: 20260329_064904
# Model: gemini-3.1-pro-preview
# Tokens: prompt=9641, output=2213, total=22328
# Examples: ResAnalytics_Rent_Roll_x05.xlsx, ResAnalytics_Rent_Roll_x06.xlsx
# GUID: A8BAFAA9-73A6-4BEE-ACDA-12DD3CAAA506 / test_message_id

"""Module for parsing rent roll data from Excel/CSV files into a clean pandas DataFrame."""
import re
import pandas as pd

def parse(file_path):
    try:
        raw_df = pd.read_excel(file_path, header=None)
    except Exception:
        try:
            raw_df = pd.read_csv(file_path, header=None, encoding='utf-8')
        except Exception:
            raw_df = pd.read_csv(file_path, header=None, encoding='latin-1')

    as_of_date = None
    period_date = None
    prop_name = None
    prop_id = None

    for i in range(min(15, len(raw_df))):
        for val in raw_df.iloc[i].dropna().astype(str):
            if not as_of_date:
                m1 = re.search(r'As Of\s*=\s*(.+)', val, re.IGNORECASE)
                if m1:
                    as_of_date = m1.group(1).strip()
            if not period_date:
                m2 = re.search(r'Month Year\s*=\s*(.+)', val, re.IGNORECASE)
                if m2:
                    period_date = m2.group(1).strip()
            if not prop_name:
                m3 = re.search(r'^(.*?)\s*\((x\d+)\)', val, re.IGNORECASE)
                if m3:
                    prop_name = m3.group(1).strip()
                    prop_id = m3.group(2).strip()

    header_idx = -1
    col_map = {}
    for i in range(min(20, len(raw_df))):
        row_str = ' '.join(raw_df.iloc[i].dropna().astype(str).str.lower())
        if 'unit' in row_str and ('market' in row_str or 'rent' in row_str or 'resident' in row_str):
            header_idx = i
            row1 = raw_df.iloc[i].fillna('').astype(str).str.strip()
            row2 = raw_df.iloc[i+1].fillna('').astype(str).str.strip() if i+1 < len(raw_df) else pd.Series([''] * len(raw_df.columns))
            
            for col_idx, (c1, c2) in enumerate(zip(row1, row2)):
                c = re.sub(r'[^a-z]', '', (c1 + ' ' + c2).lower())
                if not c:
                    continue
                
                if c == 'unit' and 'Unit' not in col_map:
                    col_map['Unit'] = col_idx
                elif c in ['unittype']:
                    col_map['Unit_Type'] = col_idx
                elif c in ['unitsqft', 'sqft']:
                    col_map['Unit_Sq_Ft'] = col_idx
                elif c == 'unit' and 'Unit_Sq_Ft' not in col_map and 'Unit' in col_map and col_map['Unit'] != col_idx:
                    col_map['Unit_Sq_Ft'] = col_idx
                elif c in ['name', 'residentname']:
                    col_map['Resident'] = col_idx
                elif c == 'resident' and 'Resident' not in col_map:
                    col_map['Resident'] = col_idx
                elif c in ['marketrent', 'market']:
                    col_map['Market_Rent'] = col_idx
                elif c in ['actualrent', 'actual']:
                    col_map['Actual_Rent'] = col_idx
                elif c in ['residentdeposit']:
                    col_map['Resident_Deposit'] = col_idx
                elif c in ['deposit'] and 'Resident_Deposit' not in col_map:
                    col_map['Resident_Deposit'] = col_idx
                elif c in ['otherdeposit', 'other']:
                    col_map['Other_Deposit'] = col_idx
                elif c in ['movein']:
                    col_map['Move_In'] = col_idx
                elif c in ['leaseexpiration', 'lease']:
                    col_map['Lease_Expiration'] = col_idx
                elif c in ['moveout']:
                    col_map['Move_Out'] = col_idx
                elif c in ['balance']:
                    col_map['Balance'] = col_idx
            break
            
    parsed_data = []
    current_status = None
    start_row = header_idx + 2 if header_idx != -1 else 0
    
    for i in range(start_row, len(raw_df)):
        row_vals = raw_df.iloc[i].fillna('').astype(str).str.strip()
        
        if any('summary groups' in v.lower() for v in row_vals.iloc[:3]):
            break
            
        if any(re.search(r'\btotals?\b|\bsubtotals?\b', v, re.IGNORECASE) for v in row_vals):
            continue
            
        if all(val == '' for val in row_vals):
            continue
            
        non_empty_count = sum(1 for v in row_vals if v)
        if row_vals.iloc[0] and non_empty_count <= 2 and 'Unit' in col_map:
            current_status = row_vals.iloc[0]
            continue
            
        if 'Unit' not in col_map or not row_vals.iloc[col_map['Unit']]:
            continue
            
        unit_val = row_vals.iloc[col_map['Unit']]
        
        record = {
            'Unit': unit_val,
            'Unit_Type': row_vals.iloc[col_map['Unit_Type']] if 'Unit_Type' in col_map else None,
            'Unit_Sq_Ft': row_vals.iloc[col_map['Unit_Sq_Ft']] if 'Unit_Sq_Ft' in col_map else None,
            'Resident': row_vals.iloc[col_map['Resident']] if 'Resident' in col_map else None,
            'Market_Rent': row_vals.iloc[col_map['Market_Rent']] if 'Market_Rent' in col_map else None,
            'Actual_Rent': row_vals.iloc[col_map['Actual_Rent']] if 'Actual_Rent' in col_map else None,
            'Resident_Deposit': row_vals.iloc[col_map['Resident_Deposit']] if 'Resident_Deposit' in col_map else None,
            'Other_Deposit': row_vals.iloc[col_map['Other_Deposit']] if 'Other_Deposit' in col_map else None,
            'Move_In': row_vals.iloc[col_map['Move_In']] if 'Move_In' in col_map else None,
            'Lease_Expiration': row_vals.iloc[col_map['Lease_Expiration']] if 'Lease_Expiration' in col_map else None,
            'Move_Out': row_vals.iloc[col_map['Move_Out']] if 'Move_Out' in col_map else None,
            'Balance': row_vals.iloc[col_map['Balance']] if 'Balance' in col_map else None,
            'As_Of_Date': as_of_date,
            'Period_Date': period_date,
            'Property_Name': prop_name,
            'Property_ID': prop_id,
            'Resident_Status_Type': current_status
        }
        parsed_data.append(record)

    target_cols = [
        'Unit', 'Unit_Type', 'Unit_Sq_Ft', 'Resident', 'Market_Rent', 'Actual_Rent', 
        'Resident_Deposit', 'Other_Deposit', 'Move_In', 'Lease_Expiration', 'Move_Out', 
        'Balance', 'As_Of_Date', 'Period_Date', 'Property_Name', 'Property_ID', 
        'Resident_Status_Type'
    ]
    
    df = pd.DataFrame(parsed_data, columns=target_cols)
    
    str_cols = ['Unit', 'Unit_Type', 'Resident', 'Property_Name', 'Property_ID', 'Resident_Status_Type']
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip().replace({'nan': None, 'None': None, '<NA>': None, '': None})
        
    num_cols = ['Unit_Sq_Ft', 'Market_Rent', 'Actual_Rent', 'Resident_Deposit', 'Other_Deposit', 'Balance']
    for col in num_cols:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(r'[$,]', '', regex=True)
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    date_cols = ['Move_In', 'Lease_Expiration', 'Move_Out', 'As_Of_Date', 'Period_Date']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    df = df.dropna(subset=['Unit']).reset_index(drop=True)
    return df