"""Initial schema — create all APIx tables.

Revision ID: 0001_initial
Revises: 
Create Date: 2026-09-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── routes ─────────────────────────────────────────────────────────────
    op.create_table(
        "routes",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("origin", sa.String(3), nullable=False),
        sa.Column("destination", sa.String(3), nullable=False),
        sa.Column("route_code", sa.String(10), unique=True, nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_routes_route_code", "routes", ["route_code"])
    op.create_index("ix_routes_origin", "routes", ["origin"])
    op.create_index("ix_routes_destination", "routes", ["destination"])

    # ── airlines ──────────────────────────────────────────────────────────
    op.create_table(
        "airlines",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("code", sa.String(10), unique=True, nullable=False),
        sa.Column("active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_airlines_code", "airlines", ["code"])

    # ── sources ───────────────────────────────────────────────────────────
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("active", sa.Boolean(), default=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── fare_observations ─────────────────────────────────────────────────
    op.create_table(
        "fare_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("airline_id", sa.Integer(), sa.ForeignKey("airlines.id"), nullable=False),
        sa.Column("route_id", sa.Integer(), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("search_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("travel_date", sa.Date(), nullable=False),
        sa.Column("lead_days", sa.Integer(), nullable=False),
        sa.Column("fare_class", sa.String(20), nullable=False, server_default="economy"),
        sa.Column("passenger_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("base_fare", sa.Float(), nullable=True),
        sa.Column("taxes", sa.Float(), nullable=True),
        sa.Column("airport_charges", sa.Float(), nullable=True),
        sa.Column("convenience_fee", sa.Float(), nullable=True),
        sa.Column("total_fare", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("availability", sa.String(30), nullable=False, server_default="available"),
        sa.Column("raw_payload", postgresql.JSON(), nullable=True),
        sa.Column("quality_status", sa.String(20), nullable=False, server_default="valid"),
        sa.Column("outlier_flag", sa.Boolean(), default=False, nullable=False),
        sa.Column("outlier_reason", sa.Text(), nullable=True),
        sa.Column("duplicate_group_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_fare_obs_source_id", "fare_observations", ["source_id"])
    op.create_index("ix_fare_obs_airline_id", "fare_observations", ["airline_id"])
    op.create_index("ix_fare_obs_route_id", "fare_observations", ["route_id"])
    op.create_index("ix_fare_obs_travel_date", "fare_observations", ["travel_date"])
    op.create_index("ix_fare_obs_lead_days", "fare_observations", ["lead_days"])
    op.create_index("ix_fare_obs_quality_status", "fare_observations", ["quality_status"])
    op.create_index("ix_fare_obs_outlier_flag", "fare_observations", ["outlier_flag"])

    # ── route_daily_prices ────────────────────────────────────────────────
    op.create_table(
        "route_daily_prices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("route_id", sa.Integer(), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("lead_days", sa.Integer(), nullable=False),
        sa.Column("representative_price", sa.Float(), nullable=True),
        sa.Column("observation_count", sa.Integer(), default=0),
        sa.Column("valid_observation_count", sa.Integer(), default=0),
        sa.Column("missing_count", sa.Integer(), default=0),
        sa.Column("outlier_count", sa.Integer(), default=0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("date", "route_id", "lead_days", name="uq_route_daily_price"),
    )
    op.create_index("ix_rdp_date", "route_daily_prices", ["date"])
    op.create_index("ix_rdp_route_id", "route_daily_prices", ["route_id"])

    # ── route_indices ─────────────────────────────────────────────────────
    op.create_table(
        "route_indices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("route_id", sa.Integer(), sa.ForeignKey("routes.id"), nullable=False),
        sa.Column("base_price", sa.Float(), nullable=False),
        sa.Column("current_price", sa.Float(), nullable=True),
        sa.Column("route_index", sa.Float(), nullable=True),
        sa.Column("route_weight", sa.Float(), nullable=False),
        sa.Column("contribution", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("date", "route_id", name="uq_route_index"),
    )
    op.create_index("ix_ri_date", "route_indices", ["date"])
    op.create_index("ix_ri_route_id", "route_indices", ["route_id"])

    # ── airfare_indices ───────────────────────────────────────────────────
    op.create_table(
        "airfare_indices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date(), nullable=False, unique=True),
        sa.Column("index_value", sa.Float(), nullable=True),
        sa.Column("daily_change_pct", sa.Float(), nullable=True),
        sa.Column("weekly_change_pct", sa.Float(), nullable=True),
        sa.Column("monthly_change_pct", sa.Float(), nullable=True),
        sa.Column("observation_count", sa.Integer(), default=0),
        sa.Column("coverage_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ai_date", "airfare_indices", ["date"])


def downgrade() -> None:
    op.drop_table("airfare_indices")
    op.drop_table("route_indices")
    op.drop_table("route_daily_prices")
    op.drop_table("fare_observations")
    op.drop_table("sources")
    op.drop_table("airlines")
    op.drop_table("routes")
