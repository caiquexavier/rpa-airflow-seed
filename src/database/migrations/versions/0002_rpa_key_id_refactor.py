from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
	# 1) Rename rpa_definitions -> rpa_domain
	op.rename_table("rpa_definitions", "rpa_domain")

	# 2) Drop FKs that reference old rpa_definitions PK before changing PK
	try:
		op.execute("ALTER TABLE rpa_automation_exec DROP CONSTRAINT IF EXISTS rpa_automation_exec_definition_id_fkey")
	except Exception:
		pass
	try:
		op.execute("ALTER TABLE rpa_steps_exec DROP CONSTRAINT IF EXISTS rpa_steps_exec_definition_id_fkey")
	except Exception:
		pass

	# 3) Drop existing primary key on rpa_domain (carried over from rpa_definitions)
	op.execute(
		"""
		DO $$
		DECLARE
			pk_name text;
		BEGIN
			SELECT conname INTO pk_name
			FROM pg_constraint
			WHERE conrelid = 'rpa_domain'::regclass AND contype = 'p';
			IF pk_name IS NOT NULL THEN
				EXECUTE format('ALTER TABLE rpa_domain DROP CONSTRAINT %I CASCADE', pk_name);
			END IF;
		END$$;
		"""
	)

	# 4) Add rpa_id (BIGSERIAL PK) and rpa_key_id (TEXT UNIQUE NOT NULL)
	op.add_column(
		"rpa_domain",
		sa.Column("rpa_id", sa.BigInteger(), autoincrement=True, nullable=True),
	)
	op.add_column(
		"rpa_domain",
		sa.Column("rpa_key_id", sa.Text(), nullable=True),
	)

	# Backfill rpa_id and rpa_key_id: set rpa_key_id = definition_id::text, rpa_id = nextval
	# Create sequence for rpa_id if not present and fill values
	op.execute(
		"""
		DO $$
		BEGIN
			IF NOT EXISTS (
				SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
				WHERE c.relkind = 'S' AND c.relname = 'rpa_domain_rpa_id_seq'
			) THEN
				CREATE SEQUENCE rpa_domain_rpa_id_seq;
			END IF;
		END$$;
		"""
	)
	op.execute(
		"""
		UPDATE rpa_domain SET rpa_key_id = definition_id::text;
		"""
	)
	op.execute(
		"""
		UPDATE rpa_domain SET rpa_id = nextval('rpa_domain_rpa_id_seq') WHERE rpa_id IS NULL;
		"""
	)

	# Set NOT NULL and PK/UNIQUE constraints
	op.alter_column("rpa_domain", "rpa_id", nullable=False)
	# Drop existing primary key on the old column if present, then set new PK
	# Drop possible old PK names after table rename
	for pk_name in ("rpa_domain_pkey", "rpa_definitions_pkey"):
		try:
			op.execute(f"ALTER TABLE rpa_domain DROP CONSTRAINT IF EXISTS {pk_name}")
		except Exception:
			pass
	op.create_primary_key("pk_rpa_domain_rpa_id", "rpa_domain", ["rpa_id"])
	op.execute("ALTER TABLE rpa_domain ALTER COLUMN rpa_id SET DEFAULT nextval('rpa_domain_rpa_id_seq')")
	op.execute("ALTER SEQUENCE rpa_domain_rpa_id_seq OWNED BY rpa_domain.rpa_id")

	op.alter_column("rpa_domain", "rpa_key_id", nullable=False)
	op.create_unique_constraint("uq_rpa_domain_rpa_key_id", "rpa_domain", ["rpa_key_id"])

	# 5) Ensure other required columns exist (name, events_config, created_at, updated_at) already exist from v0001
	# No-op here; they were present on original table.

	# 6) rpa_automation_exec.definition_id -> rpa_key_id (TEXT)
	# Drop FK/index referencing old definition_id
	with op.batch_alter_table("rpa_automation_exec") as batch:
		# Drop index if exists
		try:
			batch.drop_index("IDX_rpa_automation_exec_definition_id")
		except Exception:
			pass
		# Drop old FK constraint if exists (name unknown from autogen, handle via raw SQL)
	try:
		op.execute("ALTER TABLE rpa_automation_exec DROP CONSTRAINT IF EXISTS rpa_automation_exec_definition_id_fkey")
	except Exception:
		pass

	with op.batch_alter_table("rpa_automation_exec") as batch:
		batch.add_column(sa.Column("rpa_key_id", sa.Text(), nullable=True))

	# Backfill rpa_key_id = definition_id::text
	op.execute("UPDATE rpa_automation_exec SET rpa_key_id = definition_id::text")

	with op.batch_alter_table("rpa_automation_exec") as batch:
		batch.alter_column("rpa_key_id", existing_type=sa.Text(), nullable=False)
		# Optionally drop the old column now that data is migrated
		batch.drop_column("definition_id")

	# 7) Create index on rpa_automation_exec(rpa_key_id)
	op.create_index("IDX_rpa_automation_exec_rpa_key_id", "rpa_automation_exec", ["rpa_key_id"], unique=False)

	# 8) Update rpa_steps_exec.definition_id -> rpa_key_id (TEXT) and drop FK
	try:
		op.execute("ALTER TABLE rpa_steps_exec DROP CONSTRAINT IF EXISTS rpa_steps_exec_definition_id_fkey")
	except Exception:
		pass
	with op.batch_alter_table("rpa_steps_exec") as batch:
		batch.add_column(sa.Column("rpa_key_id", sa.Text(), nullable=True))
	# Backfill new column from prior bigint id cast to text
	op.execute("UPDATE rpa_steps_exec SET rpa_key_id = definition_id::text")
	with op.batch_alter_table("rpa_steps_exec") as batch:
		batch.alter_column("rpa_key_id", existing_type=sa.Text(), nullable=False)
		# Drop old artifacts (index on definition_id) if present
		try:
			batch.drop_index("IDX_rpa_steps_exec_definition_id")
		except Exception:
			pass
		batch.drop_column("definition_id")

	# 9) Seed rpa_domain with job-001 if not present
	op.execute(
		"""
		INSERT INTO rpa_domain (rpa_key_id, name, events_config)
		SELECT 'job-001', 'Job 001', NULL
		WHERE NOT EXISTS (
			SELECT 1 FROM rpa_domain WHERE rpa_key_id = 'job-001'
		);
		"""
	)


