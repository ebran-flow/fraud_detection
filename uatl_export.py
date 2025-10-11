import re
import numpy as np
import pdfplumber
import pandas as pd
from sqlalchemy import table
from helpers import FlowCustomExceptions, FlowInvalidStatementException, clean_numeric_columns, empty_df_thrws_error, extract_files_to_temp, cleanup, get_file_info_from_file_json, invoke_transform, notify_process_status, parse_date_in_string, remove_inessential_columns, remove_dup_in_df, clean_n_insert, set_timeout_signal, set_session, set_country_code_n_status, parse_date_in_series, clean_digits, get_lines_from_pdf_page, trim_dataframe, validate_stmt_format, handle_export_exception
import csv
import gzip
import shutil

# EXPECTED_DT_FORMATS = ['%Y-%m-%d %H:%M:%S']
EXPECTED_DT_FORMATS = ['%d-%m-%y %H:%M %p',
                       '%d-%m-%y %H:%M']

def trim_dataframe(df: pd.DataFrame):
    df.columns = df.columns.str.strip()
    df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df

def perform_basic_cleaning(df):
    df['txn_date'] = parse_date_in_series(df['txn_date'], EXPECTED_DT_FORMATS)
    df['description'] = df['description'].str.replace(r'\n', ' ', regex=True)
    df['description'] = df['description'].str.title()
    df = process_description(df)
    df[['txn_type','user']] = df.apply(extract_txn_details, axis=1, result_type='expand')
    df = clean_numeric_columns(df, ['amount','balance'], False)
    df['amount'] = pd.to_numeric(df['amount'])
    df['amount'] = np.where(df['txn_direction'] == 'Debit', -df['amount'], df['amount'])

    return df

def extract_txn_details(record):
    description = record['description']
    txn_direction = record['txn_direction']
    has_repeating_name = record['has_repeating_name']
    missing_from_msisdn = record['from_msisdn'] == None or pd.isna(record['from_msisdn'])
    missing_to_msisdn = record['to_msisdn'] == None or pd.isna(record['to_msisdn'])

    biz_keywords = [
        'Limited', 'Business', 'Contracting', 'Trading', 'Ltd', 'Telecom', 'Company', 'Investments',
        'Consult', 'Communications', 'Secondary', 'School', 'Suppliers', 'Foods', 'Traders', 'Holdings',
        'Distributors', 'Telecentre', 'Media', 'Advertising', 'Connections', 'Agencies', 'Enterprises',
        'Consults', 'Contractors', 'Agency', 'PlacementsFinance', 'Sons', 'Tech', 'Services',
        'Foundation', 'Uganda', 'Partners', 'Store', 'Group', 'Financial', 'Logistic', 'Brothers',
        'Medical', 'Logistics'
    ]

    two_step_otp_keywords = [
        'Stanbic Superagent' 
    ]

    loan_keywords = [
        'Jumoworld Uganda Limited', 'Loan'
    ]

    biz_pattern = '|'.join(biz_keywords)
    two_step_otp_pattern = '|'.join(two_step_otp_keywords)
    loan_pattern = '|'.join(loan_keywords)

    if "Reversed" in description:
        txn_type = "Transaction Reversal"
        user = "Subscriber"

    elif missing_from_msisdn and missing_to_msisdn:
        return "unknown", "unknown"

    elif "Voice Bundle Business" in description:
        txn_type = "Merchant Payment Single Step"
        user = "Voice Bundle"
    
    elif re.search(loan_pattern, description, re.IGNORECASE) and str(txn_direction).lower() == "debit":
        txn_type = "Loan Repayment"
        user = "Subscriber"

    elif re.search(loan_pattern, description, re.IGNORECASE) and str(txn_direction).lower() == "credit":
        txn_type = "Loan Disbursement"
        user = "Subscriber"
    
    elif re.search(two_step_otp_pattern, description, re.IGNORECASE):
        txn_type = "C2C Two Step OTP Confirm"
        user = "Agent"

    elif "Airtel Money Commissions Disbursement Wallet" in description or "Airtel Money" in description:
        txn_type = "Money transfer from enterprise to registered"
        user = "Unknown"

    elif "Airtime" in description:
        txn_type = "Merchant Payment Other Single Step"
        user = "Airtime"

    elif "Sent Money To" in description and re.search(biz_pattern, description, re.IGNORECASE):
        txn_type = "C2C transfer Within Hierarchy"
        user = "Agent"

    elif "Received From" in description and re.search(biz_pattern, description, re.IGNORECASE):
        txn_type = "C2C transfer Within Hierarchy"
        user = "Agent"
    
    elif has_repeating_name:
        txn_type = "C2C transfer Within Hierarchy"
        user = "Agent"

    elif "Sent Money To" in description:
        txn_type = "Deposit Money"
        user = "Subscriber"

    elif "Received From" in description:
        txn_type = "Withdraw Money"
        user = "Subscriber"

    else:
        txn_type = "unknown"
        user = "unknown"

    return txn_type, user

