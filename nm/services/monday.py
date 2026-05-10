from __future__ import annotations
import json
from datetime import date, datetime
import requests
from nm.core.output import format_leads_list, format_lead_detail, format_error

MONDAY_API_URL = "https://api.monday.com/v2"


class MondayService:
    def __init__(self, api_token: str, board_id: int | None = None):
        self._token = api_token
        self._board_id = board_id
        self._headers = {
            "Authorization": api_token,
            "Content-Type": "application/json",
        }

    def _query(self, query: str, variables: dict | None = None) -> dict:
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = requests.post(MONDAY_API_URL, headers=self._headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise RuntimeError(f"Monday API error: {data['errors']}")
        return data["data"]

    def _parse_columns(self, column_values: list) -> dict:
        result = {}
        for col in column_values:
            result[col["id"]] = col.get("text", "")
        return result

    def leads_list(self) -> str:
        data = self._query(
            '{ boards(ids: [%d]) { items_page(limit: 50) { items { id name column_values { id text } } } } }'
            % self._board_id
        )
        items = data["boards"][0]["items_page"]["items"]
        if not items:
            return format_leads_list([])

        leads = []
        today = date.today()
        for item in items:
            cols = self._parse_columns(item["column_values"])
            days = "?"
            for key in cols:
                if "date" in key and cols[key]:
                    try:
                        d = datetime.strptime(cols[key], "%Y-%m-%d").date()
                        days = (today - d).days
                    except ValueError:
                        pass
                    break
            leads.append({
                "id": item["id"],
                "name": item["name"],
                "status": cols.get("status", "N/A"),
                "days": days,
                "phone": cols.get("phone", "N/A"),
                "last_contact": cols.get("last_contact"),
            })
        return format_leads_list(leads)

    def leads_get(self, item_id: str) -> str:
        data = self._query(
            '{ items(ids: [%s]) { id name column_values { id text } updates(limit: 5) { text_body created_at } } }'
            % item_id
        )
        items = data.get("items", [])
        if not items:
            return format_error(f"Lead {item_id} non trouve")
        item = items[0]
        cols = self._parse_columns(item["column_values"])
        lead = {
            "id": item["id"],
            "name": item["name"],
            "status": cols.get("status", "N/A"),
            "phone": cols.get("phone", "N/A"),
            "email": cols.get("email", "N/A"),
            "company": cols.get("company", "N/A"),
            "notes": [u["text_body"] for u in item.get("updates", [])],
        }
        return format_lead_detail(lead)

    def leads_update(self, item_id: str, status: str) -> str:
        status_column_id = "status"
        value = json.dumps({"label": status})
        self._query(
            'mutation { change_column_value(board_id: %d, item_id: %s, column_id: "%s", value: %s) { id } }'
            % (self._board_id, item_id, status_column_id, json.dumps(value))
        )
        return f"Lead {item_id} mis a jour -> {status}"

    def leads_note(self, item_id: str, text: str) -> str:
        self._query(
            'mutation { create_update(item_id: %s, body: %s) { id } }'
            % (item_id, json.dumps(text))
        )
        return f"Note ajoutee sur lead {item_id}"

    def leads_next_actions(self) -> str:
        return self.leads_list()


def handle_monday(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials
    creds = get_credentials("monday")
    config = profile.get_service_config("monday") or {}
    boards = config.get("boards", [])
    board_id = boards[0] if boards else None

    svc = MondayService(api_token=creds["api_token"], board_id=board_id)

    if command == "leads.list":
        return svc.leads_list()
    elif command == "leads.get":
        if not args:
            return format_error("Usage: nm monday leads get <item_id>")
        return svc.leads_get(args[0])
    elif command == "leads.update":
        item_id = args[0] if args else None
        status = None
        for i, a in enumerate(args):
            if a == "--status" and i + 1 < len(args):
                status = args[i + 1]
        if not item_id or not status:
            return format_error('Usage: nm monday leads update <item_id> --status "Status"')
        allowed = config.get("allowed_statuses", [])
        if allowed and status not in allowed:
            return format_error(f"Statut '{status}' non autorise. Autorises: {', '.join(allowed)}")
        return svc.leads_update(item_id, status)
    elif command == "leads.note":
        if len(args) < 2:
            return format_error('Usage: nm monday leads note <item_id> "texte"')
        return svc.leads_note(args[0], " ".join(args[1:]))
    elif command == "leads.next-actions":
        return svc.leads_next_actions()
    else:
        return format_error(f"Commande Monday inconnue: {command}")
