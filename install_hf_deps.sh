#!/bin/bash
# Script to install HuggingFace dependencies for RAG service
# Run this after 'poetry install' to add HF support

echo "Installing HuggingFace dependencies for embeddings..."

# Install torch CPU version (compatible with macOS)
poetry run pip install torch --index-url https://download.pytorch.org/whl/cpu

# Install sentence-transformers
poetry run pip install sentence-transformers

# Verify installation
echo "Verifying installation..."
poetry run python -c "
import torch
import sentence_transformers
print(f'✅ Torch {torch.__version__}')
print(f'✅ Sentence Transformers {sentence_transformers.__version__}')
print('🎉 HuggingFace embeddings ready!')
"

echo "Installation complete!"
echo "You can now use HuggingFace embeddings in your RAG service."
