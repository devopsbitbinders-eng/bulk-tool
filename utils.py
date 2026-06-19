import pandas as pd
import io
import re
import json
import time
from datetime import datetime, timezone, timedelta

def get_now_utc():
    """Returns the current time in IST (UTC+5:30) in a format SQLite likes: YYYY-MM-DD HH:MM:SS"""
    return (datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')

def normalize_phone(phone):
    """Normalizes phone number to digits only and adds 91 if 10 digits."""
    if not phone:
        return ""
    
    # Handle float conversion artifact (e.g., "919876543210.0")
    phone_str = str(phone).strip()
    if '.' in phone_str:
        parts = phone_str.split('.')
        if len(parts) == 2 and (parts[1] == '0' or parts[1] == '00' or not parts[1]):
            phone_str = parts[0]
            
    clean = re.sub(r'\D', '', phone_str)
    if len(clean) == 10:
        clean = "91" + clean
    return clean

def extract_phone_numbers(file_content, filename):
    print(f"DEBUG: Processing file: {filename} (Content Size: {len(file_content)} bytes)")
    try:
        if str(filename).lower().endswith('.csv'):
            # Use sep=',' explicitly. sep=None causes Python sniffer to guess random digits as delimiters on single-column files.
            df = pd.read_csv(io.BytesIO(file_content), sep=',', engine='python')
            
            # Check if headers might be missing
            first_row_is_nums = True
            for val in df.columns:
                if not re.match(r'^\+?\d+$', str(val).strip()):
                    first_row_is_nums = False
                    break
            
            if first_row_is_nums:
                print("DEBUG: CSV headers look like data. Re-reading without headers.")
                df = pd.read_csv(io.BytesIO(file_content), header=None, sep=',', engine='python')
                df.columns = [f"col_{i}" for i in range(len(df.columns))]
        elif str(filename).lower().endswith(('.xls', '.xlsx')):
            # First, try reading the first sheet normally (simplest way)
            df = pd.read_excel(io.BytesIO(file_content))
            
            # If we only got 1 column, let's see if other sheets have more
            if len(df.columns) <= 1:
                xl = pd.ExcelFile(io.BytesIO(file_content))
                print(f"DEBUG: Single column found. Checking all sheets: {xl.sheet_names}")
                for sheet in xl.sheet_names:
                    temp_df = pd.read_excel(io.BytesIO(file_content), sheet_name=sheet)
                    if len(temp_df.columns) > len(df.columns):
                        print(f"DEBUG: Sheet '{sheet}' has more columns ({len(temp_df.columns)}). Switching to it.")
                        df = temp_df
        else:
            raise ValueError(f"Unsupported file format: {filename}")
    except Exception as e:
        print(f"DEBUG: Error reading file with primary method: {e}")
        # Final fallback
        df = pd.read_csv(io.BytesIO(file_content), header=None)
        df.columns = [f"col_{i}" for i in range(len(df.columns))]

    # Normalize column names - CRITICAL: Strip any non-visible characters
    df.columns = [re.sub(r'[^a-zA-Z0-9 ]', '', str(c)).strip().lower() for c in df.columns]
    print(f"DEBUG: Final detected columns: {list(df.columns)}")
    
    if not df.empty:
        print("DEBUG: Row 1 Data Sample (Keys):", list(df.iloc[0].to_dict().keys()))
        print("DEBUG: Row 1 Data Sample (Values):", list(df.iloc[0].to_dict().values()))

    phone_col = None
    for col in df.columns:
        if 'phone' in col or 'mobile' in col or 'number' in col:
            phone_col = col
            break
            
    if phone_col is None:
        phone_col = df.columns[0]
        print(f"DEBUG: No obvious phone column. Falling back to: {phone_col}")
    else:
        print(f"DEBUG: Identified phone column: {phone_col}")

    # Filter out rows that are completely empty or have no phone number
    filtered_data = []
    for row in df.to_dict(orient='records'):
        # Check if the row has any non-null values
        if not any(pd.notna(v) and str(v).strip() != '' for v in row.values()):
            continue
            
        # Check if the phone column is totally missing/empty
        phone_val = row.get(phone_col)
        if pd.isna(phone_val) or str(phone_val).strip() == '':
            continue
            
        filtered_data.append(row)
        
    # Deduplicate based on phone number to strictly prevent duplicates
    seen_phones = set()
    deduped_data = []
    for row in filtered_data:
        p_val = normalize_phone(str(row.get(phone_col, "")))
        if p_val and p_val not in seen_phones:
            seen_phones.add(p_val)
            deduped_data.append(row)
            
    data = deduped_data
    print(f"DEBUG: Extracted {len(data)} valid UNIQUE rows after deduplication.")
    return data, phone_col

def substitute_template(template, data_row):
    print(f"DEBUG: Processing template substitution...")
    # Normalize data_row keys to lowercase for easier matching
    normalized_row = {str(k).strip().lower(): v for k, v in data_row.items()}
    print(f"DEBUG: Available keys in row: {list(normalized_row.keys())}")
    
    message = template
    
    # Process {{double braces}}, {single braces}, [square brackets], (parentheses)
    patterns = [
        (r'\{\{(.*?)\}\}', '{{', '}}'),
        (r'\{(.*?)\}', '{', '}'),
        (r'\[(.*?)\]', '[', ']'),
        (r'\((.*?)\)', '(', ')')
    ]
    
    for pattern, prefix, suffix in patterns:
        found = re.findall(pattern, message)
        for p in found:
            key = p.strip().lower()
            if key in normalized_row:
                replacement = str(normalized_row[key])
                if replacement == 'nan' or replacement == 'None':
                    replacement = ""
                
                target = f"{prefix}{p}{suffix}"
                print(f"DEBUG: Substituting placeholder '{target}' with value '{replacement}'")
                message = message.replace(target, replacement)
            else:
                print(f"DEBUG: Placeholder '{p}' not found in row data.")
                
    return message

def sync_to_google_sheet(report_data, sheet_name="messenger"):
    """Syncs campaign results to Google Sheet with formatting and color-coding."""
    if not report_data:
        return False
        
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        from gspread_formatting import (
            format_cell_range, CellFormat, TextFormat, Color, set_column_width
        )
    except ImportError:
        print("DEBUG: gspread or gspread-formatting not installed.")
        return False
        
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
    client = gspread.authorize(creds)
    
    try:
        try:
            sh = client.open(sheet_name)
        except gspread.exceptions.SpreadsheetNotFound:
            sh = client.create(sheet_name)
            
        worksheet = sh.get_worksheet(0)
        
        # 1. Define Professional Column Mapping
        key_map = {
            'phone number': 'Phone Number',
            'phone': 'Phone Number',
            'name': 'Customer Name',
            'delivery status': 'Delivery Status',
            'sent at': 'Sent Timestamp',
            'message': 'Message Sent',
            'status': 'Status'
        }
        
        # 2. Extract All Columns & Rename
        raw_cols = []
        for d in report_data:
            for k in d.keys():
                if k not in raw_cols: raw_cols.append(k)
        
        display_headers = [key_map.get(str(c).lower(), str(c).title()) for c in raw_cols]
        
        # 3. Handle Headers
        existing_values = worksheet.get_all_values()
        if not existing_values:
            worksheet.append_row(display_headers)
            # Format header: Bold
            format_cell_range(worksheet, '1:1', CellFormat(textFormat=TextFormat(bold=True)))
            header_count = 1
        else:
            header_count = 0 # Headers already exist
            
        # 4. Prepare Rows
        rows_to_append = []
        for d in report_data:
            rows_to_append.append([str(d.get(c, "")) for c in raw_cols])
            
        # 5. Append Data
        start_row = len(existing_values) + 1
        if not existing_values: start_row = 2
        
        worksheet.append_rows(rows_to_append)
        end_row = start_row + len(rows_to_append) - 1
        
        # 6. Apply Color Coding (Status Column)
        try:
            status_col_idx = -1
            for i, h in enumerate(display_headers):
                if 'status' in h.lower():
                    status_col_idx = i + 1
                    break
            
            if status_col_idx > 0:
                # Iterate rows to find success/failure
                for i, row in enumerate(rows_to_append):
                    current_row = start_row + i
                    status_val = str(row[status_col_idx - 1]).lower()
                    
                    cell_range = f"R{current_row}C{status_col_idx}"
                    if 'sent' in status_val or 'success' in status_val:
                        format_cell_range(worksheet, cell_range, CellFormat(backgroundColor=Color(0.85, 1, 0.85))) # Light Green
                    elif 'failed' in status_val or 'error' in status_val:
                        format_cell_range(worksheet, cell_range, CellFormat(backgroundColor=Color(1, 0.85, 0.85))) # Light Red
        except Exception as e:
            print(f"DEBUG: Formatting error: {e}")
            
        # 7. Auto-resize columns
        for i in range(len(display_headers)):
            set_column_width(worksheet, str(i+1), 150) # Setting a decent default width
            
        print(f"DEBUG: Sync to '{sheet_name}' successful.")
        return True
        
    except Exception as e:
        print(f"DEBUG: Sync failed: {e}")
        return False

def send_email_report(report_data, to_email, smtp_config):
    """Sends the campaign report via email."""
    if not report_data or not to_email:
        return False
        
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_config.get('user')
        msg['To'] = to_email
        msg['Subject'] = f"WhatsApp Campaign Report"
        
        body = f"Attached is the report for your WhatsApp campaign. \nTotal rows: {len(report_data)}"
        msg.attach(MIMEText(body, 'plain'))
        
        # Create Excel attachment
        df = pd.DataFrame(report_data)
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_buffer.seek(0)
        
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(excel_buffer.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="campaign_report.xlsx"')
        msg.attach(part)
        
        # Send email
        server = smtplib.SMTP(smtp_config.get('host'), smtp_config.get('port'))
        server.starttls()
        server.login(smtp_config.get('user'), smtp_config.get('pass'))
        server.send_message(msg)
        server.quit()
        
        print(f"DEBUG: Email report sent to {to_email}")
        return True
    except Exception as e:
        print(f"DEBUG: Email sending failed: {str(e)}")
        return False
