"""
Tests for Pricing model.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import select

from app.models.pricing import Pricing


class TestPricingModel:
    """Tests for Pricing model."""

    def test_pricing_creation(self):
        """Test creating a pricing record."""
        pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            cache_creation_price_per_mtok=Decimal("3.75"),
            cache_read_price_per_mtok=Decimal("0.30"),
            effective_from=date.today(),
        )

        assert pricing.provider == "anthropic"
        assert pricing.model == "claude-sonnet-4-20250514"
        assert pricing.input_price_per_mtok == Decimal("3.00")
        assert pricing.output_price_per_mtok == Decimal("15.00")

    def test_pricing_default_cache_prices(self):
        """Test that cache prices default to 0."""
        pricing = Pricing(
            provider="openai",
            model="gpt-4o",
            input_price_per_mtok=Decimal("2.50"),
            output_price_per_mtok=Decimal("10.00"),
            effective_from=date.today(),
        )

        assert pricing.cache_creation_price_per_mtok == Decimal("0")
        assert pricing.cache_read_price_per_mtok == Decimal("0")


class TestCalculateCost:
    """Tests for cost calculation."""

    def test_calculate_cost_basic(self):
        """Test basic cost calculation without caching."""
        pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            cache_creation_price_per_mtok=Decimal("3.75"),
            cache_read_price_per_mtok=Decimal("0.30"),
            effective_from=date.today(),
        )

        # 1000 input tokens, 500 output tokens
        cost = pricing.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
        )

        # Expected: (1000/1M * 3) + (500/1M * 15) = 0.003 + 0.0075 = 0.0105
        expected = Decimal("0.0105")
        assert cost == expected

    def test_calculate_cost_with_caching(self):
        """Test cost calculation with prompt caching."""
        pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            cache_creation_price_per_mtok=Decimal("3.75"),
            cache_read_price_per_mtok=Decimal("0.30"),
            effective_from=date.today(),
        )

        # With caching tokens
        cost = pricing.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
            cache_creation_tokens=500,
            cache_read_tokens=200,
        )

        # Expected:
        # Input: (1000/1M * 3) = 0.003
        # Output: (500/1M * 15) = 0.0075
        # Cache creation: (500/1M * 3.75) = 0.001875
        # Cache read: (200/1M * 0.30) = 0.00006
        # Total: 0.012435
        expected = Decimal("0.012435")
        assert cost == expected

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            cache_creation_price_per_mtok=Decimal("3.75"),
            cache_read_price_per_mtok=Decimal("0.30"),
            effective_from=date.today(),
        )

        cost = pricing.calculate_cost(
            input_tokens=0,
            output_tokens=0,
        )

        assert cost == Decimal("0")

    def test_calculate_cost_large_values(self):
        """Test cost calculation with large token values."""
        pricing = Pricing(
            provider="anthropic",
            model="claude-opus-4-6-20250514",
            input_price_per_mtok=Decimal("15.00"),
            output_price_per_mtok=Decimal("75.00"),
            cache_creation_price_per_mtok=Decimal("18.75"),
            cache_read_price_per_mtok=Decimal("1.50"),
            effective_from=date.today(),
        )

        # 1M input tokens, 500K output tokens
        cost = pricing.calculate_cost(
            input_tokens=1_000_000,
            output_tokens=500_000,
        )

        # Expected: (1M/1M * 15) + (500K/1M * 75) = 15 + 37.5 = 52.5
        expected = Decimal("52.50")
        assert cost == expected


class TestFindPricing:
    """Tests for pricing lookup."""

    def test_find_pricing_exact_match(self):
        """Test finding pricing with exact provider/model match."""
        # Mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            cache_creation_price_per_mtok=Decimal("3.75"),
            cache_read_price_per_mtok=Decimal("0.30"),
            effective_from=date.today() - timedelta(days=30),
        )
        mock_result.scalar_one_or_none.return_value = mock_pricing
        mock_session.execute.return_value = mock_result

        result = Pricing.find_pricing(
            mock_session,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
        )

        assert result is not None
        assert result.provider == "anthropic"
        assert result.model == "claude-sonnet-4-20250514"

    def test_find_pricing_not_found(self):
        """Test finding pricing when not found."""
        # Mock session
        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = Pricing.find_pricing(
            mock_session,
            provider="unknown",
            model="unknown-model",
        )

        assert result is None

    def test_find_pricing_with_date(self):
        """Test finding pricing for specific date."""
        mock_session = MagicMock()
        mock_result = MagicMock()

        # Create pricing effective from 60 days ago
        mock_pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            cache_creation_price_per_mtok=Decimal("3.75"),
            cache_read_price_per_mtok=Decimal("0.30"),
            effective_from=date.today() - timedelta(days=60),
        )
        mock_result.scalar_one_or_none.return_value = mock_pricing
        mock_session.execute.return_value = mock_result

        # Query for date 30 days ago
        result = Pricing.find_pricing(
            mock_session,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            effective_date=date.today() - timedelta(days=30),
        )

        assert result is not None


class TestPricingConstraints:
    """Tests for pricing model constraints."""

    def test_unique_constraint_provider_model_date(self):
        """Test that provider/model/effective_from must be unique."""
        # This would be tested at the database level
        # Here we just verify the constraint is defined
        pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            effective_from=date.today(),
        )

        assert hasattr(Pricing.__table_args__, "__iter__")
        # Find the UniqueConstraint
        from sqlalchemy import UniqueConstraint

        constraints = [arg for arg in Pricing.__table_args__ if isinstance(arg, UniqueConstraint)]
        assert len(constraints) > 0

    def test_effective_to_nullable(self):
        """Test that effective_to is nullable."""
        pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            effective_from=date.today(),
        )

        assert pricing.effective_to is None

    def test_effective_to_set(self):
        """Test setting effective_to."""
        pricing = Pricing(
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            input_price_per_mtok=Decimal("3.00"),
            output_price_per_mtok=Decimal("15.00"),
            effective_from=date.today(),
            effective_to=date.today() + timedelta(days=30),
        )

        assert pricing.effective_to is not None


class TestPricingModelCatalog:
    """Tests for model catalog pricing data."""

    def test_anthropic_claude_opus_pricing(self):
        """Test Claude Opus 4.6 pricing is correct."""
        pricing = Pricing(
            provider="anthropic",
            model="claude-opus-4-6-20250514",
            input_price_per_mtok=Decimal("15.00"),
            output_price_per_mtok=Decimal("75.00"),
            cache_creation_price_per_mtok=Decimal("18.75"),
            cache_read_price_per_mtok=Decimal("1.50"),
            effective_from=date(2025, 5, 14),
        )

        # 100K input + 50K output
        cost = pricing.calculate_cost(100_000, 50_000)

        # Expected: (100K/1M * 15) + (50K/1M * 75) = 1.5 + 3.75 = 5.25
        expected = Decimal("5.25")
        assert cost == expected

    def test_openai_gpt4o_pricing(self):
        """Test GPT-4o pricing is correct."""
        pricing = Pricing(
            provider="openai",
            model="gpt-4o-2024-11-20",
            input_price_per_mtok=Decimal("2.50"),
            output_price_per_mtok=Decimal("10.00"),
            effective_from=date(2024, 11, 20),
        )

        # 200K input + 100K output
        cost = pricing.calculate_cost(200_000, 100_000)

        # Expected: (200K/1M * 2.5) + (100K/1M * 10) = 0.5 + 1.0 = 1.5
        expected = Decimal("1.50")
        assert cost == expected

    def test_deepseek_pricing(self):
        """Test DeepSeek V3 pricing is correct."""
        pricing = Pricing(
            provider="deepseek",
            model="deepseek-v3.2-20260201",
            input_price_per_mtok=Decimal("0.27"),
            output_price_per_mtok=Decimal("1.10"),
            effective_from=date(2026, 2, 1),
        )

        # 1M input + 500K output
        cost = pricing.calculate_cost(1_000_000, 500_000)

        # Expected: (1M/1M * 0.27) + (500K/1M * 1.10) = 0.27 + 0.55 = 0.82
        expected = Decimal("0.82")
        assert cost == expected
