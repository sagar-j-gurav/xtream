# TESS Knowledge Base Upload Guide

This guide explains how to upload FAQs and content to the TESS knowledge base using **form-data** (file uploads).

## Prerequisites

1. **TESS server must be running:**
   ```bash
   ./start.sh dev
   ```

2. **For Python scripts** (optional - CURL also works):
   ```bash
   pip install requests
   ```

## Quick Start

### Upload FAQ File (Excel/CSV)

**Expected columns in your Excel/CSV file:**
- `QUESTION` (required)
- `ANSWER` (required)
- `SL.NO` (optional - serial number)
- `Document Linkage` (optional - reference links)

**Using Python script:**
```bash
python upload_faqs_from_excel.py your_faqs.xlsx
```

**Using CURL:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-faqs \
  -F "file=@your_faqs.xlsx" \
  -F "source=my_faqs"
```

### Upload Content File (Text)

**Using Python script:**
```bash
python upload_content_from_txt.py your_content.txt
```

**Using CURL:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-content \
  -F "file=@your_content.txt" \
  -F "url=https://example.com/docs" \
  -F "page_title=Product Documentation"
```

---

## Method 1: Using Python Helper Scripts (Recommended)

### Upload FAQs from Excel/CSV

**Command:**
```bash
python upload_faqs_from_excel.py faqs.xlsx
```

**With custom API URL:**
```bash
python upload_faqs_from_excel.py faqs.xlsx http://localhost:8000
```

**With custom source identifier:**
```bash
python upload_faqs_from_excel.py faqs.xlsx http://localhost:8000 my_source
```

**Expected file format:**

| SL.NO | QUESTION | ANSWER | Document Linkage |
|-------|----------|--------|------------------|
| 1 | What is your refund policy? | We offer 30-day refunds... | https://docs.example.com/refund |
| 2 | How long does shipping take? | Standard shipping takes 3-5 days | https://docs.example.com/shipping |

✅ **Supports:** `.xlsx`, `.xls`, `.csv`
✅ **Case-insensitive** column names
✅ **Automatically skips** empty rows

### Upload Content from Text File

**Command:**
```bash
python upload_content_from_txt.py docs.txt
```

**With custom URL and title:**
```bash
python upload_content_from_txt.py docs.txt "https://example.com/docs" "Product Documentation"
```

**Auto-generates title** from filename if not provided.

---

## Method 2: Using CURL Commands

### Upload FAQs (Excel/CSV File)

**Basic upload:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-faqs \
  -F "file=@faqs.xlsx"
```

**With source identifier:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-faqs \
  -F "file=@faqs.xlsx" \
  -F "source=customer_support_faqs"
```

**Upload CSV instead:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-faqs \
  -F "file=@faqs.csv" \
  -F "source=csv_import"
```

**Expected response:**
```json
{
  "indexed": 10,
  "source": "customer_support_faqs_faqs.xlsx",
  "type": "faq",
  "filename": "faqs.xlsx"
}
```

### Upload Content (Text File)

**Basic upload:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-content \
  -F "file=@documentation.txt"
```

**With URL and title:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-content \
  -F "file=@documentation.txt" \
  -F "url=https://example.com/docs" \
  -F "page_title=Product Documentation"
```

**Expected response:**
```json
{
  "indexed": 15,
  "source": "https://example.com/docs_documentation.txt",
  "type": "website_content",
  "chunk_size": 1000,
  "filename": "documentation.txt"
}
```

---

## Configuration

### Chunking Settings

Chunking is configured in `.env.dev` (or `.env.uat`, `.env.prod`):

```bash
# FAQ chunking (each Q&A pair = 1 chunk, no splitting)
FAQ_CHUNK_SIZE=2000

