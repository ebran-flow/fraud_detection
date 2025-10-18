#!/usr/bin/env python3
"""
Export FATAL analysis with loans data

Tabs:
- FATAL_filtered: All FATAL UATL statements
- loans_raw: All loans for FATAL customers (with statement RM name)
- analysis_raw: Aggregated by cust_id with fraud and loan metrics
- business_impact: Payment performance and current risk
- Statement_Formats: Analysis of statement formats by provider
- RM_Submitted: RM who submitted fraud statements
- CS_Analysis: CS who applied for loans
- os_vs_revenue: Outstanding vs Revenue analysis
- monthly_trends: Fraud submissions by month
- exposure_utilization: Exposure by exact loan amounts

Output: docs/analysis/fatal_analysis_report.xlsx
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import pandas as pd
from openpyxl.utils import get_column_letter
from datetime import datetime
from collections import Counter

# Setup paths
load_dotenv(Path(__file__).parent.parent.parent / '.env')
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def get_fraud_engine():
    """Create fraud_detection database engine."""
    return create_engine(
        f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}@"
        f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}",
        pool_pre_ping=True
    )

def get_flow_engine():
    """Create flow_api database engine."""
    return create_engine(
        f"mysql+pymysql://{os.getenv('FLOW_DB_USER')}:{os.getenv('FLOW_DB_PASSWORD')}@"
        f"{os.getenv('FLOW_DB_HOST')}:{os.getenv('FLOW_DB_PORT')}/{os.getenv('FLOW_DB_NAME')}",
        pool_pre_ping=True
    )

def get_fatal_statements(fraud_engine):
    """Get all FATAL UATL statements."""
    query = text("""
        SELECT
            u.run_id, u.acc_number, u.acc_prvdr_code, u.format, u.mime,
            u.submitted_date, u.start_date, u.end_date, u.rm_name,
            u.custom_verification, u.custom_verification_reason,
            u.balance_match, u.balance_diff_change_ratio,
            u.stmt_opening_balance, u.stmt_closing_balance,
            u.calculated_closing_balance, u.balance_diff_changes,
            u.credits, u.debits, u.fees, u.charges,
            u.duplicate_count, u.quality_issues_count,
            u.header_row_manipulation_count, u.gap_related_balance_changes,
            u.meta_title, u.meta_author, u.meta_producer,
            u.meta_created_at, u.meta_modified_at,
            u.summary_customer_name, u.summary_mobile_number,
            cd.cust_id, cd.borrower_biz_name
        FROM unified_statements u
        LEFT JOIN customer_details cd ON u.run_id = cd.run_id
        WHERE u.acc_prvdr_code = 'UATL'
          AND u.custom_verification = 'FATAL'
          AND u.format IN ('format_1', 'format_2')
        ORDER BY u.submitted_date DESC
    """)

    with fraud_engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df

def get_loans_for_customers(flow_engine, fraud_engine, cust_ids):
    """Get all loans for FATAL customers with derived fields."""
    if not cust_ids:
        return pd.DataFrame()

    cust_id_list = "','".join(cust_ids)

    # Get statement RM names for each customer
    with fraud_engine.connect() as conn:
        rm_query = text(f"""
            SELECT DISTINCT
                cd.cust_id,
                u.rm_name as statement_rm_name
            FROM customer_details cd
            INNER JOIN unified_statements u ON cd.run_id = u.run_id
            WHERE cd.cust_id IN ('{cust_id_list}')
              AND u.custom_verification = 'FATAL'
        """)
        rm_df = pd.read_sql(rm_query, conn)

    # For customers with multiple FATAL statements, use the most recent RM
    rm_df = rm_df.groupby('cust_id').last().reset_index()

    query = text(f"""
        SELECT
            l.cust_id,
            l.loan_doc_id,
            l.biz_name,
            l.product_id,
            l.loan_principal,
            l.flow_fee,
            l.disbursal_date,
            l.due_date,
            l.paid_date,
            l.status,
            DATEDIFF(COALESCE(l.paid_date, NOW()), l.due_date) as overdue_days_calc,
            l.current_os_amount as os_amount,
            l.flow_rel_mgr_name as loan_flow_rel_mgr_name,
            CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name) as loan_applier_name,
            au.role_codes as loan_applier_role
        FROM loans l
        LEFT JOIN app_users au ON l.loan_applied_by = au.id
        LEFT JOIN persons p ON au.person_id = p.id
        WHERE l.cust_id IN ('{cust_id_list}')
          AND product_id not in (select id from loan_products where product_type = 'float_vending')
          AND l.status NOT IN ('voided', 'hold', 'pending_approval', 'rejected')
        ORDER BY l.cust_id, l.disbursal_date
    """)

    with flow_engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Convert Decimal to float
    df['os_amount'] = df['os_amount'].apply(lambda x: float(x) if pd.notna(x) else 0.0)
    df['flow_fee'] = df['flow_fee'].apply(lambda x: float(x) if pd.notna(x) else 0.0)
    df['loan_principal'] = df['loan_principal'].apply(lambda x: float(x) if pd.notna(x) else 0.0)

    # Add statement RM name
    df = df.merge(rm_df, on='cust_id', how='left')

    return df

def aggregate_by_customer(fatal_df, loans_df, fraud_engine):
    """Create analysis_raw with aggregations by cust_id."""

    # Get customer details ONLY for FATAL customers
    fatal_cust_ids = fatal_df['cust_id'].dropna().unique().tolist()

    if not fatal_cust_ids:
        return pd.DataFrame()

    cust_id_list = "','".join(fatal_cust_ids)

    query = text(f"""
        SELECT DISTINCT
            cd.cust_id,
            cd.borrower_biz_name,
            cd.reg_rm_name as registered_rm,
            cd.current_rm_name as current_rm,
            cd.borrower_reg_date as reg_date,
            cd.crnt_fa_limit
        FROM customer_details cd
        WHERE cd.cust_id IN ('{cust_id_list}')
    """)

    with fraud_engine.connect() as conn:
        customers_df = pd.read_sql(query, conn)

    # Fraud submission stats
    fraud_stats = []
    for cust_id in fatal_df['cust_id'].dropna().unique():
        cust_submissions = fatal_df[fatal_df['cust_id'] == cust_id].copy()
        cust_submissions = cust_submissions.sort_values('submitted_date')

        # Get RM frequencies
        rm_counts = Counter(cust_submissions['rm_name'].dropna())
        most_frequent_rm = rm_counts.most_common(1)[0][0] if rm_counts else None

        fraud_stats.append({
            'cust_id': cust_id,
            'no_of_times_fraud': len(cust_submissions),
            'first_submitted_date': cust_submissions['submitted_date'].min(),
            'last_submitted_date': cust_submissions['submitted_date'].max(),
            'first_rm_name': cust_submissions['rm_name'].iloc[0] if len(cust_submissions) > 0 else None,
            'last_rm_name': cust_submissions['rm_name'].iloc[-1] if len(cust_submissions) > 0 else None,
            'rm_name': most_frequent_rm
        })

    fraud_stats_df = pd.DataFrame(fraud_stats)

    # Loan stats (only for FATAL customers)
    loan_stats = []
    for cust_id in fatal_cust_ids:
        cust_loans = loans_df[loans_df['cust_id'] == cust_id].copy()

        if len(cust_loans) == 0:
            # Customer has no loans
            loan_stats.append({
                'cust_id': cust_id,
                'tot_loans': 0,
                'first_loan_date': None,
                'last_loan_date': None,
                'last_loan_amount': 0,
                'days_since_last_loan': None,
                'tot_ontime_count': 0,
                'tot_ontime_perc': 0,
                'tot_3_day_late_loans': 0,
                'tot_10_day_late_loans': 0,
                'tot_overdue_loans': 0,
                'last_loan_status': 'No Loans',
                'tot_os_amount': 0,
                'tot_od_amount': 0,
                'tot_revenue': 0
            })
            continue

        # Payment performance (paid loans only)
        paid_loans = cust_loans[cust_loans['paid_date'].notna()]
        tot_paid_loans = len(paid_loans)
        tot_ontime = len(paid_loans[paid_loans['overdue_days_calc'] <= 1])
        tot_3_day_late = len(paid_loans[paid_loans['overdue_days_calc'] > 3])
        tot_10_day_late = len(paid_loans[paid_loans['overdue_days_calc'] >= 10])

        # Current status
        tot_overdue = len(cust_loans[cust_loans['status'] == 'overdue'])
        tot_os_amount = cust_loans[cust_loans['status'].isin(['ongoing', 'due'])]['os_amount'].sum()
        tot_od_amount = cust_loans[cust_loans['status'] == 'overdue']['os_amount'].sum()

        # Last loan details
        last_loan = cust_loans.sort_values('disbursal_date', ascending=False).iloc[0]
        last_loan_status = last_loan['status']
        last_loan_amount = last_loan['loan_principal']

        # Revenue
        tot_revenue = paid_loans['flow_fee'].sum()

        # Days since last loan
        last_loan_date = cust_loans['disbursal_date'].max()
        days_since_last = (datetime.now() - last_loan_date).days if pd.notna(last_loan_date) else None

        loan_stats.append({
            'cust_id': cust_id,
            'tot_loans': len(cust_loans),
            'first_loan_date': cust_loans['disbursal_date'].min(),
            'last_loan_date': last_loan_date,
            'last_loan_amount': last_loan_amount,
            'days_since_last_loan': days_since_last,
            'tot_ontime_count': tot_ontime,
            'tot_ontime_perc': round(tot_ontime * 100 / tot_paid_loans, 2) if tot_paid_loans > 0 else 0,
            'tot_3_day_late_loans': tot_3_day_late,
            'tot_10_day_late_loans': tot_10_day_late,
            'tot_overdue_loans': tot_overdue,
            'last_loan_status': last_loan_status,
            'tot_os_amount': tot_os_amount,
            'tot_od_amount': tot_od_amount,
            'tot_revenue': tot_revenue
        })

    loan_stats_df = pd.DataFrame(loan_stats)

    # Merge all
    analysis_df = customers_df.merge(fraud_stats_df, on='cust_id', how='left')
    analysis_df = analysis_df.merge(loan_stats_df, on='cust_id', how='left')

    # Fill NaN for customers without fraud stats
    analysis_df['no_of_times_fraud'] = analysis_df['no_of_times_fraud'].fillna(0).astype(int)
    analysis_df['tot_loans'] = analysis_df['tot_loans'].fillna(0).astype(int)
    analysis_df['tot_os_amount'] = analysis_df['tot_os_amount'].fillna(0)
    analysis_df['tot_od_amount'] = analysis_df['tot_od_amount'].fillna(0)
    analysis_df['tot_revenue'] = analysis_df['tot_revenue'].fillna(0)

    return analysis_df

def generate_business_impact(analysis_df):
    """Generate business impact summary."""

    # Filter to only FATAL customers (those with fraud submissions)
    fatal_customers = analysis_df[analysis_df['no_of_times_fraud'] > 0].copy()

    # By last loan status
    customers_ongoing = len(fatal_customers[fatal_customers['last_loan_status'].isin(['ongoing', 'due'])])
    customers_overdue = len(fatal_customers[fatal_customers['last_loan_status'] == 'overdue'])
    customers_settled = len(fatal_customers[fatal_customers['last_loan_status'] == 'settled'])
    customers_no_loans = len(fatal_customers[fatal_customers['last_loan_status'] == 'No Loans'])

    # By activity
    customers_active_30 = len(fatal_customers[fatal_customers['days_since_last_loan'] <= 30])

    data = {
        'metric': [
            'Total FATAL Customers',
            '',
            'By Last Disbursed Loan Status:',
            '  - Customers Ongoing/Due',
            '  - Customers Overdue',
            '  - Customers Settled',
            '  - Customers No Loans',
            '',
            'By Activity:',
            '  - Customers Active (loan in last 30 days)',
            '',
            'Financial:',
            '  - Total Outstanding Amount (ongoing/due) (UGX)',
            '  - Total Overdue Amount (UGX)',
            '  - Total Revenue Collected (UGX)',
            '  - Net Impact (Revenue - OS - OD) (UGX)'
        ],
        'value': [
            len(fatal_customers),
            '',
            '',
            customers_ongoing,
            customers_overdue,
            customers_settled,
            customers_no_loans,
            '',
            '',
            customers_active_30,
            '',
            '',
            fatal_customers['tot_os_amount'].sum(),
            fatal_customers['tot_od_amount'].sum(),
            fatal_customers['tot_revenue'].sum(),
            fatal_customers['tot_revenue'].sum() - fatal_customers['tot_os_amount'].sum() - fatal_customers['tot_od_amount'].sum()
        ]
    }

    return pd.DataFrame(data)

def generate_rm_cs_analysis(analysis_df, loans_df, fatal_df):
    """Generate RM and CS involvement analysis."""

    # Filter to FATAL customers only
    fatal_customers = analysis_df[analysis_df['no_of_times_fraud'] > 0].copy()
    fatal_cust_ids = fatal_customers['cust_id'].tolist()
    fatal_loans = loans_df[loans_df['cust_id'].isin(fatal_cust_ids)].copy()

    # RM who submitted statements (with overdue customer count and new submissions)
    rm_data = []
    for rm_name in fatal_customers['rm_name'].dropna().unique():
        rm_customers = fatal_customers[fatal_customers['rm_name'] == rm_name]
        overdue_customers = len(rm_customers[rm_customers['tot_overdue_loans'] > 0])

        # Count new submissions (format_1, submitted >= July 2025)
        rm_statements = fatal_df[fatal_df['rm_name'] == rm_name]
        new_submissions = len(rm_statements[
            (rm_statements['format'] == 'format_1') &
            (pd.to_datetime(rm_statements['submitted_date']) >= '2025-07-01')
        ])

        rm_data.append({
            'RM Name': rm_name,
            'Unique Customers': len(rm_customers),
            'Total Fraud Submissions': rm_customers['no_of_times_fraud'].sum(),
            'New Submissions': new_submissions,
            'Total OS Amount': rm_customers['tot_os_amount'].sum(),
            'Total OD Amount': rm_customers['tot_od_amount'].sum(),
            'Total Revenue': rm_customers['tot_revenue'].sum(),
            'Total Customers in Overdue': overdue_customers
        })

    rm_submitted = pd.DataFrame(rm_data).sort_values('Total Fraud Submissions', ascending=False)

    # CS who applied for loans (with overdue loan count)
    cs_data = []
    for (cs_name, cs_role), group in fatal_loans.groupby(['loan_applier_name', 'loan_applier_role']):
        overdue_loans = len(group[group['status'] == 'overdue'])

        cs_data.append({
            'CS Name': cs_name,
            'CS Role': cs_role,
            'Unique Customers': group['cust_id'].nunique(),
            'Total Loans Applied': len(group),
            'Total Loans Overdue': overdue_loans
        })

    cs_analysis = pd.DataFrame(cs_data).sort_values('Total Loans Applied', ascending=False)

    return {
        'RM_Submitted': rm_submitted,
        'CS_Analysis': cs_analysis
    }

def generate_statement_formats(fraud_engine):
    """Generate statement formats analysis."""
    query = text("""
        SELECT
            acc_prvdr_code as provider,
            format,
            COUNT(*) as no_of_submissions,
            MIN(submitted_date) as started,
            MAX(submitted_date) as ended,
            SUM(CASE WHEN custom_verification in ('FATAL','CRITICAL') THEN 1 ELSE 0 END) as fraud,
            SUM(CASE WHEN custom_verification = 'NO_ISSUES' THEN 1 ELSE 0 END) as valid,
            SUM(CASE WHEN custom_verification is null THEN 1 ELSE 0 END) as unknown
        FROM unified_statements
        WHERE (acc_prvdr_code = 'UATL' AND format IN ('format_1', 'format_2'))
           OR (acc_prvdr_code = 'UMTN' AND format = 'excel')
        GROUP BY acc_prvdr_code, format
        ORDER BY provider, format
    """)

    with fraud_engine.connect() as conn:
        df = pd.read_sql(query, conn)

    return df

def generate_os_vs_revenue(analysis_df):
    """Generate OS amount vs revenue analysis."""

    # Filter to FATAL customers only
    fatal_customers = analysis_df[analysis_df['no_of_times_fraud'] > 0].copy()

    os_rev = fatal_customers[['cust_id', 'borrower_biz_name', 'tot_revenue', 'tot_os_amount']].copy()
    os_rev['net_impact'] = os_rev['tot_revenue'] - os_rev['tot_os_amount']
    os_rev['status'] = os_rev['net_impact'].apply(lambda x: 'Profitable' if x > 0 else ('Loss' if x < 0 else 'Break Even'))

    os_rev = os_rev.sort_values('net_impact', ascending=True)

    return os_rev

def generate_monthly_trends(fatal_df):
    """Generate monthly fraud submission trends."""

    monthly = fatal_df.copy()
    monthly['month'] = pd.to_datetime(monthly['submitted_date']).dt.to_period('M').astype(str)

    trends = monthly.groupby('month').agg({
        'run_id': 'count',
        'cust_id': 'nunique'
    }).reset_index()
    trends.columns = ['Month', 'Total Submissions', 'Unique Customers']
    trends = trends.sort_values('Month', ascending=False)

    return trends

def generate_exposure_utilization(analysis_df, loans_df):
    """Generate exposure and utilization analysis grouped by exact loan principal amounts."""

    # Filter to FATAL customers only
    fatal_customers = analysis_df[analysis_df['no_of_times_fraud'] > 0].copy()
    fatal_cust_ids = fatal_customers['cust_id'].tolist()
    fatal_loans = loans_df[loans_df['cust_id'].isin(fatal_cust_ids)].copy()

    # Define standard loan amounts
    standard_amounts = [250000, 500000, 750000, 1000000, 1500000, 2000000, 2500000, 3000000, 4000000, 5000000]

    # Categorize each loan
    def categorize_loan_amount(amount):
        if amount in standard_amounts:
            return amount
        else:
            return 'others'

    fatal_loans['loan_category'] = fatal_loans['loan_principal'].apply(categorize_loan_amount)

    # Prepare results for each category
    results = []

    for amount in standard_amounts + ['others']:
        category_loans = fatal_loans[fatal_loans['loan_category'] == amount].copy()

        if len(category_loans) == 0:
            results.append({
                'loan_principal': f'{amount/1000000:.1f}M' if amount != 'others' else 'Others',
                'total_disbursed': 0,
                'ongoing': 0,
                'overdue': 0,
                'settled': 0,
                'paid_ontime': 0,
                'paid_late': 0
            })
            continue

        # Total disbursed (sum of all loan principals)
        total_disbursed = category_loans['loan_principal'].sum()

        # Ongoing: sum of os_amount where status = ongoing or due
        ongoing = category_loans[category_loans['status'].isin(['ongoing', 'due'])]['os_amount'].sum()

        # Overdue: sum of os_amount where status = overdue
        overdue = category_loans[category_loans['status'] == 'overdue']['os_amount'].sum()

        # Settled: sum of loan_principal where status = settled
        settled = category_loans[category_loans['status'] == 'settled']['loan_principal'].sum()

        # Paid ontime: sum of loan_principal where paid_date is not null and overdue_days <= 1
        paid_loans = category_loans[category_loans['paid_date'].notna()].copy()
        paid_ontime = paid_loans[paid_loans['overdue_days_calc'] <= 1]['loan_principal'].sum()

        # Paid late: sum of loan_principal where paid_date is not null and overdue_days > 3
        paid_late = paid_loans[paid_loans['overdue_days_calc'] > 3]['loan_principal'].sum()

        results.append({
            'loan_principal': f'{amount/1000000:.1f}M' if amount != 'others' else 'Others',
            'total_disbursed': total_disbursed,
            'ongoing': ongoing,
            'overdue': overdue,
            'settled': settled,
            'paid_ontime': paid_ontime,
            'paid_late': paid_late
        })

    # Create DataFrame
    df = pd.DataFrame(results)

    # Add totals row
    totals = {
        'loan_principal': 'TOTAL',
        'total_disbursed': df['total_disbursed'].sum(),
        'ongoing': df['ongoing'].sum(),
        'overdue': df['overdue'].sum(),
        'settled': df['settled'].sum(),
        'paid_ontime': df['paid_ontime'].sum(),
        'paid_late': df['paid_late'].sum()
    }
    df = pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

    return df

def format_excel_sheet(writer, sheet_name):
    """Apply formatting to Excel sheet."""
    workbook = writer.book
    worksheet = workbook[sheet_name]

    # Auto-adjust column widths
    for column in worksheet.columns:
        max_length = 0
        column_letter = get_column_letter(column[0].column)

        for cell in column:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass

        adjusted_width = min(max_length + 2, 50)
        worksheet.column_dimensions[column_letter].width = adjusted_width

    # Freeze top row
    worksheet.freeze_panes = 'A2'

def main():
    print("=" * 80)
    print("EXPORT FATAL ANALYSIS WITH LOANS DATA")
    print("=" * 80)

    fraud_engine = get_fraud_engine()
    flow_engine = get_flow_engine()

    output_dir = Path('docs/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / 'fatal_analysis_report.xlsx'

    # 1. Get FATAL statements
    print("\n1. Querying FATAL statements...")
    fatal_df = get_fatal_statements(fraud_engine)
    print(f"   ✓ {len(fatal_df):,} FATAL statements")

    # 2. Get customer IDs
    print("\n2. Extracting customer IDs...")
    cust_ids = fatal_df['cust_id'].dropna().unique().tolist()
    print(f"   ✓ {len(cust_ids):,} unique customers with cust_id")

    # 3. Get loans data
    print("\n3. Querying loans data...")
    loans_df = get_loans_for_customers(flow_engine, fraud_engine, cust_ids)
    print(f"   ✓ {len(loans_df):,} total loans for FATAL customers")

    # 4. Aggregate by customer
    print("\n4. Aggregating by customer...")
    analysis_df = aggregate_by_customer(fatal_df, loans_df, fraud_engine)
    print(f"   ✓ {len(analysis_df):,} customer records")

    # 5. Generate insights
    print("\n5. Generating insights...")
    business_impact = generate_business_impact(analysis_df)
    print(f"   ✓ Business impact summary")

    statement_formats = generate_statement_formats(fraud_engine)
    print(f"   ✓ Statement formats analysis")

    rm_cs_analysis = generate_rm_cs_analysis(analysis_df, loans_df, fatal_df)
    print(f"   ✓ RM/CS involvement analysis")

    os_vs_revenue = generate_os_vs_revenue(analysis_df)
    print(f"   ✓ OS vs Revenue analysis")

    monthly_trends = generate_monthly_trends(fatal_df)
    print(f"   ✓ Monthly trends")

    exposure_utilization = generate_exposure_utilization(analysis_df, loans_df)
    print(f"   ✓ Exposure and utilization analysis")

    # 6. Write to Excel
    print(f"\n6. Writing to Excel: {output_file}")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Main tabs
        fatal_df.to_excel(writer, sheet_name='FATAL_filtered', index=False)
        format_excel_sheet(writer, 'FATAL_filtered')

        loans_df.to_excel(writer, sheet_name='loans_raw', index=False)
        format_excel_sheet(writer, 'loans_raw')

        analysis_df.to_excel(writer, sheet_name='analysis_raw', index=False)
        format_excel_sheet(writer, 'analysis_raw')

        # Insight tabs
        business_impact.to_excel(writer, sheet_name='business_impact', index=False)
        format_excel_sheet(writer, 'business_impact')

        statement_formats.to_excel(writer, sheet_name='Statement_Formats', index=False)
        format_excel_sheet(writer, 'Statement_Formats')

        rm_cs_analysis['RM_Submitted'].to_excel(writer, sheet_name='RM_Submitted', index=False)
        format_excel_sheet(writer, 'RM_Submitted')

        rm_cs_analysis['CS_Analysis'].to_excel(writer, sheet_name='CS_Analysis', index=False)
        format_excel_sheet(writer, 'CS_Analysis')

        os_vs_revenue.to_excel(writer, sheet_name='os_vs_revenue', index=False)
        format_excel_sheet(writer, 'os_vs_revenue')

        monthly_trends.to_excel(writer, sheet_name='monthly_trends', index=False)
        format_excel_sheet(writer, 'monthly_trends')

        exposure_utilization.to_excel(writer, sheet_name='exposure_utilization', index=False)
        format_excel_sheet(writer, 'exposure_utilization')

    print(f"   ✓ Excel file created")

    print("\n" + "=" * 80)
    print("EXPORT COMPLETE")
    print("=" * 80)
    print(f"\nOutput file: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    print(f"\nTabs created:")
    print("  1. FATAL_filtered")
    print("  2. loans_raw")
    print("  3. analysis_raw")
    print("  4. business_impact")
    print("  5. Statement_Formats")
    print("  6. RM_Submitted")
    print("  7. CS_Analysis")
    print("  8. os_vs_revenue")
    print("  9. monthly_trends")
    print(" 10. exposure_utilization")

    return 0


if __name__ == '__main__':
    exit(main())
