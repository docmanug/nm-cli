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

    def pixel_stats(self, pixel_id: str, date_range: str = "last_7d") -> str:
        data = self._get(
            f"/{pixel_id}/stats",
            {"aggregation": "event", "start_time": "", "end_time": ""},
        )
        stats = data.get("data", [])
        if not stats:
            return f"Aucun event pixel {pixel_id}."
        lines = [f"Pixel {pixel_id} — events recents :\n"]
        for s in stats:
            lines.append(
                f"  {s.get('event', '?')}: {s.get('count', 0)} events | "
                f"value: {s.get('value', 0)}"
            )
        return "\n".join(lines)

    def pixel_diagnostics(self, pixel_id: str) -> str:
        data = self._get(
            f"/{pixel_id}/da_checks",
            {"checks": '["pixel_fires","custom_conversions","page_view"]'},
        )
        checks = data.get("data", [])
        if not checks:
            return f"Aucun diagnostic pour pixel {pixel_id}."
        lines = [f"Diagnostics pixel {pixel_id} :\n"]
        for c in checks:
            status = "OK" if c.get("result") == "passed" else "ERREUR"
            lines.append(
                f"  [{status}] {c.get('check_name', c.get('name', '?'))}: "
                f"{c.get('description', c.get('message', ''))}"
            )
        return "\n".join(lines)

    def pixel_events(self, pixel_id: str, limit: int = 20) -> str:
        # Use the test events endpoint to see recent server events
        data = self._get(
            f"/{pixel_id}/test_events",
            {"limit": limit},
        )
        events = data.get("data", [])
        if not events:
            # Fallback: try recent_events
            data = self._get(
                f"/{pixel_id}/recent_events",
                {"limit": limit},
            )
            events = data.get("data", [])
        if not events:
            return f"Aucun event recent pixel {pixel_id}."
        lines = [f"{len(events)} events recents pixel {pixel_id} :\n"]
        for e in events:
            lines.append(
                f"  [{e.get('event_name', e.get('event', '?'))}] "
                f"{e.get('timestamp', e.get('time', '?'))} — "
                f"url: {e.get('url', e.get('event_source_url', 'N/A'))}"
            )
        return "\n".join(lines)

    # --- CREATION ---

    def _post(self, path: str, data: dict) -> dict:
        data["access_token"] = self._token
        resp = requests.post(f"{META_GRAPH_URL}{path}", data=data)
        resp.raise_for_status()
        return resp.json()

    def campaign_create(self, name: str, objective: str = "OUTCOME_LEADS",
                        status: str = "PAUSED",
                        daily_budget: int = 0,
                        lifetime_budget: int = 0,
                        special_ad_categories: str = "") -> str:
        payload = {
            "name": name,
            "objective": objective,
            "status": status,
            "special_ad_categories": f"[{special_ad_categories}]" if special_ad_categories else "[]",
        }
        if daily_budget:
            payload["daily_budget"] = daily_budget * 100  # cents
        if lifetime_budget:
            payload["lifetime_budget"] = lifetime_budget * 100
        data = self._post(f"{self._account_path()}/campaigns", payload)
        return f"Campagne creee — ID: {data.get('id', '?')} | Nom: {name} | Status: {status}"

    def adset_create(self, campaign_id: str, name: str,
                     daily_budget: int = 0,
                     billing_event: str = "IMPRESSIONS",
                     optimization_goal: str = "LEAD_GENERATION",
                     targeting: str = "",
                     start_time: str = "",
                     end_time: str = "",
                     status: str = "PAUSED",
                     pixel_id: str = "",
                     page_id: str = "",
                     promoted_object: str = "") -> str:
        payload = {
            "campaign_id": campaign_id,
            "name": name,
            "billing_event": billing_event,
            "optimization_goal": optimization_goal,
            "status": status,
        }
        if daily_budget:
            payload["daily_budget"] = daily_budget * 100
        if targeting:
            payload["targeting"] = targeting
        if start_time:
            payload["start_time"] = start_time
        if end_time:
            payload["end_time"] = end_time
        if promoted_object:
            payload["promoted_object"] = promoted_object
        elif pixel_id:
            payload["promoted_object"] = f'{{"pixel_id":"{pixel_id}","custom_event_type":"LEAD"}}'
        elif page_id:
            payload["promoted_object"] = f'{{"page_id":"{page_id}"}}'
        data = self._post(f"{self._account_path()}/adsets", payload)
        return f"Adset cree — ID: {data.get('id', '?')} | Nom: {name} | Campaign: {campaign_id}"

    def ad_create(self, adset_id: str, name: str, creative_id: str,
                  status: str = "PAUSED") -> str:
        payload = {
            "adset_id": adset_id,
            "name": name,
            "creative": f'{{"creative_id":"{creative_id}"}}',
            "status": status,
        }
        data = self._post(f"{self._account_path()}/ads", payload)
        return f"Ad creee — ID: {data.get('id', '?')} | Nom: {name} | Adset: {adset_id}"

    def creative_create(self, name: str, page_id: str,
                        image_hash: str = "", image_url: str = "",
                        video_id: str = "",
                        message: str = "", headline: str = "",
                        description: str = "", link: str = "",
                        call_to_action: str = "LEARN_MORE") -> str:
        payload = {"name": name}

        # Build object_story_spec
        page_data = f'"page_id":"{page_id}"'

        if video_id:
            # Video ad
            video_data = f'"video_id":"{video_id}"'
            if message:
                video_data += f',"message":"{message}"'
            cta = f'"type":"{call_to_action}"'
            if link:
                cta += f',"value":{{"link":"{link}"}}'
            video_data += f',"call_to_action":{{{cta}}}'
            payload["object_story_spec"] = f'{{{page_data},"video_data":{{{video_data}}}}}'
        elif image_hash or image_url:
            # Image ad
            link_data = ""
            if image_hash:
                link_data = f'"image_hash":"{image_hash}"'
            elif image_url:
                link_data = f'"picture":"{image_url}"'
            if message:
                link_data += f',"message":"{message}"'
            if headline:
                link_data += f',"name":"{headline}"'
            if description:
                link_data += f',"description":"{description}"'
            if link:
                link_data += f',"link":"{link}"'
            link_data += f',"call_to_action":{{"type":"{call_to_action}"}}'
            payload["object_story_spec"] = f'{{{page_data},"link_data":{{{link_data}}}}}'

        data = self._post(f"{self._account_path()}/adcreatives", payload)
        return f"Creative cree — ID: {data.get('id', '?')} | Nom: {name}"

    def image_upload(self, image_url: str) -> str:
        """Upload an image from URL to the ad account."""
        data = self._post(f"{self._account_path()}/adimages", {"url": image_url})
        images = data.get("images", {})
        if images:
            key = list(images.keys())[0]
            img = images[key]
            return f"Image uploadee — hash: {img.get('hash', '?')} | url: {img.get('url', 'N/A')}"
        return f"Image uploadee — response: {data}"

    def video_upload(self, video_url: str, title: str = "") -> str:
        """Upload a video from URL to the ad account."""
        payload = {"file_url": video_url}
        if title:
            payload["title"] = title
        data = self._post(f"{self._account_path()}/advideos", payload)
        return f"Video uploadee — ID: {data.get('id', '?')}"

    def entity_update(self, entity_id: str, updates: dict) -> str:
        """Update any entity (campaign, adset, ad) — pause, activate, rename."""
        data = self._post(f"/{entity_id}", updates)
        return f"Entity {entity_id} mise a jour — {data}"

    def pages_list(self) -> str:
        """List pages accessible by this token."""
        data = self._get("/me/accounts", {"fields": "id,name,instagram_business_account{id,username}", "limit": 50})
        pages = data.get("data", [])
        if not pages:
            return "Aucune page."
        lines = [f"{len(pages)} pages :\n"]
        for p in pages:
            ig = p.get("instagram_business_account", {})
            ig_info = f" | IG: @{ig.get('username', '?')} ({ig.get('id', '?')})" if ig else ""
            lines.append(f"  [{p.get('id', '?')}] {p.get('name', '?')}{ig_info}")
        return "\n".join(lines)

    def audiences_list(self) -> str:
        """List custom audiences."""
        data = self._get(
            f"{self._account_path()}/customaudiences",
            {"fields": "id,name,subtype,approximate_count_lower_bound,approximate_count_upper_bound", "limit": 30}
        )
        audiences = data.get("data", [])
        if not audiences:
            return "Aucune audience custom."
        lines = [f"{len(audiences)} audiences :\n"]
        for a in audiences:
            lower = a.get("approximate_count_lower_bound", "?")
            upper = a.get("approximate_count_upper_bound", "?")
            lines.append(f"  [{a.get('id', '?')}] {a.get('name', '?')} ({a.get('subtype', '?')}) — {lower}-{upper}")
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

    # --- CREATION ---
    elif command == "campaigns.create":
        name = _flag("name")
        if not name:
            return format_error('Usage: nm meta campaigns create --name "Nom" [--objective OUTCOME_LEADS] [--daily-budget 20] [--status PAUSED]')
        return svc.campaign_create(
            name=name,
            objective=_flag("objective") or "OUTCOME_LEADS",
            status=_flag("status") or "PAUSED",
            daily_budget=int(_flag("daily-budget") or "0"),
            lifetime_budget=int(_flag("lifetime-budget") or "0"),
            special_ad_categories=_flag("special-categories") or "",
        )

    elif command == "adsets.create":
        campaign_id = _flag("campaign")
        name = _flag("name")
        if not campaign_id or not name:
            return format_error('Usage: nm meta adsets create --campaign <id> --name "Nom" --daily-budget 20 [--targeting \'{"geo":...}\'] [--pixel <id>] [--page <id>]')
        return svc.adset_create(
            campaign_id=campaign_id, name=name,
            daily_budget=int(_flag("daily-budget") or "0"),
            optimization_goal=_flag("optimization") or "LEAD_GENERATION",
            targeting=_flag("targeting") or "",
            start_time=_flag("start-time") or "",
            end_time=_flag("end-time") or "",
            status=_flag("status") or "PAUSED",
            pixel_id=_flag("pixel") or "",
            page_id=_flag("page") or "",
            promoted_object=_flag("promoted-object") or "",
        )

    elif command == "ads.create":
        adset_id = _flag("adset")
        name = _flag("name")
        creative_id = _flag("creative")
        if not adset_id or not name or not creative_id:
            return format_error('Usage: nm meta ads create --adset <id> --name "Nom" --creative <creative_id>')
        return svc.ad_create(adset_id, name, creative_id, _flag("status") or "PAUSED")

    elif command == "creatives.create":
        name = _flag("name")
        page_id = _flag("page")
        if not name or not page_id:
            return format_error('Usage: nm meta creatives create --name "Nom" --page <page_id> [--video-id <id>] [--image-url <url>] [--message "..."] [--headline "..."] [--link "..."]')
        return svc.creative_create(
            name=name, page_id=page_id,
            image_hash=_flag("image-hash") or "",
            image_url=_flag("image-url") or "",
            video_id=_flag("video-id") or "",
            message=_flag("message") or "",
            headline=_flag("headline") or "",
            description=_flag("description") or "",
            link=_flag("link") or "",
            call_to_action=_flag("cta") or "LEARN_MORE",
        )

    elif command == "images.upload":
        url = _flag("url") or (args[0] if args else "")
        if not url:
            return format_error("Usage: nm meta images upload --url <image_url>")
        return svc.image_upload(url)

    elif command == "videos.upload":
        url = _flag("url") or (args[0] if args else "")
        if not url:
            return format_error("Usage: nm meta videos upload --url <video_url> [--title 'Titre']")
        return svc.video_upload(url, _flag("title") or "")

    elif command == "entity.update":
        entity_id = args[0] if args else ""
        if not entity_id:
            return format_error('Usage: nm meta entity update <entity_id> --status ACTIVE|PAUSED [--name "..."]')
        flags = {}
        for key in ["status", "name", "daily_budget"]:
            val = _flag(key)
            if val:
                flags[key] = val
        return svc.entity_update(entity_id, flags)

    elif command == "pages.list":
        return svc.pages_list()

    elif command == "audiences.list":
        return svc.audiences_list()

    elif command == "pixel.stats":
        pixel_id = _flag("pixel") or args[0] if args else ""
        if not pixel_id:
            return format_error("Usage: nm meta pixel stats <pixel_id>")
        return svc.pixel_stats(pixel_id)

    elif command == "pixel.diagnostics":
        pixel_id = _flag("pixel") or args[0] if args else ""
        if not pixel_id:
            return format_error("Usage: nm meta pixel diagnostics <pixel_id>")
        return svc.pixel_diagnostics(pixel_id)

    elif command == "pixel.events":
        pixel_id = _flag("pixel") or args[0] if args else ""
        if not pixel_id:
            return format_error("Usage: nm meta pixel events <pixel_id>")
        limit = int(_flag("limit") or "20")
        return svc.pixel_events(pixel_id, limit)

    else:
        return format_error(f"Commande Meta inconnue: {command}")
