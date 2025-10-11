"""
Streamlit UI for Multi-Provider Fraud Detection System
Connects to FastAPI backend on port 8501
"""
import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime

# API Configuration
API_BASE_URL = "http://localhost:8501/api/v1"

# Page config
st.set_page_config(
    page_title="Fraud Detection System",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def call_api(endpoint, method="GET", **kwargs):
    """Make API call to backend"""
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, **kwargs)
        elif method == "POST":
            response = requests.post(url, **kwargs)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        return None

# Title
st.markdown('<p class="main-header">🔍 Multi-Provider Fraud Detection System</p>', unsafe_allow_html=True)
st.markdown("**Supports:** Airtel (PDF) | MTN (Excel/CSV)")

# Sidebar
with st.sidebar:
    st.header("📊 System Status")

    # Get system status
    status_response = call_api("status")
    if status_response and status_response.status_code == 200:
        status_data = status_response.json()

        st.success("✅ System Online")

        if 'statistics' in status_data:
            stats = status_data['statistics']
            st.subheader("Database Statistics")

            # Provider breakdown
            if 'by_provider' in stats:
                for provider, count in stats['by_provider'].items():
                    provider_name = "Airtel" if provider == "UATL" else "MTN"
                    st.metric(f"{provider_name} Statements", count)

            st.metric("Total Metadata", stats.get('metadata_count', 0))
            st.metric("Total Summaries", stats.get('summary_count', 0))
    else:
        st.error("❌ System Offline")

    st.markdown("---")
    st.markdown("**Provider Detection:**")
    st.info("📄 PDF → Airtel (UATL)\n📊 Excel/CSV → MTN (UMTN)")

# Main content
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload & Process", "📋 View Statements", "📥 Download", "🗑️ Delete Data"])

