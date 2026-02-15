"""Pricing model for LLM model costs."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Pricing(BaseModel):
    """
    Pricing data for LLM models.

    Stores versioned pricing information for all supported models.
    Prices are per 1 million tokens in USD.
    """

    __tablename__ = "pricing"
    __table_args__ = (
        UniqueConstraint("provider", "model", "effective_from", name="uq_pricing_provider_model_date"),
        Index("ix_pricing_lookup", "provider", "model", "effective_from"),
    )

    provider: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    model: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Prices per 1M tokens
    input_price_per_mtok: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    output_price_per_mtok: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    cache_creation_price_per_mtok: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0")
    )
    cache_read_price_per_mtok: Mapped[Decimal] = mapped_column(
        Numeric(10, 6), nullable=False, default=Decimal("0")
    )

    # Validity period
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
    ) -> Decimal:
        """
        Calculate total cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cache_creation_tokens: Number of cache creation tokens (Anthropic)
            cache_read_tokens: Number of cache read tokens (Anthropic)

        Returns:
            Total cost in USD
        """
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * self.input_price_per_mtok
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * self.output_price_per_mtok
        cache_creation_cost = (
            Decimal(cache_creation_tokens) / Decimal(1_000_000)
        ) * self.cache_creation_price_per_mtok
        cache_read_cost = (
            Decimal(cache_read_tokens) / Decimal(1_000_000)
        ) * self.cache_read_price_per_mtok

        return input_cost + output_cost + cache_creation_cost + cache_read_cost

    @classmethod
    def find_pricing(
        cls,
        session,
        provider: str,
        model: str,
        effective_date: date | None = None,
    ) -> "Pricing | None":
        """
        Find the applicable pricing for a provider/model combination.

        Args:
            session: Database session
            provider: Provider name (e.g., 'anthropic', 'openai')
            model: Model name (e.g., 'claude-sonnet-4-20250514')
            effective_date: Date to check pricing for (defaults to today)

        Returns:
            Pricing record or None if not found
        """
        from sqlalchemy import select

        if effective_date is None:
            effective_date = date.today()

        stmt = (
            select(cls)
            .where(cls.provider == provider)
            .where(cls.model == model)
            .where(cls.effective_from <= effective_date)
            .where((cls.effective_to.is_(None)) | (cls.effective_to >= effective_date))
            .order_by(cls.effective_from.desc())
            .limit(1)
        )

        result = session.execute(stmt)
        return result.scalar_one_or_none()
