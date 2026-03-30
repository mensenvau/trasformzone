# Generated: 20260329_062906
# Model: gemini-2.5-pro
# Tokens: prompt=9641, output=2165, total=21342
# Examples: ResAnalytics_Rent_Roll_x05.xlsx, ResAnalytics_Rent_Roll_x06.xlsx
# GUID: A8BAFAA9-73A6-4BEE-ACDA-12DD3CAAA506 / test_message_id

import re
import pandas as pd
from pathlib import Path

def parse(file_path: str) -> pd.DataFrame:
    """
    Parses raw Excel/CSV rent roll files into a clean pandas DataFrame.

    This function reads a file, extracts header metadata, dynamically locates
    the data table, processes section titles, and applies cleaning and typing
    rules as defined by a configuration.

    Args:
        file_path: The full path to the Excel or CSV file.

    Returns:
        A cleaned pandas DataFrame with a standardized schema.
    """
    
    config = {
        'columns': [
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
        ],
        'unique_identifier': 'Unit'
    }
    final_cols = [c['name'] for c in config['columns']]
    col_types = {c['name']: c['type'] for c in config['columns']}

    def _read_file(path):
        file_suffix = Path(path).suffix.lower()
        if file_suffix in ['.xlsx', '.xls']:
            return pd.read_excel(path, header=None, sheet_name=0)
        elif file_suffix == '.csv':
            try:
                return pd.read_csv(path, header=None, encoding='utf-8')
            except UnicodeDecodeError:
                return pd.read_csv(path, header=None, encoding='latin-1')
        raise ValueError(f"Unsupported file type: {file_suffix}")

    def _extract_metadata(df_head):
        metadata = {
            'As_Of_Date': None, 'Period_Date': None,
            'Property_Name': None, 'Property_ID': None
        }
        for _, row in df_head.iterrows():
            row_str = ' '.join(str(s) for s in row.dropna())
            if not row_str:
                continue

            try:
                if not metadata['Property_Name']:
                    prop_match = re.search(r'^\s*([^()]+?)\s*\(([^)]+)\)', row_str)
                    if prop_match:
                        metadata['Property_Name'] = prop_match.group(1).strip()
                        metadata['Property_ID'] = prop_match.group(2).strip()
                
                if not metadata['As_Of_Date']:
                    as_of_match = re.search(r'As\s*Of\s*=\s*(\d{1,2}/\d{1,2}/\d{4})', row_str, re.IGNORECASE)
                    if as_of_match:
                        metadata['As_Of_Date'] = pd.to_datetime(as_of_match.group(1), errors='coerce', format='%m/%d/%Y')

                if not metadata['Period_Date']:
                    period_match = re.search(r'Month\s*Year\s*=\s*(\d{1,2}/\d{4})', row_str, re.IGNORECASE)
                    if period_match:
                        metadata['Period_Date'] = pd.to_datetime(period_match.group(1), errors='coerce', format='%m/%Y')
            except Exception:
                continue
        
        for k in ['As_Of_Date', 'Period_Date']:
            if pd.notna(metadata[k]):
                metadata[k] = metadata[k].normalize()

        return metadata

    def _find_header_index(df_head):
        header_keywords = ['unit', 'resident', 'market', 'rent', 'balance', 'move in', 'lease']
        best_score, best_index = -1, -1

        for i in range(len(df_head) - 1):
            row1_vals = df_head.iloc[i].dropna().astype(str).str.lower().tolist()
            if len(row1_vals) < 4: continue
            
            score = sum(any(key in val for key in header_keywords) for val in row1_vals)
            
            if score > best_score:
                best_score = score
                best_index = i
        
        if best_index == -1:
            raise ValueError("Could not dynamically find the header row.")
        return best_index

    try:
        raw_df = _read_file(file_path)
    except (FileNotFoundError, ValueError) as e:
        return pd.DataFrame(columns=final_cols)

    df_head = raw_df.head(15)
    metadata = _extract_metadata(df_head)
    
    try:
        header_row_index = _find_header_index(df_head)
    except ValueError:
        return pd.DataFrame(columns=final_cols)

    h1 = df_head.iloc[header_row_index].ffill()
    h2 = df_head.iloc[header_row_index + 1].fillna('')
    combined_header = [f"{c1} {c2}".strip() for c1, c2 in zip(h1, h2)]
    
    df = raw_df.iloc[header_row_index + 2:].copy()
    if df.shape[1] > len(combined_header):
        df = df.iloc[:, :len(combined_header)]
    df.columns = combined_header

    stop_rows = df[df.iloc[:, 0].astype(str).str.contains('Summary Groups', na=False, case=False)]
    if not stop_rows.empty:
        stop_index = stop_rows.index[0]
        df = df.loc[:stop_index - 1]

    is_title = df.iloc[:, 0].notna() & df.iloc[:, 1].isna() & df.iloc[:, 2].isna()
    df['Resident_Status_Type'] = df.iloc[:, 0].where(is_title).ffill()
    df = df[~is_title].copy()

    df.dropna(how='all', inplace=True)
    skip_mask = df.iloc[:, 0].astype(str).str.contains('Total', na=False, case=False)
    df = df[~skip_mask]

    rename_map = {
        'Unit': 'Unit', 'Unit Type': 'Unit_Type', 'Unit Sq Ft': 'Unit_Sq_Ft',
        'Name': 'Resident', 'Market Rent': 'Market_Rent', 'Actual Rent': 'Actual_Rent',
        'Resident Deposit': 'Resident_Deposit', 'Other Deposit': 'Other_Deposit',
        'Move In': 'Move_In', 'Lease Expiration': 'Lease_Expiration',
        'Move Out': 'Move_Out', 'Balance': 'Balance'
    }
    df.rename(columns=rename_map, inplace=True)

    for col, value in metadata.items():
        df[col] = value
        
    for col in final_cols:
        if col not in df.columns:
            df[col] = None
    
    df = df[final_cols]

    if config['unique_identifier'] in df.columns:
        df.dropna(subset=[config['unique_identifier']], inplace=True)
        df = df[df[config['unique_identifier']].astype(str).str.strip() != '']

    for col_name, col_type in col_types.items():
        if col_name in df.columns:
            if col_type == 'string':
                df[col_name] = df[col_name].astype(str).str.strip()
                df[col_name] = df[col_name].replace({'nan': None, 'None': None, '<NA>': None, '': None})
            elif col_type == 'number':
                df[col_name] = pd.to_numeric(df[col_name], errors='coerce')
            elif col_type == 'date':
                df[col_name] = pd.to_datetime(df[col_name], errors='coerce').dt.normalize()

    df.reset_index(drop=True, inplace=True)
    return df