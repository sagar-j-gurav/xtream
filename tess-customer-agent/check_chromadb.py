"""
Check ChromaDB Status and Contents
Usage: python check_chromadb.py
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.vectorstore.chromadb_client import get_chroma_client
from src.config.settings import get_settings


def check_chromadb():
    """Check ChromaDB collection status and contents"""

    print("=" * 80)
    print("CHROMADB STATUS CHECK")
    print("=" * 80)

    try:
        # Load settings
        settings = get_settings()
        print(f"\n📂 Collection Name: {settings.chroma_collection_name}")
        print(f"📂 Persist Directory: {settings.chroma_persist_dir}")
        print(f"🔍 Similarity Threshold: {settings.chroma_similarity_threshold}")
        print(f"📊 Top K Results: {settings.chroma_top_k}")

        # Get ChromaDB client
        print("\n🔌 Connecting to ChromaDB...")
        client = get_chroma_client()
        print("✅ Connected successfully!")

        # Get collection info
        print(f"\n📋 Collection Information:")
        info = client.get_collection_info()
        print(f"  Name: {info['name']}")
        print(f"  Document Count: {info['count']}")
        print(f"  Metadata: {info.get('metadata', {})}")

        if info['count'] == 0:
            print("\n⚠️  WARNING: Collection is EMPTY!")
            print("   You need to upload FAQs first.")
            return

        # Get sample documents
        print(f"\n📄 Sample Documents (first 5):")
        print("-" * 80)

        # Access collection directly to get samples
        collection = client.collection
        results = collection.get(limit=5, include=['documents', 'metadatas'])

        for i, (doc, metadata) in enumerate(zip(results['documents'], results['metadatas'])):
            print(f"\n{i+1}. ID: {results['ids'][i]}")
            print(f"   Content: {doc[:150]}...")
            print(f"   Metadata: {metadata}")

        # Test searches with different queries
        print("\n" + "=" * 80)
        print("SEARCH TESTS")
        print("=" * 80)

        test_queries = [
            "BOM",
            "lead time",
            "parts",
            "how to identify long lead time parts",
            "product information",
            "refund policy",
        ]

        for query in test_queries:
            print(f"\n🔎 Testing Query: '{query}'")
            print("-" * 80)

            # Perform search
            results = client.search(query, n_results=5)

            if not results:
                print("   ❌ No results found")
            else:
                print(f"   ✅ Found {len(results)} results:")
                for i, result in enumerate(results, 1):
                    similarity = result['similarity']
                    doc_preview = result['document'][:100]
                    source = result.get('metadata', {}).get('source', 'unknown')

                    status = "✅" if similarity >= settings.chroma_similarity_threshold else "⚠️"
                    print(f"   {status} Result {i}: similarity={similarity:.4f}")
                    print(f"      Content: {doc_preview}...")
                    print(f"      Source: {source}")

        # Show statistics
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"✅ Collection has {info['count']} documents")
        print(f"✅ ChromaDB is working correctly")
        print(f"\n💡 If searches return 0 results, try lowering CHROMA_SIMILARITY_THRESHOLD in .env.dev")
        print(f"   Current threshold: {settings.chroma_similarity_threshold}")
        print(f"   Recommended: 0.3 - 0.5 for FAQ data")

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: {e}")
        print("   Make sure .env.dev exists and has correct settings")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    check_chromadb()
