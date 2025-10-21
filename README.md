# Amex-Acumatica Self-Service

A Streamlit-based application for converting American Express statement data into a format compatible with Acumatica’s self-service imports. This tool reads your Amex statements (CSV or Excel), cleans and transforms the transaction data, and outputs a processed file ready for upload.

## Features

- **Easy Upload:** Upload your Amex statement as a CSV or Excel file; the app auto-detects the format.
- **Data Cleaning:** Automatically strips currency symbols, converts monetary strings to numeric types, and filters out any negative amounts.
- **Customizable Processing:** Uses Python pandas and a modular `FileHandler` / `AmexCleaner` architecture so you can extend or adapt the business logic.
- **Streamlit UI:** A simple web interface built with Streamlit for interacting with your data without writing code.

## Getting Started

1. **Clone the repository:**

   ```bash
   git clone https://github.com/xantoine-dev/amex-acumatica-selfservice.git
   cd amex-acumatica-selfservice
   ```

2. **Install the dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app with Streamlit:**

   ```bash
   streamlit run Amex2acumatica_DELTA_1.0.1.py
   ```

4. **Upload your statement:**
   - When the app launches in your browser, choose your Amex statement file (CSV or Excel).
   - Wait for the processing to finish; a cleaned DataFrame is displayed with columns sanitized and negatives removed.
   - Download the processed file for import into Acumatica.

## Technologies Used

- **Python**
- **pandas**
- **Streamlit**
- **openpyxl**

## Project Structure

- `Amex2acumatica_DELTA_1.0.1.py` – Core application logic, including file handling and data cleaning classes.
- `requirements.txt` – List of Python dependencies.
- `.devcontainer/` – Configuration for developing in a containerized environment.

## License

This project is released under the MIT License.
