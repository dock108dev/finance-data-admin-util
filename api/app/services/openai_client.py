"""OpenAI client for AI-powered market narrative generation.

Equivalent to sports-data-admin's openai_client.py.
Two-pass rendering: per-block generation + flow smoothing pass.
"""

import json
from typing import Any

import httpx
import structlog

from app.config import get_settings
from app.services.pipeline import NarrativeRole

logger = structlog.get_logger(__name__)

# ── Forbidden language patterns (financial advice guardrails) ────────────────

FORBIDDEN_PHRASES = [
    "you should buy",
    "you should sell",
    "guaranteed return",
    "guaranteed profit",
    "risk-free",
    "can't lose",
    "financial advice",
    "investment advice",
    "not financial advice",
    "buy now",
    "sell now",
    "act fast",
    "don't miss out",
    "100% certain",
]

# ── Prompts ─────────────────────────────────────────────────────────────────

NARRATIVE_SYSTEM_PROMPT = """\
You are a financial market analyst writing structured session narratives.
Your output is a JSON array of narrative blocks, each with a semantic role.

Rules:
- Generate 3-5 blocks
- Each block: 40-100 words, consequence-based analysis (not play-by-play)
- Roles must follow this order: SETUP first, RESOLUTION last
- Available roles: SETUP, CATALYST, REACTION, DECISION_POINT, RESOLUTION
- Focus on WHY prices moved, not just WHAT happened
- Never give financial advice or use promotional language
- Use precise numbers (prices, percentages) when available
- Write in third person, present tense for analysis
"""

FLOW_PASS_SYSTEM_PROMPT = """\
You are an editor smoothing transitions between narrative blocks.
Given a JSON array of narrative blocks, improve flow between them.
Keep the same structure, roles, and approximate word counts.
Only adjust language for smoother transitions between blocks.
Return the same JSON array format.
"""


def _build_narrative_prompt(
    candle_summary: dict[str, Any],
    events: list[dict[str, Any]],
    sentiment: dict[str, Any],
    indicators: dict[str, Any],
) -> str:
    """Build the user prompt for narrative generation."""
    parts = [
        "Generate a market narrative for this trading session.",
        "",
        f"## Session Summary",
        f"- Open: {candle_summary.get('open', 'N/A')}",
        f"- High: {candle_summary.get('high', 'N/A')}",
        f"- Low: {candle_summary.get('low', 'N/A')}",
        f"- Close: {candle_summary.get('close', 'N/A')}",
        f"- Volume: {candle_summary.get('volume', 'N/A')}",
        f"- Change: {candle_summary.get('change_pct', 'N/A')}%",
        f"- Candle count: {candle_summary.get('candle_count', 'N/A')}",
        "",
    ]

    if indicators:
        parts.append("## Technical Indicators")
        for key, val in indicators.items():
            parts.append(f"- {key}: {val}")
        parts.append("")

    if events:
        parts.append("## Key Events")
        for ev in events:
            parts.append(
                f"- [{ev.get('event_type', 'unknown')}] "
                f"{ev.get('description', '')} "
                f"(price: {ev.get('price', 'N/A')}, volume: {ev.get('volume', 'N/A')})"
            )
        parts.append("")

    if sentiment:
        parts.append("## Sentiment")
        parts.append(f"- Score: {sentiment.get('sentiment_score', 'N/A')}")
        parts.append(f"- Social posts: {sentiment.get('social_posts', 0)}")
        parts.append(f"- News articles: {sentiment.get('news_articles', 0)}")
        parts.append(f"- Fear & Greed: {sentiment.get('fear_greed_index', 'N/A')}")
        parts.append("")

    parts.append(
        'Return a JSON array: [{"role": "SETUP", "narrative": "..."}, ...]'
    )
    return "\n".join(parts)


async def _call_openai(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Make a single OpenAI API call with JSON mode."""
    settings = get_settings()

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.openai_model_analysis,
                "response_format": {"type": "json_object"},
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


def strip_forbidden_language(text: str) -> str:
    """Remove forbidden financial advice phrases from text."""
    result = text
    for phrase in FORBIDDEN_PHRASES:
        # Case-insensitive replacement
        lower = result.lower()
        idx = lower.find(phrase)
        while idx != -1:
            result = result[:idx] + result[idx + len(phrase):]
            lower = result.lower()
            idx = lower.find(phrase)
    return result


async def generate_market_narrative(
    candle_summary: dict[str, Any],
    events: list[dict[str, Any]],
    sentiment: dict[str, Any],
    indicators: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate narrative blocks via OpenAI (pass 1: per-block generation).

    Returns list of dicts with keys: role, narrative, word_count.
    """
    user_prompt = _build_narrative_prompt(
        candle_summary, events, sentiment, indicators
    )

    logger.info("openai.generate_narrative", prompt_len=len(user_prompt))

    raw = await _call_openai(
        system_prompt=NARRATIVE_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.7,
    )

    # OpenAI may return {"blocks": [...]} or just [...]
    if isinstance(raw, dict):
        blocks = raw.get("blocks", raw.get("narrative", []))
    elif isinstance(raw, list):
        blocks = raw
    else:
        blocks = []

    # Normalize blocks
    result = []
    for block in blocks:
        role = block.get("role", "REACTION")
        narrative = strip_forbidden_language(block.get("narrative", ""))
        word_count = len(narrative.split())
        result.append({
            "role": role,
            "narrative": narrative,
            "word_count": word_count,
        })

    logger.info("openai.narrative_generated", block_count=len(result))
    return result


async def apply_flow_pass(
    blocks: list[dict[str, Any]],
    asset_context: str = "",
) -> list[dict[str, Any]]:
    """Smooth transitions between narrative blocks (pass 2: flow pass).

    Takes existing blocks and improves inter-block transitions.
    """
    if not blocks:
        return blocks

    user_prompt = (
        f"Smooth the transitions in these narrative blocks for {asset_context}.\n\n"
        f"Input blocks:\n{json.dumps(blocks, indent=2)}\n\n"
        'Return a JSON object with key "blocks" containing the smoothed array.'
    )

    logger.info("openai.flow_pass", block_count=len(blocks))

    raw = await _call_openai(
        system_prompt=FLOW_PASS_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3,  # Lower temperature for editing
    )

    if isinstance(raw, dict):
        smoothed = raw.get("blocks", [])
    elif isinstance(raw, list):
        smoothed = raw
    else:
        return blocks  # Fallback to original on unexpected format

    # Re-normalize
    result = []
    for block in smoothed:
        narrative = strip_forbidden_language(block.get("narrative", ""))
        result.append({
            "role": block.get("role", "REACTION"),
            "narrative": narrative,
            "word_count": len(narrative.split()),
        })

    logger.info("openai.flow_pass_complete", block_count=len(result))
    return result
