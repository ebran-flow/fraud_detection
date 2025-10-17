#!/usr/bin/env python3
"""
Export FATAL analysis with loans data

Tabs:
- FATAL_filtered: All FATAL UATL statements
- loans_raw: All loans for FATAL customers
- analysis_raw: Aggregated by cust_id with fraud and loan metrics
- business_impact: Payment performance and current risk
- rm_cs_involvement: RM and CS analysis
- os_vs_revenue: Outstanding vs Revenue analysis
- monthly_trends: Fraud submissions by month

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

def get_loans_for_customers(flow_engine, cust_ids):
    """Get all loans for FATAL customers with derived fields."""
    if not cust_ids:
        return pd.DataFrame()

    cust_id_list = "','".join(cust_ids)

    query = text(f"""
        SELECT
            l.cust_id,
            l.loan_doc_id,
            l.biz_name,
            l.loan_principal,
            l.flow_fee,
            l.disbursal_date,
            l.due_date,
            l.paid_date,
            l.status,
            DATEDIFF(COALESCE(l.paid_date, NOW()), l.due_date) as overdue_days_calc,
            l.current_os_amount as os_amount,
            l.flow_rel_mgr_name,
            CONCAT_WS(' ', p.first_name, p.middle_name, p.last_name) as loan_applier_name,
            au.role_codes as loan_applier_role
        FROM loans l
        LEFT JOIN app_users au ON l.loan_applied_by = au.id
        LEFT JOIN persons p ON au.person_id = p.id
        WHERE l.cust_id IN ('{cust_id_list}')
        ORDER BY l.cust_id, l.disbursal_date
    """)

    with flow_engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Convert Decimal to float
    df['os_amount'] = df['os_amount'].apply(lambda x: float(x) if pd.notna(x) else 0.0)
    df['flow_fee'] = df['flow_fee'].apply(lambda x: float(x) if pd.notna(x) else 0.0)
    df['loan_principal'] = df['loan_principal'].apply(lambda x: float(x) if pd.notna(x) else 0.0)

    return df

def aggregate_by_customer(fatal_df, loans_df, fraud_engine):
    """Create analysis_raw with aggregations by cust_id."""

    # Get customer details
    query = text("""
        SELECT DISTINCT
            cd.cust_id,
            cd.borrower_biz_name,
            cd.reg_rm_name as registered_rm,
            cd.current_rm_name as current_rm,
            cd.borrower_reg_date as reg_date
        FROM customer_details cd
        WHERE cd.cust_id IS NOT NULL
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

    # Loan stats
    loan_stats = []
    for cust_id in loans_df['cust_id'].unique():
        cust_loans = loans_df[loans_df['cust_id'] == cust_id].copy()

        # Payment performance (paid loans only)
        paid_loans = cust_loans[cust_loans['paid_date'].notna()]
        tot_paid_loans = len(paid_loans)
        tot_ontime = len(paid_loans[paid_loans['overdue_days_calc'] <= 1])
        tot_3_day_late = len(paid_loans[paid_loans['overdue_days_calc'] > 3])
        tot_10_day_late = len(paid_loans[paid_loans['overdue_days_calc'] >= 10])

        # Current status
        tot_overdue = len(cust_loans[cust_loans['status'] == 'overdue'])
        tot_os_amount = cust_loans[cust_loans['status'].isin(['ongoing', 'overdue'])]['os_amount'].sum()

        # Last loan status
        last_loan = cust_loans.sort_values('disbursal_date', ascending=False).iloc[0] if len(cust_loans) > 0 else None
        last_loan_status = last_loan['status'] if last_loan is not None else None

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
            'days_since_last_loan': days_since_last,
            'tot_ontime_count': tot_ontime,
            'tot_ontime_perc': round(tot_ontime * 100 / tot_paid_loans, 2) if tot_paid_loans > 0 else 0,
            'tot_3_day_late_loans': tot_3_day_late,
            'tot_10_day_late_loans': tot_10_day_late,
            'tot_overdue_loans': tot_overdue,
            'last_loan_status': last_loan_status,
            'tot_os_amount': tot_os_amount,
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
    analysis_df['tot_revenue'] = analysis_df['tot_revenue'].fillna(0)

    return analysis_df

def generate_business_impact(analysis_df):
    """Generate business impact summary."""

    # Filter to only FATAL customers (those with fraud submissions)
    fatal_customers = analysis_df[analysis_df['no_of_times_fraud'] > 0].copy()

    data = {
        'metric': [
            'Total FATAL Customers',
            'Customers Paying On Time (100%)',
            'Customers Paying Late (any late payment)',
            'Customers Currently Ongoing',
            'Customers Currently Overdue',
            'Total Outstanding Amount (UGX)',
            'Total Revenue Collected (UGX)',
            'Net Impact (Revenue - OS) (UGX)',
            'Customers Active (loan in last 30 days)'
        ],
        'value': [
            len(fatal_customers),
            len(fatal_customers[fatal_customers['tot_ontime_perc'] == 100]),
            len(fatal_customers[fatal_customers['tot_3_day_late_loans'] > 0]),
            len(fatal_customers[fatal_customers['last_loan_status'] == 'ongoing']),
            len(fatal_customers[fatal_customers['tot_overdue_loans'] > 0]),
            fatal_customers['tot_os_amount'].sum(),
            fatal_customers['tot_revenue'].sum(),
            fatal_customers['tot_revenue'].sum() - fatal_customers['tot_os_amount'].sum(),
            len(fatal_customers[fatal_customers['days_since_last_loan'] <= 30])
        ]
    }

    return pd.DataFrame(data)

