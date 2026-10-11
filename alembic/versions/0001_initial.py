
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
        ),
        sa.Column(
            "total_recipients",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "successful_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "failed_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "error_message",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "certificate_data",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.create_table(
        "recipients",
        sa.Column(
            "id",
            sa.Uuid(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Uuid(),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "email",
            sa.String(length=320),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "certificate_path",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "error_message",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["jobs.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "job_id",
            "email",
            name="uq_recipient_job_email",
        ),
    )

    op.create_index(
        "ix_recipients_job_id",
        "recipients",
        ["job_id"],
    )

    op.create_index(
        "ix_recipients_job_status",
        "recipients",
        ["job_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_recipients_job_status",
        table_name="recipients",
    )
    op.drop_index(
        "ix_recipients_job_id",
        table_name="recipients",
    )
    op.drop_table("recipients")
    op.drop_table("jobs")

