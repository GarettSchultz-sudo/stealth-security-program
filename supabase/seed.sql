-- Seed pricing data for AgentCostControl
-- Auto-generated from model catalog version 2026-02-13
-- Prices are per 1M tokens in USD
-- Total models: 91 across 16 providers

-- ============================================================================
-- ANTHROPIC - Claude Models (10 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, cache_creation_price_per_mtok, cache_read_price_per_mtok, effective_from) VALUES
-- Claude 4.x Series (Latest)
('anthropic', 'claude-opus-4-6-20250514', 15.00, 75.00, 18.75, 1.50, '2025-05-14'),
('anthropic', 'claude-opus-4-20250514', 15.00, 75.00, 18.75, 1.50, '2025-05-14'),
('anthropic', 'claude-sonnet-4-5-20250915', 3.00, 15.00, 3.75, 0.30, '2025-09-15'),
('anthropic', 'claude-sonnet-4-20250514', 3.00, 15.00, 3.75, 0.30, '2025-05-14'),
('anthropic', 'claude-haiku-4-5-20250915', 0.80, 4.00, 1.00, 0.08, '2025-09-15'),
-- Claude 3.5 (Legacy)
('anthropic', 'claude-3-5-sonnet-20241022', 3.00, 15.00, 3.75, 0.30, '2024-10-22'),
('anthropic', 'claude-3-5-haiku-20241022', 0.80, 4.00, 1.00, 0.08, '2024-10-22'),
-- Claude 3 (Legacy)
('anthropic', 'claude-3-opus-20240229', 15.00, 75.00, 18.75, 1.50, '2024-02-29'),
('anthropic', 'claude-3-sonnet-20240229', 3.00, 15.00, 3.75, 0.30, '2024-02-29'),
('anthropic', 'claude-3-haiku-20240307', 0.25, 1.25, 0.30, 0.03, '2024-03-07');

-- ============================================================================
-- OPENAI - GPT & o-series (11 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, cache_creation_price_per_mtok, cache_read_price_per_mtok, effective_from) VALUES
-- GPT-5 Series (Latest)
('openai', 'gpt-5.2-pro-20260115', 30.00, 120.00, NULL, NULL, '2026-01-15'),
('openai', 'gpt-5-pro-20251001', 20.00, 80.00, NULL, NULL, '2025-10-01'),
('openai', 'gpt-5.1-20250915', 10.00, 40.00, NULL, NULL, '2025-09-15'),
-- GPT-4o Series
('openai', 'gpt-4o-2024-11-20', 2.50, 10.00, NULL, NULL, '2024-11-20'),
('openai', 'gpt-4o-mini-2024-07-18', 0.15, 0.60, NULL, NULL, '2024-07-18'),
-- o-series (Reasoning)
('openai', 'o3-pro-20260201', 50.00, 200.00, NULL, NULL, '2026-02-01'),
('openai', 'o3-20260115', 20.00, 80.00, NULL, NULL, '2026-01-15'),
('openai', 'o3-mini-20251215', 5.00, 20.00, NULL, NULL, '2025-12-15'),
('openai', 'o1-2024-12-17', 15.00, 60.00, NULL, NULL, '2024-12-17'),
('openai', 'o1-mini-2024-09-12', 3.00, 12.00, NULL, NULL, '2024-09-12'),
-- Legacy
('openai', 'gpt-4-turbo', 10.00, 30.00, NULL, NULL, '2024-01-01');

-- ============================================================================
-- GOOGLE - Gemini Models (6 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, cache_creation_price_per_mtok, cache_read_price_per_mtok, effective_from) VALUES
-- Gemini 3 (Latest)
('google', 'gemini-3-pro-preview-20260201', 7.00, 21.00, 1.75, 0.49, '2026-02-01'),
-- Gemini 2.5
('google', 'gemini-2.5-pro-preview-20260115', 5.00, 15.00, 1.25, 0.35, '2026-01-15'),
('google', 'gemini-2.5-flash-preview-20260115', 0.30, 1.20, 0.075, 0.021, '2026-01-15'),
-- Gemini 2.0
('google', 'gemini-2.0-flash-001', 0.10, 0.40, 0.025, 0.007, '2025-02-01'),
('google', 'gemini-2-flash-lite-preview-20250915', 0.075, 0.30, 0.01875, 0.00525, '2025-09-15'),
-- Legacy
('google', 'gemini-1.5-pro', 1.25, 5.00, 2.50, 0.31, '2024-05-01');

