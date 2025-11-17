"""Make saga_id nullable in event_store.

This allows execution events (ExecutionCreated, ExecutionStarted, etc.) to be stored
without a saga_id, since they are created before the saga exists.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the foreign key constraint first (check both possible constraint names)
    # The constraint might be named differently, so we'll try to drop it
    op.execute("ALTER TABLE event_store DROP CONSTRAINT IF EXISTS event_store_saga_id_fkey")
    op.execute("ALTER TABLE event_store DROP CONSTRAINT IF EXISTS fk_event_store_saga_id")
    
    # Make saga_id nullable
    op.alter_column(
        "event_store",
        "saga_id",
        existing_type=sa.BigInteger(),
        nullable=True,
        existing_nullable=False
    )
    
    # Recreate the foreign key constraint with ON DELETE CASCADE
    op.create_foreign_key(
        "event_store_saga_id_fkey",
        "event_store",
        "saga",
        ["saga_id"],
        ["saga_id"],
        ondelete="CASCADE"
    )


def downgrade() -> None:
    # Drop the foreign key constraint
    op.execute("ALTER TABLE event_store DROP CONSTRAINT IF EXISTS event_store_saga_id_fkey")
    
    # Make saga_id NOT NULL again (this will fail if there are NULL values)
    op.alter_column(
        "event_store",
        "saga_id",
        existing_type=sa.BigInteger(),
        nullable=False,
        existing_nullable=True
    )
    
    # Recreate the foreign key constraint
    op.create_foreign_key(
        "event_store_saga_id_fkey",
        "event_store",
        "saga",
        ["saga_id"],
        ["saga_id"],
        ondelete="CASCADE"
    )

