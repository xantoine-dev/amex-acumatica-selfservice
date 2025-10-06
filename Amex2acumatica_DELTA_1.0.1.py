import streamlit as st
import pandas as pd
import openpyxl
import csv
import io
from io import BytesIO, StringIO
import re
import zipfile

st.set_page_config(page_title="Amex → Acumatica Self-Service", layout="centered")

st.title("💳 Amex → Acumatica Converter")
st.caption("Upload your Amex statement (.csv or .xlsx) and generate employee-specific claim files.")


# ------------------ HELPERS ------------------

def clean_columns(df):
    """Standardize and clean column headers."""
    df.columns = (
        df.columns.astype(str)
        .str.replace("\n", " ", regex=False)
        .str.replace(r"\s+", " ", regex=True)
        .str.strip()
    )
    return df


def read_file(uploaded_file):
    """Reads uploaded CSV or Excel safely with auto-delimiter and cleans headers."""
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        # Detect delimiter
        sample = uploaded_file.read(2048).decode("utf-8", errors="ignore")
        uploaded_file.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
            sep = dialect.delimiter
        except Exception:
            sep = ","

        st.info(f"Detected delimiter: '{sep}'")

        df = pd.read_csv(
            uploaded_file,
            header=13,  # Start from row 14
            skip_blank_lines=True,
            on_bad_lines="skip",
            sep=sep,
            engine="python",
            encoding="utf-8",
        )

    elif name.endswith((".xls", ".xlsx")):
        df = pd.read_excel(uploaded_file, header=13, engine="openpyxl")

    else:
        st.error("❌ Unsupported file type. Please upload a CSV or Excel file.")
        st.stop()

    df = clean_columns(df)
    st.success(f"✅ Loaded {len(df)} rows with {len(df.columns)} columns.")
    st.dataframe(df.head(10))
    return df


def process_statement(df):
    """Example Amex cleaning logic."""
    for col in df.columns:
        if "amount" in col.lower():
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("$", "", regex=False)
                .str.replace(",", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def split_by_employee(df, export_format):
    """Split dataframe by employee last name column (auto-detected) and zip outputs."""
    detected_col = None

    # Attempt to auto-detect the 'Last Name' column
    for col in df.columns:
        normalized = re.sub(r"\s+", " ", col.strip().lower())
        if re.search(r"supplemental.*cardmember.*last", normalized):
            detected_col = col
            break
    if not detected_col:
        for col in df.columns:
            normalized = re.sub(r"\s+", " ", col.strip().lower())
            if re.search(r"cardmember.*last", normalized):
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

    # --- Create per-employee claim ZIP ---
    memory_zip = BytesIO()
    with zipfile.ZipFile(memory_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for last_name in df[detected_col].dropna().unique():
            employee_data = df[df[detected_col] == last_name]
            buf = StringIO()
            employee_data.to_csv(buf, index=False)
            zf.writestr(f"{last_name}_AMEX_Claim.csv", buf.getvalue())

    memory_zip.seek(0)
    return memory_zip


# ------------------ UI ------------------

uploaded_file = st.file_uploader("📤 Upload Amex statement", type=["csv", "xls", "xlsx"])
export_format = st.selectbox("Select output format", ["csv", "excel"])

if uploaded_file is not None:
    df = read_file(uploaded_file)
    if st.button("⚙️ Process and Generate Files"):
        with st.spinner("Processing statement..."):
            cleaned = process_statement(df)
            zip_data = split_by_employee(cleaned, export_format)
        st.success("✅ Processing complete! Download your files below.")
        st.download_button(
            "⬇️ Download ZIP",
            data=zip_data,
            file_name="Amex_Output.zip",
            mime="application/zip",
        )
