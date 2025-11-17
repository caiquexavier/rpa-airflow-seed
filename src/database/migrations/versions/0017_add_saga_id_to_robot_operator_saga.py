"""Add saga_id foreign key to robot_operator_saga.

This migration:
- Adds saga_id column to robot_operator_saga table with foreign key to saga.saga_id
- Adds saga_id column to robot_operator_saga_read_model table
- Creates index on saga_id for performance
- Updates sync_robot_operator_saga_read_model trigger function to include saga_id
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Step 1: Add saga_id column to robot_operator_saga table
    # ============================================
    # Add column as nullable first (for safety, though table should be empty)
    op.add_column(
        "robot_operator_saga",
        sa.Column(
            "saga_id",
            sa.BigInteger(),
            nullable=True,
            comment="Foreign key to parent saga.saga_id"
        )
    )
    
    # Since this is a new table (created in migration 0016), there should be no data
    # But to be safe, we'll make it NOT NULL after adding the foreign key
    
    # ============================================
    # Step 2: Create foreign key constraint
    # ============================================
    op.create_foreign_key(
        "fk_robot_operator_saga_saga_id",
        "robot_operator_saga",
        "saga",
        ["saga_id"],
        ["saga_id"],
        ondelete="CASCADE"
    )
    
    # ============================================
    # Step 3: Make saga_id NOT NULL (safe since table is new)
    # ============================================
    op.alter_column(
        "robot_operator_saga",
        "saga_id",
        existing_type=sa.BigInteger(),
        nullable=False
    )
    
    # ============================================
    # Step 4: Create index on saga_id for performance
    # ============================================
    op.create_index(
        "IDX_robot_operator_saga_saga_id",
        "robot_operator_saga",
        ["saga_id"],
        unique=False
    )
    
    # ============================================
    # Step 5: Add saga_id column to robot_operator_saga_read_model table
    # ============================================
    # Add column as nullable first (for safety, though table should be empty)
    op.add_column(
        "robot_operator_saga_read_model",
        sa.Column(
            "saga_id",
            sa.BigInteger(),
            nullable=True,
            comment="Foreign key to parent saga.saga_id"
        )
    )
    
    # Create foreign key constraint for read model
    op.create_foreign_key(
        "fk_robot_operator_saga_read_model_saga_id",
        "robot_operator_saga_read_model",
        "saga",
        ["saga_id"],
        ["saga_id"],
        ondelete="CASCADE"
    )
    
    # Make saga_id NOT NULL (safe since table is new)
    op.alter_column(
        "robot_operator_saga_read_model",
        "saga_id",
        existing_type=sa.BigInteger(),
        nullable=False
    )
    
    # Create index on saga_id in read model
    op.create_index(
        "IDX_robot_operator_saga_read_model_saga_id",
        "robot_operator_saga_read_model",
        ["saga_id"],
        unique=False
    )
    
    # ============================================
    # Step 6: Update sync_robot_operator_saga_read_model trigger function
    # ============================================
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_robot_operator_saga_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO robot_operator_saga_read_model (
                robot_operator_saga_id, saga_id, robot_operator_id, current_state, data,
                events_count, last_event_type, last_event_at, created_at, updated_at
            )
            VALUES (
                NEW.robot_operator_saga_id, NEW.saga_id, NEW.robot_operator_id, NEW.current_state, NEW.data,
                jsonb_array_length(NEW.events::jsonb),
                (SELECT event_type FROM robot_operator_saga_event_store WHERE robot_operator_saga_id = NEW.robot_operator_saga_id ORDER BY occurred_at DESC LIMIT 1),
                (SELECT occurred_at FROM robot_operator_saga_event_store WHERE robot_operator_saga_id = NEW.robot_operator_saga_id ORDER BY occurred_at DESC LIMIT 1),
                NEW.created_at, NEW.updated_at
            )
            ON CONFLICT (robot_operator_saga_id) DO UPDATE SET
                saga_id = EXCLUDED.saga_id,
                robot_operator_id = EXCLUDED.robot_operator_id,
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


def downgrade() -> None:
    # ============================================
    # Step 1: Drop trigger function (will be recreated without saga_id)
    # ============================================
    op.execute("DROP TRIGGER IF EXISTS trigger_sync_robot_operator_saga_read_model ON robot_operator_saga")
    op.execute("DROP FUNCTION IF EXISTS sync_robot_operator_saga_read_model()")
    
    # ============================================
    # Step 2: Drop indexes
    # ============================================
    op.drop_index("IDX_robot_operator_saga_read_model_saga_id", table_name="robot_operator_saga_read_model")
    op.drop_index("IDX_robot_operator_saga_saga_id", table_name="robot_operator_saga")
    
    # ============================================
    # Step 3: Drop foreign key constraints
    # ============================================
    op.drop_constraint("fk_robot_operator_saga_read_model_saga_id", "robot_operator_saga_read_model", type_="foreignkey")
    op.drop_constraint("fk_robot_operator_saga_saga_id", "robot_operator_saga", type_="foreignkey")
    
    # ============================================
    # Step 4: Drop columns (make nullable first if needed, then drop)
    # ============================================
    op.alter_column(
        "robot_operator_saga_read_model",
        "saga_id",
        existing_type=sa.BigInteger(),
        nullable=True
    )
    op.alter_column(
        "robot_operator_saga",
        "saga_id",
        existing_type=sa.BigInteger(),
        nullable=True
    )
    op.drop_column("robot_operator_saga_read_model", "saga_id")
    op.drop_column("robot_operator_saga", "saga_id")
    
    # ============================================
    # Step 5: Restore trigger function without saga_id
    # ============================================
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_robot_operator_saga_read_model()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO robot_operator_saga_read_model (
                robot_operator_saga_id, robot_operator_id, current_state, data,
                events_count, last_event_type, last_event_at, created_at, updated_at
            )
            VALUES (
                NEW.robot_operator_saga_id, NEW.robot_operator_id, NEW.current_state, NEW.data,
                jsonb_array_length(NEW.events::jsonb),
                (SELECT event_type FROM robot_operator_saga_event_store WHERE robot_operator_saga_id = NEW.robot_operator_saga_id ORDER BY occurred_at DESC LIMIT 1),
                (SELECT occurred_at FROM robot_operator_saga_event_store WHERE robot_operator_saga_id = NEW.robot_operator_saga_id ORDER BY occurred_at DESC LIMIT 1),
                NEW.created_at, NEW.updated_at
            )
            ON CONFLICT (robot_operator_saga_id) DO UPDATE SET
                robot_operator_id = EXCLUDED.robot_operator_id,
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
    
    op.execute("""
        CREATE TRIGGER trigger_sync_robot_operator_saga_read_model
        AFTER INSERT OR UPDATE ON robot_operator_saga
        FOR EACH ROW
        EXECUTE FUNCTION sync_robot_operator_saga_read_model();
    """)

