"""Persist structured reports, retry state, and step audit trail."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260812_0001"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("reports", sa.Column("evidence_refs", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("reports", sa.Column("remediation_steps", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column("reports", sa.Column("root_cause_retried", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("reports", sa.Column("remediation_retried", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("reports", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.add_column("investigations", sa.Column("root_cause_retried", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("investigations", sa.Column("remediation_retried", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("investigations", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.create_table(
        "step_executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("investigation_id", sa.Uuid(), sa.ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_name", sa.String(50), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("output", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("error", sa.String(2000)),
    )
    op.create_index("uq_active_investigation_per_incident", "investigations", ["incident_id"], unique=True, postgresql_where=sa.text("status IN ('QUEUED', 'RUNNING')"))

def downgrade() -> None:
    op.drop_index("uq_active_investigation_per_incident", table_name="investigations")
    op.drop_table("step_executions")
    for table, column in (("investigations", "confidence_score"), ("investigations", "remediation_retried"), ("investigations", "root_cause_retried"), ("reports", "confidence_score"), ("reports", "remediation_retried"), ("reports", "root_cause_retried"), ("reports", "remediation_steps"), ("reports", "evidence_refs")):
        op.drop_column(table, column)