# Tab 1: Upload & Process
with tab1:
    st.header("Upload Statement Files")
    st.markdown("Upload **PDF files** for Airtel or **Excel/CSV files** for MTN")

    uploaded_files = st.file_uploader(
        "Choose files",
        type=['pdf', 'xlsx', 'xls', 'csv'],
        accept_multiple_files=True,
        help="Drag and drop files here or click to browse"
    )

    if uploaded_files:
        st.info(f"📄 {len(uploaded_files)} file(s) selected")

        # Show file details
        for file in uploaded_files:
            ext = file.name.split('.')[-1].upper()
            provider = "Airtel (UATL)" if ext == "PDF" else "MTN (UMTN)"
            st.text(f"• {file.name} → {provider}")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚀 Upload Files", type="primary", use_container_width=True):
                with st.spinner("Uploading and parsing files..."):
                    files_data = [("files", (file.name, file.getvalue(), file.type)) for file in uploaded_files]

                    response = call_api("upload", method="POST", files=files_data)

                    if response and response.status_code == 200:
                        result = response.json()

                        if result['successful'] > 0:
                            st.markdown(f'<div class="success-box">✅ Successfully uploaded {result["successful"]} file(s)</div>', unsafe_allow_html=True)

                        if result['skipped'] > 0:
                            st.markdown(f'<div class="warning-box">⏭️ Skipped {result["skipped"]} file(s) (already exists)</div>', unsafe_allow_html=True)

                        if result['failed'] > 0:
                            st.markdown(f'<div class="error-box">❌ Failed to upload {result["failed"]} file(s)</div>', unsafe_allow_html=True)

                        # Show detailed results
                        if 'results' in result:
                            with st.expander("📊 Detailed Results"):
                                for res in result['results']:
                                    status_emoji = "✅" if res['status'] == 'success' else "⏭️" if res['status'] == 'skipped' else "❌"
                                    st.text(f"{status_emoji} {res['filename']}: {res['message']}")
                                    if res.get('num_transactions'):
                                        st.text(f"   → {res['num_transactions']} transactions parsed")

                        # Store run_ids for processing
                        if result['successful'] > 0:
                            st.session_state['uploaded_run_ids'] = [
                                res['run_id'] for res in result['results']
                                if res['status'] == 'success'
                            ]
                            st.success("Files are ready for processing!")

        with col2:
            # Process uploaded files
            if st.session_state.get('uploaded_run_ids'):
                if st.button("⚙️ Process Statements", type="secondary", use_container_width=True):
                    with st.spinner("Processing statements (detecting duplicates, verifying balances)..."):
                        response = call_api(
                            "process",
                            method="POST",
                            json={"run_ids": st.session_state['uploaded_run_ids']}
                        )

                        if response and response.status_code == 200:
                            result = response.json()

                            st.markdown(f'<div class="success-box">✅ Successfully processed {result["successful"]} statement(s)</div>', unsafe_allow_html=True)

                            if result['failed'] > 0:
                                st.markdown(f'<div class="error-box">❌ Failed to process {result["failed"]} statement(s)</div>', unsafe_allow_html=True)

                            # Show processing results with summaries
                            if 'results' in result:
                                st.subheader("📊 Processing Summary")

                                # Create dataframe for summary
                                summary_data = []
                                for res in result['results']:
                                    if res['status'] == 'success':
                                        summary_data.append({
                                            'Run ID': res['run_id'],
                                            'Provider': res.get('provider_code', 'N/A'),
                                            'Transactions': res.get('processed_count', 0),
                                            'Duplicates': res.get('duplicate_count', 0),
                                            'Balance Match': res.get('balance_match', 'N/A'),
                                            'Status': res.get('verification_status', 'N/A')
                                        })

                                if summary_data:
                                    df_summary = pd.DataFrame(summary_data)

                                    # Apply styling
                                    def style_balance(val):
                                        if val == 'Success':
                                            return 'background-color: #d4edda'
                                        elif val == 'Failed':
                                            return 'background-color: #f8d7da'
                                        return ''

                                    def style_status(val):
                                        if val == 'PASS':
                                            return 'background-color: #d4edda'
                                        elif val == 'FAIL':
                                            return 'background-color: #f8d7da'
                                        elif val == 'WARNING':
                                            return 'background-color: #fff3cd'
                                        return ''

                                    styled_df = df_summary.style.applymap(
                                        style_balance, subset=['Balance Match']
                                    ).applymap(
                                        style_status, subset=['Status']
                                    )

                                    st.dataframe(styled_df, use_container_width=True)

                                    # Summary metrics
                                    col1, col2, col3, col4 = st.columns(4)
                                    with col1:
                                        st.metric("Total Processed", len(summary_data))
                                    with col2:
                                        passed = sum(1 for d in summary_data if d['Status'] == 'PASS')
                                        st.metric("Verified", passed)
                                    with col3:
                                        failed = sum(1 for d in summary_data if d['Status'] == 'FAIL')
                                        st.metric("Failed", failed)
                                    with col4:
                                        total_dupes = sum(d['Duplicates'] for d in summary_data)
                                        st.metric("Total Duplicates", total_dupes)

                                    st.success("✅ Processing complete! Go to 'Download' tab to export results.")

                            # Clear session state
                            st.session_state['uploaded_run_ids'] = []

# Tab 2: View Statements
with tab2:
    st.header("View Uploaded Statements")

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_provider = st.selectbox("Provider", ["All", "UATL (Airtel)", "UMTN (MTN)"])
    with col2:
        filter_account = st.text_input("Account Number")
    with col3:
        page_size = st.selectbox("Items per page", [10, 25, 50, 100], index=2)

    # Build query parameters
    params = {
        'page': 1,
        'page_size': page_size
    }
    if filter_provider != "All":
        params['acc_prvdr_code'] = 'UATL' if 'Airtel' in filter_provider else 'UMTN'
    if filter_account:
        params['acc_number'] = filter_account

    # Fetch statements
    response = call_api("list", params=params)

    if response and response.status_code == 200:
        data = response.json()

        if data['items']:
            # Display pagination info
            pagination = data['pagination']
            st.info(f"📄 Showing {len(data['items'])} of {pagination['total']} statements (Page {pagination['page']}/{pagination['total_pages']})")

            # Convert to DataFrame
            df = pd.DataFrame(data['items'])

            # Format columns
            if 'acc_prvdr_code' in df.columns:
                df['Provider'] = df['acc_prvdr_code'].map({'UATL': 'Airtel', 'UMTN': 'MTN'})

            display_cols = ['run_id', 'Provider', 'acc_number', 'rm_name', 'num_rows', 'created_at']
            display_cols = [col for col in display_cols if col in df.columns]

            st.dataframe(df[display_cols], use_container_width=True)
        else:
            st.info("No statements found. Upload files in the 'Upload & Process' tab.")

