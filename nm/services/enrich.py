"""Pre-Call Intelligence enrichment service.

Pipeline: read lead (Monday) → search URLs (DuckDuckGo) → scrape (Crawl4AI)
         → qualify content (keyword matching) → build briefing → write Monday.
"""
from __future__ import annotations

import re
import json
from datetime import date

import requests

try:
    from duckduckgo_search import DDGS
except ImportError:  # graceful degradation if not installed
    DDGS = None  # type: ignore

from nm.core.auth import get_credentials
from nm.core.output import (
    format_enrich_result,
    format_enrich_batch,
    format_enrich_status,
    format_error,
)
from nm.services.monday import MondayService


# ---------------------------------------------------------------------------
# Column ID mappings
# ---------------------------------------------------------------------------

ENRICHMENT_COLUMNS_FR_LEADS = {
    "site_web": "text_mm13wqzg",
    "ig": "text_mkraxd0w",
    "qualif_ig": "long_text_mm13xv4c",
    "linkedin": "text_mkraa31t",
    "fb": "text_mkrag2dx",
    "doctolib": "text_mkradpsa",
    "qualif_doctolib": "long_text_mm13q0qp",
    "specialite": "text_mkrapkr1",
    "nb_praticiens": "numeric_mks0a91v",
    "nb_assistantes": "numeric_mks0hfyf",
    "nb_secretaires": "numeric_mks0hgrz",
    "enrichi": "boolean_mm13e5ct",
    "google_checked": "boolean_mm15wxry",
    "fait_esthetique": "boolean_mm15smqp",
    "global_context": "global_context",
}

ENRICHMENT_COLUMNS_CONTACTS = {
    "site_web": "text_mm15c7qf",
    "ig": "text_mm15gas7",
    "qualif_ig": "text_mm15xe0j",
    "linkedin": "text_mm15djvh",
    "fb": "text_mm156k68",
    "doctolib": "text_mm15cra9",
    "qualif_doctolib": "text_mm156c3m",
    "specialite": "text_mm19jvry",
    "nb_praticiens": "numeric_mm191k8a",
    "nb_assistantes": "numeric_mm19smh0",
    "nb_secretaires": "numeric_mm19z8jq",
    "google_checked": "boolean_mm1584a3",
    "fait_esthetique": "boolean_mm1557qy",
    "global_context": "global_context",
}

# Map board name → column dict (no "enrichi" key in contacts board)
_BOARD_COLUMNS = {
    "fr_leads": ENRICHMENT_COLUMNS_FR_LEADS,
    "contacts": ENRICHMENT_COLUMNS_CONTACTS,
}

# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

ESTHETIQUE_KEYWORDS = [
    "acide hyaluronique", "botox", "toxine botulique", "injection",
    "peeling", "laser", "medecine esthetique", "chirurgie esthetique",
    "rajeunissement", "rides", "volumetrie", "skinbooster",
    "mesolift", "cryolipolyse", "hifu", "fils tenseurs",
    "rhinoplastie", "blepharoplastie", "liposuccion",
]

SPECIALTY_KEYWORDS = [
    "injection", "botox", "acide hyaluronique", "laser", "peeling",
    "cryolipolyse", "hifu", "fils tenseurs", "mesolift", "skinbooster",
    "rhinoplastie", "blepharoplastie", "liposuccion", "lifting",
    "dermato", "dermatologie", "epilation", "microblading",
]

COMPETITOR_KEYWORDS = [
    "doctolib pro", "galaxie", "dr sante", "clinicminds",
    "aesthetic manager", "beauty angel", "patientpop",
]


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def search_urls(query: str, max_results: int = 5) -> list[dict]:
    """Search DuckDuckGo and return a list of {href, title} dicts.

    Returns [] on any failure (network, import, etc.).
    """
    if DDGS is None:
        return []
    try:
        with DDGS() as ddgs:
            results = ddgs.text(query, max_results=max_results)
            return list(results) if results else []
    except Exception:
        return []


