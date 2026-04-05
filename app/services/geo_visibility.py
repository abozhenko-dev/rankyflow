"""
GEO Visibility Service — Multi-LLM Query Engine.
Sends prompts to 5 AI platforms, detects brand mentions, scores visibility.
"""
import json
import re
from datetime import date
from typing import Optional
import httpx
import structlog

from app.core.config import settings
from app.models.geo import LLMPlatform, Sentiment

logger = structlog.get_logger()


class GEOVisibilityService:
    """
    Queries multiple LLM platforms and analyzes brand visibility.
    Inspired by Peec.ai / Otterly.ai approach.
    """

    # ── LLM API Calls ─────────────────────────────────

    async def query_chatgpt(self, prompt: str) -> dict:
        """Query OpenAI ChatGPT API (gpt-4o-mini for cost efficiency)."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return {
            "platform": "chatgpt",
            "response_text": text,
            "model_used": "gpt-4o-mini",
            "tokens_used": usage.get("total_tokens", 0),
            "cited_urls": [],  # ChatGPT doesn't provide native citations
            "cited_domains": [],
        }

    async def query_perplexity(self, prompt: str) -> dict:
        """
        Query Perplexity API — KEY platform for GEO.
        Returns native citations and source URLs.
        """
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {settings.perplexity_api_key}"},
                json={
                    "model": "sonar",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                },
            )
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        # Perplexity returns citations natively
        citations = data.get("citations", [])
        cited_urls = citations if isinstance(citations, list) else []
        cited_domains = list({self._extract_domain(url) for url in cited_urls})

        return {
            "platform": "perplexity",
            "response_text": text,
            "model_used": "sonar",
            "tokens_used": usage.get("total_tokens", 0),
            "cited_urls": cited_urls,
            "cited_domains": cited_domains,
        }

    async def query_claude(self, prompt: str) -> dict:
        """Query Anthropic Claude API (Sonnet)."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            data = response.json()

        text = data["content"][0]["text"]
        usage = data.get("usage", {})
        tokens = (usage.get("input_tokens", 0) + usage.get("output_tokens", 0))

        return {
            "platform": "claude",
            "response_text": text,
            "model_used": "claude-sonnet-4-20250514",
            "tokens_used": tokens,
            "cited_urls": [],
            "cited_domains": [],
        }

    async def query_gemini(self, prompt: str) -> dict:
        """Query Google Gemini API."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.gemini_api_key}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.3, "maxOutputTokens": 2000},
                },
            )
            response.raise_for_status()
            data = response.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        usage = data.get("usageMetadata", {})
        tokens = usage.get("totalTokenCount", 0)

        return {
            "platform": "gemini",
            "response_text": text,
            "model_used": "gemini-2.0-flash",
            "tokens_used": tokens,
            "cited_urls": [],
            "cited_domains": [],
        }

    async def query_deepseek(self, prompt: str) -> dict:
        """Query DeepSeek API (OpenAI-compatible endpoint)."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.deepseek.com/chat/completions",
                headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                json={
                    "model": "deepseek-chat",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 2000,
                },
            )
            response.raise_for_status()
            data = response.json()

        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return {
            "platform": "deepseek",
            "response_text": text,
            "model_used": "deepseek-chat",
            "tokens_used": usage.get("total_tokens", 0),
            "cited_urls": [],
            "cited_domains": [],
        }

    # ── Query All Platforms ───────────────────────────

    PLATFORM_METHODS = {
        "chatgpt": "query_chatgpt",
        "perplexity": "query_perplexity",
        "claude": "query_claude",
        "gemini": "query_gemini",
        "deepseek": "query_deepseek",
    }

    async def query_all_platforms(
        self,
        prompt: str,
        platforms: list[LLMPlatform] | None = None,
    ) -> list[dict]:
        """
        Query multiple LLM platforms with the same prompt.
        Returns list of results, one per platform.
        """
        if platforms is None:
            platforms = list(LLMPlatform)

        results = []
        for platform in platforms:
            method_name = self.PLATFORM_METHODS.get(platform)
            if not method_name:
                continue
            try:
                method = getattr(self, method_name)
                result = await method(prompt)
                results.append(result)
                logger.info(f"GEO: queried {platform.value}", tokens=result.get("tokens_used"))
            except Exception as e:
                logger.error(f"GEO: failed to query {platform.value}", error=str(e))
                results.append({
                    "platform": platform,
                    "response_text": "",
                    "model_used": "",
                    "tokens_used": 0,
                    "cited_urls": [],
                    "cited_domains": [],
                    "error": str(e),
                })

        return results

    # ── Brand Mention Detection ───────────────────────

    def detect_mentions(
        self,
        response_text: str,
        brand_name: str,
        brand_domain: str,
        competitor_names: dict[str, str],  # {domain: display_name}
        cited_urls: list[str] | None = None,
    ) -> list[dict]:
        """
        Detect brand and competitor mentions in an LLM response.

        Returns list of mention dicts:
        {domain, brand_name, is_mentioned, is_cited, is_recommended,
         position_in_list, mention_count, is_own_brand}
        """
        text_lower = response_text.lower()
        mentions = []

        # Check own brand
        mentions.append(self._analyze_brand_in_response(
            text=response_text,
            brand_name=brand_name,
            domain=brand_domain,
            cited_urls=cited_urls or [],
            is_own_brand=True,
        ))

        # Check each competitor
        for comp_domain, comp_name in competitor_names.items():
            mentions.append(self._analyze_brand_in_response(
                text=response_text,
                brand_name=comp_name,
                domain=comp_domain,
                cited_urls=cited_urls or [],
                is_own_brand=False,
            ))

        return mentions

    def _analyze_brand_in_response(
        self,
        text: str,
        brand_name: str,
        domain: str,
        cited_urls: list[str],
        is_own_brand: bool,
    ) -> dict:
        text_lower = text.lower()
        name_lower = brand_name.lower()
        domain_lower = domain.lower()

        # Mention detection (fuzzy: name or domain appears in text)
        is_mentioned = (name_lower in text_lower) or (domain_lower in text_lower)
        mention_count = text_lower.count(name_lower) + text_lower.count(domain_lower)

        # Citation detection (domain appears in cited URLs)
        is_cited = any(domain_lower in url.lower() for url in cited_urls)

        # Position in numbered/bulleted list
        position = self._find_list_position(text, brand_name, domain)

        # Recommendation detection
        is_recommended = self._is_recommended(text, brand_name)

        # Extract the sentence mentioning the brand (for sentiment analysis)
        snippet = self._extract_mention_snippet(text, brand_name, domain)

        return {
            "domain": domain,
            "brand_name": brand_name,
            "is_mentioned": is_mentioned,
            "is_cited": is_cited,
            "is_recommended": is_recommended,
            "position_in_list": position,
            "mention_count": mention_count,
            "is_own_brand": is_own_brand,
            "sentiment_snippet": snippet,
        }

    def _find_list_position(self, text: str, brand_name: str, domain: str) -> Optional[int]:
        """Find position of brand in numbered lists (1., 2., 3.…)."""
        lines = text.split("\n")
        pattern = re.compile(r"^\s*(\d+)[\.\)\-]")

        for line in lines:
            match = pattern.match(line)
            if match:
                line_lower = line.lower()
                if brand_name.lower() in line_lower or domain.lower() in line_lower:
                    return int(match.group(1))

        # Try markdown bold headers: **1. BrandName**
        pattern2 = re.compile(r"\*\*(\d+)[\.\)]?\s*[^*]*\*\*")
        for match in pattern2.finditer(text):
            block = match.group(0).lower()
            if brand_name.lower() in block or domain.lower() in block:
                return int(match.group(1))

        return None

    def _is_recommended(self, text: str, brand_name: str) -> bool:
        """Check if brand is explicitly recommended."""
        recommend_patterns = [
            f"recommend {brand_name.lower()}",
            f"{brand_name.lower()} is a great",
            f"{brand_name.lower()} is the best",
            f"{brand_name.lower()} is an excellent",
            f"top pick.*{brand_name.lower()}",
            f"best overall.*{brand_name.lower()}",
            f"{brand_name.lower()}.*top pick",
            f"{brand_name.lower()}.*best overall",
            f"i would suggest {brand_name.lower()}",
        ]
        text_lower = text.lower()
        return any(re.search(p, text_lower) for p in recommend_patterns)

    def _extract_mention_snippet(self, text: str, brand_name: str, domain: str) -> Optional[str]:
        """Extract the sentence where brand is first mentioned."""
        sentences = re.split(r'[.!?]\s+', text)
        for sentence in sentences:
            if brand_name.lower() in sentence.lower() or domain.lower() in sentence.lower():
                return sentence.strip()[:500]
        return None

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        url = url.lower().strip()
        for prefix in ["https://", "http://", "www."]:
            url = url.removeprefix(prefix)
        return url.split("/")[0].split("?")[0]

    # ── Aggregate Metrics ─────────────────────────────

    @staticmethod
    def compute_visibility_metrics(
        all_mentions: list[list[dict]],
        own_domain: str,
    ) -> dict:
        """
        Compute aggregated visibility metrics from multiple prompt responses.

        Args:
            all_mentions: List of mention-lists (one per prompt)
            own_domain: The user's own domain

        Returns:
            {mention_rate, citation_rate, recommendation_rate, avg_position, share_of_voice}
        """
        total_prompts = len(all_mentions)
        if total_prompts == 0:
            return {
                "mention_rate": 0, "citation_rate": 0,
                "recommendation_rate": 0, "avg_position": None,
                "share_of_voice": 0,
            }

        own_mentioned = 0
        own_cited = 0
        own_recommended = 0
        own_positions = []
        total_brands_mentioned = 0

        for prompt_mentions in all_mentions:
            any_mentioned = sum(1 for m in prompt_mentions if m["is_mentioned"])
            total_brands_mentioned += any_mentioned

            for m in prompt_mentions:
                if m["domain"].lower() == own_domain.lower():
                    if m["is_mentioned"]:
                        own_mentioned += 1
                    if m["is_cited"]:
                        own_cited += 1
                    if m["is_recommended"]:
                        own_recommended += 1
                    if m["position_in_list"] is not None:
                        own_positions.append(m["position_in_list"])

        mention_rate = own_mentioned / total_prompts
        citation_rate = own_cited / total_prompts
        recommendation_rate = own_recommended / total_prompts
        avg_position = (sum(own_positions) / len(own_positions)) if own_positions else None
        share_of_voice = (own_mentioned / total_brands_mentioned) if total_brands_mentioned > 0 else 0

        return {
            "mention_rate": round(mention_rate, 4),
            "citation_rate": round(citation_rate, 4),
            "recommendation_rate": round(recommendation_rate, 4),
            "avg_position": round(avg_position, 2) if avg_position else None,
            "share_of_voice": round(share_of_voice, 4),
        }


# Singleton
geo_service = GEOVisibilityService()
