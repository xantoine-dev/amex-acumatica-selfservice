import streamlit as st
import pandas as pd
import openpyxl
import csv
from io import StringIO

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
