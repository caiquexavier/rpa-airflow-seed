"""Create robot_operator_saga tables.

This migration introduces:
- robot_operator_saga table for orchestrating robot operator workflows
- robot_operator_saga_event_store for tracking all robot operator domain events
- Read model for CQRS query side
- Separation of command and query concerns for RobotOperatorSaga
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # ROBOT OPERATOR SAGA TABLE (Command Side)
    # ============================================
    op.create_table(
        "robot_operator_saga",
        sa.Column("robot_operator_saga_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("robot_operator_id", sa.Text(), nullable=False, comment="Robot operator identifier"),
        sa.Column("data", sa.JSON(), nullable=False, comment="Saga data payload"),
        sa.Column("current_state", sa.Text(), nullable=False, server_default=sa.text("'PENDING'")),
        sa.Column("events", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json"), comment="Array of events for each robot operator step"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("IDX_robot_operator_saga_robot_operator_id", "robot_operator_saga", ["robot_operator_id"], unique=False)
    op.create_index("IDX_robot_operator_saga_current_state", "robot_operator_saga", ["current_state"], unique=False)
    op.create_index("IDX_robot_operator_saga_created_at", "robot_operator_saga", ["created_at"], unique=False)

    # ============================================
    # ROBOT OPERATOR SAGA EVENT STORE (Command Side - Event Sourcing)
    # ============================================
    op.create_table(
        "robot_operator_saga_event_store",
        sa.Column("event_id", sa.BigInteger(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column("robot_operator_saga_id", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False, comment="Event type: RobotOperatorSagaStarted, RobotOperatorStepRequested, RobotOperatorStepCompleted, RobotOperatorStepFailed, etc."),
        sa.Column("event_data", sa.JSON(), nullable=False, comment="Event payload"),
        sa.Column("step_id", sa.Text(), nullable=True, comment="Robot operator step identifier"),
        sa.Column("robot_operator_id", sa.Text(), nullable=False, comment="Robot operator identifier"),
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("1"), comment="Event version for optimistic locking"),
        sa.ForeignKeyConstraint(["robot_operator_saga_id"], ["robot_operator_saga.robot_operator_saga_id"], ondelete="CASCADE"),
    )
    op.create_index("IDX_robot_operator_saga_event_store_saga_id", "robot_operator_saga_event_store", ["robot_operator_saga_id"], unique=False)
    op.create_index("IDX_robot_operator_saga_event_store_event_type", "robot_operator_saga_event_store", ["event_type"], unique=False)
    op.create_index("IDX_robot_operator_saga_event_store_step_id", "robot_operator_saga_event_store", ["step_id"], unique=False)
    op.create_index("IDX_robot_operator_saga_event_store_robot_operator_id", "robot_operator_saga_event_store", ["robot_operator_id"], unique=False)
    op.create_index("IDX_robot_operator_saga_event_store_occurred_at", "robot_operator_saga_event_store", ["occurred_at"], unique=False)
    op.create_index("IDX_robot_operator_saga_event_store_saga_version", "robot_operator_saga_event_store", ["robot_operator_saga_id", "version"], unique=False)

    # ============================================
    # READ MODEL (Query Side - CQRS)
    # ============================================
    op.create_table(
        "robot_operator_saga_read_model",
        sa.Column("robot_operator_saga_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("robot_operator_id", sa.Text(), nullable=False),
        sa.Column("current_state", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("events_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_event_type", sa.Text(), nullable=True),
        sa.Column("last_event_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["robot_operator_saga_id"], ["robot_operator_saga.robot_operator_saga_id"], ondelete="CASCADE"),
    )
    op.create_index("IDX_robot_operator_saga_read_model_robot_operator_id", "robot_operator_saga_read_model", ["robot_operator_id"], unique=False)
    op.create_index("IDX_robot_operator_saga_read_model_current_state", "robot_operator_saga_read_model", ["current_state"], unique=False)
    op.create_index("IDX_robot_operator_saga_read_model_created_at", "robot_operator_saga_read_model", ["created_at"], unique=False)

    # ============================================
    # TRIGGER FOR READ MODEL SYNCHRONIZATION
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


def downgrade() -> None:
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS trigger_sync_robot_operator_saga_read_model ON robot_operator_saga")
    op.execute("DROP FUNCTION IF EXISTS sync_robot_operator_saga_read_model()")

    # Drop read model
    op.drop_index("IDX_robot_operator_saga_read_model_created_at", table_name="robot_operator_saga_read_model")
    op.drop_index("IDX_robot_operator_saga_read_model_current_state", table_name="robot_operator_saga_read_model")
    op.drop_index("IDX_robot_operator_saga_read_model_robot_operator_id", table_name="robot_operator_saga_read_model")
    op.drop_table("robot_operator_saga_read_model")

    # Drop event store
    op.drop_index("IDX_robot_operator_saga_event_store_saga_version", table_name="robot_operator_saga_event_store")
    op.drop_index("IDX_robot_operator_saga_event_store_occurred_at", table_name="robot_operator_saga_event_store")
    op.drop_index("IDX_robot_operator_saga_event_store_robot_operator_id", table_name="robot_operator_saga_event_store")
    op.drop_index("IDX_robot_operator_saga_event_store_step_id", table_name="robot_operator_saga_event_store")
    op.drop_index("IDX_robot_operator_saga_event_store_event_type", table_name="robot_operator_saga_event_store")
    op.drop_index("IDX_robot_operator_saga_event_store_saga_id", table_name="robot_operator_saga_event_store")
    op.drop_table("robot_operator_saga_event_store")

    # Drop saga
    op.drop_index("IDX_robot_operator_saga_created_at", table_name="robot_operator_saga")
    op.drop_index("IDX_robot_operator_saga_current_state", table_name="robot_operator_saga")
    op.drop_index("IDX_robot_operator_saga_robot_operator_id", table_name="robot_operator_saga")
    op.drop_table("robot_operator_saga")

