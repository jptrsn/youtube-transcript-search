"""add full text search indexes

Revision ID: b40bb7fb8f96
Revises: d3af9a235507
Create Date: 2025-11-28 14:14:03.120266

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b40bb7fb8f96'
down_revision: Union[str, None] = 'd3af9a235507'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for fuzzy matching
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')

    # Add tsvector columns for full-text search
    op.add_column('transcripts', sa.Column('text_search_vector', sa.dialects.postgresql.TSVECTOR))
    op.add_column('videos', sa.Column('title_search_vector', sa.dialects.postgresql.TSVECTOR))
    op.add_column('videos', sa.Column('description_search_vector', sa.dialects.postgresql.TSVECTOR))

    # Populate the tsvector columns with existing data
    op.execute("""
        UPDATE transcripts
        SET text_search_vector = to_tsvector('english', COALESCE(text, ''))
    """)

    op.execute("""
        UPDATE videos
        SET title_search_vector = to_tsvector('english', COALESCE(title, ''))
    """)

    op.execute("""
        UPDATE videos
        SET description_search_vector = to_tsvector('english', COALESCE(description, ''))
    """)

    # Create GIN indexes for fast full-text search
    op.create_index('idx_transcripts_text_search', 'transcripts', ['text_search_vector'],
                    postgresql_using='gin')
    op.create_index('idx_videos_title_search', 'videos', ['title_search_vector'],
                    postgresql_using='gin')
    op.create_index('idx_videos_description_search', 'videos', ['description_search_vector'],
                    postgresql_using='gin')

    # Create trigram indexes for fuzzy matching
    op.create_index('idx_transcripts_text_trgm', 'transcripts', ['text'],
                    postgresql_using='gin', postgresql_ops={'text': 'gin_trgm_ops'})
    op.create_index('idx_videos_title_trgm', 'videos', ['title'],
                    postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})

    # Create triggers to automatically update tsvector columns on INSERT/UPDATE
    op.execute("""
        CREATE TRIGGER transcripts_text_search_update
        BEFORE INSERT OR UPDATE ON transcripts
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(text_search_vector, 'pg_catalog.english', text)
    """)

    op.execute("""
        CREATE TRIGGER videos_title_search_update
        BEFORE INSERT OR UPDATE ON videos
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(title_search_vector, 'pg_catalog.english', title)
    """)

    op.execute("""
        CREATE TRIGGER videos_description_search_update
        BEFORE INSERT OR UPDATE ON videos
        FOR EACH ROW EXECUTE FUNCTION
        tsvector_update_trigger(description_search_vector, 'pg_catalog.english', description)
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS transcripts_text_search_update ON transcripts')
    op.execute('DROP TRIGGER IF EXISTS videos_title_search_update ON videos')
    op.execute('DROP TRIGGER IF EXISTS videos_description_search_update ON videos')

    # Drop indexes
    op.drop_index('idx_transcripts_text_trgm', table_name='transcripts')
    op.drop_index('idx_videos_title_trgm', table_name='videos')
    op.drop_index('idx_transcripts_text_search', table_name='transcripts')
    op.drop_index('idx_videos_title_search', table_name='videos')
    op.drop_index('idx_videos_description_search', table_name='videos')

    # Drop tsvector columns
    op.drop_column('transcripts', 'text_search_vector')
    op.drop_column('videos', 'title_search_vector')
    op.drop_column('videos', 'description_search_vector')

    # Drop extension
    op.execute('DROP EXTENSION IF EXISTS pg_trgm')