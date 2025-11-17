"""Remove robot_step column from event_store.

This migration:
- Drops robot_step column from event_store table
- Drops index on robot_step column
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Step 1: Drop index on robot_step
    # ============================================
    op.drop_index("IDX_event_store_robot_step", table_name="event_store", if_exists=True)
    
    # ============================================
    # Step 2: Drop robot_step column
    # ============================================
    op.drop_column("event_store", "robot_step")


def downgrade() -> None:
    # ============================================
    # Step 1: Add robot_step column back
    # ============================================
    op.add_column(
        "event_store",
        sa.Column(
            "robot_step",
            sa.Text(),
            nullable=True,
            comment="Robot Framework step identifier (e.g., Start Browser, Login To e-Cargo)"
        )
    )
    
    # ============================================
    # Step 2: Recreate index
    # ============================================
    op.create_index("IDX_event_store_robot_step", "event_store", ["robot_step"], unique=False)

