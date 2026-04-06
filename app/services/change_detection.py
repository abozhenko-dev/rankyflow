"""
Change Detection Service — crawls competitor pages, detects changes.
Uses Playwright for JS-rendered pages, BeautifulSoup for parsing.
"""
import hashlib
import json
import difflib
from typing import Optional
from bs4 import BeautifulSoup
import structlog

logger = structlog.get_logger()


class ChangeDetectionService:
    """Crawls pages, extracts SEO elements, detects changes."""

    async def crawl_page(self, url: str) -> dict:
        """
        Crawl a page using httpx, extract SEO-relevant data.
        Returns structured snapshot data.
        """
        import httpx

        try:
            async with httpx.AsyncClient(
                timeout=30,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SEOTrackerBot/1.0; +https://rankyflow.com)",
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text
        except Exception as e:
            logger.error(f"Crawl failed for {url}", error=str(e))
            return {"error": str(e)}

        return self.parse_page(html, url)

    def parse_page(self, html: str, url: str) -> dict:
        """Parse HTML and extract SEO elements."""
        soup = BeautifulSoup(html, "lxml")

        # Title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None

        # Meta description
        meta_desc_tag = soup.find("meta", attrs={"name": "description"})
        meta_description = meta_desc_tag.get("content", "") if meta_desc_tag else None

        # H1
        h1_tag = soup.find("h1")
        h1 = h1_tag.get_text(strip=True) if h1_tag else None

        # All headings
        headings = {}
        for level in range(2, 7):
            tag_name = f"h{level}"
            tags = soup.find_all(tag_name)
            if tags:
                headings[tag_name] = [t.get_text(strip=True) for t in tags]

        # Body text (stripped of scripts/styles)
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        body_text = soup.get_text(separator=" ", strip=True)
        word_count = len(body_text.split())

        # Links
        all_links = soup.find_all("a", href=True)
        from urllib.parse import urlparse
        page_domain = urlparse(url).netloc

        internal_links = 0
        external_links = 0
        for link in all_links:
            href = link.get("href", "")
            if href.startswith(("http://", "https://")):
                link_domain = urlparse(href).netloc
                if page_domain in link_domain:
                    internal_links += 1
                else:
                    external_links += 1
            elif href.startswith("/"):
                internal_links += 1

        # Schema markup
        schema_tags = soup.find_all("script", type="application/ld+json")
        schema_data = []
        for tag in schema_tags:
            try:
                schema_data.append(json.loads(tag.string))
            except (json.JSONDecodeError, TypeError):
                pass

        # Content hash for quick change detection
        content_hash = hashlib.sha256(body_text.encode()).hexdigest()

        return {
            "title": title,
            "meta_description": meta_description,
            "h1": h1,
            "headings_json": json.dumps(headings) if headings else None,
            "word_count": word_count,
            "internal_links_count": internal_links,
            "external_links_count": external_links,
            "schema_markup": json.dumps(schema_data) if schema_data else None,
            "content_hash": content_hash,
            "raw_text": body_text[:50000],  # cap at 50k chars
        }

    def compare_snapshots(self, old: dict, new: dict) -> list[dict]:
        """
        Compare two snapshots and return list of detected changes.
        Each change: {field_name, change_type, old_value, new_value, severity, diff_html}
        """
        changes = []

        # Fields to compare with their severity mapping
        field_config = {
            "title": {"type": "title", "severity": "major"},
            "meta_description": {"type": "meta", "severity": "moderate"},
            "h1": {"type": "content", "severity": "major"},
            "word_count": {"type": "content", "severity": "moderate"},
            "internal_links_count": {"type": "structure", "severity": "minor"},
            "external_links_count": {"type": "structure", "severity": "minor"},
            "schema_markup": {"type": "schema", "severity": "moderate"},
        }

        for field, config in field_config.items():
            old_val = old.get(field)
            new_val = new.get(field)

            if old_val != new_val:
                # For word count, check if change is significant
                if field == "word_count" and old_val and new_val:
                    pct_change = abs(new_val - old_val) / max(old_val, 1)
                    if pct_change < 0.05:  # less than 5% change = skip
                        continue
                    if pct_change > 0.3:
                        config["severity"] = "major"

                diff_html = None
                if isinstance(old_val, str) and isinstance(new_val, str):
                    diff_html = self._generate_diff_html(old_val, new_val)

                changes.append({
                    "field_name": field,
                    "change_type": config["type"],
                    "severity": config["severity"],
                    "old_value": str(old_val) if old_val else None,
                    "new_value": str(new_val) if new_val else None,
                    "diff_html": diff_html,
                })

        # Check content hash for body text changes
        if old.get("content_hash") != new.get("content_hash"):
            # Generate diff of first 5000 chars of body text
            old_text = (old.get("raw_text") or "")[:5000]
            new_text = (new.get("raw_text") or "")[:5000]
            diff_html = self._generate_diff_html(old_text, new_text)

            changes.append({
                "field_name": "body_content",
                "change_type": "content",
                "severity": "moderate",
                "old_value": f"hash:{old.get('content_hash', '')[:16]}",
                "new_value": f"hash:{new.get('content_hash', '')[:16]}",
                "diff_html": diff_html,
            })

        # Headings structure changes
        old_headings = old.get("headings_json", "{}")
        new_headings = new.get("headings_json", "{}")
        if old_headings != new_headings:
            changes.append({
                "field_name": "headings_structure",
                "change_type": "structure",
                "severity": "moderate",
                "old_value": old_headings,
                "new_value": new_headings,
                "diff_html": None,
            })

        return changes

    @staticmethod
    def _generate_diff_html(old_text: str, new_text: str) -> str:
        """Generate an HTML diff between two text strings."""
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)

        differ = difflib.HtmlDiff(wrapcolumn=80)
        return differ.make_table(
            old_lines[:100], new_lines[:100],
            fromdesc="Before", todesc="After",
        )

    @staticmethod
    def classify_overall_severity(changes: list[dict]) -> str:
        """Determine overall severity from a list of changes."""
        if not changes:
            return "none"
        severities = [c["severity"] for c in changes]
        if "major" in severities:
            return "major"
        if "moderate" in severities:
            return "moderate"
        return "minor"


# Singleton
change_detection_service = ChangeDetectionService()
