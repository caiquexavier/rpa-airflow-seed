"""Remove rpa_domain table and replace rpa_automation_exec with execution_requests.

This migration:
- Drops rpa_domain table
- Creates execution_requests table based on rpa_automation_exec with:
  - Removed: current_step, started_at
  - Added: saga_id, last_saga_state, flowchart_definition
- Migrates data from rpa_automation_exec to execution_requests
- Updates all foreign keys to reference execution_requests
- Updates triggers to use execution_requests
- Drops rpa_automation_exec table
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Step 1: Create execution_requests table
    # ============================================
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
        sa.Column("saga_id", sa.BigInteger(), nullable=True, comment="Reference to saga orchestrator"),
        sa.Column("last_saga_state", sa.Text(), nullable=True, comment="Last state of the saga orchestrator"),
        sa.Column("flowchart_definition", sa.JSON(), nullable=True, comment="Flowchart definition for the execution"),
    )
    
    # Create indexes for execution_requests
    op.create_index("IDX_execution_requests_status", "execution_requests", ["exec_status"], unique=False)
    op.create_index("IDX_execution_requests_rpa_key_id", "execution_requests", ["rpa_key_id"], unique=False)
    op.create_index("IDX_execution_requests_created_at", "execution_requests", ["created_at"], unique=False)
    op.create_index("IDX_execution_requests_saga_id", "execution_requests", ["saga_id"], unique=False)
    
    # ============================================
    # Step 2: Migrate data from rpa_automation_exec to execution_requests
    # ============================================
    # Get saga_id and current_state from saga table for each exec_id
    op.execute("""
        INSERT INTO execution_requests (
            exec_id, rpa_key_id, exec_status, rpa_request, rpa_response,
            error_message, callback_url, created_at, updated_at, finished_at,
            saga_id, last_saga_state
        )
        SELECT 
            e.exec_id,
            e.rpa_key_id,
            e.exec_status,
            e.rpa_request,
            e.rpa_response,
            e.error_message,
            e.callback_url,
            e.created_at,
            e.updated_at,
            e.finished_at,
            s.saga_id,
            s.current_state
        FROM rpa_automation_exec e
        LEFT JOIN saga s ON s.exec_id = e.exec_id AND s.saga_type = 'DAG_SAGA'
    """)
    
    # ============================================
    # Step 3: Update foreign keys to reference execution_requests
    # ============================================
    # Drop old foreign keys
    op.execute("ALTER TABLE saga DROP CONSTRAINT IF EXISTS saga_exec_id_fkey")
    op.execute("ALTER TABLE event_store DROP CONSTRAINT IF EXISTS event_store_exec_id_fkey")
    op.execute("ALTER TABLE execution_read_model DROP CONSTRAINT IF EXISTS execution_read_model_exec_id_fkey")
    op.execute("ALTER TABLE saga_read_model DROP CONSTRAINT IF EXISTS saga_read_model_exec_id_fkey")
    
    # Create foreign key from execution_requests.saga_id to saga.saga_id
    op.create_foreign_key(
        "fk_execution_requests_saga_id",
        "execution_requests",
        "saga",
        ["saga_id"],
        ["saga_id"],
        ondelete="SET NULL"
    )
    
    # Create new foreign keys pointing to execution_requests
    op.create_foreign_key(
        "fk_saga_exec_id",
        "saga",
        "execution_requests",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    op.create_foreign_key(
        "fk_event_store_exec_id",
        "event_store",
        "execution_requests",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    op.create_foreign_key(
        "fk_execution_read_model_exec_id",
        "execution_read_model",
        "execution_requests",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    op.create_foreign_key(
        "fk_saga_read_model_exec_id",
        "saga_read_model",
        "execution_requests",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    # ============================================
    # Step 4: Update sync_execution_read_model trigger function
    # ============================================
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
    
    # Drop old trigger and create new one on execution_requests
    op.execute("DROP TRIGGER IF EXISTS trigger_sync_execution_read_model ON rpa_automation_exec")
    op.execute("""
        CREATE TRIGGER trigger_sync_execution_read_model
        AFTER INSERT OR UPDATE ON execution_requests
        FOR EACH ROW
        EXECUTE FUNCTION sync_execution_read_model();
    """)
    
    # ============================================
    # Step 5: Drop rpa_automation_exec table
    # ============================================
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS IDX_rpa_automation_exec_status")
    op.execute("DROP INDEX IF EXISTS IDX_rpa_automation_exec_rpa_key_id")
    op.execute("DROP INDEX IF EXISTS IDX_rpa_automation_exec_created_at")
    
    # Drop the table
    op.execute("DROP TABLE IF EXISTS rpa_automation_exec CASCADE")
    
    # ============================================
    # Step 6: Drop rpa_domain table
    # ============================================
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS IDX_rpa_definitions_name")
    op.execute("DROP INDEX IF EXISTS IDX_rpa_domain_rpa_key_id")
    
    # Drop constraints
    try:
        op.drop_constraint("uq_rpa_domain_rpa_key_id", "rpa_domain", type_="unique")
    except Exception:
        pass
    try:
        op.drop_constraint("pk_rpa_domain_rpa_id", "rpa_domain", type_="primary")
    except Exception:
        pass
    
    # Drop the table
    op.execute("DROP TABLE IF EXISTS rpa_domain CASCADE")
    
    # Drop sequence if exists
    op.execute("DROP SEQUENCE IF EXISTS rpa_domain_rpa_id_seq")


def downgrade() -> None:
    # ============================================
    # Step 1: Recreate rpa_domain table
    # ============================================
    op.create_table(
        "rpa_domain",
        sa.Column("rpa_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("rpa_key_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("events_config", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("IDX_rpa_domain_rpa_key_id", "rpa_domain", ["rpa_key_id"], unique=True)
    op.create_index("IDX_rpa_definitions_name", "rpa_domain", ["name"], unique=False)
    
    # ============================================
    # Step 2: Recreate rpa_automation_exec table
    # ============================================
    op.create_table(
        "rpa_automation_exec",
        sa.Column("exec_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("rpa_key_id", sa.Text(), nullable=False),
        sa.Column("exec_status", sa.Text(), server_default=sa.text("'PENDING'"), nullable=False),
        sa.Column("current_step", sa.Text(), nullable=True),
        sa.Column("rpa_request", sa.JSON(), nullable=True),
        sa.Column("rpa_response", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("callback_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("IDX_rpa_automation_exec_status", "rpa_automation_exec", ["exec_status"], unique=False)
    op.create_index("IDX_rpa_automation_exec_rpa_key_id", "rpa_automation_exec", ["rpa_key_id"], unique=False)
    op.create_index("IDX_rpa_automation_exec_created_at", "rpa_automation_exec", ["created_at"], unique=False)
    
    # ============================================
    # Step 3: Migrate data back from execution_requests to rpa_automation_exec
    # ============================================
    op.execute("""
        INSERT INTO rpa_automation_exec (
            exec_id, rpa_key_id, exec_status, rpa_request, rpa_response,
            error_message, callback_url, created_at, updated_at, finished_at
        )
        SELECT 
            exec_id, rpa_key_id, exec_status, rpa_request, rpa_response,
            error_message, callback_url, created_at, updated_at, finished_at
        FROM execution_requests
    """)
    
    # ============================================
    # Step 4: Restore foreign keys to rpa_automation_exec
    # ============================================
    # Drop foreign keys pointing to execution_requests
    op.execute("ALTER TABLE execution_requests DROP CONSTRAINT IF EXISTS fk_execution_requests_saga_id")
    op.execute("ALTER TABLE saga DROP CONSTRAINT IF EXISTS fk_saga_exec_id")
    op.execute("ALTER TABLE event_store DROP CONSTRAINT IF EXISTS fk_event_store_exec_id")
    op.execute("ALTER TABLE execution_read_model DROP CONSTRAINT IF EXISTS fk_execution_read_model_exec_id")
    op.execute("ALTER TABLE saga_read_model DROP CONSTRAINT IF EXISTS fk_saga_read_model_exec_id")
    
    # Restore foreign keys pointing to rpa_automation_exec
    op.create_foreign_key(
        "saga_exec_id_fkey",
        "saga",
        "rpa_automation_exec",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    op.create_foreign_key(
        "event_store_exec_id_fkey",
        "event_store",
        "rpa_automation_exec",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    op.create_foreign_key(
        "execution_read_model_exec_id_fkey",
        "execution_read_model",
        "rpa_automation_exec",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    op.create_foreign_key(
        "saga_read_model_exec_id_fkey",
        "saga_read_model",
        "rpa_automation_exec",
        ["exec_id"],
        ["exec_id"],
        ondelete="CASCADE"
    )
    
    # ============================================
    # Step 5: Restore trigger on rpa_automation_exec
    # ============================================
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
                (SELECT saga_id FROM saga WHERE exec_id = NEW.exec_id AND saga_type = 'DAG_SAGA' LIMIT 1),
                (SELECT current_state FROM saga WHERE exec_id = NEW.exec_id AND saga_type = 'DAG_SAGA' LIMIT 1)
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
    
    op.execute("DROP TRIGGER IF EXISTS trigger_sync_execution_read_model ON execution_requests")
    op.execute("""
        CREATE TRIGGER trigger_sync_execution_read_model
        AFTER INSERT OR UPDATE ON rpa_automation_exec
        FOR EACH ROW
        EXECUTE FUNCTION sync_execution_read_model();
    """)
    
    # ============================================
    # Step 6: Drop execution_requests table
    # ============================================
    op.execute("DROP INDEX IF EXISTS IDX_execution_requests_status")
    op.execute("DROP INDEX IF EXISTS IDX_execution_requests_rpa_key_id")
    op.execute("DROP INDEX IF EXISTS IDX_execution_requests_created_at")
    op.execute("DROP INDEX IF EXISTS IDX_execution_requests_saga_id")
    op.execute("DROP TABLE IF EXISTS execution_requests CASCADE")

