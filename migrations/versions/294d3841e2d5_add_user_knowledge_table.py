"""Add user_knowledge table

Revision ID: 294d3841e2d5
Revises: 
Create Date: 2025-07-27 10:01:35.467683

"""
import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '294d3841e2d5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Создаем таблицу user_knowledge только если она не существует
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_knowledge (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(50) NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            personality TEXT,
            background TEXT,
            expertise JSONB,
            communication_style TEXT,
            preferences JSONB,
            file_path VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Создаем индексы
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_knowledge_user_id ON user_knowledge (user_id)")
    
    # Создаем триггер для обновления updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ language 'plpgsql'
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS update_user_knowledge_updated_at ON user_knowledge;
        CREATE TRIGGER update_user_knowledge_updated_at
            BEFORE UPDATE ON user_knowledge
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем триггер и функцию
    op.execute("DROP TRIGGER IF EXISTS update_user_knowledge_updated_at ON user_knowledge")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Удаляем таблицу
    op.execute("DROP TABLE IF EXISTS user_knowledge")
