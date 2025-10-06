import streamlit as st
import pandas as pd
import openpyxl
import csv
import io
from io import BytesIO, StringIO
import re
import zipfile
import os
import sys
import logging
from pathlib import Path

# ==============================
# 🔧 BACKEND BUSINESS LOGIC LAYER
# ==============================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

class FileHandler:
    """Handles loading and validation of uploaded data files."""

    @staticmethod
    def load_dataframe(uploaded_file) -> pd.DataFrame:
        """Auto-detect file type and read into a DataFrame."""
        name = uploaded_file.name.lower()
        st.info(f"📂 Loading file: {name}")

        try:
            if name.endswith(".csv"):
                sample = uploaded_file.read(2048).decode("utf-8", errors="ignore")
                uploaded_file.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    sep = dialect.delimiter
                except Exception:
                    sep = ","
                df = pd.read_csv(
                    uploaded_file,
                    skiprows=12,
                    header=0,
                    sep=sep,
                    engine="python",
                    encoding="utf-8",
                    on_bad_lines="skip",
                )
            elif name.endswith((".xls", ".xlsx")):
                df = pd.read_excel(uploaded_file, skiprows=12, header=0, engine="openpyxl")
            else:
                st.error("❌ Unsupported file type. Please upload a CSV or Excel file.")
                st.stop()

            df.columns = (
                df.columns.str.replace("\n", " ", regex=False)
                .str.replace(r"\s+", " ", regex=True)
                .str.strip()
            )

            st.success(f"✅ Loaded {len(df)} rows, {len(df.columns)} columns.")
            st.dataframe(df.head(10))
            return df

        except Exception as e:
            st.error(f"❌ Error reading uploaded file: {e}")
            st.stop()


class AmexCleaner:
    """Handles transformation and cleaning of Amex statement data."""

    @staticmethod
    def clean_amounts(df: pd.DataFrame) -> pd.DataFrame:
        """Convert monetary strings to numeric and filter out negatives."""
        amount_cols = [c for c in df.columns if "amount" in c.lower()]
        for col in amount_cols:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace("$", "", regex=False)
                .str.replace(",", "", regex=False)
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
            before = len(df)
            df = df[df[col] >= 0]
            after = len(df)
            logging.info(f"Filtered negatives in {col}: {before - after} rows removed")
        return df


# ==============================
# 🌐 FRONT-END STREAMLIT APP
# ==============================

st.set_page_config(page_title="Amex → Acumatica Self-Service", layout="centered")

st.title("💳 Amex → Acumatica Converter")
st.caption("Upload your Amex statement (.csv or .xlsx) and generate employee-specific claim files.")

uploaded_file = st.file_uploader("📤 Upload Amex statement", type=["csv", "xls", "xlsx"])
export_format = st.selectbox("Select output format", ["csv", "excel"])

if uploaded_file is not None:
    df = FileHandler.load_dataframe(uploaded_file)

    if st.button("⚙️ Process and Generate Files"):
        with st.spinner("Processing statement..."):
            cleaned = AmexCleaner.clean_amounts(df)

            # Detect the employee "Last Name" column dynamically
            detected_col = None
            for col in cleaned.columns:
                normalized = re.sub(r"\s+", " ", col.strip().lower())
                if re.search(r"supplemental.*cardmember.*last", normalized):
                    detected_col = col
                    break
            if not detected_col:
                for col in cleaned.columns:
                    normalized = re.sub(r"\s+", " ", col.strip().lower())
                    if re.search(r"cardmember.*last", normalized):
                        detected_col = col
                        break

            if not detected_col:
                st.error("❌ Could not find a 'Supplemental Cardmember Last Name' column.")
                st.write("Available columns:", cleaned.columns.tolist())
                st.stop()

            st.info(f"Detected employee last name column: **{detected_col}**")

            # Create per-employee ZIP file
            memory_zip = BytesIO()
            with zipfile.ZipFile(memory_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for last_name in cleaned[detected_col].dropna().unique():
                    employee_data = cleaned[cleaned[detected_col] == last_name]
                    buf = StringIO()
                    employee_data.to_csv(buf, index=False)
                    zf.writestr(f"{last_name}_AMEX_Claim.csv", buf.getvalue())

            memory_zip.seek(0)

        st.success("✅ Processing complete! Download your files below.")
        st.download_button(
            "⬇️ Download ZIP",
            data=memory_zip,
            file_name="Amex_Output.zip",
            mime="application/zip",
        )
