"""
Upload FAQs from Excel file to TESS knowledge base
Usage: python upload_faqs_from_excel.py <excel_file.xlsx>
"""
import sys
import pandas as pd
import requests
import json

def upload_faqs_from_excel(excel_file: str, api_url: str = "http://0.0.0.0:8000"):
    """
    Upload FAQs from Excel file

    Excel file should have columns:
    - question (or Question)
    - answer (or Answer)
    - category (or Category) - optional
    """
    print(f"Reading FAQs from {excel_file}...")

    # Read Excel file
    df = pd.read_excel(excel_file)

    # Normalize column names (lowercase)
    df.columns = df.columns.str.lower()

    # Check required columns
    if 'question' not in df.columns or 'answer' not in df.columns:
        print("ERROR: Excel file must have 'question' and 'answer' columns")
        print(f"Found columns: {list(df.columns)}")
        sys.exit(1)

    # Convert to FAQ format
    faqs = []
    for idx, row in df.iterrows():
        faq = {
            "question": str(row['question']).strip(),
            "answer": str(row['answer']).strip()
        }

        # Add category if available
        if 'category' in df.columns and pd.notna(row['category']):
            faq['category'] = str(row['category']).strip()

        # Skip empty rows
        if faq['question'] and faq['answer']:
            faqs.append(faq)

    print(f"Found {len(faqs)} valid FAQs")

    if len(faqs) == 0:
        print("No valid FAQs found. Exiting.")
        sys.exit(1)

    # Upload to TESS
    print(f"Uploading to {api_url}/api/v1/knowledge/upload-faqs...")

    response = requests.post(
        f"{api_url}/api/v1/knowledge/upload-faqs",
        json={
            "faqs": faqs,
            "source": f"excel_import_{excel_file}"
        },
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS! Indexed {result['indexed']} FAQs")
        print(f"Source: {result['source']}")
        print(f"Type: {result['type']}")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_faqs_from_excel.py <excel_file.xlsx>")
        print("\nExcel file should have columns:")
        print("  - question (required)")
        print("  - answer (required)")
        print("  - category (optional)")
        sys.exit(1)

    excel_file = sys.argv[1]
    api_url = sys.argv[2] if len(sys.argv) > 2 else "http://0.0.0.0:8000"

    upload_faqs_from_excel(excel_file, api_url)
