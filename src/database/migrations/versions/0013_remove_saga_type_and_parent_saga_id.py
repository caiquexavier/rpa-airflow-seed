"""Remove saga_type and parent_saga_id from saga tables.

This migration:
- Removes saga_type column from saga table
- Removes parent_saga_id column from saga table
- Removes saga_type column from saga_read_model table
- Removes parent_saga_id column from saga_read_model table
- Drops related indexes and foreign keys
- Updates sync_saga_read_model trigger function
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Step 1: Drop indexes on saga_type and parent_saga_id
    # ============================================
    op.execute("DROP INDEX IF EXISTS IDX_saga_saga_type")
    op.execute("DROP INDEX IF EXISTS IDX_saga_parent_saga_id")
    op.execute("DROP INDEX IF EXISTS IDX_saga_read_model_saga_type")
    op.execute("DROP INDEX IF EXISTS IDX_saga_read_model_parent_saga_id")
    
    # ============================================
    # Step 2: Drop foreign key constraint for parent_saga_id
    # ============================================
    op.execute("ALTER TABLE saga DROP CONSTRAINT IF EXISTS fk_saga_parent_saga_id")
    
    # ============================================
    # Step 3: Update sync_saga_read_model trigger function to remove saga_type and parent_saga_id
    # ============================================
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_saga_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO saga_read_model (
                saga_id, rpa_key_id, current_state, data,
                events_count, last_event_type, last_event_at, created_at, updated_at
            )
            VALUES (
                NEW.saga_id, NEW.rpa_key_id, NEW.current_state, NEW.data,
                jsonb_array_length(NEW.events::jsonb),
                (SELECT event_type FROM event_store WHERE saga_id = NEW.saga_id ORDER BY occurred_at DESC LIMIT 1),
                (SELECT occurred_at FROM event_store WHERE saga_id = NEW.saga_id ORDER BY occurred_at DESC LIMIT 1),
                NEW.created_at, NEW.updated_at
            )
            ON CONFLICT (saga_id) DO UPDATE SET
                rpa_key_id = EXCLUDED.rpa_key_id,
                current_state = EXCLUDED.current_state,
                data = EXCLUDED.data,
                events_count = EXCLUDED.events_count,
                last_event_type = EXCLUDED.last_event_type,
                last_event_at = EXCLUDED.last_event_at,
                updated_at = EXCLUDED.updated_at;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # ============================================
    # Step 4: Remove columns from saga_read_model table
    # ============================================
    op.execute("ALTER TABLE saga_read_model DROP COLUMN IF EXISTS saga_type")
    op.execute("ALTER TABLE saga_read_model DROP COLUMN IF EXISTS parent_saga_id")
    
    # ============================================
    # Step 5: Remove columns from saga table
    # ============================================
    op.execute("ALTER TABLE saga DROP COLUMN IF EXISTS parent_saga_id")
    op.execute("ALTER TABLE saga DROP COLUMN IF EXISTS saga_type")


def downgrade() -> None:
    # ============================================
    # Step 1: Add columns back to saga table
    # ============================================
    op.add_column("saga", sa.Column("saga_type", sa.String(), nullable=False, server_default="DAG_SAGA"))
    op.add_column("saga", sa.Column("parent_saga_id", sa.BigInteger(), nullable=True))
    
    # ============================================
    # Step 2: Add columns back to saga_read_model table
    # ============================================
    op.add_column("saga_read_model", sa.Column("saga_type", sa.String(), nullable=True))
    op.add_column("saga_read_model", sa.Column("parent_saga_id", sa.BigInteger(), nullable=True))
    
    # ============================================
    # Step 3: Add foreign key constraint
    # ============================================
    op.create_foreign_key(
        "fk_saga_parent_saga_id",
        "saga",
        "saga",
        ["parent_saga_id"],
        ["saga_id"],
        ondelete="CASCADE"
    )
    
    # ============================================
    # Step 4: Recreate indexes
    # ============================================
    op.create_index("IDX_saga_saga_type", "saga", ["saga_type"], unique=False)
    op.create_index("IDX_saga_parent_saga_id", "saga", ["parent_saga_id"], unique=False)
    op.create_index("IDX_saga_read_model_saga_type", "saga_read_model", ["saga_type"], unique=False)
    op.create_index("IDX_saga_read_model_parent_saga_id", "saga_read_model", ["parent_saga_id"], unique=False)
    
    # ============================================
    # Step 5: Restore sync_saga_read_model trigger function
    # ============================================
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_saga_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO saga_read_model (
                saga_id, rpa_key_id, current_state, data,
                events_count, last_event_type, last_event_at, created_at, updated_at,
                saga_type, parent_saga_id
            )
            VALUES (
                NEW.saga_id, NEW.rpa_key_id, NEW.current_state, NEW.data,
                jsonb_array_length(NEW.events::jsonb),
                (SELECT event_type FROM event_store WHERE saga_id = NEW.saga_id ORDER BY occurred_at DESC LIMIT 1),
                (SELECT occurred_at FROM event_store WHERE saga_id = NEW.saga_id ORDER BY occurred_at DESC LIMIT 1),
                NEW.created_at, NEW.updated_at,
                NEW.saga_type, NEW.parent_saga_id
            )
            ON CONFLICT (saga_id) DO UPDATE SET
                rpa_key_id = EXCLUDED.rpa_key_id,
                current_state = EXCLUDED.current_state,
                data = EXCLUDED.data,
                events_count = EXCLUDED.events_count,
                last_event_type = EXCLUDED.last_event_type,
                last_event_at = EXCLUDED.last_event_at,
                updated_at = EXCLUDED.updated_at,
                saga_type = EXCLUDED.saga_type,
                parent_saga_id = EXCLUDED.parent_saga_id;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

