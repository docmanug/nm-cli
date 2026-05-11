from __future__ import annotations
import requests
from nm.core.output import format_error

META_GRAPH_URL = "https://graph.facebook.com/v21.0"


class MetaAdsService:
    def __init__(self, access_token: str, ad_account_id: str = ""):
        self._token = access_token
        self._ad_account_id = ad_account_id

    def _get(self, path: str, params: dict | None = None) -> dict:
        all_params = params or {}
        all_params["access_token"] = self._token
        resp = requests.get(f"{META_GRAPH_URL}{path}", params=all_params)
        resp.raise_for_status()
        return resp.json()

    def _account_path(self) -> str:
        acct = self._ad_account_id
        if not acct.startswith("act_"):
            acct = f"act_{acct}"
        return f"/{acct}"

    def campaigns_list(self) -> str:
        data = self._get(
            f"{self._account_path()}/campaigns",
            {
                "fields": "id,name,status,objective,daily_budget,lifetime_budget",
                "limit": 50,
            },
        )
        campaigns = data.get("data", [])
        if not campaigns:
            return "Aucune campagne Meta Ads."
        active = [c for c in campaigns if c.get("status") == "ACTIVE"]
        paused = [c for c in campaigns if c.get("status") == "PAUSED"]
        lines = [f"{len(campaigns)} campagnes ({len(active)} actives, {len(paused)} en pause) :\n"]
        for c in campaigns:
            budget = c.get("daily_budget") or c.get("lifetime_budget") or "?"
            if budget != "?":
                budget = f"{int(budget) / 100:.0f} EUR"
            lines.append(
                f"  [{c.get('status', '?')[:3]}] {c.get('name', '?')} "
                f"| ID: {c.get('id', '?')} | Budget: {budget}"
            )
        return "\n".join(lines)

    def campaigns_insights(self, date_range: str = "last_7d") -> str:
        date_preset = date_range.replace("-", "_")
        data = self._get(
            f"{self._account_path()}/insights",
            {
                "fields": "campaign_name,spend,impressions,clicks,ctr,cpc,cpm,"
                          "actions,cost_per_action_type,frequency",
                "date_preset": date_preset,
                "level": "campaign",
                "limit": 50,
            },
        )
        rows = data.get("data", [])
        if not rows:
            return f"Aucune donnee Meta Ads pour {date_range}."
        total_spend = 0
        total_impressions = 0
        total_clicks = 0
        total_leads = 0
        lines = [f"Meta Ads insights ({date_range}) :\n"]
        for r in rows:
            spend = float(r.get("spend", 0))
            impressions = int(r.get("impressions", 0))
            clicks = int(r.get("clicks", 0))
            ctr = r.get("ctr", "0")
            frequency = r.get("frequency", "?")
            total_spend += spend
            total_impressions += impressions
            total_clicks += clicks

            # Extract leads from actions
            leads = 0
            for action in r.get("actions", []):
                if action.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"):
                    leads += int(action.get("value", 0))
            total_leads += leads

            cpl = f"{spend / leads:.1f}" if leads > 0 else "N/A"
            lines.append(
                f"  {r.get('campaign_name', '?')}"
            )
            lines.append(
                f"    Spend: {spend:.1f} EUR | Impressions: {impressions} "
                f"| Clics: {clicks} | CTR: {ctr}%"
            )
            lines.append(
                f"    Leads: {leads} | CPL: {cpl} EUR | Frequence: {frequency}"
            )

        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        avg_cpl = (total_spend / total_leads) if total_leads > 0 else 0
        lines.insert(1, f"TOTAL: Spend {total_spend:.1f} EUR | {total_impressions} impr | "
                        f"{total_clicks} clics | CTR {avg_ctr:.2f}% | "
                        f"{total_leads} leads | CPL {avg_cpl:.1f} EUR\n")
        return "\n".join(lines)

    def adsets_insights(self, campaign_id: str, date_range: str = "last_7d") -> str:
        date_preset = date_range.replace("-", "_")
        data = self._get(
            f"/{campaign_id}/adsets",
            {
                "fields": "id,name,status,daily_budget,targeting",
                "limit": 50,
            },
        )
        adsets = data.get("data", [])
        if not adsets:
            return "Aucun adset dans cette campagne."

        lines = [f"{len(adsets)} adsets :\n"]
        for adset in adsets:
            # Get insights per adset
            insights_data = self._get(
                f"/{adset['id']}/insights",
                {
                    "fields": "spend,impressions,clicks,ctr,actions,frequency",
                    "date_preset": date_preset,
                },
            )
            insights = insights_data.get("data", [{}])
            ins = insights[0] if insights else {}
            spend = float(ins.get("spend", 0))
            impressions = int(ins.get("impressions", 0))
            clicks = int(ins.get("clicks", 0))
            frequency = ins.get("frequency", "?")

            leads = 0
            for action in ins.get("actions", []):
                if action.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"):
                    leads += int(action.get("value", 0))
            cpl = f"{spend / leads:.1f}" if leads > 0 else "N/A"

            lines.append(
                f"  [{adset.get('status', '?')[:3]}] {adset.get('name', '?')}"
            )
            lines.append(
                f"    Spend: {spend:.1f} EUR | {impressions} impr | {clicks} clics | "
                f"{leads} leads | CPL: {cpl} EUR | Freq: {frequency}"
            )
        return "\n".join(lines)

    def ads_insights(self, adset_id: str, date_range: str = "last_7d") -> str:
        date_preset = date_range.replace("-", "_")
        data = self._get(
            f"/{adset_id}/ads",
            {
                "fields": "id,name,status,creative",
                "limit": 50,
            },
        )
        ads = data.get("data", [])
        if not ads:
            return "Aucune ad dans cet adset."

        lines = [f"{len(ads)} ads :\n"]
        for ad in ads:
            insights_data = self._get(
                f"/{ad['id']}/insights",
                {
                    "fields": "spend,impressions,clicks,ctr,actions",
                    "date_preset": date_preset,
                },
            )
            insights = insights_data.get("data", [{}])
            ins = insights[0] if insights else {}
            spend = float(ins.get("spend", 0))
            clicks = int(ins.get("clicks", 0))

            leads = 0
            for action in ins.get("actions", []):
                if action.get("action_type") in ("lead", "offsite_conversion.fb_pixel_lead"):
                    leads += int(action.get("value", 0))

            lines.append(
                f"  [{ad.get('status', '?')[:3]}] {ad.get('name', '?')}"
            )
            lines.append(
                f"    Spend: {spend:.1f} EUR | {clicks} clics | {leads} leads"
            )
        return "\n".join(lines)


