import os
import re
import io
import requests
import pandas as pd
from urllib.parse import unquote

# ================= CONFIGURATION =================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1c6BJ5A3dlZuzrodKPkqNqJi0NVDRmOQYnmjG2OwmEYI"
OUTPUT_DIR = "downloaded_pdfs"
# =================================================

os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_sheet_id(url):
    match = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None


def extract_file_id(url):
    """Extract Google Drive/Docs file ID from various public URL formats."""
    url = unquote(url)
    match = re.search(r"(?:/d/|id=)([a-zA-Z0-9_-]{15,})", url)
    return match.group(1) if match else None


def get_all_sheets_data(sheet_url):
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        raise ValueError("Invalid Google Sheet URL. Make sure it contains '/d/ID/'.")

    # Public sheets can be downloaded as XLSX without auth
    export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx"
    print("📥 Fetching all sheets...")
    resp = requests.get(export_url, allow_redirects=True)

    excel_file = pd.ExcelFile(io.BytesIO(resp.content))
    all_data = {}
    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        all_data[sheet_name] = df
    return all_data


def extract_last_name(full_name):
    full_name = str(full_name).strip()
    if not full_name or full_name.lower() in ("nan", "none", ""):
        return "Unknown"
    parts = full_name.split()
    return parts[0] if parts else "Unknown"


def sanitize(name):
    """Remove characters invalid for filenames."""
    name = re.sub(r'[<>:"/\\|?*]', "_", str(name))
    name = re.sub(r"\s+", "_", name.strip())
    return name or "empty"


def download_and_validate_pdf(url, filepath):
    try:
        resp = requests.get(url, stream=True, timeout=30, allow_redirects=True)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        # Verify it's actually a PDF and not an HTML error/access page
        first_bytes = resp.content[:10]
        if not first_bytes.startswith(b"%PDF"):
            return False, "Access restricted / Not a PDF"

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True, "Success"
    except Exception as e:
        return False, str(e)


def resolve_download_url(doc_url):
    """Return the best public download URL for a given link."""
    try:
        url = unquote(doc_url).strip()

        # 1. Direct PDF link
        if url.lower().endswith(".pdf"):
            return url

        # 2. Native Google Docs/Sheets/Slides viewer URL
        if "docs.google.com" in url:
            fid = extract_file_id(url)
            if fid:
                return f"https://docs.google.com/document/d/{fid}/export?format=pdf"

        # 3. drive.google.com shared link
        if "drive.google.com" in url:
            fid = extract_file_id(url)
            if fid:
                # Try direct Drive download first (works for hosted PDFs)
                return f"https://drive.google.com/uc?export=download&id={fid}&confirm=no_antivirus"

        # Fallback: try direct URL anyway
        return url
    except:
        return None


def format_date_to_day_month(val):
    s = str(val).strip()
    # Handle YYYY-MM-DD format
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(3)}_{m.group(2)}"
    # Handle DD/MM/YYYY or DD.MM.YYYY
    m = re.search(r"(\d{1,2})[./\-](\d{1,2})[./\-](\d{4}|\d{2})", s)
    if m:
        return f"{int(m.group(1)):02}_{int(m.group(2)):02}"
    # Fallback
    return sanitize(s.replace(":", "")) or "0000"


def main():
    print("🔍 Checking public access...")
    try:
        sheets_data = get_all_sheets_data(SHEET_URL)
    except Exception as e:
        print(f"❌ {e}")
        return

    counter = 1
    total_success = 0
    last_valid_time = "00_00"

    for sheet_name, df in sheets_data.items():
        print(f"\n📄 Processing sheet: {sheet_name}")
        # Normalize column names to lowercase for robust matching
        df.columns = [str(c).lower().strip() for c in df.columns]
        # print(df.columns)

        required_cols = {
            "дата/date",
            "фио/full name",
        }
        if not required_cols.issubset(df.columns):
            print(f"  ⚠️  Missing columns {required_cols - set(df.columns)}. Skipping sheet.")
            continue

        for _, row in df.iterrows():
            raw_time = row.iloc[0]
            full_name = row.iloc[2]
            doc_url = row.iloc[3]

            # Clean date (remove colons)
            if pd.isna(raw_time) or str(raw_time).strip().lower() in ("nat", "nan", ""):
                time_clean = last_valid_time
            else:
                time_clean = format_date_to_day_month(raw_time)
                if re.match(r"\d{2}_\d{2}", time_clean):
                    last_valid_time = time_clean

            # Extract & clean last name
            last_name = sanitize(extract_last_name(full_name))
            sheet_clean = sanitize(sheet_name)

            # Build filename: sheet_time_lastname_counter.pdf
            filename = f"sheet_{sheet_clean}_{time_clean}_{last_name}.pdf"
            filepath = os.path.join(OUTPUT_DIR, filename)

            if os.path.exists(filepath):
                print(f"  ⏳ {filename} ... ✅ Already Exists!")
                continue

            download_url = resolve_download_url(doc_url)
            if not download_url:
                print(f"  ⏳ {filename} ... ⚠️ Skipped: No download URL | URL: {doc_url}")
                continue

            print(f"  ⏳ {filename} ...", end=" ")
            success, msg = download_and_validate_pdf(download_url, filepath)

            if success:
                print("✅")
                counter += 1
                total_success += 1
            else:
                if os.path.exists(filepath):
                    os.remove(filepath)
                print(f"⚠️ Skipped: {msg} | URL: {doc_url}")

    print(f"\n🎉 Finished! {total_success} PDFs saved in '{OUTPUT_DIR}/'")


if __name__ == "__main__":
    main()
