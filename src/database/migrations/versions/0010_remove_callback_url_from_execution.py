"""Remove callback_url from execution tables.

This migration:
- Drops callback_url column from execution_requests table
- Drops callback_url column from execution_read_model table
- Updates sync_execution_read_model() trigger function to remove callback_url
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Step 1: Drop callback_url from execution_requests
    # ============================================
    op.drop_column("execution_requests", "callback_url")
    
    # ============================================
    # Step 2: Drop callback_url from execution_read_model
    # ============================================
    op.drop_column("execution_read_model", "callback_url")
    
    # ============================================
    # Step 3: Update sync_execution_read_model() trigger function
    # ============================================
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_execution_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO execution_read_model (
                exec_id, rpa_key_id, exec_status, rpa_request, rpa_response,
                error_message, created_at, updated_at, finished_at, saga_id, saga_state
            )
            VALUES (
                NEW.exec_id, NEW.rpa_key_id, NEW.exec_status, NEW.rpa_request, NEW.rpa_response,
                NEW.error_message, NEW.created_at, NEW.updated_at, NEW.finished_at,
                (SELECT saga_id FROM saga WHERE exec_id = NEW.exec_id LIMIT 1),
                (SELECT current_state::text FROM saga WHERE exec_id = NEW.exec_id LIMIT 1)
            )
            ON CONFLICT (exec_id) DO UPDATE SET
                rpa_key_id = EXCLUDED.rpa_key_id,
                exec_status = EXCLUDED.exec_status,
                rpa_request = EXCLUDED.rpa_request,
                rpa_response = EXCLUDED.rpa_response,
                error_message = EXCLUDED.error_message,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                finished_at = EXCLUDED.finished_at,
                saga_id = EXCLUDED.saga_id,
                saga_state = EXCLUDED.saga_state;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    # ============================================
    # Step 1: Add callback_url back to execution_read_model
    # ============================================
    op.add_column(
        "execution_read_model",
        sa.Column("callback_url", sa.Text(), nullable=True)
    )
    
    # ============================================
    # Step 2: Add callback_url back to execution_requests
    # ============================================
    op.add_column(
        "execution_requests",
        sa.Column("callback_url", sa.Text(), nullable=True)
    )
    
    # ============================================
    # Step 3: Restore sync_execution_read_model() trigger function with callback_url
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
                (SELECT saga_id FROM saga WHERE exec_id = NEW.exec_id LIMIT 1),
                (SELECT current_state::text FROM saga WHERE exec_id = NEW.exec_id LIMIT 1)
            )
            ON CONFLICT (exec_id) DO UPDATE SET
                rpa_key_id = EXCLUDED.rpa_key_id,
                exec_status = EXCLUDED.exec_status,
                rpa_request = EXCLUDED.rpa_request,
                rpa_response = EXCLUDED.rpa_response,
                error_message = EXCLUDED.error_message,
                callback_url = EXCLUDED.callback_url,
                created_at = EXCLUDED.created_at,
                updated_at = EXCLUDED.updated_at,
                finished_at = EXCLUDED.finished_at,
                saga_id = EXCLUDED.saga_id,
                saga_state = EXCLUDED.saga_state;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

