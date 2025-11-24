"""Add rpa_extracted_data table.

This migration:
- Creates rpa_extracted_data table to store JSONB metadata extracted by GPT
- Links to saga table via saga_id foreign key
- Creates index on saga_id for performance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Create rpa_extracted_data table
    # ============================================
    op.create_table(
        "rpa_extracted_data",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("saga_id", sa.BigInteger(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["saga_id"], ["saga.saga_id"], ondelete="CASCADE"),
    )
    
    # Create index on saga_id for performance
    op.create_index(
        "IDX_rpa_extracted_data_saga_id",
        "rpa_extracted_data",
        ["saga_id"],
        unique=False
    )
    
    # Create index on created_at for time-based queries
    op.create_index(
        "IDX_rpa_extracted_data_created_at",
        "rpa_extracted_data",
        ["created_at"],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("IDX_rpa_extracted_data_created_at", table_name="rpa_extracted_data")
    op.drop_index("IDX_rpa_extracted_data_saga_id", table_name="rpa_extracted_data")
    
    # Drop table
    op.drop_table("rpa_extracted_data")

