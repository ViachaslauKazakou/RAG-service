from sentence_transformers import SentenceTransformer
import logging
try:
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Test HuggingFace embeddings
    print('Loading HuggingFace model...')
    model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
    print('Model loaded successfully!')
    
    # Test single embedding
    test_text = 'Это тестовое сообщение для проверки эмбеддингов'
    print('Creating single embedding...')
    embedding = model.encode([test_text])
    print(f'Single embedding shape: {embedding.shape}')
    print(f'Embedding length: {len(embedding[0])}')
    print(f'First 5 values: {embedding[0][:5]}')
    
    # Test batch embeddings
    test_texts = [
        'Первое тестовое сообщение',
        'Второе тестовое сообщение', 
        'Третье тестовое сообщение'
    ]
    print('\nCreating batch embeddings...')
    batch_embeddings = model.encode(test_texts)
    print(f'Batch embeddings shape: {batch_embeddings.shape}')
    print(f'Number of embeddings: {len(batch_embeddings)}')
    print(f'Each embedding length: {len(batch_embeddings[0])}')
    
    print('\nHuggingFace embeddings working correctly!')
    
except ImportError as e:
    print(f'Import error: {e}')
except Exception as e:
    print(f'Error: {e}')