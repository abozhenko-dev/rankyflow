"""
DataForSEO service — SERP rank tracking.
Uses Standard Queue (batch) for cost efficiency: ~$0.0006/request.
"""
import base64
import json
from datetime import date
from typing import Optional
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()

DATAFORSEO_BASE = "https://api.dataforseo.com/v3"


class DataForSEOService:
    """Client for DataForSEO SERP API."""

    def __init__(self):
        creds = f"{settings.dataforseo_login}:{settings.dataforseo_password}"
        self.auth_header = base64.b64encode(creds.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {self.auth_header}",
            "Content-Type": "application/json",
        }

    async def check_ranks_batch(
        self,
        keywords: list[str],
        target_domains: list[str],
        location_code: int = 2840,  # US
        language_code: str = "en",
        device: str = "desktop",
    ) -> list[dict]:
        """
        Submit batch SERP check via Standard Queue (async, cheaper).

        Args:
            keywords: List of keywords to check
            target_domains: Domains to find in results (project + competitors)
            location_code: DataForSEO location code (2840 = US, 2276 = Germany, etc.)
            language_code: Language code
            device: "desktop" or "mobile"

        Returns:
            List of results with positions per keyword × domain
        """
        # Build task payload
        tasks = []
        for kw in keywords:
            tasks.append({
                "keyword": kw,
                "location_code": location_code,
                "language_code": language_code,
                "device": device,
                "depth": 100,  # check top 100
                "tag": json.dumps({"keyword": kw, "domains": target_domains}),
            })

        async with httpx.AsyncClient(timeout=60) as client:
            # POST tasks to Standard Queue
            response = await client.post(
                f"{DATAFORSEO_BASE}/serp/google/organic/task_post",
                headers=self.headers,
                json=tasks,
            )
            response.raise_for_status()
            post_result = response.json()

            if post_result.get("status_code") != 20000:
                logger.error("DataForSEO task_post failed", result=post_result)
                return []

            # Extract task IDs
            task_ids = []
            for task in post_result.get("tasks", []):
                if task.get("status_code") == 20100:
                    task_ids.append(task["id"])

            logger.info(f"DataForSEO: submitted {len(task_ids)} tasks")
            return task_ids

    async def fetch_results(self, task_ids: list[str]) -> list[dict]:
        """
        Fetch completed results from Standard Queue.
        Call this after tasks have had time to process (~1-45 min).
        """
        results = []

        async with httpx.AsyncClient(timeout=60) as client:
            for task_id in task_ids:
                response = await client.get(
                    f"{DATAFORSEO_BASE}/serp/google/organic/task_get/regular/{task_id}",
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

                for task in data.get("tasks", []):
                    if task.get("status_code") != 20000:
                        continue

                    tag = json.loads(task.get("data", {}).get("tag", "{}"))
                    keyword = tag.get("keyword", "")
                    target_domains = tag.get("domains", [])

                    for result_set in task.get("result", []):
                        items = result_set.get("items", [])
                        for item in items:
                            if item.get("type") != "organic":
                                continue

                            domain = item.get("domain", "")
                            if domain in target_domains:
                                results.append({
                                    "keyword": keyword,
                                    "domain": domain,
                                    "position": item.get("rank_group"),
                                    "url": item.get("url"),
                                    "title": item.get("title"),
                                    "description": item.get("description"),
                                })

        logger.info(f"DataForSEO: fetched {len(results)} position results")
        return results

    async def check_ranks_live(
        self,
        keyword: str,
        target_domains: list[str],
        location_code: int = 2840,
        language_code: str = "en",
        device: str = "desktop",
    ) -> list[dict]:
        """
        Live (synchronous) SERP check — more expensive but instant.
        Use sparingly, e.g. for on-demand checks from UI.
        """
        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "device": device,
            "depth": 100,
        }]

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{DATAFORSEO_BASE}/serp/google/organic/live/regular",
                headers=self.headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        results = []
        for task in data.get("tasks", []):
            if task.get("status_code") != 20000:
                continue
            for result_set in task.get("result", []):
                serp_features = []
                for item in result_set.get("items", []):
                    item_type = item.get("type", "")

                    # Track SERP features
                    if item_type in ("featured_snippet", "knowledge_graph",
                                     "local_pack", "people_also_ask", "ai_overview"):
                        serp_features.append(item_type)

                    if item_type != "organic":
                        continue

                    domain = item.get("domain", "")
                    if domain in target_domains:
                        results.append({
                            "keyword": keyword,
                            "domain": domain,
                            "position": item.get("rank_group"),
                            "url": item.get("url"),
                            "title": item.get("title"),
                            "serp_features": serp_features,
                        })

        return results

    @staticmethod
    def get_location_code(country: str) -> int:
        """Map country code to DataForSEO location code."""
        codes = {
            "US": 2840, "GB": 2826, "DE": 2276, "FR": 2250,
            "ES": 2724, "IT": 2380, "NL": 2528, "PT": 2620,
            "UA": 2804, "PL": 2616, "CZ": 2203, "AT": 2040,
            "CH": 2756, "CA": 2124, "AU": 2036, "BR": 2076,
            "IN": 2356, "JP": 2392, "KR": 2410, "SE": 2752,
        }
        return codes.get(country.upper(), 2840)


# Singleton
dataforseo_service = DataForSEOService()
