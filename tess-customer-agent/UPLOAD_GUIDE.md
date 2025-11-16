# TESS Knowledge Base Upload Guide

This guide explains how to upload FAQs and content to the TESS knowledge base.

## Prerequisites

1. TESS server must be running:
   ```bash
   ./start.sh dev
   ```

2. For Python scripts, install pandas and openpyxl:
   ```bash
   pip install pandas openpyxl requests
   ```

## Method 1: Using Python Helper Scripts (Recommended)

### Upload FAQs from Excel

Your Excel file should have these columns:
- `question` (required)
- `answer` (required)
- `category` (optional)

**Command:**
```bash
python upload_faqs_from_excel.py your_faqs.xlsx
```

**With custom API URL:**
```bash
python upload_faqs_from_excel.py your_faqs.xlsx http://localhost:8000
```

**Example Excel format:**

| question | answer | category |
|----------|--------|----------|
| What is your refund policy? | We offer 30-day refunds... | policies |
| How long does shipping take? | Standard shipping takes 3-5 days | shipping |

You can also use CSV and save as .xlsx in Excel.

### Upload Content from Text File

**Command:**
```bash
python upload_content_from_txt.py your_content.txt
```

**With custom URL and title:**
```bash
python upload_content_from_txt.py docs.txt "https://example.com/docs" "Product Documentation"
```

## Method 2: Using CURL Commands

### Upload FAQs (JSON format)

**Step 1:** Create a JSON file `faqs.json`:
```json
{
  "faqs": [
    {
      "question": "What is your refund policy?",
      "answer": "We offer a 30-day money-back guarantee on all products.",
      "category": "policies"
    },
    {
      "question": "How long does shipping take?",
      "answer": "Standard shipping takes 3-5 business days.",
      "category": "shipping"
    }
  ],
  "source": "excel_import"
}
```

**Step 2:** Upload with CURL:
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-faqs \
  -H "Content-Type: application/json" \
  -d @faqs.json
```

**Or inline:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-faqs \
  -H "Content-Type: application/json" \
  -d '{
    "faqs": [
      {
        "question": "What is your refund policy?",
        "answer": "We offer 30-day money-back guarantee.",
        "category": "policies"
      }
    ],
    "source": "manual_upload"
  }'
```

### Upload Content from Text File

**Direct from file:**
```bash
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-content \
  -H "Content-Type: application/json" \
  -d "{
    \"content\": \"$(cat your_content.txt | sed 's/\"/\\\"/g' | sed 's/$/\\n/' | tr -d '\n')\",
    \"url\": \"manual_upload\",
    \"page_title\": \"Documentation\",
    \"chunk_size\": 1000,
    \"chunk_overlap\": 200
  }"
```

**With JSON file:**
```bash
# Create content.json
{
  "content": "Your content here...",
  "url": "https://example.com/docs",
  "page_title": "Product Documentation",
  "chunk_size": 1000,
  "chunk_overlap": 200
}

# Upload
curl -X POST http://0.0.0.0:8000/api/v1/knowledge/upload-content \
  -H "Content-Type: application/json" \
  -d @content.json
```

## Method 3: Converting CSV to Excel for FAQs

If you have a CSV file:

1. **Using Python:**
   ```python
   import pandas as pd
   df = pd.read_csv('faqs.csv')
   df.to_excel('faqs.xlsx', index=False)
   ```

2. **Using Excel:** Open CSV in Excel and Save As → Excel Workbook (.xlsx)

3. **Then upload:** `python upload_faqs_from_excel.py faqs.xlsx`

## Testing Your Uploads

### Check Upload Success

Both scripts will show success messages:
```
✅ SUCCESS! Indexed 10 FAQs
Source: excel_import_your_faqs.xlsx
Type: faq
```

### Query TESS to Verify

```bash
curl -X POST http://0.0.0.0:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is your refund policy?",
    "session_id": "test-session",
    "user_id": "test@example.com"
  }'
```

TESS should now answer using the uploaded knowledge!

## Examples Provided

This repository includes example files:
- `example_faqs.csv` - Sample FAQ data
- `example_content.txt` - Sample documentation content

Try them:
```bash
# Convert CSV to Excel first (or open in Excel and save as .xlsx)
python -c "import pandas as pd; pd.read_csv('example_faqs.csv').to_excel('example_faqs.xlsx', index=False)"

# Upload
python upload_faqs_from_excel.py example_faqs.xlsx
python upload_content_from_txt.py example_content.txt
```

## API Response Format

### Successful FAQ Upload
```json
{
  "indexed": 10,
  "source": "excel_import_faqs.xlsx",
  "type": "faq"
}
```

### Successful Content Upload
```json
{
  "indexed": 15,
  "source": "https://example.com/docs",
  "type": "website_content",
  "chunk_size": 1000
}
```

### Error Response
```json
{
  "detail": "Failed to upload FAQs"
}
```

## Troubleshooting

### Excel file error: "No module named 'openpyxl'"
```bash
pip install openpyxl
```

### CURL error: "Failed to connect"
- Check TESS is running: `curl http://0.0.0.0:8000/api/v1/health`
- Verify port in your .env.dev file

### "Invalid parameter" errors
- Ensure JSON is properly formatted (use a validator like jsonlint.com)
- Check quotes are properly escaped in CURL commands

### FAQs not being retrieved
- Check ChromaDB is running: logs should show "chromadb: healthy"
- Verify embeddings are created (check logs during upload)
- Try increasing the search result limit in settings

## Advanced: Bulk Operations

For large datasets:

1. **Split into batches** (recommended: 100 FAQs per file)
2. **Upload sequentially** to avoid overwhelming the server
3. **Monitor logs** for indexing progress

```bash
for file in faqs_batch_*.xlsx; do
    echo "Uploading $file..."
    python upload_faqs_from_excel.py "$file"
    sleep 2  # Brief pause between uploads
done
```

## Need Help?

- Check API docs: http://0.0.0.0:8000/docs
- View health status: http://0.0.0.0:8000/api/v1/health
- Check logs in console where TESS is running
