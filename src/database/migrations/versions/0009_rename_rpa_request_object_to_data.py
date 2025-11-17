"""Rename rpa_request_object to data in saga tables.

This migration:
- Renames rpa_request_object column to data in saga table
- Renames rpa_request_object column to data in saga_read_model table
- Updates sync_saga_read_model() trigger function to use new column name
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Step 1: Rename column in saga table
    # ============================================
    op.alter_column(
        "saga",
        "rpa_request_object",
        new_column_name="data",
        existing_type=sa.JSON(),
        existing_nullable=False,
        existing_comment="Full RPA request payload"
    )
    
    # ============================================
    # Step 2: Rename column in saga_read_model table
    # ============================================
    op.alter_column(
        "saga_read_model",
        "rpa_request_object",
        new_column_name="data",
        existing_type=sa.JSON(),
        existing_nullable=False
    )
    
    # ============================================
    # Step 3: Update sync_saga_read_model() trigger function
    # ============================================
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_saga_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO saga_read_model (
                saga_id, exec_id, rpa_key_id, current_state, data,
                events_count, last_event_type, last_event_at, created_at, updated_at,
                saga_type, parent_saga_id
            )
            VALUES (
                NEW.saga_id, NEW.exec_id, NEW.rpa_key_id, NEW.current_state, NEW.data,
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
    # ============================================
    # Step 1: Revert sync_saga_read_model() trigger function
    # ============================================
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
    # Step 2: Rename column back in saga_read_model table
    # ============================================
    op.alter_column(
        "saga_read_model",
        "data",
        new_column_name="rpa_request_object",
        existing_type=sa.JSON(),
        existing_nullable=False
    )
    
    # ============================================
    # Step 3: Rename column back in saga table
    # ============================================
    op.alter_column(
        "saga",
        "data",
        new_column_name="rpa_request_object",
        existing_type=sa.JSON(),
        existing_nullable=False,
        existing_comment="Full RPA request payload"
    )