def has_repeating_names(name_str):
    if pd.isna(name_str):
        return False
    words = name_str.strip().split()
    seen = set()
    for word in words:
        if word in seen:
            return True
        seen.add(word)
    return False

def process_description(df):
    df['from_msisdn'] = None
    df['to_msisdn'] = None
    df['name'] = None
    df['has_repeating_name'] = False

    sent_mask = df['description'].str.contains('Sent Money To', na=False)
    recv_mask = df['description'].str.contains('Received From', na=False)

    df.loc[sent_mask, 'to_msisdn'] = df.loc[sent_mask, 'description'].str.extract(
        r'Sent Money To (\d{9})', expand=False
    ).str.strip()

    df.loc[recv_mask, 'from_msisdn'] = df.loc[recv_mask, 'description'].str.extract(
        r'Received From (\d{9})', expand=False
    ).str.strip()

    df.loc[sent_mask, 'name'] = df.loc[sent_mask, 'description'].str.extract(
        r'Sent Money To \d{9}\s+(.+)', expand=False
    ).str.strip()

    df.loc[recv_mask, 'name'] = df.loc[recv_mask, 'description'].str.extract(
        r'Received From \d{9}\s+(.+)', expand=False
    ).str.strip()

    df['has_repeating_name'] = df['name'].apply(has_repeating_names)

    return df

def clean(txn_df, acc_number, run_id, export_table):
    txn_df = perform_basic_cleaning(txn_df)
    txn_df = txn_df.assign( acc_number=acc_number,
                            export_run_id=run_id, 
                            transform_status='NOT_DONE')
    txn_df = remove_inessential_columns(txn_df, export_table)
    return txn_df

def clean_df(df: pd.DataFrame, db_con, addl_data):
    acc_number = addl_data['acc_number']
    run_id = addl_data['run_id']
    export_table = addl_data['table']

    df = clean(df, acc_number, run_id, export_table)
    df = remove_dup_in_df(df, db_con, export_table)
    return df

def validate_stmt_ownership(acc_number, acc_number_from_statement):
    if(acc_number_from_statement == acc_number): 
        return
    
    FlowCustomExceptions.raise_invalid_statement_ownership(acc_number, acc_number_from_statement, 'Agent line number') 

def is_valid_date(value):
    try:
        parse_date_in_string(str(value).strip(), EXPECTED_DT_FORMATS)
        return True
    except Exception:
        return False

def get_df_from_stmt_without_lines(pages):
    header = ['txn_id', 'txn_date', 'description','status', 'amount', 'txn_direction', 'fee','balance']
    all_rows = []
    for page in pages:
        for table in page.extract_tables():
            all_rows.extend(table)
    valid_rows = [row for row in all_rows if len(row) > 2 and is_valid_date(row[1])]

    final_df = pd.DataFrame(valid_rows, columns=header)
    return final_df

def get_stmt_acc_num_from_csv(df):
    acc_num_pattern = r"^\d{9}$" 

    for i in range(len(df)):
        for j in range(len(df.columns)):
            if str(df.iat[i, j]).strip().lower() == 'mobile number' and re.fullmatch(acc_num_pattern, str(df.iat[i, j + 1]).strip()):
                    return str(df.iat[i, j + 1]).strip()
    return None

def get_stmt_acc_number(page):
    extracted_text = page.extract_text()
    acc_number_pattern = re.compile(r'Mobile Number:.*?(\b\d{9}\b)', re.S)
    acc_number_match = acc_number_pattern.search(extracted_text)
    if acc_number_match:
        acc_number = acc_number_match.group(1)
    else:
        raise FlowInvalidStatementException("Account number not found.")
    return acc_number

def get_df_from_pdf(file_name):
    pdf = pdfplumber.open(file_name)
    pages = pdf.pages
    stmt_acc_number = get_stmt_acc_number(pages[0])
    df = get_df_from_stmt_without_lines(pages)
    return df, stmt_acc_number