# Tab 3: Download
with tab3:
    st.header("Download Results")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Download Processed Statements")
        st.markdown("Download detailed transaction data with fraud detection results")

        format_processed = st.radio("Format:", ["CSV", "Excel"], key="format_processed", horizontal=True)

        if st.button("Download Processed Statements", use_container_width=True):
            format_param = format_processed.lower()
            response = requests.get(
                f"{API_BASE_URL}/download/processed?format={format_param}",
                stream=True
            )

            if response.status_code == 200:
                filename = f"processed_statements.{format_param if format_param == 'csv' else 'xlsx'}"
                st.download_button(
                    label=f"💾 Save {filename}",
                    data=response.content,
                    file_name=filename,
                    mime="text/csv" if format_param == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error("No processed data available. Process statements first.")

    with col2:
        st.subheader("📋 Download Summary")
        st.markdown("Download summary report with balance verification results")

        format_summary = st.radio("Format:", ["CSV", "Excel"], key="format_summary", horizontal=True)

        if st.button("Download Summary", use_container_width=True):
            format_param = format_summary.lower()
            response = requests.get(
                f"{API_BASE_URL}/download/summary?format={format_param}",
                stream=True
            )

            if response.status_code == 200:
                filename = f"summary.{format_param if format_param == 'csv' else 'xlsx'}"
                st.download_button(
                    label=f"💾 Save {filename}",
                    data=response.content,
                    file_name=filename,
                    mime="text/csv" if format_param == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error("No summary data available. Process statements first.")

# Tab 4: Delete Data
with tab4:
    st.header("Delete Data")
    st.warning("⚠️ **Warning:** This action cannot be undone!")

    st.markdown("### Select Run IDs to Delete")

    # Get list of all run_ids
    response = call_api("list", params={'page_size': 1000})
    if response and response.status_code == 200:
        data = response.json()
        if data['items']:
            run_ids = [item['run_id'] for item in data['items']]

            selected_run_ids = st.multiselect(
                "Select statements to delete:",
                options=run_ids,
                help="Select one or more run IDs to delete"
            )

            delete_all = st.checkbox("Delete ALL data (including raw)", value=False)

            if selected_run_ids:
                st.info(f"Selected {len(selected_run_ids)} statement(s) for deletion")

                confirm = st.checkbox("I understand this action cannot be undone")

                if confirm:
                    if st.button("🗑️ Delete Selected Data", type="primary"):
                        with st.spinner("Deleting data..."):
                            response = call_api(
                                "delete",
                                method="POST",
                                json={
                                    "run_ids": selected_run_ids,
                                    "delete_all": delete_all,
                                    "confirm": True
                                }
                            )

                            if response and response.status_code == 200:
                                result = response.json()
                                st.success(f"✅ Successfully deleted {result['successful']} statement(s)")

                                if result['failed'] > 0:
                                    st.error(f"❌ Failed to delete {result['failed']} statement(s)")

                                st.rerun()
        else:
            st.info("No statements available to delete")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9rem;">
    <p>Multi-Provider Fraud Detection System v2.0 | FastAPI + Streamlit</p>
    <p>Supports Airtel (PDF) and MTN (Excel/CSV) statements</p>
</div>
""", unsafe_allow_html=True)