# Website content chunking (semantic splitting)
WEBSITE_CHUNK_SIZE=1000
WEBSITE_CHUNK_OVERLAP=200
```

**Best practices:**
- **FAQs**: Each question-answer pair stays together (no splitting)
- **Website content**: 800-1200 chars with 150-200 overlap for semantic search

---

## Example Data Files

This repository includes example files for testing:

### 1. Example FAQ CSV (`example_faqs.csv`)

```csv
QUESTION,ANSWER,SL.NO,Document Linkage
What is your refund policy?,We offer 30-day money-back guarantee...,1,
How long does shipping take?,Standard shipping takes 3-5 business days.,2,
```

**Convert to Excel:**
```bash
# Using Python
python -c "import pandas as pd; pd.read_csv('example_faqs.csv').to_excel('example_faqs.xlsx', index=False)"
```

**Upload:**
```bash
python upload_faqs_from_excel.py example_faqs.xlsx
```

### 2. Example Content (`example_content.txt`)

Contains sample documentation text.

**Upload:**
```bash
python upload_content_from_txt.py example_content.txt
```

---

## Testing Your Uploads

### Check Upload Success

Both scripts show success messages:
```
✅ SUCCESS! Indexed 10 FAQs
📁 Source: customer_support_faqs_faqs.xlsx
📄 File: faqs.xlsx
🏷️  Type: faq
```

### Query TESS to Verify

```bash
curl -X POST http://0.0.0.0:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is your refund policy?",
    "session_id": "test-123",
    "user_id": "test@example.com"
  }'
```

**Expected:** TESS answers using the uploaded knowledge!

---

## Advanced Usage

### Bulk Upload Multiple Files

```bash
# Upload all Excel files in a directory
for file in faqs_*.xlsx; do
    echo "📤 Uploading $file..."
    python upload_faqs_from_excel.py "$file"
    sleep 1  # Brief pause
done
```

### Upload with Custom Headers

```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-faqs \
  -H "X-Custom-Header: value" \
  -F "file=@faqs.xlsx" \
  -F "source=api_import"
```

### Check API Health

```bash
curl http://0.0.0.0:8000/api/v1/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "services": {
    "chromadb": "healthy",
    "postgresql": "healthy",
    "openai": "healthy"
  }
}
```

---

## Troubleshooting

### Error: "File must have 'QUESTION' and 'ANSWER' columns"

**Cause:** Your Excel/CSV doesn't have the required columns.

**Solution:** Ensure columns are named `QUESTION` and `ANSWER` (case-insensitive).

**Check your columns:**
```bash
python -c "import pandas as pd; print(pd.read_excel('your_file.xlsx').columns.tolist())"
```

### Error: "File must be Excel (.xlsx, .xls) or CSV (.csv)"

**Cause:** Wrong file type uploaded.

**Solution:** Convert to supported format or use correct endpoint.

### Error: "Unable to decode file"

**Cause:** Text file has invalid encoding.

**Solution:** Convert to UTF-8:
```bash
iconv -f ISO-8859-1 -t UTF-8 input.txt > output.txt
```

### Error: Connection refused

**Cause:** TESS server not running.

**Solution:**
```bash
./start.sh dev
# Wait for "Application startup complete"
```

### FAQs not being retrieved by agent

**Check ChromaDB:**
```bash
# View logs - should show "chromadb: healthy"
tail -f logs/tess.log
```

**Verify indexing:**
- Upload response should show `"indexed": N` where N > 0
- Check logs for "Indexed N chunks"

**Increase search results:**
Update `.env.dev`:
```bash
CHROMA_TOP_K=10  # Default is 5
```

### Empty or "nan" values in FAQs

**Cause:** Excel has empty cells or formulas evaluating to NaN.

**Solution:**
- Fill all required cells
- Convert formulas to values
- Remove empty rows

---

## API Documentation

### View Interactive Docs

**Swagger UI:**
```
http://0.0.0.0:8000/docs
```

**ReDoc:**
```
http://0.0.0.0:8000/redoc
```

### API Endpoints

**Upload FAQs:**
- **Endpoint:** `POST /api/v1/knowledge/upload-faqs`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file` (required): Excel/CSV file
  - `source` (optional): Source identifier

**Upload Content:**
- **Endpoint:** `POST /api/v1/knowledge/upload-content`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file` (required): Text file
  - `url` (optional): Source URL
  - `page_title` (optional): Page title

---

## Need Help?

- **Health check:** `curl http://0.0.0.0:8000/api/v1/health`
- **API docs:** http://0.0.0.0:8000/docs
- **View logs:** `tail -f logs/tess.log` (if using PM2) or check console output
- **Check ChromaDB:** Verify `data/chromadb/` directory exists and contains data