def handle_meta(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("meta")
    config = profile.get_service_config("meta") or {}

    def _flag(name):
        for i, a in enumerate(args):
            if a == f"--{name}" and i + 1 < len(args):
                return args[i + 1]
        return ""

    ad_account = _flag("account") or config.get("ad_account_id", "") or creds.get("ad_account_id", "")

    svc = MetaAdsService(
        access_token=creds["access_token"],
        ad_account_id=ad_account,
    )

    if command == "campaigns.list":
        return svc.campaigns_list()

    elif command == "campaigns.insights":
        date_range = _flag("date-range") or "last_7d"
        return svc.campaigns_insights(date_range)

    elif command == "adsets.insights":
        campaign_id = _flag("campaign")
        if not campaign_id:
            return format_error("Usage: nm meta adsets insights --campaign <campaign_id> [--date-range last_7d]")
        date_range = _flag("date-range") or "last_7d"
        return svc.adsets_insights(campaign_id, date_range)

    elif command == "ads.insights":
        adset_id = _flag("adset")
        if not adset_id:
            return format_error("Usage: nm meta ads insights --adset <adset_id> [--date-range last_7d]")
        date_range = _flag("date-range") or "last_7d"
        return svc.ads_insights(adset_id, date_range)

    else:
        return format_error(f"Commande Meta inconnue: {command}")
