"""Add foreign key relationships to users table fixed

Revision ID: 0d8feca6bb00
Revises: c55bfd491415
Create Date: 2025-07-27 11:14:18.218338

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0d8feca6bb00'
down_revision: Union[str, Sequence[str], None] = 'c55bfd491415'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем character_id колонку в user_knowledge
    op.add_column('user_knowledge', sa.Column('character_id', sa.String(50), nullable=True))
    op.create_index('ix_user_knowledge_character_id', 'user_knowledge', ['character_id'])
    op.create_unique_constraint('uq_user_knowledge_character_id', 'user_knowledge', ['character_id'])
    
    # Добавляем character_id колонку в user_message_examples
    op.add_column('user_message_examples', sa.Column('character_id', sa.String(50), nullable=True))
    op.create_index('ix_user_message_examples_character_id', 'user_message_examples', ['character_id'])
    
    # Заполняем character_id из существующих user_id (которые сейчас строковые)
    # Для user_knowledge
    op.execute("""
        UPDATE user_knowledge 
        SET character_id = user_id
    """)
    
    # Для user_message_examples
    op.execute("""
        UPDATE user_message_examples 
        SET character_id = user_id
    """)
    
    # Создаем пользователей для каждого character_id если их еще нет
    op.execute("""
        INSERT INTO users (username, firstname, lastname, password, email, user_type, status)
        SELECT DISTINCT 
            ukr.character_id,
            ukr.name,
            '',
            'fake_password_hash',
            ukr.character_id || '@example.com',
            'user',
            'active'
        FROM user_knowledge ukr
        WHERE NOT EXISTS (
            SELECT 1 FROM users u WHERE u.username = ukr.character_id
        )
    """)
    
    # Делаем user_id nullable временно
    op.alter_column('user_knowledge', 'user_id', nullable=True)
    op.alter_column('user_message_examples', 'user_id', nullable=True)
    
    # Обновляем user_id в user_knowledge чтобы ссылаться на реальных пользователей
    op.execute("""
        UPDATE user_knowledge 
        SET user_id = (
            SELECT u.id 
            FROM users u 
            WHERE u.username = user_knowledge.character_id
        )
    """)
    
    # Обновляем user_id в user_message_examples чтобы ссылаться на реальных пользователей  
    op.execute("""
        UPDATE user_message_examples 
        SET user_id = (
            SELECT u.id 
            FROM users u 
            WHERE u.username = user_message_examples.character_id
        )
    """)
    
    # Изменяем тип колонки user_id с STRING на INTEGER
    # user_knowledge - только если есть индексы/ограничения
    op.drop_index('ix_user_knowledge_user_id', 'user_knowledge')
    op.alter_column('user_knowledge', 'user_id', type_=sa.Integer(), postgresql_using='user_id::integer')
    op.create_index('ix_user_knowledge_user_id', 'user_knowledge', ['user_id'])
    op.create_unique_constraint('uq_user_knowledge_user_id', 'user_knowledge', ['user_id'])
    
    # user_message_examples
    op.drop_index('ix_user_message_examples_user_id', 'user_message_examples')
    op.alter_column('user_message_examples', 'user_id', type_=sa.Integer(), postgresql_using='user_id::integer')
    op.create_index('ix_user_message_examples_user_id', 'user_message_examples', ['user_id'])
    
    # Возвращаем NOT NULL constraint
    op.alter_column('user_knowledge', 'user_id', nullable=False)
    op.alter_column('user_message_examples', 'user_id', nullable=False)
    
    # Добавляем foreign key constraints
    op.create_foreign_key('fk_user_knowledge_user_id', 'user_knowledge', 'users', ['user_id'], ['id'])
    op.create_foreign_key('fk_user_message_examples_user_id', 'user_message_examples', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем foreign key constraints
    op.drop_constraint('fk_user_message_examples_user_id', 'user_message_examples')
    op.drop_constraint('fk_user_knowledge_user_id', 'user_knowledge')
    
    # Восстанавливаем строковый тип для user_id
    # user_knowledge
    op.drop_constraint('uq_user_knowledge_user_id', 'user_knowledge')
    op.drop_index('ix_user_knowledge_user_id', 'user_knowledge')
    op.alter_column('user_knowledge', 'user_id', type_=sa.String(50), postgresql_using='character_id')
    op.create_index('ix_user_knowledge_user_id', 'user_knowledge', ['user_id'])
    
    # user_message_examples
    op.drop_index('ix_user_message_examples_user_id', 'user_message_examples')
    op.alter_column('user_message_examples', 'user_id', type_=sa.String(50), postgresql_using='character_id')
    op.create_index('ix_user_message_examples_user_id', 'user_message_examples', ['user_id'])
    
    # Удаляем character_id колонки
    op.drop_constraint('uq_user_knowledge_character_id', 'user_knowledge')
    op.drop_index('ix_user_knowledge_character_id', 'user_knowledge')
    op.drop_column('user_knowledge', 'character_id')
    
    op.drop_index('ix_user_message_examples_character_id', 'user_message_examples')
    op.drop_column('user_message_examples', 'character_id')
