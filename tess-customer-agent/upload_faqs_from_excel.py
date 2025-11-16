"""
Upload FAQs from Excel/CSV file to TESS knowledge base
Usage: python upload_faqs_from_excel.py <excel_file.xlsx>

Supports Excel (.xlsx, .xls) and CSV (.csv) files
"""
import sys
import requests
import os

def upload_faqs_from_excel(
    file_path: str,
    api_url: str = "http://0.0.0.0:8000",
    source: str = "script_upload"
):
    """
    Upload FAQs from Excel/CSV file using form-data

    Excel/CSV file should have columns:
    - QUESTION (required)
    - ANSWER (required)
    - SL.NO (optional - serial number)
    - Document Linkage (optional)
    """
    # Validate file exists
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found: {file_path}")
        sys.exit(1)

    # Validate file extension
    file_ext = file_path.lower()
    if not (file_ext.endswith('.xlsx') or file_ext.endswith('.xls') or file_ext.endswith('.csv')):
        print("❌ ERROR: File must be Excel (.xlsx, .xls) or CSV (.csv)")
        sys.exit(1)

    print(f"📤 Uploading FAQs from {file_path}...")

    # Upload file using multipart/form-data
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        data = {'source': source}

        response = requests.post(
            f"{api_url}/api/v1/knowledge/upload-faqs",
            files=files,
            data=data
        )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS! Indexed {result['indexed']} FAQs")
        print(f"📁 Source: {result['source']}")
        print(f"📄 File: {result['filename']}")
        print(f"🏷️  Type: {result['type']}")
    else:
        print(f"❌ ERROR: {response.status_code}")
        try:
            error_detail = response.json().get('detail', response.text)
            print(f"Details: {error_detail}")
        except:
            print(response.text)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_faqs_from_excel.py <file.xlsx|csv> [api_url] [source]")
        print("\nExpected columns in Excel/CSV:")
        print("  - QUESTION (required)")
        print("  - ANSWER (required)")
        print("  - SL.NO (optional)")
        print("  - Document Linkage (optional)")
        print("\nExamples:")
        print("  python upload_faqs_from_excel.py faqs.xlsx")
        print("  python upload_faqs_from_excel.py faqs.csv http://localhost:8000")
        print("  python upload_faqs_from_excel.py faqs.xlsx http://localhost:8000 my_source")
        sys.exit(1)

    file_path = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://0.0.0.0:8000"
    source = sys.argv[3] if len(sys.argv) > 3 else "script_upload"

    upload_faqs_from_excel(file_path, api_url, source)
