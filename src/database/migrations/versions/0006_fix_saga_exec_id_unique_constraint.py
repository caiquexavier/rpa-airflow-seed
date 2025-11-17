"""Fix saga exec_id unique constraint to allow multiple Robot Sagas per execution.

This migration:
- Removes the unique constraint on exec_id (allows multiple sagas per execution)
- Adds a partial unique index on exec_id for DAG_SAGA only (ensures one DAG Saga per execution)
- Allows multiple Robot Sagas per exec_id
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the old unique index on exec_id
    op.drop_index("IDX_saga_exec_id", table_name="saga")
    
    # Create a non-unique index on exec_id for general queries
    op.create_index("IDX_saga_exec_id", "saga", ["exec_id"], unique=False)
    
    # Create a partial unique index that only enforces uniqueness for DAG_SAGA
    # This ensures one DAG Saga per execution, but allows multiple Robot Sagas
    op.execute("""
        CREATE UNIQUE INDEX IDX_saga_exec_id_dag_unique 
        ON saga (exec_id) 
        WHERE saga_type = 'DAG_SAGA'
    """)


def downgrade() -> None:
    # Drop the partial unique index
    op.execute("DROP INDEX IF EXISTS IDX_saga_exec_id_dag_unique")
    
    # Drop the non-unique index
    op.drop_index("IDX_saga_exec_id", table_name="saga")
    
    # Restore the original unique index
    op.create_index("IDX_saga_exec_id", "saga", ["exec_id"], unique=True)

