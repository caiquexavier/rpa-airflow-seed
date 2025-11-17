"""Add DAG and operator context to event_store.

This migration:
- Adds dag_run_id column to event_store table
- Adds execution_date column to event_store table
- Adds try_number column to event_store table
- Adds operator_type column to event_store table
- Adds operator_id column to event_store table
- Adds operator_params column to event_store table
- Creates indexes for the new columns
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ============================================
    # Step 1: Add DAG context columns
    # ============================================
    op.add_column(
        "event_store",
        sa.Column(
            "dag_run_id",
            sa.Text(),
            nullable=True,
            comment="DAG run ID from Airflow"
        )
    )
    
    op.add_column(
        "event_store",
        sa.Column(
            "execution_date",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Execution date/timestamp from Airflow"
        )
    )
    
    op.add_column(
        "event_store",
        sa.Column(
            "try_number",
            sa.Integer(),
            nullable=True,
            comment="Task try number from Airflow"
        )
    )
    
    # ============================================
    # Step 2: Add operator context columns
    # ============================================
    op.add_column(
        "event_store",
        sa.Column(
            "operator_type",
            sa.Text(),
            nullable=True,
            comment="Operator type (e.g., PythonOperator, RobotFrameworkOperator)"
        )
    )
    
    op.add_column(
        "event_store",
        sa.Column(
            "operator_id",
            sa.Text(),
            nullable=True,
            comment="Operator identifier"
        )
    )
    
    op.add_column(
        "event_store",
        sa.Column(
            "operator_params",
            sa.JSON(),
            nullable=True,
            comment="Operator parameters"
        )
    )
    
    # ============================================
    # Step 3: Create indexes for new columns
    # ============================================
    op.create_index("IDX_event_store_dag_run_id", "event_store", ["dag_run_id"], unique=False)
    op.create_index("IDX_event_store_execution_date", "event_store", ["execution_date"], unique=False)
    op.create_index("IDX_event_store_operator_type", "event_store", ["operator_type"], unique=False)
    op.create_index("IDX_event_store_operator_id", "event_store", ["operator_id"], unique=False)


def downgrade() -> None:
    # ============================================
    # Step 1: Drop indexes
    # ============================================
    op.drop_index("IDX_event_store_operator_id", table_name="event_store")
    op.drop_index("IDX_event_store_operator_type", table_name="event_store")
    op.drop_index("IDX_event_store_execution_date", table_name="event_store")
    op.drop_index("IDX_event_store_dag_run_id", table_name="event_store")
    
    # ============================================
    # Step 2: Drop operator context columns
    # ============================================
    op.drop_column("event_store", "operator_params")
    op.drop_column("event_store", "operator_id")
    op.drop_column("event_store", "operator_type")
    
    # ============================================
    # Step 3: Drop DAG context columns
    # ============================================
    op.drop_column("event_store", "try_number")
    op.drop_column("event_store", "execution_date")
    op.drop_column("event_store", "dag_run_id")