def generate_rm_cs_analysis(analysis_df, loans_df):
    """Generate RM and CS involvement analysis."""

    # Filter to FATAL customers only
    fatal_customers = analysis_df[analysis_df['no_of_times_fraud'] > 0].copy()

    # RM who submitted statements
    rm_submitted = fatal_customers.groupby('rm_name').agg({
        'cust_id': 'count',
        'no_of_times_fraud': 'sum',
        'tot_os_amount': 'sum',
        'tot_revenue': 'sum'
    }).reset_index()
    rm_submitted.columns = ['RM Name', 'Unique Customers', 'Total Fraud Submissions', 'Total OS Amount', 'Total Revenue']
    rm_submitted = rm_submitted.sort_values('Total Fraud Submissions', ascending=False)

    # RM who registered borrowers
    rm_registered = fatal_customers.groupby('registered_rm').agg({
        'cust_id': 'count',
        'tot_os_amount': 'sum'
    }).reset_index()
    rm_registered.columns = ['RM Name', 'Customers Registered', 'Total OS Amount']
    rm_registered = rm_registered.sort_values('Customers Registered', ascending=False)

    # CS who applied for loans
    fatal_cust_ids = fatal_customers['cust_id'].tolist()
    fatal_loans = loans_df[loans_df['cust_id'].isin(fatal_cust_ids)].copy()

    cs_analysis = fatal_loans.groupby(['loan_applier_name', 'loan_applier_role']).agg({
        'cust_id': 'nunique',
        'loan_doc_id': 'count'
    }).reset_index()
    cs_analysis.columns = ['CS Name', 'CS Role', 'Unique Customers', 'Total Loans Applied']
    cs_analysis = cs_analysis.sort_values('Total Loans Applied', ascending=False)

    # RM during overdue disbursals
    overdue_loans = fatal_loans[fatal_loans['status'] == 'overdue'].copy()
    rm_overdue = overdue_loans.groupby('flow_rel_mgr_name').agg({
        'loan_doc_id': 'count',
        'os_amount': 'sum'
    }).reset_index()
    rm_overdue.columns = ['RM Name', 'Overdue Loan Disbursals', 'Total OS Amount']
    rm_overdue = rm_overdue.sort_values('Overdue Loan Disbursals', ascending=False)

    return {
        'RM_Submitted': rm_submitted,
        'RM_Registered': rm_registered,
        'CS_Analysis': cs_analysis,
        'RM_Overdue_Disbursals': rm_overdue
    }

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
    loans_df = get_loans_for_customers(flow_engine, cust_ids)
    print(f"   ✓ {len(loans_df):,} total loans for FATAL customers")

    # 4. Aggregate by customer
    print("\n4. Aggregating by customer...")
    analysis_df = aggregate_by_customer(fatal_df, loans_df, fraud_engine)
    print(f"   ✓ {len(analysis_df):,} customer records")

    # 5. Generate insights
    print("\n5. Generating insights...")
    business_impact = generate_business_impact(analysis_df)
    print(f"   ✓ Business impact summary")

    rm_cs_analysis = generate_rm_cs_analysis(analysis_df, loans_df)
    print(f"   ✓ RM/CS involvement analysis")

    os_vs_revenue = generate_os_vs_revenue(analysis_df)
    print(f"   ✓ OS vs Revenue analysis")

    monthly_trends = generate_monthly_trends(fatal_df)
    print(f"   ✓ Monthly trends")

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

        rm_cs_analysis['RM_Submitted'].to_excel(writer, sheet_name='RM_Submitted', index=False)
        format_excel_sheet(writer, 'RM_Submitted')

        rm_cs_analysis['RM_Registered'].to_excel(writer, sheet_name='RM_Registered', index=False)
        format_excel_sheet(writer, 'RM_Registered')

        rm_cs_analysis['CS_Analysis'].to_excel(writer, sheet_name='CS_Analysis', index=False)
        format_excel_sheet(writer, 'CS_Analysis')

        rm_cs_analysis['RM_Overdue_Disbursals'].to_excel(writer, sheet_name='RM_Overdue_Disbursals', index=False)
        format_excel_sheet(writer, 'RM_Overdue_Disbursals')

        os_vs_revenue.to_excel(writer, sheet_name='os_vs_revenue', index=False)
        format_excel_sheet(writer, 'os_vs_revenue')

        monthly_trends.to_excel(writer, sheet_name='monthly_trends', index=False)
        format_excel_sheet(writer, 'monthly_trends')

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
    print("  5. RM_Submitted")
    print("  6. RM_Registered")
    print("  7. CS_Analysis")
    print("  8. RM_Overdue_Disbursals")
    print("  9. os_vs_revenue")
    print(" 10. monthly_trends")

    return 0


if __name__ == '__main__':
    exit(main())
