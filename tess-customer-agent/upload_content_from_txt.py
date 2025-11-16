"""
Upload content from text file to TESS knowledge base
Usage: python upload_content_from_txt.py <text_file.txt> [url] [title]

Automatically uses chunking settings from TESS configuration
"""
import sys
import requests
import os

def upload_content_from_txt(
    txt_file: str,
    url: str = "manual_upload",
    page_title: str = None,
    api_url: str = "http://0.0.0.0:8000"
):
    """
    Upload content from text file using form-data

    Args:
        txt_file: Path to text file
        url: Source URL identifier
        page_title: Title for the content (auto-generated from filename if not provided)
        api_url: TESS API base URL
    """
    # Validate file exists
    if not os.path.exists(txt_file):
        print(f"❌ ERROR: File not found: {txt_file}")
        sys.exit(1)

    # Validate file extension
    if not txt_file.lower().endswith('.txt'):
        print("❌ ERROR: File must be a text file (.txt)")
        sys.exit(1)

    # Auto-generate page title from filename if not provided
    if not page_title:
        page_title = os.path.basename(txt_file).replace('.txt', '').replace('_', ' ').title()

    print(f"📤 Uploading content from {txt_file}...")
    print(f"📄 Page title: {page_title}")

    # Upload file using multipart/form-data
    with open(txt_file, 'rb') as f:
        files = {'file': (os.path.basename(txt_file), f)}
        data = {
            'url': url,
            'page_title': page_title
        }

        response = requests.post(
            f"{api_url}/api/v1/knowledge/upload-content",
            files=files,
            data=data
        )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS! Indexed {result['indexed']} chunks")
        print(f"📁 Source: {result['source']}")
        print(f"📄 File: {result['filename']}")
        print(f"🏷️  Type: {result['type']}")
        print(f"📏 Chunk size: {result['chunk_size']}")
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
        print("Usage: python upload_content_from_txt.py <text_file.txt> [url] [title]")
        print("\nExamples:")
        print("  python upload_content_from_txt.py docs.txt")
        print("  python upload_content_from_txt.py docs.txt https://example.com/docs")
        print("  python upload_content_from_txt.py docs.txt https://example.com/docs 'Product Documentation'")
        print("\nNote: Chunking size/overlap is configured in TESS settings")
        sys.exit(1)

    txt_file = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else "manual_upload"
    page_title = sys.argv[3] if len(sys.argv) > 3 else None

    upload_content_from_txt(txt_file, url, page_title)
