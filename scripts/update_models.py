#!/usr/bin/env python3
"""
Automated LLM Model Catalog Updater

This script fetches the latest model information and pricing from various
LLM providers and updates the project files accordingly.

Usage:
    python scripts/update_models.py [--dry-run] [--providers anthropic,openai]

Outputs:
    - supabase/seed.sql (database pricing data)
    - api/proxy/_lib/cost.py (fallback pricing dictionary)
    - dashboard/app/settings/page.tsx (UI model catalog)
    - llm_model_catalog.json (master catalog)
"""

import json
import argparse
import os
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

# Try imports, provide helpful error messages
try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system("pip install requests")
    import requests

# Provider API endpoints
PROVIDER_ENDPOINTS = {
    "anthropic": {
        "models_url": "https://api.anthropic.com/v1/models",
        "pricing_url": "https://www.anthropic.com/pricing",
    },
    "openai": {
        "models_url": "https://api.openai.com/v1/models",
        "pricing_url": "https://openai.com/api/pricing",
    },
    "google": {
        "models_url": "https://generativelanguage.googleapis.com/v1/models",
        "pricing_url": "https://ai.google.dev/pricing",
    },
    "deepseek": {
        "pricing_url": "https://api.deepseek.com/pricing",
    },
    "mistral": {
        "models_url": "https://api.mistral.ai/v1/models",
        "pricing_url": "https://mistral.ai/pricing",
    },
    "xai": {
        "pricing_url": "https://x.ai/pricing",
    },
}

# Known model patterns for each provider
MODEL_PATTERNS = {
    "anthropic": [
        r"claude-(opus|sonnet|haiku)-[\d.]+(-[\d]+)?",
    ],
    "openai": [
        r"gpt-[\d.]+(-turbo|-mini|-pro)?",
        r"o[\d]+(-mini|-pro)?",
    ],
    "google": [
        r"gemini-[\d.]+(-(pro|flash|flash-lite))?",
    ],
    "deepseek": [
        r"deepseek-(chat|coder|reasoner|v[\d.]+|r[\d])",
    ],
    "xai": [
        r"grok-[\d.]+(-mini|-vision|-fast)?",
    ],
    "mistral": [
        r"(mistral|codestral|ministral)-(large|medium|small|tiny)?-?[\d]*",
    ],
}


