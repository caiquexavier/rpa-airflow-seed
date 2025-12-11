"""Add identifier and identifier_code fields to rpa_extracted_data table.

This migration:
- Adds identifier field (e.g., "NF-E") to identify the type of extracted data
- Adds identifier_code field (e.g., nf_e number) to identify the specific record
- Creates unique constraint on (saga_id, identifier_code) to ensure uniqueness
- Creates index on identifier and identifier_code for performance
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Add identifier and identifier_code columns
    # ============================================
    op.add_column(
        "rpa_extracted_data",
        sa.Column("identifier", sa.String(length=100), nullable=True)
    )
    
    op.add_column(
        "rpa_extracted_data",
        sa.Column("identifier_code", sa.String(length=255), nullable=True)
    )
    
    # ============================================
    # Create unique constraint on (saga_id, identifier_code)
    # ============================================
    op.create_unique_constraint(
        "uq_rpa_extracted_data_saga_id_identifier_code",
        "rpa_extracted_data",
        ["saga_id", "identifier_code"]
    )
    
    # ============================================
    # Create indexes for performance
    # ============================================
    op.create_index(
        "IDX_rpa_extracted_data_identifier",
        "rpa_extracted_data",
        ["identifier"],
        unique=False
    )
    
    op.create_index(
        "IDX_rpa_extracted_data_identifier_code",
        "rpa_extracted_data",
        ["identifier_code"],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("IDX_rpa_extracted_data_identifier_code", table_name="rpa_extracted_data")
    op.drop_index("IDX_rpa_extracted_data_identifier", table_name="rpa_extracted_data")
    
    # Drop unique constraint
    op.drop_constraint(
        "uq_rpa_extracted_data_saga_id_identifier_code",
        "rpa_extracted_data",
        type_="unique"
    )
    
    # Drop columns
    op.drop_column("rpa_extracted_data", "identifier_code")
    op.drop_column("rpa_extracted_data", "identifier")

