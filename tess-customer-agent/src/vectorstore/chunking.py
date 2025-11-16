"""
Smart Document Chunking Strategies for TESS
Different strategies for FAQs vs website content
"""
from typing import List, Dict, Any, Tuple
import re
from src.vectorstore.chromadb_client import get_chroma_client
from src.utils.logging import get_logger

logger = get_logger(__name__)


def chunk_faq_data(
    faqs: List[Dict[str, str]],
    source: str = "faq"
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Chunk FAQ data (question-answer pairs)

    Each FAQ is stored as a single chunk to preserve Q&A integrity

    Args:
        faqs: List of dicts with 'question' and 'answer' keys
        source: Source identifier

    Returns:
        Tuple[List[str], List[Dict[str, Any]]]: (documents, metadatas)
    """
    documents = []
    metadatas = []

    for idx, faq in enumerate(faqs):
        question = faq.get('question', '').strip()
        answer = faq.get('answer', '').strip()
        category = faq.get('category', 'general')
        document_linkage = faq.get('document_linkage', '')

        if not question or not answer:
            logger.warning(f"Skipping FAQ {idx}: missing question or answer")
            continue

        # Format: "Q: {question}\nA: {answer}"
        # This helps the model understand the Q&A structure
        document = f"Q: {question}\nA: {answer}"

        # Add metadata
        metadata = {
            'type': 'faq',
            'category': category,
            'source': source,
            'question': question,
            'chunk_index': idx
        }

        # Add document linkage if present
        if document_linkage and document_linkage.strip():
            metadata['document_linkage'] = document_linkage.strip()

        documents.append(document)
        metadatas.append(metadata)

    logger.info(f"Created {len(documents)} FAQ chunks from {len(faqs)} FAQs")
    return documents, metadatas


def chunk_website_content(
    content: str,
    url: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    page_title: str = None
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Chunk website content with intelligent splitting

    Splits on paragraph boundaries, headings, and semantic breaks

    Args:
        content: Website content (HTML stripped)
        url: Source URL
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
        page_title: Optional page title

    Returns:
        Tuple[List[str], List[Dict[str, Any]]]: (documents, metadatas)
    """
    documents = []
    metadatas = []

    # Clean content
    content = re.sub(r'\s+', ' ', content).strip()

    # Split on semantic boundaries (paragraphs, headings)
    # Look for double newlines, headings, or list items
    segments = re.split(r'(?:\n\n+|(?=\n#)|(?=\n\*\s)|(?=\n\d+\.))', content)
    segments = [seg.strip() for seg in segments if seg.strip()]

    current_chunk = ""
    chunk_index = 0

    for segment in segments:
        # If adding this segment exceeds chunk_size, save current chunk
        if len(current_chunk) + len(segment) > chunk_size and current_chunk:
            documents.append(current_chunk.strip())
            metadatas.append({
                'type': 'website_content',
                'source': url,
                'page_title': page_title or url,
                'chunk_index': chunk_index
            })
            chunk_index += 1

            # Start new chunk with overlap
            if chunk_overlap > 0:
                # Take last chunk_overlap characters for context
                current_chunk = current_chunk[-chunk_overlap:] + " " + segment
            else:
                current_chunk = segment
        else:
            current_chunk += " " + segment if current_chunk else segment

    # Add final chunk
    if current_chunk.strip():
        documents.append(current_chunk.strip())
        metadatas.append({
            'type': 'website_content',
            'source': url,
            'page_title': page_title or url,
            'chunk_index': chunk_index
        })

    logger.info(
        f"Created {len(documents)} website content chunks from {url}",
        total_length=len(content)
    )
    return documents, metadatas


def chunk_excel_qa_data(
    rows: List[Dict[str, Any]],
    question_col: str = 'question',
    answer_col: str = 'answer',
    category_col: str = None,
    source: str = "excel_import"
) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Chunk Q&A data from Excel/CSV

    Args:
        rows: List of row dictionaries
        question_col: Column name for questions
        answer_col: Column name for answers
        category_col: Optional category column
        source: Source identifier

    Returns:
        Tuple[List[str], List[Dict[str, Any]]]: (documents, metadatas)
    """
    documents = []
    metadatas = []

    for idx, row in enumerate(rows):
        question = str(row.get(question_col, '')).strip()
        answer = str(row.get(answer_col, '')).strip()
        category = str(row.get(category_col, 'general')).strip() if category_col else 'general'

        if not question or not answer:
            logger.warning(f"Skipping row {idx}: missing question or answer")
            continue

        # Format as Q&A
        document = f"Q: {question}\nA: {answer}"

        metadata = {
            'type': 'faq',
            'category': category,
            'source': source,
            'question': question,
            'chunk_index': idx
        }

        documents.append(document)
        metadatas.append(metadata)

    logger.info(f"Created {len(documents)} Q&A chunks from {len(rows)} Excel rows")
    return documents, metadatas


async def index_faqs(
    faqs: List[Dict[str, str]],
    source: str = "faq"
) -> int:
    """
    Index FAQ data into ChromaDB

    Args:
        faqs: List of FAQ dictionaries
        source: Source identifier

    Returns:
        int: Number of chunks indexed
    """
    documents, metadatas = chunk_faq_data(faqs, source)

    if not documents:
        logger.warning("No valid FAQs to index")
        return 0

    chroma_client = get_chroma_client()
    chroma_client.add_documents(documents=documents, metadatas=metadatas)

    logger.info(f"Indexed {len(documents)} FAQ chunks")
    return len(documents)


async def index_website_content(
    content: str,
    url: str,
    page_title: str = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200
) -> int:
    """
    Index website content into ChromaDB

    Args:
        content: Website content
        url: Source URL
        page_title: Optional page title
        chunk_size: Chunk size in characters
        chunk_overlap: Overlap between chunks

    Returns:
        int: Number of chunks indexed
    """
    documents, metadatas = chunk_website_content(
        content=content,
        url=url,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        page_title=page_title
    )

    if not documents:
        logger.warning("No valid content to index")
        return 0

    chroma_client = get_chroma_client()
    chroma_client.add_documents(documents=documents, metadatas=metadatas)

    logger.info(f"Indexed {len(documents)} website content chunks")
    return len(documents)