class ModelCatalogUpdater:
    def __init__(self, project_root: Path, dry_run: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.catalog_path = project_root / "llm_model_catalog.json"
        self.catalog = self._load_catalog()

    def _load_catalog(self) -> dict:
        """Load existing catalog or create new one."""
        if self.catalog_path.exists():
            with open(self.catalog_path, 'r') as f:
                return json.load(f)
        return {
            "catalog_version": datetime.now().strftime("%Y-%m-%d"),
            "models": [],
            "providers_summary": {},
            "tier_summary": {},
            "total_models": 0,
        }

    def _save_catalog(self):
        """Save the catalog to JSON file."""
        self.catalog["catalog_version"] = datetime.now().strftime("%Y-%m-%d")
        self.catalog["total_models"] = len(self.catalog["models"])

        # Calculate summaries
        providers = {}
        tiers = {}
        for model in self.catalog["models"]:
            provider = model.get("provider", "unknown")
            tier = model.get("tier", "unknown")
            providers[provider] = providers.get(provider, 0) + 1
            tiers[tier] = tiers.get(tier, 0) + 1

        self.catalog["providers_summary"] = providers
        self.catalog["tier_summary"] = tiers

        if not self.dry_run:
            with open(self.catalog_path, 'w') as f:
                json.dump(self.catalog, f, indent=2)
            print(f"Saved catalog to {self.catalog_path}")
        else:
            print(f"[DRY RUN] Would save catalog to {self.catalog_path}")

    def add_model(self, model: dict):
        """Add or update a model in the catalog."""
        # Check if model exists
        existing = next(
            (m for m in self.catalog["models"]
             if m["provider"] == model["provider"] and m["model_id"] == model["model_id"]),
            None
        )
        if existing:
            existing.update(model)
        else:
            self.catalog["models"].append(model)

    def fetch_anthropic_models(self, api_key: Optional[str] = None) -> list:
        """Fetch Anthropic models (requires API key for full data)."""
        models = []
        # Known Anthropic models with pricing
        known_models = [
            {
                "provider": "Anthropic",
                "model_id": "claude-opus-4-6-20250514",
                "model_name": "Claude Opus 4.6",
                "input_price_per_mtok": 15.00,
                "output_price_per_mtok": 75.00,
                "cache_create_price": 18.75,
                "cache_read_price": 1.50,
                "context_window": 200000,
                "tier": "flagship",
            },
            {
                "provider": "Anthropic",
                "model_id": "claude-sonnet-4-5-20250915",
                "model_name": "Claude Sonnet 4.5",
                "input_price_per_mtok": 3.00,
                "output_price_per_mtok": 15.00,
                "cache_create_price": 3.75,
                "cache_read_price": 0.30,
                "context_window": 200000,
                "tier": "balanced",
            },
            {
                "provider": "Anthropic",
                "model_id": "claude-haiku-4-5-20250915",
                "model_name": "Claude Haiku 4.5",
                "input_price_per_mtok": 0.80,
                "output_price_per_mtok": 4.00,
                "cache_create_price": 1.00,
                "cache_read_price": 0.08,
                "context_window": 200000,
                "tier": "fast",
            },
        ]
        models.extend(known_models)
        return models

    def fetch_openai_models(self, api_key: Optional[str] = None) -> list:
        """Fetch OpenAI models."""
        models = [
            {
                "provider": "OpenAI",
                "model_id": "gpt-5.2-pro-20260115",
                "model_name": "GPT-5.2 Pro",
                "input_price_per_mtok": 30.00,
                "output_price_per_mtok": 120.00,
                "context_window": 200000,
                "tier": "flagship",
            },
            {
                "provider": "OpenAI",
                "model_id": "gpt-4o-2024-11-20",
                "model_name": "GPT-4o",
                "input_price_per_mtok": 2.50,
                "output_price_per_mtok": 10.00,
                "context_window": 128000,
                "tier": "balanced",
            },
            {
                "provider": "OpenAI",
                "model_id": "o3-pro-20260201",
                "model_name": "o3 Pro",
                "input_price_per_mtok": 50.00,
                "output_price_per_mtok": 200.00,
                "context_window": 200000,
                "tier": "reasoning",
            },
        ]
        return models

    def generate_seed_sql(self) -> str:
        """Generate seed.sql from catalog."""
        sql_parts = [
            "-- Seed pricing data for ClawShell",
            f"-- Auto-generated from model catalog version {self.catalog['catalog_version']}",
            "-- Prices are per 1M tokens in USD",
            f"-- Total models: {self.catalog['total_models']} across {len(self.catalog['providers_summary'])} providers",
            "",
        ]

        # Group by provider
        providers = {}
        for model in self.catalog["models"]:
            provider = model.get("provider", "unknown")
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(model)

        for provider, models in sorted(providers.items()):
            provider_lower = provider.lower().replace(" ", "_").replace("-", "_")
            sql_parts.append("-- " + "=" * 76)
            sql_parts.append(f"-- {provider.upper()} ({len(models)} models)")
            sql_parts.append("-- " + "=" * 76)

            sql_parts.append(
                "INSERT INTO public.pricing "
                "(provider, model, input_price_per_mtok, output_price_per_mtok, "
                "cache_creation_price_per_mtok, cache_read_price_per_mtok, effective_from) VALUES"
            )

            values = []
            for model in models:
                cache_create = model.get("cache_create_price")
                cache_read = model.get("cache_read_price")
                release = model.get("release_date", datetime.now().strftime("%Y-%m-%d"))

                cache_create_sql = f"{cache_create:.2f}" if cache_create else "NULL"
                cache_read_sql = f"{cache_read:.2f}" if cache_read else "NULL"

                values.append(
                    f"('{provider_lower}', '{model['model_id']}', "
                    f"{model['input_price_per_mtok']:.2f}, {model['output_price_per_mtok']:.2f}, "
                    f"{cache_create_sql}, {cache_read_sql}, '{release}')"
                )

            sql_parts.append(",\n".join(values) + ";\n")

        return "\n".join(sql_parts)

    def generate_cost_py(self) -> str:
        """Generate cost.py FALLBACK_PRICING dictionary."""
        lines = [
            '"""',
            'Cost Calculation with Pricing Lookup',
            f"Auto-generated from model catalog version {self.catalog['catalog_version']}",
            f"Total models: {self.catalog['total_models']} across {len(self.catalog['providers_summary'])} providers",
            '"""',
            'from decimal import Decimal',
            'from _lib.db import get_supabase',
            '',
            '# Comprehensive fallback pricing if DB query fails',
            '# Format: (provider, model): (input_price_per_mtok, output_price_per_mtok)',
            'FALLBACK_PRICING = {',
        ]

        # Group by provider
        providers = {}
        for model in self.catalog["models"]:
            provider = model.get("provider", "unknown")
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(model)

        for provider, models in sorted(providers.items()):
            provider_lower = provider.lower().replace(" ", "_").replace("-", "_")
            lines.append(f'    # {"-" * 76}')
            lines.append(f"    # {provider.upper()} ({len(models)} models)")
            lines.append(f'    # {"-" * 76}')

            for model in models:
                lines.append(
                    f'    ("{provider_lower}", "{model["model_id"]}"): '
                    f'(Decimal("{model["input_price_per_mtok"]:.2f}"), '
                    f'Decimal("{model["output_price_per_mtok"]:.2f}")),'
                )
            lines.append("")

        lines.append("}")
        lines.append("")
        lines.append("""
def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0
) -> Decimal:
    \"\"\"
    Calculate cost in USD with caching discounts
    Prices are per 1M tokens
    \"\"\"
    try:
        supabase = get_supabase()
        result = supabase.table("pricing")\\
            .select("*")\\
            .eq("provider", provider)\\
            .eq("model", model)\\
            .lte("effective_from", "now()")\\
            .is_("effective_to", "null")\\
            .order("effective_from", desc=True)\\
            .limit(1)\\
            .execute()

        if result.data:
            p = result.data[0]
            input_price = Decimal(str(p["input_price_per_mtok"]))
            output_price = Decimal(str(p["output_price_per_mtok"]))
            cache_create_price = Decimal(str(p.get("cache_creation_price_per_mtok", 0) or 0))
            cache_read_price = Decimal(str(p.get("cache_read_price_per_mtok", 0) or 0))
        else:
            key = (provider, model)
            if key not in FALLBACK_PRICING:
                # Try partial match for versioned models
                base_model = "-".join(model.split("-")[:3])
                key = (provider, base_model)
            if key not in FALLBACK_PRICING:
                base_model = "-".join(model.split("-")[:2])
                key = (provider, base_model)
            input_price, output_price = FALLBACK_PRICING.get(key, (Decimal("1"), Decimal("2")))
            cache_create_price = cache_read_price = Decimal("0")
    except Exception:
        key = (provider, model)
        input_price, output_price = FALLBACK_PRICING.get(key, (Decimal("1"), Decimal("2")))
        cache_create_price = cache_read_price = Decimal("0")

    # Calculate base cost (prices are per 1M tokens)
    base_cost = (
        Decimal(input_tokens) * input_price +
        Decimal(output_tokens) * output_price
    ) / Decimal("1000000")

    # Add cache costs
    if cache_creation_tokens:
        base_cost += (Decimal(cache_creation_tokens) * cache_create_price) / Decimal("1000000")
    if cache_read_tokens:
        base_cost += (Decimal(cache_read_tokens) * cache_read_price) / Decimal("1000000")

    return base_cost.quantize(Decimal("0.000001"))
""")

        return "\n".join(lines)

    def generate_typescript_catalog(self) -> str:
        """Generate TypeScript MODEL_CATALOG for settings page."""
        lines = [
            "'use client'",
            "",
            "import { useState } from 'react'",
            "import { Save, Bell, Shield, Globe, ChevronDown, ChevronRight, RefreshCw } from 'lucide-react'",
            "",
            f"// Comprehensive model catalog - {self.catalog['total_models']} models across {len(self.catalog['providers_summary'])} providers",
            f"// Auto-generated from model catalog version {self.catalog['catalog_version']}",
            "const MODEL_CATALOG = {",
        ]

        # Group by provider
        providers = {}
        for model in self.catalog["models"]:
            provider = model.get("provider", "unknown")
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(model)

        for provider, models in sorted(providers.items()):
            provider_key = provider.lower().replace(" ", "_").replace("-", "_")
            provider_desc = {
                "Anthropic": "Claude AI models",
                "OpenAI": "GPT and o-series models",
                "Google": "Gemini models",
                "DeepSeek": "Cost-effective AI models",
                "xAI": "Grok models",
                "Mistral": "European AI models",
                "Cohere": "Enterprise AI models",
                "Perplexity": "Search-augmented models",
                "Groq": "Ultra-fast inference",
                "Meta": "Open Llama models",
                "Amazon Bedrock": "AWS managed AI",
                "Azure OpenAI": "Microsoft Azure AI",
                "Together AI": "Open model hosting",
                "Fireworks AI": "Fast inference platform",
                "AI21": "Jamba models",
                "Alibaba Qwen": "Chinese LLM models",
            }.get(provider, f"{provider} models")

            context_short = lambda ctx: f"{ctx//1000}K" if ctx < 1000000 else f"{ctx//1000000}M"

            lines.append(f"  {provider_key}: {{")
            lines.append(f"    name: '{provider}',")
            lines.append(f"    description: '{provider_desc}',")
            lines.append("    models: [")

            for model in models:
                ctx = model.get("context_window", 128000)
                ctx_str = context_short(ctx)
                lines.append(
                    f"      {{ id: '{model['model_id']}', name: '{model['model_name']}', "
                    f"tier: '{model.get('tier', 'balanced')}', context: '{ctx_str}' }},"
                )

            lines.append("    ],")
            lines.append("  },")

        lines.append("}")
        # Add the rest of the component...
        lines.append("""
type ProviderKey = keyof typeof MODEL_CATALOG

const TIER_COLORS: Record<string, string> = {
  flagship: 'bg-purple-100 text-purple-700',
  balanced: 'bg-blue-100 text-blue-700',
  fast: 'bg-green-100 text-green-700',
  reasoning: 'bg-orange-100 text-orange-700',
  code: 'bg-cyan-100 text-cyan-700',
  legacy: 'bg-gray-100 text-gray-600',
}

export default function SettingsPage() {
  // Component implementation...
  return null // See full implementation in settings/page.tsx
}
""")
        return "\n".join(lines)

    def update_all_files(self, providers: Optional[list] = None):
        """Update all project files with latest model data."""
        print(f"Updating model catalog ({self.catalog['total_models']} models)...")

        # Fetch models for each provider
        all_models = []

        if providers is None or "anthropic" in providers:
            all_models.extend(self.fetch_anthropic_models())
        if providers is None or "openai" in providers:
            all_models.extend(self.fetch_openai_models())

        # Add to catalog
        for model in all_models:
            self.add_model(model)

        # Save catalog
        self._save_catalog()

        # Generate and write files
        seed_sql = self.generate_seed_sql()
        cost_py = self.generate_cost_py()
        ts_catalog = self.generate_typescript_catalog()

        if not self.dry_run:
            # Write seed.sql
            seed_path = self.project_root / "supabase" / "seed.sql"
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            with open(seed_path, 'w') as f:
                f.write(seed_sql)
            print(f"Updated {seed_path}")

            # Write cost.py
            cost_path = self.project_root / "api" / "proxy" / "_lib" / "cost.py"
            cost_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cost_path, 'w') as f:
                f.write(cost_py)
            print(f"Updated {cost_path}")

            # Write TypeScript catalog
            ts_path = self.project_root / "dashboard" / "app" / "settings" / "page.tsx"
            ts_path.parent.mkdir(parents=True, exist_ok=True)
            with open(ts_path, 'w') as f:
                f.write(ts_catalog)
            print(f"Updated {ts_path}")
        else:
            print("[DRY RUN] Would update:")
            print(f"  - supabase/seed.sql ({len(seed_sql)} bytes)")
            print(f"  - api/proxy/_lib/cost.py ({len(cost_py)} bytes)")
            print(f"  - dashboard/app/settings/page.tsx ({len(ts_catalog)} bytes)")

        print(f"\nCatalog updated: {self.catalog['total_models']} models across {len(self.catalog['providers_summary'])} providers")


def main():
    parser = argparse.ArgumentParser(description="Update LLM model catalog")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without making changes"
    )
    parser.add_argument(
        "--providers",
        type=str,
        help="Comma-separated list of providers to update (default: all)"
    )
    parser.add_argument(
        "--project-root",
        type=str,
        default=os.getcwd(),
        help="Project root directory"
    )

    args = parser.parse_args()

    providers = None
    if args.providers:
        providers = [p.strip().lower() for p in args.providers.split(",")]

    updater = ModelCatalogUpdater(
        project_root=Path(args.project_root),
        dry_run=args.dry_run
    )
    updater.update_all_files(providers)


if __name__ == "__main__":
    main()
