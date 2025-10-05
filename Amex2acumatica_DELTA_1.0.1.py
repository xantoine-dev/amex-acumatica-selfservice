import streamlit as st
import pandas as pd
import os, io, zipfile, tempfile, re

st.set_page_config(page_title="Amex → Acumatica", layout="centered")
st.title("💳 Amex → Acumatica Self‑Service Processor")
st.caption("Upload your Amex statement and optionally a corporate card file. Files are processed securely in memory.")

# Utility functions

def clean_columns(df):
    df.columns = df.columns.str.replace("\n", " ", regex=False).str.replace(r"\s+", " ", regex=True).str.strip()
    return df

def remove_numbers_from_string(val):
    return re.sub(r"\d+", "", val) if isinstance(val, str) else val

def read_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, skiprows=12, header=0, sep=None, engine="python")
    elif name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(uploaded_file, skiprows=12, header=0, engine="openpyxl")
    else:
        st.error("Unsupported file type.")
        st.stop()
    return clean_columns(df)

def process_statement(statement_df, amount_column="Transaction Amount USD"):
    df = statement_df.iloc[13:] if len(statement_df) > 13 else statement_df
    if amount_column not in df.columns:
        st.error(f"Missing column: {amount_column}")
        st.stop()
    df[amount_column] = (df[amount_column].astype(str)
                         .str.replace('$','',regex=False)
                         .str.replace(',','',regex=False))
    df[amount_column] = pd.to_numeric(df[amount_column], errors='coerce')
    df = df[df[amount_column] >= 0]
    df['Transaction Description 4'] = df['Transaction Description 4'].apply(remove_numbers_from_string)
    return df

def split_by_employee(df, output_format="csv"):
    last_name_column = "Supplemental Cardmember Last Name"
    if last_name_column not in df.columns:
        st.error(f"Missing column: {last_name_column}")
        st.stop()
    template_cols = ["Branch", "Date", "Ref. Nbr.", "Expense Item", "Expense Account", "Description", "Amount", "Claim Amount", "Paid With", "Corporate Card", "AR Reference Nbr."]
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as zipf:
        for last_name in df[last_name_column].dropna().unique():
            emp_data = df[df[last_name_column]==last_name]
            emp_template = pd.DataFrame(columns=template_cols)
            for _, row in emp_data.iterrows():
                new_row = {
                    'Branch':'KEC',
                    'Date':row.get('Transaction Date'),
                    'Ref. Nbr.':row.get('Transaction Description 4'),
                    'Description':row.get('Transaction Description 1'),
                    'Amount':row.get('Transaction Amount USD'),
                    'Claim Amount':row.get('Transaction Amount USD'),
                    'Paid With':'Corporate Card, Company Expense'
                }
                emp_template = pd.concat([emp_template, pd.DataFrame([new_row])], ignore_index=True)
            fname = f"{last_name}_AMEX_Claim.{ 'xlsx' if output_format=='excel' else 'csv' }"
            with tempfile.NamedTemporaryFile(delete=False, suffix=fname) as tmp:
                if output_format=='excel':
                    emp_template.to_excel(tmp.name, index=False)
                else:
                    emp_template.to_csv(tmp.name, index=False)
                zipf.write(tmp.name, arcname=fname)
    output.seek(0)
    return output

# UI inputs
st.header("Step 1: Upload Files")
statement_file = st.file_uploader("Upload Amex Statement (.csv or .xlsx)", type=['csv','xls','xlsx'])
export_format = st.radio("Choose export format:", ['csv','excel'], horizontal=True)

if statement_file:
    st.success(f"File uploaded: {statement_file.name}")
    if st.button("⚙️ Process and Generate Files"):
        with st.spinner("Processing statement..."):
            df = read_file(statement_file)
            cleaned = process_statement(df)
            zip_data = split_by_employee(cleaned, export_format)
        st.success("✅ Processing complete! Download your files below.")
        st.download_button(label="⬇️ Download All Employee Files (ZIP)", data=zip_data, file_name="Amex_to_Acumatica_Files.zip", mime="application/zip")
