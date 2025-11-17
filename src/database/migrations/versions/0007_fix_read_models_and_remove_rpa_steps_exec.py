"""Fix read models for multiple sagas per execution and remove rpa_steps_exec.

This migration:
- Removes unique constraint on saga_read_model.exec_id
- Adds partial unique index for DAG_SAGA only in saga_read_model
- Updates sync_saga_read_model trigger to handle multiple sagas per exec_id
- Updates sync_execution_read_model to get DAG saga specifically
- Removes rpa_steps_exec table (replaced by saga/event_store)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Fix saga_read_model constraints
    # ============================================
    # Drop the unique index on exec_id
    op.drop_index("IDX_saga_read_model_exec_id", table_name="saga_read_model")
    
    # Create a non-unique index on exec_id for general queries
    op.create_index("IDX_saga_read_model_exec_id", "saga_read_model", ["exec_id"], unique=False)
    
    # Create a partial unique index that only enforces uniqueness for DAG_SAGA
    op.execute("""
        CREATE UNIQUE INDEX IDX_saga_read_model_exec_id_dag_unique 
        ON saga_read_model (exec_id) 
        WHERE saga_type = 'DAG_SAGA'
    """)
    
    # ============================================
    # Update sync_saga_read_model trigger function
    # ============================================
    # The trigger already uses saga_id as conflict key, which is correct
    # But we need to ensure saga_type and parent_saga_id are included
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_saga_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO saga_read_model (
                saga_id, exec_id, rpa_key_id, current_state, rpa_request_object,
                events_count, last_event_type, last_event_at, created_at, updated_at,
                saga_type, parent_saga_id
            )
            VALUES (
                NEW.saga_id, NEW.exec_id, NEW.rpa_key_id, NEW.current_state, NEW.rpa_request_object,
                jsonb_array_length(NEW.events::jsonb),
                (SELECT event_type FROM event_store WHERE saga_id = NEW.saga_id ORDER BY occurred_at DESC LIMIT 1),
                (SELECT occurred_at FROM event_store WHERE saga_id = NEW.saga_id ORDER BY occurred_at DESC LIMIT 1),
                NEW.created_at, NEW.updated_at,
                NEW.saga_type, NEW.parent_saga_id
            )
            ON CONFLICT (saga_id) DO UPDATE SET
                exec_id = EXCLUDED.exec_id,
                rpa_key_id = EXCLUDED.rpa_key_id,
                current_state = EXCLUDED.current_state,
                rpa_request_object = EXCLUDED.rpa_request_object,
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
    
    # ============================================
    # Update sync_execution_read_model to get DAG saga
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
    
    # ============================================
    # Remove rpa_steps_exec table (replaced by saga/event_store)
    # ============================================
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS IDX_rpa_steps_exec_definition_id")
    op.execute("DROP INDEX IF EXISTS IDX_rpa_steps_exec_step_status")
    op.execute("DROP INDEX IF EXISTS IDX_rpa_steps_exec_exec_id_event_number")
    
    # Drop the table
    op.execute("DROP TABLE IF EXISTS rpa_steps_exec CASCADE")


def downgrade() -> None:
    # Restore rpa_steps_exec table (simplified version)
    op.create_table(
        "rpa_steps_exec",
        sa.Column("step_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("event_number", sa.BigInteger(), nullable=False),
        sa.Column("exec_id", sa.BigInteger(), nullable=False),
        sa.Column("definition_id", sa.BigInteger(), nullable=False),
        sa.Column("step_status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("current_step", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["exec_id"], ["rpa_automation_exec.exec_id"], ondelete="CASCADE"),
        sa.UniqueConstraint("exec_id", "event_number", name="uq_rpa_steps_exec_exec_id_event_number"),
    )
    op.create_index("IDX_rpa_steps_exec_exec_id_event_number", "rpa_steps_exec", ["exec_id", "event_number"], unique=False)
    op.create_index("IDX_rpa_steps_exec_step_status", "rpa_steps_exec", ["step_status"], unique=False)
    op.create_index("IDX_rpa_steps_exec_definition_id", "rpa_steps_exec", ["definition_id"], unique=False)
    
    # Restore original sync_execution_read_model
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
    
    # Restore original sync_saga_read_model (without saga_type/parent_saga_id)
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
    
    # Drop partial unique index
    op.execute("DROP INDEX IF EXISTS IDX_saga_read_model_exec_id_dag_unique")
    
    # Restore unique index on exec_id
    op.drop_index("IDX_saga_read_model_exec_id", table_name="saga_read_model")
    op.create_index("IDX_saga_read_model_exec_id", "saga_read_model", ["exec_id"], unique=True)

