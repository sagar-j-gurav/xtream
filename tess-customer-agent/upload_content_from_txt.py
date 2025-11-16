"""
Upload content from text file to TESS knowledge base
Usage: python upload_content_from_txt.py <text_file.txt> [url] [title]
"""
import sys
import requests
import json

def upload_content_from_txt(
    txt_file: str,
    url: str = "manual_upload",
    page_title: str = "Documentation",
    api_url: str = "http://0.0.0.0:8000",
    chunk_size: int = 1000,
    chunk_overlap: int = 200
):
    """
    Upload content from text file

    Args:
        txt_file: Path to text file
        url: Source URL identifier
        page_title: Title for the content
        api_url: TESS API base URL
        chunk_size: Chunk size in characters
        chunk_overlap: Overlap between chunks
    """
    print(f"Reading content from {txt_file}...")

    # Read text file
    try:
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERROR: File '{txt_file}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to read file: {e}")
        sys.exit(1)

    if not content.strip():
        print("ERROR: File is empty")
        sys.exit(1)

    print(f"Content length: {len(content)} characters")

    # Upload to TESS
    print(f"Uploading to {api_url}/api/v1/knowledge/upload-content...")

    response = requests.post(
        f"{api_url}/api/v1/knowledge/upload-content",
        json={
            "content": content,
            "url": url,
            "page_title": page_title,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap
        },
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ SUCCESS! Indexed {result['indexed']} chunks")
        print(f"Source: {result['source']}")
        print(f"Type: {result['type']}")
        print(f"Chunk size: {result['chunk_size']}")
    else:
        print(f"❌ ERROR: {response.status_code}")
        print(response.text)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python upload_content_from_txt.py <text_file.txt> [url] [title]")
        print("\nExample:")
        print("  python upload_content_from_txt.py docs.txt https://example.com/docs 'Product Docs'")
        sys.exit(1)

    txt_file = sys.argv[1]
    url = sys.argv[2] if len(sys.argv) > 2 else "manual_upload"
    page_title = sys.argv[3] if len(sys.argv) > 3 else "Documentation"

    upload_content_from_txt(txt_file, url, page_title)
