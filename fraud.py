import os
import pdfplumber
from datetime import datetime
import pandas as pd
import zipfile
from helpers import cleanup, connect_to_database_engine


ZIP_FOLDER_PATH = "/home/ebran/Developer/projects/data_score_factors/DATA/archive/UATL/"
EXTRACTED_FOLDER_PATH = "/home/ebran/Developer/projects/data_score_factors/DATA/archive/UATL_extracted/"
FRAUD_DETECTED_PATH = "/home/ebran/Developer/projects/data_score_factors/DATA/archive/UATL.csv"
MULTIPLE_PATH = "/home/ebran/Developer/projects/data_score_factors/DATA/archive/UATL_multiple/"

def parse_pdf_date(date_str):
    """Parse PDF date format like D:20240807103154+03'00' into '2024-08-07 10:31:54'."""
    if not date_str or not date_str.startswith("D:"):
        return date_str
    try:
        return datetime.strptime(date_str[2:16], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return date_str
    
def get_metadata(path):
    result = {}
    with pdfplumber.open(path) as pdf:
        metadata = pdf.metadata or {}
        for key, value in metadata.items():
            if key in ["CreationDate", "ModDate"]:
                value = parse_pdf_date(value)
                metadata[key] = parse_pdf_date(value)

        result = {
                    'title' : metadata.get('Title', 'N/A'),
                    'author' : metadata.get('Author', 'N/A'),
                    'creator' : metadata.get('Creator', 'N/A'),
                    'producer' : metadata.get('Producer', 'N/A'),
                    'created_at': metadata.get('CreationDate', 'N/A'),
                    'modified_at': metadata.get('ModDate', 'N/A'),
                }
    return result  

def get_acc_numbers(db_con):
    query = f"""
        select 
            id,
            acc_number,
            flow_req_id run_id
        from 
            partner_acc_stmt_requests 
        where 
            flow_req_id = '68babf7f23139'
            # acc_number in ('751199483','755925071','746593483','745637223','754143388','752514763','707683843','744252806','740217008','740841442','749506625','749371625','741340315')
            # (lambda_status = 'score_calc_success')
            # and acc_prvdr_code = 'UATL'
            # and extract(year_month from created_at) = '202510'
    """
    return pd.read_sql(query, db_con)

def extract_zip(account):
    pdf_out_path = os.path.join(EXTRACTED_FOLDER_PATH, f"{account['run_id']}.pdf")
    # Skip extraction if file already exists
    if os.path.isfile(pdf_out_path):
        print(f"Extraction already done for {account['run_id']}, skipping.")
        return
    zip_path = ZIP_FOLDER_PATH + account['run_id']
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        file_list = zip_ref.namelist()
        if not file_list:
            print(f"No files found in zip for {account['run_id']}")
            return
        if len(file_list) > 1:
            # Move zip to UATL_multiple if multiple files found
            os.makedirs(MULTIPLE_PATH, exist_ok=True)
            new_zip_path = os.path.join(MULTIPLE_PATH, account['run_id'])
            os.rename(zip_path, new_zip_path)
            print(f"Moved zip with multiple files for {account['run_id']} to {MULTIPLE_PATH}")
            return
        with zip_ref.open(file_list[0]) as source, open(pdf_out_path, 'wb') as target:
            target.write(source.read())

def check_metadata(d, account):
    pdf_path = os.path.join(EXTRACTED_FOLDER_PATH, f"{account['run_id']}.pdf")
    if not os.path.isfile(pdf_path):
        print(f"PDF not found for {account['run_id']}")
        d.append({
            "run_id": account['run_id'],
            "acc_number": account['acc_number'],
            "title": "",
            "author": "",
            "creator": "",
            "producer": "",
            "created_at": "",
            "modified_at": "",
            "error": "PDF not found"
        })
        return d
    try:
        meta_data = get_metadata(pdf_path)
        d.append({
            "run_id": account['run_id'],
            "acc_number": account['acc_number'],
            "title": meta_data.get("title", ""),
            "author": meta_data.get("author", ""),
            "creator": meta_data.get("creator", ""),
            "producer": meta_data.get("producer", ""),
            "created_at": meta_data.get("created_at", ""),
            "modified_at": meta_data.get("modified_at", ""),
            "error": ""
        })
    except Exception as e:
        print(f"Error reading PDF for {account['run_id']}: {e}")
        d.append({
            "run_id": account['run_id'],
            "acc_number": account['acc_number'],
            "title": "",
            "author": "",
            "creator": "",
            "producer": "",
            "created_at": "",
            "modified_at": "",
            "error": str(e)
        })
    return

def main(action='check'):
    d = []
    engine = connect_to_database_engine('LIVE')
    with engine.begin() as db_con:
        accounts = get_acc_numbers(db_con)
    cleanup(engine)

    for index in range(len(accounts)):
        account = accounts.iloc[index]
        print(account)
        if action == 'extract':
            extract_zip(account)
        elif action == 'check':
            check_metadata(d, account)
        
    if action == 'check':
        df = pd.DataFrame(d)
        df.to_csv(FRAUD_DETECTED_PATH, index=False)

if __name__ == '__main__':
    main()