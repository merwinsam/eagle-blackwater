"""
Reasoning Layer: LLM-powered signal interpretation and chat agent.
News-aware: injects headlines + economic calendar into all prompts.
"""

import json
from openai import OpenAI
import config

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


SYSTEM_PROMPT = """You are Eagle, a cautious quantitative risk analyst for Blackwater Capital.
You receive structured daily market signals AND a feed of recent financial/political/macro news headlines.

Your job:
- Connect the dots between news events and the signals you see.
- Identify which headlines are relevant to the current regime and which are noise.
- Highlight geopolitical or macro risks that could amplify or reverse current trends.
- Be concise, precise, and use financial language.

Hard rules:
- Never recommend specific trades or predict exact prices.
- Never fabricate data — only reference what's explicitly in the context.
- When citing news, reference the headline briefly — don't invent quotes.
- Distinguish between signal-relevant news vs. noise.
- Format lists with bullet points."""


def build_signal_context(signals_dict: dict) -> str:
    summary = {}
    for sym, sig in signals_dict.items():
        if not sig:
            continue
        summary[sym] = {
            "date": sig.get("date"),
            "price": sig.get("price"),
            "momentum_20d": sig.get("momentum_20d"),
            "momentum_regime": sig.get("momentum_regime"),
            "vol_20d_ann": sig.get("vol_20d_ann"),
            "vol_state": sig.get("vol_state"),
            "corr_to_peer": sig.get("corr_to_peer"),
            "corr_state": sig.get("corr_state"),
            "max_drawdown_60d": sig.get("max_drawdown_60d"),
            "market_regime": sig.get("market_regime"),
            "risk_flags": sig.get("risk_flags", []),
        }
    return json.dumps(summary, indent=2)


def generate_daily_summary(signals_dict: dict, news_context: str = "", econ_context: str = "") -> str:
    """Generate a daily plain-English summary of market conditions, news-aware."""
    signal_ctx = build_signal_context(signals_dict)

    news_section = ""
    if news_context:
        news_section = f"\n\nRECENT NEWS HEADLINES:\n{news_context}"
    if econ_context:
        news_section += f"\n\nUPCOMING ECONOMIC EVENTS:\n{econ_context}"

    prompt = f"""Here are today's structured market signals:
{signal_ctx}
{news_section}

Please provide:
1. A 2-3 sentence market regime summary (what is the overall state?).
2. Up to 4 key risk observations across all assets.
3. Up to 3 news items or macro events most relevant to the current signals — explain the connection.

Do not predict prices. Do not recommend trades. Do not include questions. Only reference news items from the list above."""

    try:
        resp = get_client().chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=700,
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[LLM Error: {e}]"


def explain_asset_signal(sig: dict, news_context: str = "") -> str:
    """Generate a targeted explanation for one asset's signals, with news context."""
    payload = {k: v for k, v in sig.items() if not k.startswith("_")}

    news_section = f"\n\nRELEVANT HEADLINES FOR {sig['symbol']}:\n{news_context}" if news_context else ""

    prompt = f"""Here is today's signal snapshot for {sig['symbol']}:
{json.dumps(payload, indent=2)}
{news_section}

Please:
1. Restate the regime in 2 sentences.
2. List up to 3 risk observations specific to this asset.
3. Identify 1-2 news items above that are relevant to this asset's current signals (if any).

Be specific. Do not propose trades. Do not include questions. Only reference news from the list provided."""

    try:
        resp = get_client().chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=500,
            temperature=0.3,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[LLM Error: {e}]"


def chat_with_agent(messages: list, signals_dict: dict,
                    news_context: str = "", econ_context: str = "") -> str:
    """Multi-turn chat with the Eagle agent, news-aware."""
    signal_ctx = build_signal_context(signals_dict)

    news_block = ""
    if news_context:
        news_block += f"\n\nRECENT MARKET & POLITICAL NEWS:\n{news_context}"
    if econ_context:
        news_block += f"\n\nUPCOMING ECONOMIC EVENTS:\n{econ_context}"

    system = (
        SYSTEM_PROMPT
        + f"\n\nCurrent market signals (today's data):\n{signal_ctx}"
        + news_block
    )

    full_messages = [{"role": "system", "content": system}] + messages

    try:
        resp = get_client().chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=full_messages,
            max_tokens=800,
            temperature=0.4,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"[Eagle Error: {e}]"
