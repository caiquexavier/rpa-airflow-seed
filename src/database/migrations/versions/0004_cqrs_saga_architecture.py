"""CQRS and SAGA architecture migration.

This migration introduces:
- SAGA table for orchestrating workflows with rpa_request_object and events list
- Event store for tracking all domain events
- Read models for CQRS query side
- Separation of command and query concerns
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # SAGA ORCHESTRATOR TABLE (Command Side)
    # ============================================
    op.create_table(
        "saga",
        sa.Column("saga_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("exec_id", sa.BigInteger(), nullable=False),
        sa.Column("rpa_key_id", sa.Text(), nullable=False),
        sa.Column("rpa_request_object", sa.JSON(), nullable=False, comment="Full RPA request payload"),
        sa.Column("current_state", sa.Text(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("events", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json"), comment="Array of events for each DAG task"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.ForeignKeyConstraint(["exec_id"], ["rpa_automation_exec.exec_id"], ondelete="CASCADE"),
    )
    op.create_index("IDX_saga_exec_id", "saga", ["exec_id"], unique=True)
    op.create_index("IDX_saga_rpa_key_id", "saga", ["rpa_key_id"], unique=False)
    op.create_index("IDX_saga_current_state", "saga", ["current_state"], unique=False)
    op.create_index("IDX_saga_created_at", "saga", ["created_at"], unique=False)

    # ============================================
    # EVENT STORE (Command Side - Event Sourcing)
    # ============================================
    op.create_table(
        "event_store",
        sa.Column("event_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("saga_id", sa.BigInteger(), nullable=False),
        sa.Column("exec_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False, comment="Event type: ExecutionStarted, TaskCompleted, TaskFailed, etc."),
        sa.Column("event_data", sa.JSON(), nullable=False, comment="Event payload"),
        sa.Column("task_id", sa.Text(), nullable=True, comment="DAG task identifier"),
        sa.Column("dag_id", sa.Text(), nullable=True, comment="DAG identifier"),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("1"), comment="Event version for optimistic locking"),
        sa.ForeignKeyConstraint(["saga_id"], ["saga.saga_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exec_id"], ["rpa_automation_exec.exec_id"], ondelete="CASCADE"),
    )
    op.create_index("IDX_event_store_saga_id", "event_store", ["saga_id"], unique=False)
    op.create_index("IDX_event_store_exec_id", "event_store", ["exec_id"], unique=False)
    op.create_index("IDX_event_store_event_type", "event_store", ["event_type"], unique=False)
    op.create_index("IDX_event_store_task_id", "event_store", ["task_id"], unique=False)
    op.create_index("IDX_event_store_occurred_at", "event_store", ["occurred_at"], unique=False)
    op.create_index("IDX_event_store_saga_version", "event_store", ["saga_id", "version"], unique=False)

    # ============================================
    # READ MODELS (Query Side - CQRS)
    # ============================================
    # Execution Read Model - Denormalized view for fast queries
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
        sa.ForeignKeyConstraint(["exec_id"], ["rpa_automation_exec.exec_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saga_id"], ["saga.saga_id"], ondelete="SET NULL"),
    )
    op.create_index("IDX_execution_read_model_rpa_key_id", "execution_read_model", ["rpa_key_id"], unique=False)
    op.create_index("IDX_execution_read_model_exec_status", "execution_read_model", ["exec_status"], unique=False)
    op.create_index("IDX_execution_read_model_saga_id", "execution_read_model", ["saga_id"], unique=False)
    op.create_index("IDX_execution_read_model_created_at", "execution_read_model", ["created_at"], unique=False)

    # SAGA Read Model - Denormalized view for SAGA queries
    op.create_table(
        "saga_read_model",
        sa.Column("saga_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("exec_id", sa.BigInteger(), nullable=False),
        sa.Column("rpa_key_id", sa.Text(), nullable=False),
        sa.Column("current_state", sa.Text(), nullable=False),
        sa.Column("rpa_request_object", sa.JSON(), nullable=False),
        sa.Column("events_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_event_type", sa.Text(), nullable=True),
        sa.Column("last_event_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["saga_id"], ["saga.saga_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["exec_id"], ["rpa_automation_exec.exec_id"], ondelete="CASCADE"),
    )
    op.create_index("IDX_saga_read_model_exec_id", "saga_read_model", ["exec_id"], unique=True)
    op.create_index("IDX_saga_read_model_rpa_key_id", "saga_read_model", ["rpa_key_id"], unique=False)
    op.create_index("IDX_saga_read_model_current_state", "saga_read_model", ["current_state"], unique=False)
    op.create_index("IDX_saga_read_model_created_at", "saga_read_model", ["created_at"], unique=False)

    # ============================================
    # TRIGGERS FOR READ MODEL SYNCHRONIZATION
    # ============================================
    # Function to update execution_read_model when rpa_automation_exec changes
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
                (SELECT saga_id FROM saga WHERE exec_id = NEW.exec_id LIMIT 1),
                (SELECT current_state FROM saga WHERE exec_id = NEW.exec_id LIMIT 1)
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
        AFTER INSERT OR UPDATE ON rpa_automation_exec
        FOR EACH ROW
        EXECUTE FUNCTION sync_execution_read_model();
    """)

    # Function to update saga_read_model when saga changes
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_saga_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO saga_read_model (
                saga_id, exec_id, rpa_key_id, current_state, rpa_request_object,
                events_count, last_event_type, last_event_at, created_at, updated_at
            )
            VALUES (
                NEW.saga_id, NEW.exec_id, NEW.rpa_key_id, NEW.current_state, NEW.rpa_request_object,
                jsonb_array_length(NEW.events::jsonb),
                (SELECT event_type FROM event_store WHERE saga_id = NEW.saga_id ORDER BY occurred_at DESC LIMIT 1),
                (SELECT occurred_at FROM event_store WHERE saga_id = NEW.saga_id ORDER BY occurred_at DESC LIMIT 1),
                NEW.created_at, NEW.updated_at
            )
            ON CONFLICT (saga_id) DO UPDATE SET
                exec_id = EXCLUDED.exec_id,
                rpa_key_id = EXCLUDED.rpa_key_id,
                current_state = EXCLUDED.current_state,
                rpa_request_object = EXCLUDED.rpa_request_object,
                events_count = EXCLUDED.events_count,
                last_event_type = EXCLUDED.last_event_type,
                last_event_at = EXCLUDED.last_event_at,
                updated_at = EXCLUDED.updated_at;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER trigger_sync_saga_read_model
        AFTER INSERT OR UPDATE ON saga
        FOR EACH ROW
        EXECUTE FUNCTION sync_saga_read_model();
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS trigger_sync_saga_read_model ON saga")
    op.execute("DROP TRIGGER IF EXISTS trigger_sync_execution_read_model ON rpa_automation_exec")
    op.execute("DROP FUNCTION IF EXISTS sync_saga_read_model()")
    op.execute("DROP FUNCTION IF EXISTS sync_execution_read_model()")

    # Drop read models
    op.drop_index("IDX_saga_read_model_created_at", table_name="saga_read_model")
    op.drop_index("IDX_saga_read_model_current_state", table_name="saga_read_model")
    op.drop_index("IDX_saga_read_model_rpa_key_id", table_name="saga_read_model")
    op.drop_index("IDX_saga_read_model_exec_id", table_name="saga_read_model")
    op.drop_table("saga_read_model")

    op.drop_index("IDX_execution_read_model_created_at", table_name="execution_read_model")
    op.drop_index("IDX_execution_read_model_saga_id", table_name="execution_read_model")
    op.drop_index("IDX_execution_read_model_exec_status", table_name="execution_read_model")
    op.drop_index("IDX_execution_read_model_rpa_key_id", table_name="execution_read_model")
    op.drop_table("execution_read_model")

    # Drop event store
    op.drop_index("IDX_event_store_saga_version", table_name="event_store")
    op.drop_index("IDX_event_store_occurred_at", table_name="event_store")
    op.drop_index("IDX_event_store_task_id", table_name="event_store")
    op.drop_index("IDX_event_store_event_type", table_name="event_store")
    op.drop_index("IDX_event_store_exec_id", table_name="event_store")
    op.drop_index("IDX_event_store_saga_id", table_name="event_store")
    op.drop_table("event_store")

    # Drop saga
    op.drop_index("IDX_saga_created_at", table_name="saga")
    op.drop_index("IDX_saga_current_state", table_name="saga")
    op.drop_index("IDX_saga_rpa_key_id", table_name="saga")
    op.drop_index("IDX_saga_exec_id", table_name="saga")
    op.drop_table("saga")