-- ============================================================================
-- DEEPSEEK - DeepSeek Models (7 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, cache_creation_price_per_mtok, cache_read_price_per_mtok, effective_from) VALUES
-- DeepSeek V3 (Latest)
('deepseek', 'deepseek-v3.2-20260201', 0.27, 1.10, NULL, NULL, '2026-02-01'),
('deepseek', 'deepseek-v3.1-20260115', 0.27, 1.10, NULL, NULL, '2026-01-15'),
-- DeepSeek R1 (Reasoning)
('deepseek', 'deepseek-r1-20250120', 0.55, 2.19, NULL, NULL, '2025-01-20'),
('deepseek', 'deepseek-reasoner', 0.55, 2.19, NULL, NULL, '2025-01-20'),
-- DeepSeek Chat
('deepseek', 'deepseek-chat', 0.14, 0.28, NULL, NULL, '2024-05-01'),
-- DeepSeek Coder
('deepseek', 'deepseek-coder-v2-240614', 0.14, 0.28, NULL, NULL, '2024-06-14'),
('deepseek', 'deepseek-coder', 0.14, 0.28, NULL, NULL, '2024-06-14');

-- ============================================================================
-- XAI - Grok Models (7 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- Grok 4 (Latest)
('xai', 'grok-4-20260115', 10.00, 30.00, '2026-01-15'),
('xai', 'grok-4.1-20260201', 12.00, 36.00, '2026-02-01'),
('xai', 'grok-4.1-fast-20260201', 5.00, 15.00, '2026-02-01'),
-- Grok 3
('xai', 'grok-3-20251001', 5.00, 15.00, '2025-10-01'),
('xai', 'grok-3-mini-20251115', 0.30, 0.90, '2025-11-15'),
-- Grok 2 (Legacy)
('xai', 'grok-2-1212', 2.00, 10.00, '2024-12-12'),
-- Grok Vision
('xai', 'grok-2-image-20250815', 8.00, 24.00, '2025-08-15');

-- ============================================================================
-- MISTRAL - Mistral AI Models (8 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- Mistral Large (Latest)
('mistral', 'mistral-large-3-20260115', 6.00, 18.00, '2026-01-15'),
('mistral', 'mistral-large-2-2407', 3.00, 9.00, '2024-07-24'),
-- Mistral Medium
('mistral', 'mistral-medium-2505', 1.50, 4.50, '2025-05-01'),
-- Mistral Small
('mistral', 'mistral-small-2501', 0.30, 0.90, '2025-01-01'),
-- Codestral (Code)
('mistral', 'codestral-2501', 0.30, 0.90, '2025-01-01'),
-- Ministral (Edge)
('mistral', 'ministral-8b-2410', 0.10, 0.10, '2024-10-01'),
('mistral', 'ministral-3b-2410', 0.04, 0.04, '2024-10-01'),
-- Open Models
('mistral', 'open-mixtral-8x7b', 0.025, 0.025, '2024-01-01');

-- ============================================================================
-- COHERE - Command Models (4 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- Command A (Latest)
('cohere', 'command-a-20260115', 2.50, 10.00, '2026-01-15'),
-- Command R Series
('cohere', 'command-r-plus-08-2024', 2.50, 10.00, '2024-08-01'),
('cohere', 'command-r-08-2024', 0.15, 0.60, '2024-08-01'),
-- Command Vision
('cohere', 'command-vision-20250115', 3.00, 12.00, '2025-01-15');

-- ============================================================================
-- PERPLEXITY - Sonar Models (3 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- Sonar (Latest)
('perplexity', 'sonar-20260115', 1.00, 1.00, '2026-01-15'),
('perplexity', 'sonar-pro-20260115', 3.00, 15.00, '2026-01-15'),
-- Deep Research
('perplexity', 'sonar-deep-research-20260201', 5.00, 25.00, '2026-02-01');

-- ============================================================================
-- GROQ - Fast Inference (4 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- Llama on Groq
('groq', 'llama-3.3-70b-versatile', 0.59, 0.79, '2024-12-06'),
('groq', 'llama-3.1-8b-instant', 0.05, 0.08, '2024-07-23'),
-- Mixtral on Groq
('groq', 'mixtral-8x7b-32768', 0.24, 0.24, '2024-01-01'),
-- DeepSeek on Groq
('groq', 'deepseek-r1-distill-llama-70b', 0.59, 0.79, '2025-01-20');

-- ============================================================================
-- META - Llama Models (6 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- Llama 4 (Latest)
('meta', 'llama-4-maverick-20260201', 0.20, 0.60, '2026-02-01'),
('meta', 'llama-4-scout-20260201', 0.10, 0.30, '2026-02-01'),
('meta', 'llama-4-behemoth-20260201', 0.50, 1.50, '2026-02-01'),
-- Llama 3.3
('meta', 'llama-3.3-70b-instruct', 0.60, 0.60, '2024-12-06'),
-- Llama 3.1
('meta', 'llama-3.1-405b-instruct', 3.00, 3.00, '2024-07-23'),
-- Legacy
('meta', 'llama-3.1-8b-instruct', 0.05, 0.05, '2024-07-23');

-- ============================================================================
-- AMAZON BEDROCK (5 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, cache_creation_price_per_mtok, cache_read_price_per_mtok, effective_from) VALUES
-- Claude on Bedrock
('bedrock', 'anthropic.claude-opus-4-6-v1', 15.00, 75.00, 18.75, 1.50, '2025-05-14'),
('bedrock', 'anthropic.claude-sonnet-4-5-v1', 3.00, 15.00, 3.75, 0.30, '2025-09-15'),
-- Llama on Bedrock
('bedrock', 'us.meta.llama4-maverick-v1', 0.22, 0.66, NULL, NULL, '2026-02-01'),
-- Amazon Nova
('bedrock', 'amazon.nova-2-pro-v1', 0.80, 3.20, NULL, NULL, '2026-01-15'),
-- DeepSeek on Bedrock
('bedrock', 'deepseek.r1-v1', 0.60, 2.40, NULL, NULL, '2025-01-20');

-- ============================================================================
-- AZURE OPENAI (4 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- GPT-5 on Azure
('azure', 'gpt-5.2-pro', 30.00, 120.00, '2026-01-15'),
('azure', 'gpt-5-pro', 20.00, 80.00, '2025-10-01'),
-- o-series on Azure
('azure', 'o3-pro', 50.00, 200.00, '2026-02-01'),
('azure', 'o3', 20.00, 80.00, '2026-01-15');

-- ============================================================================
-- TOGETHER AI (5 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- Llama 4 on Together
('together', 'meta-llama/Llama-4-Maverick-17B-128E-Instruct', 0.20, 0.60, '2026-02-01'),
('together', 'meta-llama/Llama-4-Scout-17B-16E-Instruct', 0.10, 0.30, '2026-02-01'),
-- DeepSeek on Together
('together', 'deepseek-ai/DeepSeek-R1', 0.55, 2.19, '2025-01-20'),
-- Qwen on Together
('together', 'Qwen/Qwen3-235B-A22B-Instruct', 0.90, 0.90, '2026-01-15'),
-- Mistral on Together
('together', 'mistralai/Mistral-Large-3', 6.00, 18.00, '2026-01-15');

-- ============================================================================
-- FIREWORKS AI (3 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
('fireworks', 'llama4-maverick-fireworks', 0.18, 0.54, '2026-02-01'),
('fireworks', 'deepseek-r1-fireworks', 0.50, 2.00, '2025-01-20'),
('fireworks', 'qwen3-235b-fireworks', 0.80, 0.80, '2026-01-15');

-- ============================================================================
-- AI21 - Jamba Models (2 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
('ai21', 'jamba-1-7-large', 2.00, 8.00, '2026-01-15'),
('ai21', 'jamba-1-5-mini', 0.20, 0.40, '2025-06-01');

-- ============================================================================
-- ALIBABA QWEN (6 models)
-- ============================================================================
INSERT INTO public.pricing (provider, model, input_price_per_mtok, output_price_per_mtok, effective_from) VALUES
-- Qwen Latest
('qwen', 'qwen-max-20260115', 4.00, 12.00, '2026-01-15'),
('qwen', 'qwen-plus-20260115', 0.80, 2.00, '2026-01-15'),
('qwen', 'qwen-turbo-20260115', 0.30, 0.60, '2026-01-15'),
-- Qwen3
('qwen', 'qwen3-235b-a22b-instruct', 0.90, 0.90, '2026-01-15'),
-- Qwen2.5
('qwen', 'qwen2.5-72b-instruct', 0.35, 0.35, '2024-09-19'),
('qwen', 'qwen2.5-coder-32b-instruct', 0.18, 0.18, '2024-11-01');
