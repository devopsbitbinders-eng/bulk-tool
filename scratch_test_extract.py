import pandas as pd
import io
import re

def normalize_phone(phone):
    if not phone:
        return ""
    phone_str = str(phone).strip()
    if '.' in phone_str:
        parts = phone_str.split('.')
        if len(parts) == 2 and (parts[1] == '0' or parts[1] == '00' or not parts[1]):
            phone_str = parts[0]
            
    clean = re.sub(r'\D', '', phone_str)
    if len(clean) == 10:
        clean = "91" + clean
    return clean

def test_extract():
    with open("last_uploaded.csv", "rb") as f:
        file_content = f.read()

    # Emulate utils.py extract_phone_numbers
    df = pd.read_csv(io.BytesIO(file_content), sep=',', engine='python')
    print("Initial rows:", len(df))
    
    first_row_is_nums = True
    for val in df.columns:
        if not re.match(r'^\+?\d+$', str(val).strip()):
            first_row_is_nums = False
            break
            
    if first_row_is_nums:
        df = pd.read_csv(io.BytesIO(file_content), header=None, sep=',', engine='python')
        df.columns = [f"col_{i}" for i in range(len(df.columns))]
        print("Re-read without headers. Rows:", len(df))

    df.columns = [re.sub(r'[^a-zA-Z0-9 ]', '', str(c)).strip().lower() for c in df.columns]

    phone_col = None
    for col in df.columns:
        if 'phone' in col or 'mobile' in col or 'number' in col:
            phone_col = col
            break
            
    if phone_col is None:
        phone_col = df.columns[0]
        
    print("Phone Col:", phone_col)

    filtered_data = []
    empty_rows = 0
    empty_phone_cells = 0
    for row in df.to_dict(orient='records'):
        if not any(pd.notna(v) and str(v).strip() != '' for v in row.values()):
            empty_rows += 1
            continue
            
        phone_val = row.get(phone_col)
        if pd.isna(phone_val) or str(phone_val).strip() == '':
            empty_phone_cells += 1
            continue
            
        filtered_data.append(row)
        
    print(f"Empty rows removed: {empty_rows}")
    print(f"Empty phone cells removed: {empty_phone_cells}")
    print("After filter step 1:", len(filtered_data))

    seen_phones = set()
    deduped_data = []
    duplicates = 0
    invalid_phones = 0
    for row in filtered_data:
        p_val = normalize_phone(str(row.get(phone_col, "")))
        if p_val:
            if p_val not in seen_phones:
                seen_phones.add(p_val)
                deduped_data.append(row)
            else:
                duplicates += 1
        else:
            invalid_phones += 1
            
    print(f"Exact duplicates removed: {duplicates}")
    print(f"Invalid phones (0 digits) removed: {invalid_phones}")
    print("Final rows:", len(deduped_data))

test_extract()
