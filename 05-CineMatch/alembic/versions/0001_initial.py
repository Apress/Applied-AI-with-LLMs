"""initial

Revision ID: 0001_initial
Revises: None
Create Date: 2026-03-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


vote_enum = sa.Enum("like", "dislike", "never_seen", name="vote_enum")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("country", sa.String(length=5), nullable=False, server_default="IT"),
        sa.Column("language", sa.String(length=5), nullable=False, server_default="it"),
        sa.Column("owned_services_json", sa.JSON(), nullable=True),
        sa.Column("mood_text", sa.Text(), nullable=True),
        sa.Column("taste_profile_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "votes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("vote_enum", vote_enum, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_votes_user_id", "votes", ["user_id"])
    op.create_index("ix_votes_tmdb_id", "votes", ["tmdb_id"])
    op.create_index("ix_votes_vote_enum", "votes", ["vote_enum"])

    op.create_table(
        "suggestions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("tmdb_id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_suggestions_user_id", "suggestions", ["user_id"])
    op.create_index("ix_suggestions_tmdb_id", "suggestions", ["tmdb_id"])
    op.create_index("ix_suggestions_batch_id", "suggestions", ["batch_id"])

    op.create_table(
        "cache",
        sa.Column("key", sa.Text(), primary_key=True),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(), nullable=False),
    )
    op.create_index("ix_cache_expires_at", "cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_cache_expires_at", table_name="cache")
    op.drop_table("cache")

    op.drop_index("ix_suggestions_batch_id", table_name="suggestions")
    op.drop_index("ix_suggestions_tmdb_id", table_name="suggestions")
    op.drop_index("ix_suggestions_user_id", table_name="suggestions")
    op.drop_table("suggestions")

    op.drop_index("ix_votes_vote_enum", table_name="votes")
    op.drop_index("ix_votes_tmdb_id", table_name="votes")
    op.drop_index("ix_votes_user_id", table_name="votes")
    op.drop_table("votes")
    vote_enum.drop(op.get_bind(), checkfirst=True)

    op.drop_table("users")
