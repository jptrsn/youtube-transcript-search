"""convert_snippets_to_jsonb

Revision ID: c15af48eb42b
Revises: b40bb7fb8f96
Create Date: 2025-12-01 23:24:26.650062

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c15af48eb42b'
down_revision: Union[str, None] = 'b40bb7fb8f96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert JSON to JSONB - PostgreSQL handles this safely
    # The USING clause tells PG how to convert the data
    op.execute("""
        ALTER TABLE transcripts
        ALTER COLUMN snippets TYPE JSONB
        USING snippets::jsonb
    """)

    # Add GIN index for faster JSONB queries (optional but recommended)
    op.create_index(
        'idx_transcripts_snippets_gin',
        'transcripts',
        ['snippets'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    # Remove the index
    op.drop_index('idx_transcripts_snippets_gin', table_name='transcripts')

    # Convert back to JSON if needed
    op.execute("""
        ALTER TABLE transcripts
        ALTER COLUMN snippets TYPE JSON
        USING snippets::json
    """)