def downgrade() -> None:
	# Reverse seed removal is a no-op or delete the seeded row
	op.execute("DELETE FROM rpa_domain WHERE rpa_key_id = 'job-001'")

	# Recreate definition_id columns where required (best-effort minimal downgrade)
	with op.batch_alter_table("rpa_steps_exec") as batch:
		batch.add_column(sa.Column("definition_id", sa.BigInteger(), nullable=False))
	op.execute("UPDATE rpa_steps_exec SET definition_id = COALESCE(NULLIF(rpa_key_id, '')::bigint, 0)")
	with op.batch_alter_table("rpa_steps_exec") as batch:
		batch.drop_column("rpa_key_id")

	with op.batch_alter_table("rpa_automation_exec") as batch:
		batch.add_column(sa.Column("definition_id", sa.BigInteger(), nullable=False))
	op.execute("UPDATE rpa_automation_exec SET definition_id = COALESCE(NULLIF(rpa_key_id, '')::bigint, 0)")
	with op.batch_alter_table("rpa_automation_exec") as batch:
		batch.drop_index("IDX_rpa_automation_exec_rpa_key_id")
		batch.drop_column("rpa_key_id")

	# Drop new constraints from rpa_domain
	try:
		op.drop_constraint("uq_rpa_domain_rpa_key_id", "rpa_domain", type_="unique")
	except Exception:
		pass
	try:
		op.drop_constraint("pk_rpa_domain_rpa_id", "rpa_domain", type_="primary")
	except Exception:
		pass

	# Remove rpa_id and rpa_key_id columns
	with op.batch_alter_table("rpa_domain") as batch:
		batch.drop_column("rpa_key_id")
		batch.drop_column("rpa_id")

	# Rename rpa_domain back to rpa_definitions
	op.rename_table("rpa_domain", "rpa_definitions")

