"""Create user_message_examples table

Revision ID: c55bfd491415
Revises: e37612d6272b
Create Date: 2025-07-27 10:41:30.026769

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c55bfd491415'
down_revision: Union[str, Sequence[str], None] = '294d3841e2d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Удаляем таблицу если существует (для чистого пересоздания)
    op.execute("DROP TABLE IF EXISTS user_message_examples CASCADE")
    
    # Создаем таблицу точно по модели UserMessageExample
    op.execute("""
        CREATE TABLE user_message_examples (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50) NOT NULL,
            context TEXT,
            content TEXT NOT NULL,
            thread_id VARCHAR(100),
            reply_to VARCHAR(100),
            timestamp TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            content_embedding vector(1536),
            context_embedding vector(1536),
            extra_metadata JSONB,
            source_file VARCHAR(255),
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Создаем индексы точно как в модели
    op.execute("""
        CREATE INDEX ix_user_message_examples_id ON user_message_examples (id);
        CREATE INDEX ix_user_message_examples_user_id ON user_message_examples (user_id);
        CREATE INDEX ix_user_message_examples_reply_to ON user_message_examples (reply_to);
    """)
    
    # Создаем векторные индексы для эмбеддингов (ivfflat для similarity search)
    op.execute("""
        CREATE INDEX ix_user_message_examples_content_embedding 
        ON user_message_examples USING ivfflat (content_embedding vector_cosine_ops) 
        WITH (lists = 100);
        
        CREATE INDEX ix_user_message_examples_context_embedding 
        ON user_message_examples USING ivfflat (context_embedding vector_cosine_ops) 
        WITH (lists = 100);
    """)
    
    # Создаем триггер для автоматического обновления updated_at
    op.execute("""
        DROP TRIGGER IF EXISTS update_user_message_examples_updated_at ON user_message_examples;
        CREATE TRIGGER update_user_message_examples_updated_at
            BEFORE UPDATE ON user_message_examples
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем триггер
    op.execute("DROP TRIGGER IF EXISTS update_user_message_examples_updated_at ON user_message_examples")
    
    # Удаляем таблицу
    op.execute("DROP TABLE IF EXISTS user_message_examples CASCADE")
