from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
	# rpa_definitions
	op.create_table(
		"rpa_definitions",
		sa.Column("definition_id", sa.BigInteger(), primary_key=True, nullable=False),
		sa.Column("name", sa.Text(), nullable=False),
		sa.Column("events_config", sa.Text(), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
		sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
	)
	op.create_index("IDX_rpa_definitions_name", "rpa_definitions", ["name"], unique=False)

	# rpa_automation_exec
	op.create_table(
		"rpa_automation_exec",
		sa.Column("exec_id", sa.BigInteger(), primary_key=True, nullable=False),
		sa.Column("definition_id", sa.BigInteger(), nullable=False),
		sa.Column("exec_status", sa.Text(), server_default=sa.text("'pending'"), nullable=False),
		sa.Column("current_step", sa.Text(), nullable=True),
		sa.Column("request", sa.Text(), nullable=True),
		sa.Column("response", sa.Text(), nullable=True),
		sa.Column("callback_url", sa.Text(), nullable=True),
		sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
		sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
		sa.Column("started_at", sa.TIMESTAMP(timezone=True), nullable=True),
		sa.Column("finished_at", sa.TIMESTAMP(timezone=True), nullable=True),
		sa.ForeignKeyConstraint(["definition_id"], ["rpa_definitions.definition_id"], ondelete="RESTRICT"),
	)
	op.create_index("IDX_rpa_automation_exec_status", "rpa_automation_exec", ["exec_status"], unique=False)
	op.create_index("IDX_rpa_automation_exec_definition_id", "rpa_automation_exec", ["definition_id"], unique=False)
	op.create_index("IDX_rpa_automation_exec_created_at", "rpa_automation_exec", ["created_at"], unique=False)

	# rpa_steps_exec
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
		sa.ForeignKeyConstraint(["definition_id"], ["rpa_definitions.definition_id"], ondelete="RESTRICT"),
		# Unique constraint for (exec_id, event_number)
		sa.UniqueConstraint("exec_id", "event_number", name="uq_rpa_steps_exec_exec_id_event_number"),
	)
	op.create_index("IDX_rpa_steps_exec_exec_id_event_number", "rpa_steps_exec", ["exec_id", "event_number"], unique=False)
	op.create_index("IDX_rpa_steps_exec_step_status", "rpa_steps_exec", ["step_status"], unique=False)
	op.create_index("IDX_rpa_steps_exec_definition_id", "rpa_steps_exec", ["definition_id"], unique=False)


def downgrade() -> None:
	op.drop_index("IDX_rpa_steps_exec_definition_id", table_name="rpa_steps_exec")
	op.drop_index("IDX_rpa_steps_exec_step_status", table_name="rpa_steps_exec")
	op.drop_index("IDX_rpa_steps_exec_exec_id_event_number", table_name="rpa_steps_exec")
	op.drop_table("rpa_steps_exec")

	op.drop_index("IDX_rpa_automation_exec_created_at", table_name="rpa_automation_exec")
	op.drop_index("IDX_rpa_automation_exec_definition_id", table_name="rpa_automation_exec")
	op.drop_index("IDX_rpa_automation_exec_status", table_name="rpa_automation_exec")
	op.drop_table("rpa_automation_exec")

	op.drop_index("IDX_rpa_definitions_name", table_name="rpa_definitions")
	op.drop_table("rpa_definitions")