def get_df_from_csv(file_name):

    header = ['Transaction ID', 'Transaction Date', 'Description', 'Status',
              'Transaction Amount', 'Credit/Debit', 'Fee', 'Balance']
    
    acc_number = None
    matched_acc_num = False
    data_rows = []
    header_found = False

    with open(file_name, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            row_lower = [str(cell).strip().lower() for cell in row]
            if header_found and len(row) == len(header): 
                data_rows.append(row)

            elif not matched_acc_num and 'mobile number' in row_lower:
                idx = row_lower.index('mobile number')
                if idx + 1 < len(row) and re.fullmatch(r"\d{9}", row[idx + 1].strip()):
                    acc_number = row[idx + 1].strip()
                    matched_acc_num = True

            elif row == header:
                header_found = True 

    if not header_found:
        FlowCustomExceptions.raise_invalid_statement_exception('Unsupported format')

    df = pd.DataFrame(data_rows, columns=[
        'txn_id', 'txn_date', 'description', 'status',
        'amount', 'txn_direction', 'fee', 'balance'
    ])

    return df, acc_number

def get_inner_file_extension(file_name):
    file_extension = file_name.split('.')[-1]
    extracted_file = file_name.replace(f'.{file_extension}','')
    with gzip.open(file_name, 'rb') as f_in:
        with open(extracted_file, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    inner_extension = extracted_file.split('.')[-1]
    return inner_extension, extracted_file

@empty_df_thrws_error
def process_file_and_get_df(object_key, file_json, kyc_acc_number):
    extract_files_to_temp(object_key)

    file = get_file_info_from_file_json(file_json, 'txn_stmt')
    if file is None:
        FlowCustomExceptions.raise_invalid_statement_exception("Transaction Statement is not uploaded")
    
    file_extension = file['file_extension']
    if file_extension == 'pdf':
        df, stmt_acc_number = get_df_from_pdf(file['file_name'])
    elif file_extension == 'csv':
        df, stmt_acc_number = get_df_from_csv(file['file_name'])
    elif file_extension in ['gzip','gz']:
        inner_extension, extracted_file = get_inner_file_extension(file['file_name'])
        if inner_extension == 'pdf':
            df, stmt_acc_number = get_df_from_pdf(extracted_file)
        elif inner_extension == 'csv':
            df, stmt_acc_number = get_df_from_csv(extracted_file)
        else:
            FlowCustomExceptions.raise_invalid_file_type_exception(file_extension, ['pdf','csv'])
    else:
        FlowCustomExceptions.raise_invalid_file_type_exception(file_extension, ['pdf','csv'])
    
    validate_stmt_ownership(kyc_acc_number, stmt_acc_number)
    return df

def export(event, context, engine, df, country_code):
    try:
        run_id = event['run_id'] = f"{event['flow_req_id']}"
        acc_number = event['acc_number'] 
        file_json = event['file_json']
        object_key = event['object_key']
        export_table = 'uatl_cust_acc_stmts'
        event = set_country_code_n_status(event, country_code, 'success', 'export')
        set_timeout_signal(context, 10)

        df = process_file_and_get_df(object_key, file_json, acc_number)
        addl_data = { 'run_id': run_id, 'acc_number': acc_number, 'table': export_table, 'event': event, 'context': context }
        with engine.begin() as db_con:
            df, exp_list = clean_n_insert(df, db_con, addl_data, clean_df)
            notify_process_status(event, context, df, ['lead_id','file_json'], None)
        invoke_transform(event)
    
    except Exception as e:
        handle_export_exception(event, context, df, e)
        
    finally:
        cleanup(engine)
        return event

def main(event, context):
    df, engine, country_code = set_session('UGA', event)
    return export(event, context, engine, df, country_code)

def lambda_handler(event, context):
    return main(event, context)


if __name__ == '__main__':
    LEAD_FILE_BASE_TMPLT = {
        'file_data' : None,
        "file_err" : None
    }

    event = {
        "lender_code" : "FLOW",
        "acc_prvdr_code" : "UATL",
        "run_id" : "759660424",
        "flow_req_id" : "759660424",
        "object_key" : "DATA/UATL/759660424_or.zip",
        "acc_number" : "759660424",
        "file_json" : {
            "desc":"Transaction Statement",
            "file_err":None,
            "multi_file_mail_support":True,
            "files":[
                {
                    "file_data":None,
                    "file_name": "759660424.pdf",
                    "file_err":None,
                    "file_of":"txn_stmt",
                    "file_label":"Transaction Statement",
                    "file_type":"application/pdf"
                }
            ]
        }
    }
    
    main(event,None)