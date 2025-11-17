"""Remove execution domain and exec_id from saga.

This migration:
- Drops execution_read_model table
- Drops execution_requests table
- Removes exec_id column from saga table
- Removes exec_id column from event_store table
- Updates foreign keys and triggers
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Step 1: Drop triggers that reference execution tables
    # ============================================
    op.execute("DROP TRIGGER IF EXISTS trigger_sync_execution_read_model ON execution_requests")
    op.execute("DROP FUNCTION IF EXISTS sync_execution_read_model()")
    
    # ============================================
    # Step 2: Drop foreign keys that reference execution_requests
    # ============================================
    op.execute("ALTER TABLE saga DROP CONSTRAINT IF EXISTS fk_saga_exec_id")
    op.execute("ALTER TABLE event_store DROP CONSTRAINT IF EXISTS fk_event_store_exec_id")
    op.execute("ALTER TABLE saga_read_model DROP CONSTRAINT IF EXISTS fk_saga_read_model_exec_id")
    
    # ============================================
    # Step 3: Drop execution_read_model table
    # ============================================
    op.execute("DROP INDEX IF EXISTS IDX_execution_read_model_created_at")
    op.execute("DROP INDEX IF EXISTS IDX_execution_read_model_saga_id")
    op.execute("DROP INDEX IF EXISTS IDX_execution_read_model_exec_status")
    op.execute("DROP INDEX IF EXISTS IDX_execution_read_model_rpa_key_id")
    op.execute("DROP TABLE IF EXISTS execution_read_model CASCADE")
    
    # ============================================
    # Step 4: Drop execution_requests table
    # ============================================
    op.execute("DROP INDEX IF EXISTS IDX_execution_requests_saga_id")
    op.execute("DROP INDEX IF EXISTS IDX_execution_requests_created_at")
    op.execute("DROP INDEX IF EXISTS IDX_execution_requests_rpa_key_id")
    op.execute("DROP INDEX IF EXISTS IDX_execution_requests_status")
    op.execute("DROP TABLE IF EXISTS execution_requests CASCADE")
    
    # ============================================
    # Step 5: Remove exec_id from saga table
    # ============================================
    # Drop unique index on exec_id first
    op.execute("DROP INDEX IF EXISTS IDX_saga_exec_id")
    # Drop the column
    op.alter_column("saga", "exec_id", existing_type=sa.BigInteger(), nullable=True)
    op.execute("ALTER TABLE saga DROP COLUMN IF EXISTS exec_id")
    
    # ============================================
    # Step 6: Remove exec_id from event_store table
    # ============================================
    # Drop index on exec_id first
    op.execute("DROP INDEX IF EXISTS IDX_event_store_exec_id")
    # Drop foreign key constraint if it exists
    op.execute("ALTER TABLE event_store DROP CONSTRAINT IF EXISTS event_store_exec_id_fkey")
    # Drop the column
    op.execute("ALTER TABLE event_store DROP COLUMN IF EXISTS exec_id")
    
    # ============================================
    # Step 7: Remove exec_id from saga_read_model table
    # ============================================
    # Drop index on exec_id first
    op.execute("DROP INDEX IF EXISTS IDX_saga_read_model_exec_id")
    op.execute("DROP INDEX IF EXISTS IDX_saga_read_model_exec_id_dag_unique")
    # Drop foreign key constraint if it exists
    op.execute("ALTER TABLE saga_read_model DROP CONSTRAINT IF EXISTS saga_read_model_exec_id_fkey")
    # Drop the column
    op.execute("ALTER TABLE saga_read_model DROP COLUMN IF EXISTS exec_id")
    
    # ============================================
    # Step 8: Update sync_saga_read_model() trigger function to remove exec_id
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


def downgrade() -> None:
    # Note: This downgrade is complex and may not fully restore all data
    # Recreate execution_requests table
    op.create_table(
        "execution_requests",
        sa.Column("exec_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("rpa_key_id", sa.Text(), nullable=False),
        sa.Column("exec_status", sa.Text(), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("rpa_request", sa.JSON(), nullable=True),
        sa.Column("rpa_response", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("callback_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("saga_id", sa.BigInteger(), nullable=True),
        sa.Column("last_saga_state", sa.Text(), nullable=True),
        sa.Column("flowchart_definition", sa.JSON(), nullable=True),
    )
    op.create_index("IDX_execution_requests_status", "execution_requests", ["exec_status"], unique=False)
    op.create_index("IDX_execution_requests_rpa_key_id", "execution_requests", ["rpa_key_id"], unique=False)
    op.create_index("IDX_execution_requests_created_at", "execution_requests", ["created_at"], unique=False)
    op.create_index("IDX_execution_requests_saga_id", "execution_requests", ["saga_id"], unique=False)
    
    # Recreate execution_read_model table
    op.create_table(
        "execution_read_model",
        sa.Column("exec_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("rpa_key_id", sa.Text(), nullable=False),
        sa.Column("exec_status", sa.Text(), nullable=False),
        sa.Column("rpa_request", sa.JSON(), nullable=True),
        sa.Column("rpa_response", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("callback_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("saga_id", sa.BigInteger(), nullable=True),
        sa.Column("saga_state", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["exec_id"], ["execution_requests.exec_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saga_id"], ["saga.saga_id"], ondelete="SET NULL"),
    )
    op.create_index("IDX_execution_read_model_rpa_key_id", "execution_read_model", ["rpa_key_id"], unique=False)
    op.create_index("IDX_execution_read_model_exec_status", "execution_read_model", ["exec_status"], unique=False)
    op.create_index("IDX_execution_read_model_saga_id", "execution_read_model", ["saga_id"], unique=False)
    op.create_index("IDX_execution_read_model_created_at", "execution_read_model", ["created_at"], unique=False)
    
    # Recreate sync_execution_read_model function and trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_execution_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO execution_read_model (
                exec_id, rpa_key_id, exec_status, rpa_request, rpa_response,
                error_message, callback_url, created_at, updated_at, finished_at, saga_id, saga_state
            )
            VALUES (
                NEW.exec_id, NEW.rpa_key_id, NEW.exec_status, NEW.rpa_request, NEW.rpa_response,
                NEW.error_message, NEW.callback_url, NEW.created_at, NEW.updated_at, NEW.finished_at,
                NEW.saga_id, NEW.last_saga_state
            )
            ON CONFLICT (exec_id) DO UPDATE SET
                rpa_key_id = EXCLUDED.rpa_key_id,
                exec_status = EXCLUDED.exec_status,
                rpa_request = EXCLUDED.rpa_request,
                rpa_response = EXCLUDED.rpa_response,
                error_message = EXCLUDED.error_message,
                callback_url = EXCLUDED.callback_url,
                updated_at = EXCLUDED.updated_at,
                finished_at = EXCLUDED.finished_at,
                saga_id = EXCLUDED.saga_id,
                saga_state = EXCLUDED.saga_state;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER trigger_sync_execution_read_model
        AFTER INSERT OR UPDATE ON execution_requests
        FOR EACH ROW
        EXECUTE FUNCTION sync_execution_read_model();
    """)
    
    # Add exec_id back to saga table (will be NULL for existing rows)
    op.add_column("saga", sa.Column("exec_id", sa.BigInteger(), nullable=True))
    op.create_index("IDX_saga_exec_id", "saga", ["exec_id"], unique=False)
    op.create_foreign_key(
        "fk_saga_exec_id",
        "saga",
        "execution_requests",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    # Add exec_id back to event_store table (will be NULL for existing rows)
    op.add_column("event_store", sa.Column("exec_id", sa.BigInteger(), nullable=True))
    op.create_index("IDX_event_store_exec_id", "event_store", ["exec_id"], unique=False)
    op.create_foreign_key(
        "fk_event_store_exec_id",
        "event_store",
        "execution_requests",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    # Add exec_id back to saga_read_model table (will be NULL for existing rows)
    op.add_column("saga_read_model", sa.Column("exec_id", sa.BigInteger(), nullable=True))
    op.create_index("IDX_saga_read_model_exec_id", "saga_read_model", ["exec_id"], unique=False)
    op.create_foreign_key(
        "fk_saga_read_model_exec_id",
        "saga_read_model",
        "execution_requests",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )

