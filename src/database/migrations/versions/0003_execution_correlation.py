from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to rpa_automation_exec table
    with op.batch_alter_table("rpa_automation_exec") as batch:
        # Add rpa_request column (jsonb)
        batch.add_column(sa.Column("rpa_request", sa.JSON(), nullable=True))
        
        # Add rpa_response column (jsonb)
        batch.add_column(sa.Column("rpa_response", sa.JSON(), nullable=True))
        
        # Add error_message column
        batch.add_column(sa.Column("error_message", sa.Text(), nullable=True))
        
        # Update exec_status to use proper enum values and add default
        batch.alter_column("exec_status", 
                          existing_type=sa.Text(), 
                          server_default=sa.text("'PENDING'"),
                          nullable=False)
    
    # Migrate data from old columns to new ones
    op.execute("""
        UPDATE rpa_automation_exec 
        SET rpa_request = request::jsonb 
        WHERE request IS NOT NULL
    """)
    
    op.execute("""
        UPDATE rpa_automation_exec 
        SET rpa_response = response::jsonb 
        WHERE response IS NOT NULL
    """)
    
    # Drop old columns after migration
    with op.batch_alter_table("rpa_automation_exec") as batch:
        # Drop old request column
        try:
            batch.drop_column("request")
        except Exception:
            pass  # Column might not exist
        
        # Drop old response column  
        try:
            batch.drop_column("response")
        except Exception:
            pass  # Column might not exist
    
    # Backfill exec_status for existing records
    op.execute("""
        UPDATE rpa_automation_exec 
        SET exec_status = 'PENDING' 
        WHERE exec_status IS NULL OR exec_status = 'pending' OR exec_status = 'RECEIVED'
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS update_rpa_automation_exec_updated_at ON rpa_automation_exec")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop indexes
    op.drop_index("IDX_rpa_automation_exec_created_at", table_name="rpa_automation_exec")
    op.drop_index("IDX_rpa_automation_exec_exec_status", table_name="rpa_automation_exec")
    op.drop_index("IDX_rpa_automation_exec_rpa_key_id", table_name="rpa_automation_exec")
    
    # Revert column changes
    with op.batch_alter_table("rpa_automation_exec") as batch:
        # Add back old columns
        batch.add_column(sa.Column("request", sa.Text(), nullable=True))
        batch.add_column(sa.Column("response", sa.Text(), nullable=True))
        
        # Migrate data back
        op.execute("""
            UPDATE rpa_automation_exec 
            SET request = rpa_request::text 
            WHERE rpa_request IS NOT NULL
        """)
        
        op.execute("""
            UPDATE rpa_automation_exec 
            SET response = rpa_response::text 
            WHERE rpa_response IS NOT NULL
        """)
        
        # Drop new columns
        batch.drop_column("rpa_response")
        batch.drop_column("rpa_request")
        
        # Revert exec_status
        batch.alter_column("exec_status", 
                          existing_type=sa.Text(), 
                          server_default=sa.text("'pending'"),
                          nullable=False)
