import streamlit as st
import pandas as pd
import openpyxl
import csv
from io import BytesIO,  StringIO
import re
import zipfile


st.set_page_config(page_title="Amex → Acumatica Self-Service", layout="centered")

st.title("💳 Amex → Acumatica Converter")
st.caption("Upload your Amex statement (.csv or .xlsx) and generate employee-specific claim files.")


def clean_columns(df):
    """Standardize and clean column headers."""
    df.columns = (
        df.columns
        .astype(str)
        .str.replace('\n', ' ', regex=False)
        .str.replace(r'\s+', ' ', regex=True)
        .str.strip()
    )
    return df


def read_file(uploaded_file):
    """Reads uploaded CSV or Excel safely with auto-delimiter and flattens multiline headers."""
    name = uploaded_file.name.lower()

    if name.endswith('.csv'):
        sample = uploaded_file.read(2048).decode('utf-8', errors='ignore')
        uploaded_file.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
            sep = dialect.delimiter
        except Exception:
            sep = ','

        st.info(f"Detected delimiter: '{sep}'")

        df = pd.read_csv(
            uploaded_file,
            header=13,  # start from row 14 (0-indexed)
            skip_blank_lines=True,
            on_bad_lines='skip',
            sep=sep,
            engine='python',
            encoding='utf-8'
        )

    elif name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(uploaded_file, header=13, engine='openpyxl')

    else:
        st.error("Unsupported file type. Please upload a CSV or Excel file.")
        st.stop()

    # --- Flatten messy multi-line headers ---
    df.columns = (
        df.columns
        .astype(str)
        .str.replace(r'\s+', ' ', regex=True)   # collapse whitespace
        .str.replace('\n', ' ', regex=False)    # replace newlines
        .str.strip()                            # trim ends
    )

    st.success(f"✅ Loaded {len(df)} rows with {len(df.columns)} columns.")
    st.dataframe(df.head(10))
    return df
    """Reads uploaded CSV or Excel safely with delimiter detection and skips malformed rows."""
    name = uploaded_file.name.lower()

    if name.endswith('.csv'):
        # Peek to detect delimiter
        sample = uploaded_file.read(2048).decode('utf-8', errors='ignore')
        uploaded_file.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
            sep = dialect.delimiter
        except Exception:
            sep = ','

        st.info(f"Detected delimiter: '{sep}'")

        df = pd.read_csv(
            uploaded_file,
            header=0,
            skip_blank_lines=True,
            on_bad_lines='skip',
            sep=sep,
            engine='python',
            encoding='utf-8'
        )

    elif name.endswith(('.xls', '.xlsx')):
        df = pd.read_excel(uploaded_file, engine='openpyxl')

    else:
        st.error("Unsupported file type. Please upload a CSV or Excel file.")
        st.stop()

    df = clean_columns(df)

    st.success(f"✅ File loaded successfully with {len(df)} rows and {len(df.columns)} columns.")
    st.dataframe(df.head(10))  # show preview
    return df


def process_statement(df):
    """Example placeholder for your Amex cleaning logic."""
    # Convert $amounts to floats
    for col in df.columns:
        if "amount" in col.lower():
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("$", "", regex=False)
                .str.replace(",", "", regex=False)
                .astype(float, errors='ignore')
            )
    return df


def split_by_employee(df, export_format):
    """Split dataframe by employee last name column (auto-detected and regex-based) and zip outputs."""

    # --- Detect the "Last Name" column dynamically ---
    detected_col = None
    for col in df.columns:
        # Normalize and test
        normalized = re.sub(r'\s+', ' ', col.strip().lower())
        if re.search(r'supplemental.*cardmember.*last', normalized):
            detected_col = col
            break
    if not detected_col:
        for col in df.columns:
            normalized = re.sub(r'\s+', ' ', col.strip().lower())
            if re.search(r'cardmember.*last', normalized):
                detected_col = col
                break

    if not detected_col:
        st.error(
            "❌ Could not detect a 'Supplemental Cardmember Last Name' column.\n"
            "Please verify the file headers (row 14) include a similar field."
        )
        st.write("Available columns:", df.columns.tolist())
        st.stop()

    st.info(f"Detected employee last name column: **{detected_col}**")

    # --- Generate per-employee claim files ---
    memory_zip = BytesIO()
    with zipfile.ZipFile(memory_zip, "w") as zf:
        for last_name in df[detected_col].dropna().unique():
            employee_data = df[df[detected_col] == last_name]
            buf = StringIO()
            employee_data.to_csv(buf, index=False)
            zf.writestr(f"{last_name}_AMEX_Claim.csv", buf.getvalue())

    memory_zip.seek(0)
    return memory_zip
    """Split dataframe by detected employee last name column and zip outputs."""
    from io import BytesIO, StringIO
    import zipfile

    # --- Detect the last-name column dynamically ---
    last_name_col = None
    for col in df.columns:
        if re.search(r'(supplemental.*cardmember.*last)', col, re.IGNORECASE):
            last_name_col = col
            break

    if not last_name_col:
        st.error(
            "❌ Could not detect the Supplemental Cardmember Last Name column.\n"
            "Please confirm your input file includes it on row 14."
        )
        st.stop()

    st.info(f"Detected employee last-name column: **{last_name_col}**")

    memory_zip = BytesIO()
    with zipfile.ZipFile(memory_zip, "w") as zf:
        for last_name in df[last_name_col].dropna().unique():
            employee_data = df[df[last_name_col] == last_name]
            buf = StringIO()
            employee_data.to_csv(buf, index=False)
            zf.writestr(f"{last_name}_AMEX_Claim.csv", buf.getvalue())
    memory_zip.seek(0)
    return memory_zip
    """Split dataframe by employee last name and package into downloadable ZIP."""
    # Example logic stub – replace with your export process
    from io import BytesIO
    import zipfile

    memory_zip = BytesIO()
    with zipfile.ZipFile(memory_zip, "w") as zf:
        for last_name in df["Supplemental Cardmember Last Name"].dropna().unique():
            employee_data = df[df["Supplemental Cardmember Last Name"] == last_name]
            buf = StringIO()
            employee_data.to_csv(buf, index=False)
            zf.writestr(f"{last_name}_AMEX_Claim.csv", buf.getvalue())
    memory_zip.seek(0)
    return memory_zip


# --- Streamlit interface ---

uploaded_file = st.file_uploader("📤 Upload Amex statement", type=["csv", "xls", "xlsx"])
export_format = st.selectbox("Select output format", ["csv", "excel"])

if uploaded_file is not None:
    df = read_file(uploaded_file)
    if st.button("⚙️ Process and Generate Files"):
        with st.spinner("Processing statement..."):
            cleaned = process_statement(df)
            zip_data = split_by_employee(cleaned, export_format)
        st.success("✅ Processing complete! Download your files below.")
        st.download_button("⬇️ Download ZIP", data=zip_data, file_name="Amex_Output.zip", mime="application/zip")
