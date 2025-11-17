"""Add saga_type and parent_saga_id to support DAG and Robot sagas.

This migration introduces:
- saga_type column to distinguish between DAG_SAGA and ROBOT_SAGA
- parent_saga_id to support nested sagas (Robot Saga within DAG Saga)
- robot_step column to event_store for robot step tracking
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add saga_type column to saga table
    op.add_column(
        "saga",
        sa.Column(
            "saga_type",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'DAG_SAGA'"),
            comment="SAGA type: DAG_SAGA or ROBOT_SAGA"
        )
    )
    
    # Add parent_saga_id column to saga table for nested sagas
    op.add_column(
        "saga",
        sa.Column(
            "parent_saga_id",
            sa.BigInteger(),
            nullable=True,
            comment="Parent saga ID for nested sagas (Robot Saga within DAG Saga)"
        )
    )
    
    # Add foreign key constraint for parent_saga_id
    op.create_foreign_key(
        "fk_saga_parent_saga_id",
        "saga",
        "saga",
        ["parent_saga_id"],
        ["saga_id"],
        ondelete="CASCADE"
    )
    
    # Add index for saga_type
    op.create_index("IDX_saga_saga_type", "saga", ["saga_type"], unique=False)
    
    # Add index for parent_saga_id
    op.create_index("IDX_saga_parent_saga_id", "saga", ["parent_saga_id"], unique=False)
    
    # Add robot_step column to event_store for robot step tracking
    op.add_column(
        "event_store",
        sa.Column(
            "robot_step",
            sa.Text(),
            nullable=True,
            comment="Robot Framework step identifier (e.g., Start Browser, Login To e-Cargo)"
        )
    )
    
    # Add index for robot_step
    op.create_index("IDX_event_store_robot_step", "event_store", ["robot_step"], unique=False)
    
    # Update saga_read_model to include saga_type
    op.add_column(
        "saga_read_model",
        sa.Column(
            "saga_type",
            sa.Text(),
            nullable=True,
            comment="SAGA type: DAG_SAGA or ROBOT_SAGA"
        )
    )
    
    op.add_column(
        "saga_read_model",
        sa.Column(
            "parent_saga_id",
            sa.BigInteger(),
            nullable=True,
            comment="Parent saga ID for nested sagas"
        )
    )
    
    op.create_index("IDX_saga_read_model_saga_type", "saga_read_model", ["saga_type"], unique=False)
    op.create_index("IDX_saga_read_model_parent_saga_id", "saga_read_model", ["parent_saga_id"], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index("IDX_saga_read_model_parent_saga_id", table_name="saga_read_model")
    op.drop_index("IDX_saga_read_model_saga_type", table_name="saga_read_model")
    op.drop_index("IDX_event_store_robot_step", table_name="event_store")
    op.drop_index("IDX_saga_parent_saga_id", table_name="saga")
    op.drop_index("IDX_saga_saga_type", table_name="saga")
    
    # Drop foreign key
    op.drop_constraint("fk_saga_parent_saga_id", "saga", type_="foreignkey")
    
    # Drop columns
    op.drop_column("saga_read_model", "parent_saga_id")
    op.drop_column("saga_read_model", "saga_type")
    op.drop_column("event_store", "robot_step")
    op.drop_column("saga", "parent_saga_id")
    op.drop_column("saga", "saga_type")

