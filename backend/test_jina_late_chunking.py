"""Test script for Jina Late Chunking implementation."""

import time
from app.embedding.embedders.jina_late_chunking import JinaLocalLateChunkingEmbedder
from app.chunking.chunkers.late_chunking import LateChunkingWrapper
from app.models.base_document import BaseDocument


def main():
    print("=" * 60)
    print("🚀 Jina Late Chunking Test")
    print("=" * 60)
    
    # Sample document
    document_text = """
    Machine learning is a branch of artificial intelligence that focuses on 
    building applications that learn from data and improve their accuracy over time. 
    Deep learning is a subset of machine learning that uses neural networks with 
    multiple layers to learn from large amounts of data. Natural language processing 
    is another important area that enables computers to understand and process human 
    language. Computer vision allows machines to interpret and understand visual 
    information from the world. These technologies are revolutionizing industries 
    from healthcare to finance. The future of AI looks incredibly promising as 
    researchers continue to push the boundaries of what's possible.
    """
    
    print(f"\n📄 Document length: {len(document_text)} characters")
    
    # Initialize embedder
    print("\n🔧 Initializing Jina v3 Embedder...")
    try:
        embedder = JinaLocalLateChunkingEmbedder(
            model_name="jinaai/jina-embeddings-v3",
            device=None,  # Auto-detect
            use_fp16=None  # Auto-detect
        )
        print(f"✅ Embedder initialized on: {embedder.device}")
        print(f"   Dimension: {embedder.get_dimension()}")
        print(f"   Batch size: {embedder.optimal_batch_size}")
    except Exception as e:
        print(f"❌ Failed to initialize embedder: {e}")
        print("\n💡 Make sure to install transformers:")
        print("   pip install transformers>=4.36.0")
        return
    
    # Initialize chunker
    print("\n🔧 Initializing Late Chunking Wrapper...")
    chunker = LateChunkingWrapper(
        sentences_per_chunk=2,
        min_chunk_tokens=30,
        max_chunk_tokens=200
    )
    print(f"✅ Chunker initialized: {chunker}")
    
    # Create document
    document = BaseDocument(
        id="test_doc_1",
        content=document_text,
        source_type="test",
        filename="test.txt"
    )
    
    # Chunk document
    print("\n✂️  Chunking document...")
    chunks = chunker.chunk_document(document)
    print(f"✅ Created {len(chunks)} chunks")
    
    for i, chunk in enumerate(chunks, 1):
        preview = chunk.content[:60].replace("\n", " ")
        print(f"   Chunk {i}: {preview}...")
    
    # Test 1: Traditional embedding (slow)
    print("\n" + "=" * 60)
    print("📊 Test 1: Traditional Embedding (각 청크를 따로 임베딩)")
    print("=" * 60)
    
    chunk_texts = [chunk.content for chunk in chunks]
    
    start_time = time.time()
    embeddings_traditional = embedder.embed_texts(chunk_texts)
    traditional_time = time.time() - start_time
    
    print(f"✅ Traditional embedding completed")
    print(f"   Time: {traditional_time:.3f} seconds")
    print(f"   Embeddings: {len(embeddings_traditional['dense'])} x {embedder.get_dimension()}")
    print(f"   Forward passes: {len(chunks)} times")
    
    # Test 2: Late Chunking (fast)
    print("\n" + "=" * 60)
    print("⚡ Test 2: Late Chunking (문서를 한 번만 임베딩)")
    print("=" * 60)
    
    start_time = time.time()
    embeddings_late = embedder.embed_document_with_late_chunking(
        document_text,
        chunk_texts
    )
    late_chunking_time = time.time() - start_time
    
    print(f"✅ Late chunking completed")
    print(f"   Time: {late_chunking_time:.3f} seconds")
    print(f"   Embeddings: {len(embeddings_late)} x {embedder.get_dimension()}")
    print(f"   Forward passes: 1 time only!")
    
    # Compare performance
    print("\n" + "=" * 60)
    print("📈 Performance Comparison")
    print("=" * 60)
    
    if late_chunking_time > 0:
        speedup = traditional_time / late_chunking_time
        print(f"Traditional method: {traditional_time:.3f}s ({len(chunks)} forward passes)")
        print(f"Late Chunking:      {late_chunking_time:.3f}s (1 forward pass)")
        print(f"\n🚀 Speedup: {speedup:.2f}x faster!")
        
        if speedup > 5:
            print("✨ Late Chunking is working perfectly!")
        elif speedup > 2:
            print("✅ Late Chunking shows improvement")
        else:
            print("⚠️  Speedup is lower than expected (document may be too small)")
    
    # Test query embedding
    print("\n" + "=" * 60)
    print("🔍 Test 3: Query Embedding")
    print("=" * 60)
    
    query = "What is machine learning?"
    query_embedding = embedder.embed_query(query, enhanced=True)
    
    print(f"✅ Query embedded: '{query}'")
    print(f"   Dimension: {len(query_embedding['dense'])}")
    print(f"   First 5 values: {query_embedding['dense'][:5]}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed successfully!")
    print("=" * 60)
    print("\n💡 Next steps:")
    print("   1. Use this in your RAG pipeline")
    print("   2. Try with larger documents for better speedup")
    print("   3. Combine with SemanticChunker for optimal results")
    print(f"\n📖 See JINA_LATE_CHUNKING_GUIDE.md for usage examples")


if __name__ == "__main__":
    main()