def scrape_page(url: str, crawl4ai_url: str = "http://localhost:11235",
                timeout: int = 30, api_token: str = "") -> str:
    """POST url to Crawl4AI HTTP endpoint and return markdown content.

    Uses the official Crawl4AI REST API (async: POST /crawl → task_id → GET /task/{id}).
    Returns "" on any failure.
    """
    import time

    headers = {"Content-Type": "application/json"}
    if api_token:
        headers["Authorization"] = f"Bearer {api_token}"

    try:
        # Step 1: Submit crawl task
        resp = requests.post(
            f"{crawl4ai_url}/crawl",
            headers=headers,
            json={
                "urls": [url],
                "browser_config": {
                    "type": "BrowserConfig",
                    "params": {"headless": True},
                },
                "crawler_config": {
                    "type": "CrawlerRunConfig",
                    "params": {"cache_mode": "bypass"},
                },
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("task_id", "")
        if not task_id:
            # Synchronous response — try to extract directly
            results = data.get("results", data.get("result", []))
            if isinstance(results, list) and results:
                return results[0].get("markdown") or results[0].get("cleaned_html", "")
            return ""

        # Step 2: Poll for result
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(2)
            poll = requests.get(
                f"{crawl4ai_url}/task/{task_id}",
                headers=headers,
                timeout=10,
            )
            poll.raise_for_status()
            task_data = poll.json()
            status = task_data.get("status", "")
            if status == "completed":
                results = task_data.get("results", [])
                if results:
                    return results[0].get("markdown") or results[0].get("cleaned_html", "")
                return ""
            if status == "failed":
                return ""
        return ""  # timeout
    except Exception:
        return ""


def _normalize(text: str) -> str:
    """Lowercase + strip accents for keyword matching."""
    import unicodedata
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def qualify_content(content: str) -> dict:
    """Keyword-based qualification of scraped content.

    Returns:
        {
            "fait_esthetique": bool,
            "specialites": str,   # comma-separated found keywords
            "competitors": str,   # comma-separated found competitors
            "nb_praticiens": str, # extracted count or ""
        }
    """
    if not content:
        return {
            "fait_esthetique": False,
            "specialites": "",
            "competitors": "",
            "nb_praticiens": "",
        }

    normalized = _normalize(content)

    # Detect aesthetic medicine
    fait_esthetique = any(kw in normalized for kw in ESTHETIQUE_KEYWORDS)

    # Extract specialties
    found_specialties = []
    seen = set()
    for kw in SPECIALTY_KEYWORDS:
        if kw in normalized and kw not in seen:
            found_specialties.append(kw)
            seen.add(kw)

    # Extract competitors
    found_competitors = []
    for kw in COMPETITOR_KEYWORDS:
        if kw in normalized:
            found_competitors.append(kw)

    # Try to extract practitioner count — pattern like "3 praticiens", "une équipe de 5"
    nb_praticiens = ""
    patterns = [
        r"(\d+)\s+praticien",
        r"(\d+)\s+m[eé]decin",
        r"(\d+)\s+chirurgien",
        r"(\d+)\s+docteur",
        r"équipe\s+de\s+(\d+)",
        r"equipe\s+de\s+(\d+)",
    ]
    for pat in patterns:
        m = re.search(pat, normalized)
        if m:
            nb_praticiens = m.group(1)
            break

    return {
        "fait_esthetique": fait_esthetique,
        "specialites": ", ".join(found_specialties),
        "competitors": ", ".join(found_competitors),
        "nb_praticiens": nb_praticiens,
    }


def build_briefing(data: dict) -> str:
    """Format enrichment data dict into a pre-call briefing string."""
    name = data.get("name", "?")
    lines = [f"=== BRIEFING PRE-CALL : {name} ==="]

    # Presence web
    site = data.get("site_web", "")
    doctolib = data.get("doctolib", "")
    ig = data.get("ig", "")
    linkedin = data.get("linkedin", "")

    if site:
        lines.append(f"Site web : {site}")
    if doctolib:
        lines.append(f"Doctolib : {doctolib}")
    if ig:
        lines.append(f"Instagram : {ig}")
    if linkedin:
        lines.append(f"LinkedIn : {linkedin}")

    # Aesthetic medicine
    fait_esthetique = data.get("fait_esthetique")
    if fait_esthetique is True:
        lines.append("Medecine esthetique : OUI (detecte)")
    elif fait_esthetique is False:
        lines.append("Medecine esthetique : non detecte")

    # Specialties
    specialites = data.get("specialites", "")
    if specialites:
        lines.append(f"Specialites detectees : {specialites}")

    # Practitioners
    nb_praticiens = data.get("nb_praticiens", "")
    if nb_praticiens:
        lines.append(f"Nb praticiens : {nb_praticiens}")

    # Competitors — important for pitch
    competitors = data.get("competitors", "")
    if competitors:
        lines.append(f"Logiciels concurrents detectes : {competitors}")
        lines.append("  -> Mention dans le pitch : remplacez/complementez avec Nextmotion")

    # Doctolib qualification notes
    qualif_doctolib = data.get("qualif_doctolib", "")
    if qualif_doctolib:
        lines.append(f"Notes Doctolib : {qualif_doctolib[:300]}")

    # IG qualification
    qualif_ig = data.get("qualif_ig", "")
    if qualif_ig:
        lines.append(f"Notes Instagram : {qualif_ig[:300]}")

    lines.append(f"Enrichi le : {date.today().isoformat()}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# EnrichService — orchestrates the full pipeline
# ---------------------------------------------------------------------------

class EnrichService:
    def __init__(
        self,
        monday_svc: MondayService,
        crawl4ai_url: str = "http://localhost:11235",
        timeout: int = 30,
        max_results: int = 5,
        api_token: str = "",
    ):
        self._monday = monday_svc
        self._crawl4ai_url = crawl4ai_url
        self._timeout = timeout
        self._max_results = max_results
        self._api_token = api_token

    def _col_map(self, board_name: str) -> dict:
        return _BOARD_COLUMNS.get(board_name, ENRICHMENT_COLUMNS_FR_LEADS)

    def _get_lead_raw(self, item_id: str) -> dict:
        """Fetch item from Monday and return parsed columns dict plus name."""
        data = self._monday._query(
            '{ items(ids: [%s]) { id name board { id } '
            'column_values { id text value } } }' % item_id
        )
        items = data.get("items", [])
        if not items:
            raise RuntimeError(f"Item {item_id} non trouve")
        return items[0]

    def status(self, item_id: str, board_name: str = "fr_leads") -> dict:
        """Check enrichment status for a lead. Returns status dict."""
        try:
            item = self._get_lead_raw(item_id)
        except RuntimeError as exc:
            return {"name": "?", "error": str(exc), "enriched": False, "filled": [], "empty": []}

        col_map = self._col_map(board_name)
        cols = self._monday._parse_columns(item.get("column_values", []))

        enrichi_col = col_map.get("enrichi", "")
        enriched = bool(cols.get(enrichi_col, "").lower() in ("true", "1", "v", "yes"))

        filled = []
        empty = []
        url_keys = ["site_web", "ig", "linkedin", "doctolib", "fb"]
        for key in url_keys:
            col_id = col_map.get(key, "")
            val = cols.get(col_id, "")
            if val and val.lower() not in ("null", "none"):
                filled.append(key)
            else:
                empty.append(key)

        return {
            "name": item.get("name", "?"),
            "enriched": enriched,
            "filled": filled,
            "empty": empty,
        }

    def enrich_lead(self, item_id: str, board_name: str = "fr_leads") -> dict:
        """Full enrichment pipeline for a single lead.

        Steps:
        1. Read lead from Monday
        2. Check if already enriched (skip if yes)
        3. Search missing URLs via DuckDuckGo
        4. Scrape found URLs via Crawl4AI
        5. Qualify content
        6. Build briefing
        7. Write columns to Monday
        8. Add note
        """
        try:
            item = self._get_lead_raw(item_id)
        except RuntimeError as exc:
            return {"error": str(exc)}

        col_map = self._col_map(board_name)
        cols = self._monday._parse_columns(item.get("column_values", []))
        lead_name = item.get("name", "?")

        # --- Step 2: skip if already enriched ---
        enrichi_col = col_map.get("enrichi", "")
        already_enriched = bool(
            cols.get(enrichi_col, "").lower() in ("true", "1", "v", "yes")
        )
        if already_enriched:
            return {
                "name": lead_name,
                "already_enriched": True,
                "briefing": "",
                "filled_columns": [],
                "skipped_columns": [],
                "errors": [],
            }

        # --- Step 3: search for missing URLs ---
        def _col_val(key: str) -> str:
            cid = col_map.get(key, "")
            v = cols.get(cid, "")
            return v if v and v.lower() not in ("null", "none", "") else ""

        existing = {
            "site_web": _col_val("site_web"),
            "doctolib": _col_val("doctolib"),
            "ig": _col_val("ig"),
            "linkedin": _col_val("linkedin"),
        }

        found_urls: dict[str, str] = {}
        all_content: list[str] = []

        # Site web
        if not existing["site_web"]:
            results = search_urls(f"{lead_name} site officiel medecine esthetique",
                                  max_results=self._max_results)
            for r in results:
                href = r.get("href", "")
                if href and "doctolib" not in href and "instagram" not in href:
                    found_urls["site_web"] = href
                    break

        # Doctolib
        if not existing["doctolib"]:
            results = search_urls(f"{lead_name} doctolib",
                                  max_results=self._max_results)
            for r in results:
                href = r.get("href", "")
                if href and "doctolib.fr" in href:
                    found_urls["doctolib"] = href
                    break

        # Instagram
        if not existing["ig"]:
            results = search_urls(f"{lead_name} instagram medecin esthetique",
                                  max_results=self._max_results)
            for r in results:
                href = r.get("href", "")
                if href and "instagram.com" in href:
                    found_urls["ig"] = href
                    break

        # LinkedIn
        if not existing["linkedin"]:
            results = search_urls(f"{lead_name} linkedin medecin",
                                  max_results=self._max_results)
            for r in results:
                href = r.get("href", "")
                if href and "linkedin.com" in href:
                    found_urls["linkedin"] = href
                    break

        # Merge existing + found
        urls_to_use = {**{k: v for k, v in existing.items() if v}, **found_urls}

        # --- Step 4: scrape found URLs ---
        for key, url in urls_to_use.items():
            content = scrape_page(url, crawl4ai_url=self._crawl4ai_url,
                                  timeout=self._timeout,
                                  api_token=self._api_token)
            if content:
                all_content.append(content)

        combined_content = "\n\n".join(all_content)

        # --- Step 5: qualify ---
        qualification = qualify_content(combined_content)

        # --- Step 6: build briefing ---
        briefing_data = {
            "name": lead_name,
            **urls_to_use,
            **qualification,
        }
        briefing = build_briefing(briefing_data)

        # --- Step 7: write columns to Monday ---
        update_values: dict[str, object] = {}
        filled_columns: list[str] = []
        skipped_columns: list[str] = []
        errors: list[str] = []

        # URL columns
        url_field_map = {
            "site_web": col_map.get("site_web"),
            "doctolib": col_map.get("doctolib"),
            "ig": col_map.get("ig"),
            "linkedin": col_map.get("linkedin"),
        }
        for field, col_id in url_field_map.items():
            if not col_id or col_id == "global_context":
                continue
            url_val = urls_to_use.get(field, "")
            if url_val:
                if _col_val(field):
                    skipped_columns.append(field)
                else:
                    update_values[col_id] = url_val
                    filled_columns.append(field)

        # Boolean columns — Monday checkbox format: {"checked": "true"} or {"checked": "false"}
        def _checkbox(val: bool) -> dict:
            return {"checked": "true"} if val else {}

        if col_map.get("fait_esthetique") and col_map["fait_esthetique"] != "global_context":
            cid = col_map["fait_esthetique"]
            if qualification["fait_esthetique"]:
                update_values[cid] = _checkbox(True)
                filled_columns.append("fait_esthetique")

        if col_map.get("google_checked") and col_map["google_checked"] != "global_context":
            cid = col_map["google_checked"]
            update_values[cid] = _checkbox(True)
            filled_columns.append("google_checked")

        # enrichi flag (fr_leads only)
        if col_map.get("enrichi") and col_map["enrichi"] != "global_context":
            update_values[col_map["enrichi"]] = _checkbox(True)
            filled_columns.append("enrichi")

        # Specialite
        if qualification["specialites"] and col_map.get("specialite"):
            cid = col_map["specialite"]
            if cid != "global_context":
                update_values[cid] = qualification["specialites"][:255]
                filled_columns.append("specialite")

        # nb_praticiens
        if qualification["nb_praticiens"] and col_map.get("nb_praticiens"):
            cid = col_map["nb_praticiens"]
            if cid != "global_context":
                try:
                    update_values[cid] = int(qualification["nb_praticiens"])
                    filled_columns.append("nb_praticiens")
                except ValueError:
                    pass

        if update_values:
            try:
                self._monday._update_columns(board_name, item_id, update_values)
            except Exception as exc:
                errors.append(f"Monday update error: {exc}")

        # --- Step 8: add note ---
        try:
            self._monday._add_note(item_id, briefing[:3000])
        except Exception as exc:
            errors.append(f"Monday note error: {exc}")

        return {
            "name": lead_name,
            "already_enriched": False,
            "briefing": briefing,
            "filled_columns": filled_columns,
            "skipped_columns": skipped_columns,
            "errors": errors,
            "qualification": qualification,
        }

    def enrich_batch(self, board_name: str = "fr_leads", limit: int = 10) -> list[dict]:
        """Batch enrich non-enriched leads from a board."""
        col_map = self._col_map(board_name)
        enrichi_col = col_map.get("enrichi", "")

        # Fetch items from board
        try:
            board_id = self._monday._board_id(board_name)
            data = self._monday._query(
                '{ boards(ids: [%d]) { items_page(limit: %d) '
                '{ items { id name column_values { id text value } } } } }'
                % (board_id, limit * 3)  # over-fetch to find unenriched ones
            )
            items = data["boards"][0]["items_page"]["items"]
        except Exception as exc:
            return [{"error": str(exc)}]

        results = []
        count = 0
        for item in items:
            if count >= limit:
                break
            cols = self._monday._parse_columns(item.get("column_values", []))
            already = bool(cols.get(enrichi_col, "").lower() in ("true", "1", "v", "yes"))
            if not already:
                result = self.enrich_lead(item["id"], board_name)
                results.append(result)
                count += 1

        return results


# ---------------------------------------------------------------------------
# CLI handler
# ---------------------------------------------------------------------------

def handle_enrich(command: str, args: list, profile) -> str:
    """CLI entry point for the enrich service.

    Commands:
        lead <item_id> [--board fr_leads]
        contact <item_id>
        batch [--board fr_leads] [--limit 10]
        status <item_id> [--board fr_leads]
    """
    # Get credentials
    monday_creds = get_credentials("monday")
    enrich_creds = get_credentials("enrich")

    # Profile config
    monday_config = profile.get_service_config("monday") or {}
    enrich_config = profile.get_service_config("enrich") or {}

    boards = monday_config.get("boards", {})
    if isinstance(boards, list):
        boards = {"fr_leads": boards[0]} if boards else {}

    column_maps = monday_config.get("column_maps", monday_config.get("column_map", {}))
    if column_maps and not any(isinstance(v, dict) for v in column_maps.values()):
        column_maps = {"fr_leads": column_maps}

    monday_svc = MondayService(
        api_token=monday_creds["api_token"],
        boards=boards,
        column_maps=column_maps,
        config=monday_config,
    )

    crawl4ai_url = enrich_creds.get("crawl4ai_url") or enrich_config.get(
        "crawl4ai_url", "http://localhost:11235"
    )
    api_token = enrich_creds.get("crawl4ai_api_token") or enrich_config.get(
        "crawl4ai_api_token", ""
    )
    timeout = int(enrich_config.get("timeout", 30))
    max_results = int(enrich_config.get("max_results", 5))

    svc = EnrichService(
        monday_svc=monday_svc,
        crawl4ai_url=crawl4ai_url,
        timeout=timeout,
        max_results=max_results,
        api_token=api_token,
    )

    # Helpers
    def _get_flag(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == f"--{flag}" and i + 1 < len(args):
                return args[i + 1]
        return None

    def _positional() -> list[str]:
        return [a for a in args if not a.startswith("--")]

    board = _get_flag("board")

    # The CLI joins all non-flag tokens with dots, e.g. "status 12345" → "status.12345"
    # Split the command to extract the base command and any embedded item_id
    cmd_parts = command.split(".")
    base_cmd = cmd_parts[0]
    if len(cmd_parts) > 1:
        # Prepend the embedded arg(s) to args list
        args = list(cmd_parts[1:]) + list(args)

    # --- route commands ---

    if base_cmd == "status":
        positional = _positional()
        if not positional:
            return format_error("Usage: nm enrich status <item_id> [--board fr_leads]")
        item_id = positional[0]
        bname = board or "fr_leads"
        result = svc.status(item_id, bname)
        return format_enrich_status(result)

    elif base_cmd in ("lead", "enrich"):
        positional = _positional()
        if not positional:
            return format_error("Usage: nm enrich lead <item_id> [--board fr_leads]")
        item_id = positional[0]
        bname = board or "fr_leads"
        result = svc.enrich_lead(item_id, bname)
        return format_enrich_result(result)

    elif base_cmd == "contact":
        positional = _positional()
        if not positional:
            return format_error("Usage: nm enrich contact <item_id>")
        item_id = positional[0]
        result = svc.enrich_lead(item_id, "contacts")
        return format_enrich_result(result)

    elif base_cmd == "batch":
        bname = board or "fr_leads"
        limit = int(_get_flag("limit") or "10")
        results = svc.enrich_batch(bname, limit)
        return format_enrich_batch(results)

    else:
        return format_error(f"Commande enrich inconnue: {base_cmd}")
