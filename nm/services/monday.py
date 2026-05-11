from __future__ import annotations
import json
from datetime import date, datetime
import requests
from nm.core.output import (
    format_leads_list, format_lead_detail, format_error,
    format_tasks_list, format_task_detail, format_enrollment_detail,
    format_item_created, format_deals_list, format_deal_detail,
    format_pipeline_summary, format_company_detail, format_meetings_list,
    format_calls_list_detailed,
)

MONDAY_API_URL = "https://api.monday.com/v2"


class MondayService:
    DEFAULT_COLUMNS = {
        "status": "status",
        "phone": "phone",
        "email": "email",
        "company": "company",
        "last_contact": "last_contact",
    }

    def __init__(self, api_token: str, boards: dict | None = None,
                 column_maps: dict | None = None, config: dict | None = None):
        self._token = api_token
        self._boards = boards or {}
        self._column_maps = column_maps or {}
        self._config = config or {}
        self._headers = {
            "Authorization": api_token,
            "Content-Type": "application/json",
        }

    def _board_id(self, name: str) -> int:
        bid = self._boards.get(name)
        if not bid:
            raise RuntimeError(f"Board '{name}' non configure dans le profil")
        return int(bid)

    def _col(self, board_name: str, field: str) -> str:
        maps = self._column_maps.get(board_name, {})
        return maps.get(field, field)

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
            text = col.get("text") or ""
            raw_value = col.get("value") or ""
            # Phone columns return masked text (e.g. +336****1432)
            # Extract the real number from the value JSON
            if text and "****" in text and raw_value:
                try:
                    val = json.loads(raw_value)
                    if isinstance(val, dict) and "phone" in val:
                        text = val["phone"]
                except (json.JSONDecodeError, TypeError):
                    pass
            result[col["id"]] = text
            # Store raw value for people columns (needed for owner filtering)
            result[f"_raw_{col['id']}"] = raw_value
        return result

    def _person_ids_in_column(self, cols: dict, col_id: str) -> list[int]:
        """Extract person IDs from a people column raw value."""
        raw = cols.get(f"_raw_{col_id}", "")
        if not raw:
            return []
        try:
            val = json.loads(raw)
            if isinstance(val, dict):
                return [p["id"] for p in val.get("personsAndTeams", [])
                        if p.get("kind") == "person"]
        except (json.JSONDecodeError, TypeError, KeyError):
            pass
        return []

    def _create_item(self, board_name: str, item_name: str,
                     column_values: dict, group_id: str = "topics") -> dict:
        bid = self._board_id(board_name)
        values_json = json.dumps(json.dumps(column_values))
        query = (
            'mutation { create_item(board_id: %d, group_id: "%s", '
            'item_name: %s, column_values: %s) { id name } }'
            % (bid, group_id, json.dumps(item_name), values_json)
        )
        data = self._query(query)
        return data["create_item"]

    def _update_columns(self, board_name: str, item_id: str,
                        column_values: dict) -> dict:
        bid = self._board_id(board_name)
        values_json = json.dumps(json.dumps(column_values))
        query = (
            'mutation { change_multiple_column_values(board_id: %d, '
            'item_id: %s, column_values: %s) { id } }'
            % (bid, int(item_id), values_json)
        )
        data = self._query(query)
        return data["change_multiple_column_values"]

    def _add_note(self, item_id: str, text: str) -> dict:
        query = (
            'mutation { create_update(item_id: %s, body: %s) { id } }'
            % (item_id, json.dumps(text))
        )
        return self._query(query)

    def _list_items(self, board_name: str, limit: int = 50,
                    order_by_column: str | None = None,
                    order_direction: str = "desc",
                    paginate_all: bool = False) -> list:
        bid = self._board_id(board_name)
        page_size = min(limit, 100)
        qp = ""
        if order_by_column:
            col_id = self._col(board_name, order_by_column)
            qp = (', query_params: {order_by: [{column_id: "%s", direction: %s}]}'
                  % (col_id, order_direction))

        all_items = []
        cursor = None
        while True:
            if cursor:
                data = self._query(
                    '{ next_items_page(limit: %d, cursor: "%s") '
                    '{ cursor items { id name column_values { id text value } } } }'
                    % (page_size, cursor)
                )
                page = data["next_items_page"]
            else:
                data = self._query(
                    '{ boards(ids: [%d]) { items_page(limit: %d%s) '
                    '{ cursor items { id name column_values { id text value } } } } }'
                    % (bid, page_size, qp)
                )
                page = data["boards"][0]["items_page"]

            items = page.get("items", [])
            all_items.extend(items)
            cursor = page.get("cursor")

            if not paginate_all or not cursor or len(all_items) >= limit:
                break

        return all_items[:limit] if not paginate_all else all_items

    def _get_item(self, item_id: str) -> dict:
        data = self._query(
            '{ items(ids: [%s]) { id name board { id } '
            'column_values { id text value } '
            'updates(limit: 5) { text_body created_at } } }'
            % item_id
        )
        items = data.get("items", [])
        if not items:
            raise RuntimeError(f"Item {item_id} non trouve")
        return items[0]

    # --- GENERIC (cross-board) ---

    def search(self, query: str, limit: int = 20) -> str:
        """Search items across all boards by name."""
        data = self._query(
            '{ items_page_by_column_values(limit: %d, board_id: 0, columns: [{column_id: "name", column_values: ["%s"]}]) '
            '{ items { id name board { id name } column_values { id text } } } }'
            % (limit, query.replace('"', '\\"'))
        )
        # Fallback: use complexity-friendly search
        if "errors" in str(data):
            data = self._query(
                '{ boards(limit: 50, state: active) { id name items_page(limit: 5, '
                'query_params: {rules: [{column_id: "name", compare_value: ["%s"], '
                'operator: contains_text}]}) { items { id name } } } }'
                % query.replace('"', '\\"')
            )
            results = []
            for board in data.get("boards", []):
                for item in board.get("items_page", {}).get("items", []):
                    results.append(f"  #{item['id']} {item['name']} | Board: {board['name']}")
            if not results:
                return f"Aucun resultat pour '{query}'"
            return f"{len(results)} resultats pour '{query}' :\n\n" + "\n".join(results)

        items = data.get("items_page_by_column_values", {}).get("items", [])
        if not items:
            return f"Aucun resultat pour '{query}'"
        lines = [f"{len(items)} resultats :\n"]
        for item in items:
            board = item.get("board", {})
            lines.append(f"  #{item['id']} {item['name']} | Board: {board.get('name', '?')} ({board.get('id', '?')})")
        return "\n".join(lines)

    def boards_list(self, limit: int = 50) -> str:
        """List all active boards."""
        data = self._query(
            '{ boards(limit: %d, state: active, order_by: used_at) '
            '{ id name items_count board_kind } }' % limit
        )
        boards = data.get("boards", [])
        if not boards:
            return "Aucun board."
        lines = [f"{len(boards)} boards :\n"]
        for b in boards:
            lines.append(
                f"  [{b.get('id')}] {b.get('name')} — {b.get('items_count', '?')} items ({b.get('board_kind', '?')})"
            )
        return "\n".join(lines)

    def board_info(self, board_id: int) -> str:
        """Get board structure (columns, groups)."""
        data = self._query(
            '{ boards(ids: [%d]) { id name columns { id title type settings_str } '
            'groups { id title } } }' % board_id
        )
        boards = data.get("boards", [])
        if not boards:
            return f"Board {board_id} non trouve"
        b = boards[0]
        lines = [f"Board: {b.get('name')} ({b.get('id')})\n"]
        lines.append("COLONNES :")
        for col in b.get("columns", []):
            lines.append(f"  [{col['id']}] {col['title']} ({col['type']})")
        lines.append("\nGROUPES :")
        for grp in b.get("groups", []):
            lines.append(f"  [{grp['id']}] {grp['title']}")
        return "\n".join(lines)

    def generic_items_list(self, board_id: int, limit: int = 25,
                           group_id: str = "") -> str:
        """List items from any board by ID."""
        if group_id:
            data = self._query(
                '{ boards(ids: [%d]) { groups(ids: ["%s"]) { items_page(limit: %d) '
                '{ items { id name column_values { id text } } } } } }'
                % (board_id, group_id, limit)
            )
            grps = data["boards"][0].get("groups", [])
            items = grps[0]["items_page"]["items"] if grps else []
        else:
            data = self._query(
                '{ boards(ids: [%d]) { items_page(limit: %d) '
                '{ items { id name column_values { id text } } } } }'
                % (board_id, limit)
            )
            items = data["boards"][0]["items_page"]["items"]

        if not items:
            return f"Aucun item dans le board {board_id}."
        lines = [f"{len(items)} items :\n"]
        for item in items:
            cols = self._parse_columns(item.get("column_values", []))
            status = cols.get("status", cols.get("color", ""))
            lines.append(f"  #{item['id']} {item['name']}" + (f" | {status}" if status else ""))
        return "\n".join(lines)

    def generic_item_create(self, board_id: int, item_name: str,
                            group_id: str = "topics",
                            column_values: dict | None = None) -> str:
        """Create an item on any board."""
        values_json = json.dumps(json.dumps(column_values or {}))
        query = (
            'mutation { create_item(board_id: %d, group_id: "%s", '
            'item_name: %s, column_values: %s) { id name } }'
            % (board_id, group_id, json.dumps(item_name), values_json)
        )
        data = self._query(query)
        item = data["create_item"]
        return f"Item cree : #{item['id']} — {item['name']} (board {board_id})"

    def generic_item_update(self, board_id: int, item_id: str,
                            column_values: dict) -> str:
        """Update columns on any item."""
        values_json = json.dumps(json.dumps(column_values))
        query = (
            'mutation { change_multiple_column_values(board_id: %d, '
            'item_id: %s, column_values: %s) { id } }'
            % (board_id, int(item_id), values_json)
        )
        self._query(query)
        return f"Item {item_id} mis a jour (board {board_id})"

    def group_create(self, board_id: int, group_name: str) -> str:
        """Create a group on a board."""
        data = self._query(
            'mutation { create_group(board_id: %d, group_name: %s) { id title } }'
            % (board_id, json.dumps(group_name))
        )
        grp = data["create_group"]
        return f"Groupe cree : [{grp['id']}] {grp['title']} (board {board_id})"

    def column_create(self, board_id: int, title: str,
                      column_type: str = "text") -> str:
        """Create a column on a board."""
        data = self._query(
            'mutation { create_column(board_id: %d, title: %s, column_type: %s) { id title type } }'
            % (board_id, json.dumps(title), column_type)
        )
        col = data["create_column"]
        return f"Colonne creee : [{col['id']}] {col['title']} ({col['type']}) (board {board_id})"

    def item_note(self, item_id: str, text: str) -> str:
        """Add a note/update to any item."""
        self._add_note(item_id, text)
        return f"Note ajoutee sur item {item_id}"

    # --- DEALS ---

    def _board_label(self, board_name: str) -> str:
        labels = {
            "abonnements": "Abonnements",
            "renewal": "Renewal",
            "machine": "Machine",
        }
        return labels.get(board_name, board_name)

    def _deal_stage_col(self, board_name: str) -> str:
        return self._col(board_name, "deal_stage")

    def deals_list(self, board_name: str, group: str | None = None,
                   owner_filter: str | None = None,
                   limit: int = 500) -> str:
        bid = self._board_id(board_name)
        people_ids = self._config.get("people_ids", {})

        if group:
            query = (
                '{ boards(ids: [%d]) { groups(ids: ["%s"]) { items_page(limit: 100) '
                '{ cursor items { id name column_values { id text value } } } } } }'
                % (bid, group)
            )
            data = self._query(query)
            grps = data["boards"][0].get("groups", [])
            items = grps[0]["items_page"]["items"] if grps else []
            cursor = grps[0]["items_page"].get("cursor") if grps else None
            # Paginate within group
            while cursor and len(items) < limit:
                data = self._query(
                    '{ next_items_page(limit: 100, cursor: "%s") '
                    '{ cursor items { id name column_values { id text value } } } }'
                    % cursor
                )
                page = data["next_items_page"]
                items.extend(page.get("items", []))
                cursor = page.get("cursor")
        else:
            items = self._list_items(board_name, limit, paginate_all=True)

        stage_col = self._deal_stage_col(board_name)
        arr_col = self._col(board_name, "deal_arr")
        close_col = (self._col(board_name, "close_date")
                     if board_name != "renewal"
                     else self._col(board_name, "renewal_date"))
        owner_col = self._col(board_name, "deal_owner")

        # Resolve owner filter to person ID
        target_owner_id = None
        if owner_filter:
            target_owner_id = people_ids.get(owner_filter)
            if not target_owner_id:
                # Try to match by name substring
                owner_filter_lower = owner_filter.lower()

        deals = []
        for item in items:
            cols = self._parse_columns(item["column_values"])

            # Filter by owner (people column — client-side filtering)
            if owner_filter:
                if target_owner_id:
                    person_ids = self._person_ids_in_column(cols, owner_col)
                    if target_owner_id not in person_ids:
                        continue
                else:
                    owner_text = cols.get(owner_col, "").lower()
                    if owner_filter_lower not in owner_text:
                        continue

            ns = cols.get(self._col(board_name, "next_step"), "")
            nsd = cols.get(self._col(board_name, "next_step_date"), "")
            deals.append({
                "id": item["id"],
                "name": item["name"],
                "stage": cols.get(stage_col, "N/A"),
                "arr": cols.get(arr_col, "0"),
                "close_date": cols.get(close_col, "N/A"),
                "owner": cols.get(owner_col, ""),
                "next_step": ns,
                "next_step_date": nsd,
            })
        return format_deals_list(deals, self._board_label(board_name))

    def deals_get(self, item_id: str) -> str:
        item = self._get_item(item_id)
        board_id = str(item.get("board", {}).get("id", ""))
        cols = self._parse_columns(item["column_values"])

        # Detect which board
        board_name = "abonnements"
        for name, bid in self._boards.items():
            if str(bid) == board_id:
                board_name = name
                break

        stage_col = self._deal_stage_col(board_name)
        close_key = "close_date" if board_name != "renewal" else "renewal_date"

        deal = {
            "id": item["id"],
            "name": item["name"],
            "board": self._board_label(board_name),
            "stage": cols.get(stage_col, "N/A"),
            "contract_status": cols.get(self._col(board_name, "contract_status"), "N/A"),
            "arr": cols.get(self._col(board_name, "deal_arr"), "0"),
            "mrr": cols.get(self._col(board_name, "deal_mrr"), "0"),
            "tcv": cols.get(self._col(board_name, "deal_tcv"), "0"),
            "terms": cols.get(self._col(board_name, "terms"), "N/A"),
            "close_date": cols.get(self._col(board_name, close_key), "N/A"),
            "contract_end_date": cols.get(self._col(board_name, "contract_end_date"), "N/A"),
            "payment_date": cols.get(self._col(board_name, "payment_date"), "N/A"),
            "owner": cols.get(self._col(board_name, "deal_owner"), "N/A"),
            "company": cols.get(self._col(board_name, "company"), "N/A"),
            "next_step": cols.get(self._col(board_name, "next_step"), ""),
            "next_step_date": cols.get(self._col(board_name, "next_step_date"), ""),
            "notes": [u["text_body"] for u in item.get("updates", [])],
        }
        return format_deal_detail(deal)

    def deals_pipeline(self, board_name: str,
                       owner_filter: str | None = None) -> str:
        items = self._list_items(board_name, limit=500, paginate_all=True)
        stage_col = self._deal_stage_col(board_name)
        arr_col = self._col(board_name, "deal_arr")
        owner_col = self._col(board_name, "deal_owner")
        people_ids = self._config.get("people_ids", {})

        target_owner_id = None
        if owner_filter:
            target_owner_id = people_ids.get(owner_filter)
            if not target_owner_id:
                owner_filter_lower = owner_filter.lower()

        stages: dict = {}
        total_arr = 0.0
        count = 0
        for item in items:
            cols = self._parse_columns(item["column_values"])

            if owner_filter:
                if target_owner_id:
                    person_ids = self._person_ids_in_column(cols, owner_col)
                    if target_owner_id not in person_ids:
                        continue
                else:
                    owner_text = cols.get(owner_col, "").lower()
                    if owner_filter_lower not in owner_text:
                        continue

            stage = cols.get(stage_col, "Unknown")
            try:
                arr = float(cols.get(arr_col, "0") or "0")
            except (ValueError, TypeError):
                arr = 0.0
            if stage not in stages:
                stages[stage] = {"count": 0, "arr": 0.0}
            stages[stage]["count"] += 1
            stages[stage]["arr"] += arr
            total_arr += arr
            count += 1

        label = self._board_label(board_name)
        if owner_filter:
            label += f" ({owner_filter})"
        return format_pipeline_summary(stages, label, total_arr, count)

    # --- COMPANIES ---

    def companies_get(self, item_id: str) -> str:
        item = self._get_item(item_id)
        cols = self._parse_columns(item["column_values"])
        company = {
            "id": item["id"],
            "name": item["name"],
            "status": cols.get(self._col("companies", "status"), "N/A"),
            "phone": cols.get(self._col("companies", "phone"), "N/A"),
            "city": cols.get(self._col("companies", "city"), "N/A"),
            "country": cols.get(self._col("companies", "country"), "N/A"),
            "cs": cols.get(self._col("companies", "cs"), "N/A"),
            "superadmin_matching": cols.get(self._col("companies", "superadmin_matching"), "N/A"),
        }
        return format_company_detail(company)

    # --- SEARCH ---

    def _normalize_search(self, query: str) -> list[str]:
        """Return search variants: original + stripped accents."""
        import unicodedata
        stripped = "".join(
            c for c in unicodedata.normalize("NFD", query)
            if unicodedata.category(c) != "Mn"
        )
        variants = [query]
        if stripped != query:
            variants.append(stripped)
        return variants

    def _search_board(self, board_name: str, query: str,
                      limit: int = 20) -> list:
        bid = self._boards.get(board_name)
        if not bid:
            return []
        seen = set()
        all_items = []
        for variant in self._normalize_search(query):
            data = self._query(
                '{ boards(ids: [%d]) { items_page(limit: %d, query_params: '
                '{rules: [{column_id: "name", compare_value: ["%s"], '
                'operator: contains_text}]}) '
                '{ items { id name column_values { id text value } } } } }'
                % (int(bid), limit, variant.replace('"', '\\"'))
            )
            for item in data["boards"][0]["items_page"]["items"]:
                if item["id"] not in seen:
                    seen.add(item["id"])
                    all_items.append(item)
        return all_items

    def deals_search(self, query: str) -> str:
        results = []
        for board_name in ("abonnements", "renewal", "machine"):
            if board_name not in self._boards:
                continue
            items = self._search_board(board_name, query)
            stage_col = self._deal_stage_col(board_name)
            arr_col = self._col(board_name, "deal_arr")
            contacts_col = self._col(board_name, "contacts")
            company_col = self._col(board_name, "company")
            for item in items:
                cols = self._parse_columns(item["column_values"])
                results.append({
                    "id": item["id"],
                    "name": item["name"],
                    "board": self._board_label(board_name),
                    "stage": cols.get(stage_col, "N/A"),
                    "arr": cols.get(arr_col, "0"),
                    "company": cols.get(company_col, ""),
                    "contacts": cols.get(contacts_col, ""),
                })
        if not results:
            return f"Aucun deal trouve pour '{query}'"
        lines = [f"{len(results)} deal(s) trouve(s) :\n"]
        for r in results:
            line = (f"#{r['id']} {r['name']} | {r['board']} "
                    f"| Stage: {r['stage']} | ARR: {r['arr']} EUR")
            if r.get("company"):
                line += f" | Company: {r['company']}"
            if r.get("contacts"):
                line += f" | Contact: {r['contacts']}"
            lines.append(line)
        return "\n".join(lines)

    def companies_search(self, query: str) -> str:
        items = self._search_board("companies", query)
        if not items:
            return f"Aucune company trouvee pour '{query}'"
        lines = [f"{len(items)} company(s) trouvee(s) :\n"]
        for item in items:
            cols = self._parse_columns(item["column_values"])
            contacts_col = self._col("companies", "contacts")
            line = (f"#{item['id']} {item['name']} "
                    f"| Statut: {cols.get(self._col('companies', 'status'), 'N/A')}")
            contacts = cols.get(contacts_col, "")
            if contacts:
                line += f" | Contacts: {contacts}"
            lines.append(line)
        return "\n".join(lines)

    # --- CALLS LIST (read-only for managers) ---

    def calls_list(self, owner_filter: str | None = None,
                   date_filter: str | None = None,
                   days: int | None = None,
                   limit: int = 50) -> str:
        items = self._list_items("calls", limit, order_by_column="date")
        people_ids = self._config.get("people_ids", {})

        # Resolve date filters
        if date_filter == "today":
            date_filter = date.today().isoformat()
        if days and not date_filter:
            from datetime import timedelta
            cutoff = (date.today() - timedelta(days=days)).isoformat()
        else:
            cutoff = None

        calls = []
        for item in items:
            cols = self._parse_columns(item["column_values"])
            call_date = cols.get(self._col("calls", "date"), "")

            # Filter by date
            if date_filter and call_date and not call_date.startswith(date_filter):
                continue
            if cutoff and call_date and call_date < cutoff:
                continue

            # Filter by owner (people column)
            if owner_filter:
                sdr_col = self._col("calls", "sdr")
                target_id = str(people_ids.get(owner_filter, ""))
                if target_id:
                    sdr_value = next(
                        (c.get("value", "") for c in item["column_values"]
                         if c["id"] == sdr_col), ""
                    )
                    if target_id not in str(sdr_value):
                        continue

            calls.append({
                "id": item["id"],
                "name": item["name"],
                "date": call_date or "N/A",
                "outcome": cols.get(self._col("calls", "call_outcome"), "N/A"),
                "duration": cols.get(self._col("calls", "duree"), "?"),
            })
        return format_calls_list_detailed(calls)

    # --- MEETINGS LIST (read-only for managers) ---

    def meetings_list(self, date_filter: str | None = None,
                      days: int | None = None,
                      limit: int = 50) -> str:
        items = self._list_items("meetings", limit, order_by_column="start_date")

        # Resolve date filters
        if date_filter == "today":
            date_filter = date.today().isoformat()
        if days and not date_filter:
            from datetime import timedelta
            cutoff = (date.today() - timedelta(days=days)).isoformat()
        else:
            cutoff = None

        meetings = []
        for item in items:
            cols = self._parse_columns(item["column_values"])
            meeting_date = cols.get(self._col("meetings", "start_date"), "")

            if date_filter and meeting_date and not meeting_date.startswith(date_filter):
                continue
            if cutoff and meeting_date and meeting_date < cutoff:
                continue

            meetings.append({
                "id": item["id"],
                "name": item["name"],
                "title": cols.get(self._col("meetings", "titre"), item["name"]),
                "date": meeting_date or "N/A",
                "type": cols.get(self._col("meetings", "type"), "N/A"),
                "status": cols.get(self._col("meetings", "status"), "N/A"),
                "people": cols.get(self._col("meetings", "people"), ""),
            })
        return format_meetings_list(meetings)

    # --- LEADS (FR Leads + Contacts) ---

    def _detect_lead_board(self, item_id: str) -> str:
        item = self._get_item(item_id)
        board_id = item.get("board", {}).get("id")
        if str(board_id) == str(self._boards.get("fr_leads")):
            return "fr_leads"
        elif str(board_id) == str(self._boards.get("contacts")):
            return "contacts"
        return "fr_leads"

    def leads_list(self, board_name: str = "fr_leads") -> str:
        items = self._list_items(board_name)
        if not items:
            return format_leads_list([])

        leads = []
        today = date.today()
        lc_col = self._col(board_name, "last_call_date") if board_name == "fr_leads" else self._col(board_name, "next_step_date")
        for item in items:
            cols = self._parse_columns(item["column_values"])
            days = "?"
            lc = cols.get(lc_col, "")
            if lc:
                try:
                    d = datetime.strptime(lc, "%Y-%m-%d").date()
                    days = (today - d).days
                except ValueError:
                    pass
            leads.append({
                "id": item["id"],
                "name": item["name"],
                "status": cols.get(self._col(board_name, "status"), "N/A"),
                "days": days,
                "phone": cols.get(self._col(board_name, "phone"), "N/A"),
                "last_contact": lc or None,
            })
        return format_leads_list(leads)

    def leads_get(self, item_id: str) -> str:
        item = self._get_item(item_id)
        board_id = item.get("board", {}).get("id")
        board_name = "fr_leads"
        if str(board_id) == str(self._boards.get("contacts")):
            board_name = "contacts"

        cols = self._parse_columns(item["column_values"])
        lead = {
            "id": item["id"],
            "name": item["name"],
            "board": board_name,
            "status": cols.get(self._col(board_name, "status"), "N/A"),
            "phone": cols.get(self._col(board_name, "phone"), "N/A"),
            "email": cols.get(self._col(board_name, "email"), "N/A"),
            "company": cols.get(self._col(board_name, "company"), "N/A"),
            "notes": [u["text_body"] for u in item.get("updates", [])],
        }
        return format_lead_detail(lead)

    def leads_update(self, item_id: str, column_values: dict,
                     board_name: str | None = None) -> str:
        if not board_name:
            board_name = self._detect_lead_board(item_id)
        mapped = {}
        for key, value in column_values.items():
            col_id = self._col(board_name, key)
            mapped[col_id] = value
        self._update_columns(board_name, item_id, mapped)
        return f"Lead {item_id} mis a jour ({board_name})"

    def leads_note(self, item_id: str, text: str) -> str:
        self._add_note(item_id, text)
        return f"Note ajoutee sur lead {item_id}"

    def leads_next_actions(self) -> str:
        return self.leads_list("fr_leads")

    def leads_create(self, name: str, column_values: dict,
                     board_name: str = "fr_leads") -> str:
        mapped = {}
        for key, value in column_values.items():
            col_id = self._col(board_name, key)
            mapped[col_id] = value
        item = self._create_item(board_name, name, mapped)
        return format_item_created("Lead", item["id"], name)

    def leads_search(self, query: str) -> str:
        results = []
        for board_name in ("fr_leads", "contacts"):
            bid = self._boards.get(board_name)
            if not bid:
                continue
            data = self._query(
                '{ boards(ids: [%d]) { items_page(limit: 20, query_params: '
                '{rules: [{column_id: "name", compare_value: ["%s"], '
                'operator: contains_text}]}) '
                '{ items { id name column_values { id text } } } } }'
                % (bid, query.replace('"', '\\"'))
            )
            items = data["boards"][0]["items_page"]["items"]
            for item in items:
                cols = self._parse_columns(item["column_values"])
                results.append({
                    "id": item["id"],
                    "name": item["name"],
                    "board": board_name,
                    "status": cols.get(self._col(board_name, "status"), "N/A"),
                    "phone": cols.get(self._col(board_name, "phone"), "N/A"),
                })
        if not results:
            return f"Aucun lead trouve pour '{query}'"
        lines = [f"{len(results)} lead(s) trouve(s) :\n"]
        for r in results:
            lines.append(f"#{r['id']} {r['name']} | {r['board']} | Statut: {r['status']} | Tel: {r['phone']}")
        return "\n".join(lines)

    # --- ENROLLMENTS ---

    def enrollment_create(self, lead_id: str, lead_name: str,
                          board_source: str, sequence_id: str) -> str:
        people_ids = self._config.get("people_ids", {})
        sophie_id = people_ids.get("sophie", 103430792)
        today_str = date.today().isoformat()

        cols = {
            self._col("enrollments", "statut"): {"label": "Active"},
            self._col("enrollments", "current_step"): "1",
            self._col("enrollments", "step_name"): "J1 -- Appel 1",
            self._col("enrollments", "enrolled_date"): {"date": today_str},
            self._col("enrollments", "total_attempts"): "0",
            self._col("enrollments", "board_source"): {"label": board_source},
            self._col("enrollments", "sdr"): {
                "personsAndTeams": [{"id": sophie_id, "kind": "person"}]
            },
            self._col("enrollments", "source_item_id"): lead_id,
        }

        item = self._create_item("enrollments", lead_name, cols)

        # Link to sequence and lead
        enroll_id = item["id"]
        link_cols = {}
        if sequence_id:
            link_cols[self._col("enrollments", "sequence")] = {"item_ids": [int(sequence_id)]}
        link_cols[self._col("enrollments", "lead")] = {"item_ids": [int(lead_id)]}
        if link_cols:
            self._update_columns("enrollments", str(enroll_id), link_cols)

        return format_item_created("Enrollment", enroll_id, lead_name)

    def enrollment_get(self, item_id: str) -> str:
        item = self._get_item(item_id)
        cols = self._parse_columns(item["column_values"])
        enrollment = {
            "id": item["id"],
            "name": item["name"],
            "statut": cols.get(self._col("enrollments", "statut"), "N/A"),
            "current_step": cols.get(self._col("enrollments", "current_step"), "N/A"),
            "step_name": cols.get(self._col("enrollments", "step_name"), "N/A"),
            "total_attempts": cols.get(self._col("enrollments", "total_attempts"), "0"),
            "dernier_canal": cols.get(self._col("enrollments", "dernier_canal"), "N/A"),
            "exit_reason": cols.get(self._col("enrollments", "exit_reason"), ""),
        }
        return format_enrollment_detail(enrollment)

    def enrollment_update(self, item_id: str, column_values: dict) -> str:
        mapped = {}
        for key, value in column_values.items():
            col_id = self._col("enrollments", key)
            mapped[col_id] = value
        self._update_columns("enrollments", item_id, mapped)
        return f"Enrollment {item_id} mis a jour"

    # --- CALLS ---

    def call_log(self, lead_id: str, lead_name: str, call_data: dict) -> str:
        people_ids = self._config.get("people_ids", {})
        sophie_id = people_ids.get("sophie", 103430792)
        today_str = date.today().isoformat()
        now = datetime.now()
        item_name = f"{lead_name} -- {today_str} {now.strftime('%H:%M')}"

        cols = {
            self._col("calls", "date"): {"date": today_str},
            self._col("calls", "heure"): {"hour": now.hour, "minute": now.minute},
            self._col("calls", "sdr"): {
                "personsAndTeams": [{"id": sophie_id, "kind": "person"}]
            },
        }

        # Duration
        if "duration" in call_data:
            cols[self._col("calls", "duree")] = str(call_data["duration"])

        # Phone
        if "phone" in call_data:
            cols[self._col("calls", "phone")] = {
                "phone": call_data["phone"], "countryShortName": "FR"
            }

        # Call type
        if "call_type" in call_data:
            cols[self._col("calls", "call_type")] = {"label": call_data["call_type"]}

        # Call outcome
        if "outcome" in call_data:
            cols[self._col("calls", "call_outcome")] = {"label": call_data["outcome"]}

        # Transcript
        if "transcript_raw" in call_data:
            cols[self._col("calls", "transcript_raw")] = call_data["transcript_raw"]

        if "transcript_ia" in call_data:
            cols[self._col("calls", "transcript_ia")] = call_data["transcript_ia"]

        # AI scoring
        if "note_globale" in call_data:
            cols[self._col("calls", "note_globale")] = call_data["note_globale"]

        if "feedback" in call_data:
            cols[self._col("calls", "feedback_global")] = {"text": call_data["feedback"]}

        if "points_ameliorer" in call_data:
            cols[self._col("calls", "points_ameliorer")] = {"text": call_data["points_ameliorer"]}

        # Prospect scoring
        for field in ("pain_level", "digital_maturity", "business_mindset", "change_friction"):
            if field in call_data:
                cols[self._col("calls", field)] = {"index": call_data[field]}

        # Recording link
        if "lien_call" in call_data:
            cols[self._col("calls", "lien_call")] = call_data["lien_call"]

        item = self._create_item("calls", item_name, cols)
        call_item_id = item["id"]

        # Link to lead
        link_cols = {
            self._col("calls", "linked_contact"): {"item_ids": [int(lead_id)]}
        }
        self._update_columns("calls", str(call_item_id), link_cols)

        return format_item_created("Call", call_item_id, item_name)

    def call_get(self, item_id: str) -> str:
        item = self._get_item(item_id)
        cols = self._parse_columns(item["column_values"])
        return format_lead_detail({
            "id": item["id"],
            "name": item["name"],
            "status": cols.get(self._col("calls", "call_outcome"), "N/A"),
            "phone": cols.get(self._col("calls", "phone"), "N/A"),
            "email": "N/A",
            "company": "N/A",
            "notes": [cols.get(self._col("calls", "transcript_ia"), "")],
        })

    # --- TASKS ---

    def tasks_today(self) -> str:
        items = self._list_items("tasks", limit=100)
        today_str = date.today().isoformat()
        tasks = []
        for item in items:
            cols = self._parse_columns(item["column_values"])
            status = cols.get(self._col("tasks", "status"), "")
            due = cols.get(self._col("tasks", "due_date"), "")
            if status in ("To Do", "Working on it", "") and due and due <= today_str:
                tasks.append({
                    "id": item["id"],
                    "name": item["name"],
                    "type": cols.get(self._col("tasks", "task_type"), "N/A"),
                    "due_date": due,
                    "description": cols.get(self._col("tasks", "description"), ""),
                    "phone": cols.get(self._col("tasks", "telephone"), "N/A"),
                })
        return format_tasks_list(tasks)

    def tasks_get(self, item_id: str) -> str:
        item = self._get_item(item_id)
        cols = self._parse_columns(item["column_values"])
        task = {
            "id": item["id"],
            "name": item["name"],
            "type": cols.get(self._col("tasks", "task_type"), "N/A"),
            "status": cols.get(self._col("tasks", "status"), "N/A"),
            "due_date": cols.get(self._col("tasks", "due_date"), "N/A"),
            "description": cols.get(self._col("tasks", "description"), ""),
            "phone": cols.get(self._col("tasks", "telephone"), "N/A"),
            "notes": [u["text_body"] for u in item.get("updates", [])],
        }
        return format_task_detail(task)

    def tasks_done(self, item_id: str, resultat: str = "Fait") -> str:
        today_str = date.today().isoformat()
        cols = {
            self._col("tasks", "status"): {"index": 1},
            self._col("tasks", "complete_date"): {"date": today_str},
            self._col("tasks", "resultat"): {"label": resultat},
        }
        self._update_columns("tasks", item_id, cols)
        return f"Tache {item_id} terminee -> {resultat}"

    # --- MEETINGS ---

    def meeting_create(self, lead_id: str, lead_name: str,
                       meeting_data: dict) -> str:
        people_ids = self._config.get("people_ids", {})
        theo_id = people_ids.get("theo", 70103039)

        start_date = meeting_data["date"]
        start_time = meeting_data["time"]
        duration = meeting_data.get("duration", 30)

        start_dt = datetime.strptime(f"{start_date} {start_time}", "%Y-%m-%d %H:%M")
        from datetime import timedelta
        end_dt = start_dt + timedelta(minutes=duration)

        day = start_dt.strftime("%d/%m")
        item_name = f"{lead_name} - {day} - Demo - {duration}min"

        cols = {
            self._col("meetings", "status"): {"label": "confirmed"},
            self._col("meetings", "type"): {"label": "Demo"},
            self._col("meetings", "start_date"): {
                "date": start_date,
                "time": start_dt.strftime("%H:%M:00"),
            },
            self._col("meetings", "end_date"): {
                "date": end_dt.strftime("%Y-%m-%d"),
                "time": end_dt.strftime("%H:%M:00"),
            },
            self._col("meetings", "duree"): str(duration),
            self._col("meetings", "titre"): f"Presentation Nextmotion / {lead_name}",
            self._col("meetings", "people"): {
                "personsAndTeams": [{"id": theo_id, "kind": "person"}]
            },
        }

        # Attendees
        attendee_email = meeting_data.get("email", "")
        if attendee_email:
            cols[self._col("meetings", "attendees")] = {
                "text": f"{attendee_email}, theo@nextmotion.net"
            }

        item = self._create_item("meetings", item_name, cols)
        meeting_id = item["id"]

        # Link to lead/contact
        link_cols = {
            self._col("meetings", "contacts_relation"): {"item_ids": [int(lead_id)]}
        }
        self._update_columns("meetings", str(meeting_id), link_cols)

        return format_item_created("Meeting", meeting_id, item_name)


# --- COMMAND HANDLER ---

def handle_monday(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials
    creds = get_credentials("monday")
    config = profile.get_service_config("monday") or {}

    boards = config.get("boards", {})
    # Backwards compat: if boards is a list, use first as fr_leads
    if isinstance(boards, list):
        boards = {"fr_leads": boards[0]} if boards else {}

    column_maps = config.get("column_maps", config.get("column_map", {}))
    # Backwards compat: flat column_map → fr_leads
    if column_maps and not any(isinstance(v, dict) for v in column_maps.values()):
        column_maps = {"fr_leads": column_maps}

    svc = MondayService(
        api_token=creds["api_token"],
        boards=boards,
        column_maps=column_maps,
        config=config,
    )

    # --- Parse args helpers ---
    def get_flag(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == f"--{flag}" and i + 1 < len(args):
                return args[i + 1]
        return None

    def get_json_flags() -> dict:
        """Parse --key value pairs into a dict."""
        result = {}
        i = 0
        while i < len(args):
            if args[i].startswith("--") and i + 1 < len(args):
                key = args[i][2:]
                val = args[i + 1]
                # Try to parse as JSON for complex values
                try:
                    result[key] = json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    result[key] = val
                i += 2
            else:
                i += 1
        return result

    # --- GENERIC ---
    if command == "search":
        if not args:
            return format_error('Usage: nm monday search "terme"')
        limit = int(get_flag("limit") or "20")
        return svc.search(" ".join([a for a in args if not a.startswith("--")]), limit)

    elif command == "boards.list":
        limit = int(get_flag("limit") or "50")
        return svc.boards_list(limit)

    elif command == "board.info":
        board_id = args[0] if args else get_flag("board")
        if not board_id:
            return format_error("Usage: nm monday board info <board_id>")
        return svc.board_info(int(board_id))

    elif command == "board.items":
        board_id = args[0] if args else get_flag("board")
        if not board_id:
            return format_error("Usage: nm monday board items <board_id> [--group <group_id>] [--limit 25]")
        limit = int(get_flag("limit") or "25")
        group_id = get_flag("group") or ""
        return svc.generic_items_list(int(board_id), limit, group_id)

    elif command == "board.create-item":
        board_id = get_flag("board")
        name = get_flag("name")
        if not board_id or not name:
            return format_error('Usage: nm monday board create-item --board <id> --name "Titre" [--group <group_id>] [--col_id value ...]')
        group_id = get_flag("group") or "topics"
        flags = get_json_flags()
        flags.pop("board", None)
        flags.pop("name", None)
        flags.pop("group", None)
        return svc.generic_item_create(int(board_id), name, group_id, flags if flags else None)

    elif command == "board.update-item":
        board_id = get_flag("board")
        item_id = args[0] if args else get_flag("item")
        if not board_id or not item_id:
            return format_error('Usage: nm monday board update-item <item_id> --board <id> --col_id value ...')
        flags = get_json_flags()
        flags.pop("board", None)
        flags.pop("item", None)
        return svc.generic_item_update(int(board_id), item_id, flags)

    elif command == "board.create-group":
        board_id = get_flag("board")
        name = get_flag("name") or (args[0] if args else "")
        if not board_id or not name:
            return format_error('Usage: nm monday board create-group --board <id> --name "Nom du groupe"')
        return svc.group_create(int(board_id), name)

    elif command == "board.create-column":
        board_id = get_flag("board")
        title = get_flag("title") or (args[0] if args else "")
        col_type = get_flag("type") or "text"
        if not board_id or not title:
            return format_error('Usage: nm monday board create-column --board <id> --title "Nom" --type text|status|numbers|date|...')
        return svc.column_create(int(board_id), title, col_type)

    elif command == "board.note":
        if len(args) < 2:
            return format_error('Usage: nm monday board note <item_id> "texte"')
        return svc.item_note(args[0], " ".join(args[1:]))

    # --- DEALS ---
    elif command == "deals.list":
        board = get_flag("board") or "abonnements"
        group = get_flag("group")
        owner = get_flag("owner")
        return svc.deals_list(board, group, owner)

    elif command == "deals.get":
        if not args:
            return format_error("Usage: nm monday deals get <item_id>")
        return svc.deals_get(args[0])

    elif command == "deals.pipeline":
        board = get_flag("board") or "abonnements"
        owner = get_flag("owner")
        return svc.deals_pipeline(board, owner)

    # --- COMPANIES ---
    elif command == "companies.get":
        if not args:
            return format_error("Usage: nm monday companies get <item_id>")
        return svc.companies_get(args[0])

    elif command == "companies.search":
        if not args:
            return format_error('Usage: nm monday companies search "nom"')
        return svc.companies_search(" ".join(args))

    # --- DEALS SEARCH ---
    elif command == "deals.search":
        if not args:
            return format_error('Usage: nm monday deals search "nom"')
        return svc.deals_search(" ".join(args))

    # --- CALLS LIST ---
    elif command == "calls.list":
        owner = get_flag("owner")
        date_filter = get_flag("date")
        days_str = get_flag("days")
        days = int(days_str) if days_str else None
        return svc.calls_list(owner, date_filter, days)

    # --- MEETINGS LIST ---
    elif command == "meetings.list":
        date_filter = get_flag("date")
        days_str = get_flag("days")
        days = int(days_str) if days_str else None
        return svc.meetings_list(date_filter, days)

    # --- LEADS ---
    elif command == "leads.list":
        board = get_flag("board") or "fr_leads"
        return svc.leads_list(board)

    elif command == "leads.get":
        if not args:
            return format_error("Usage: nm monday leads get <item_id>")
        return svc.leads_get(args[0])

    elif command == "leads.update":
        item_id = args[0] if args else None
        if not item_id:
            return format_error('Usage: nm monday leads update <item_id> --status "Status" [--key value ...]')
        flags = get_json_flags()
        if not flags:
            return format_error('Usage: nm monday leads update <item_id> --status "Status"')

        # Validate status if provided
        if "status" in flags:
            status_val = flags["status"]
            allowed = config.get("allowed_statuses", {})
            if isinstance(allowed, dict):
                board_name = get_flag("board")
                if not board_name:
                    board_name = svc._detect_lead_board(item_id)
                board_allowed = allowed.get(board_name, [])
                if board_allowed and status_val not in board_allowed:
                    return format_error(f"Statut '{status_val}' non autorise pour {board_name}")
            elif isinstance(allowed, list) and allowed and status_val not in allowed:
                return format_error(f"Statut '{status_val}' non autorise")
            flags["status"] = {"label": status_val}

        return svc.leads_update(item_id, flags, get_flag("board"))

    elif command == "leads.note":
        if len(args) < 2:
            return format_error('Usage: nm monday leads note <item_id> "texte"')
        return svc.leads_note(args[0], " ".join(args[1:]))

    elif command == "leads.next-actions":
        return svc.leads_next_actions()

    elif command == "leads.search":
        if not args:
            return format_error('Usage: nm monday leads search "nom ou terme"')
        return svc.leads_search(" ".join(args))

    elif command == "leads.create":
        name = get_flag("name")
        if not name:
            return format_error('Usage: nm monday leads create --name "Prenom Nom" [--phone "+33..."] [--email "..."] [--board fr_leads]')
        board = get_flag("board") or "fr_leads"
        flags = get_json_flags()
        flags.pop("name", None)
        flags.pop("board", None)
        return svc.leads_create(name, flags, board)

    # --- ENROLLMENTS ---
    elif command == "enrollment.create":
        lead_id = get_flag("lead-id")
        lead_name = get_flag("name") or "Lead"
        board_source = get_flag("source") or "FR Leads"
        seq_ids = config.get("sequence_ids", {})
        seq_name = get_flag("sequence") or "cold_outreach_classic"
        sequence_id = str(seq_ids.get(seq_name, ""))
        if not lead_id:
            return format_error('Usage: nm monday enrollment create --lead-id <id> --name "Nom" --source "FR Leads"')
        return svc.enrollment_create(lead_id, lead_name, board_source, sequence_id)

    elif command == "enrollment.get":
        if not args:
            return format_error("Usage: nm monday enrollment get <item_id>")
        return svc.enrollment_get(args[0])

    elif command == "enrollment.update":
        item_id = args[0] if args else None
        if not item_id:
            return format_error('Usage: nm monday enrollment update <item_id> --key value')
        flags = get_json_flags()
        return svc.enrollment_update(item_id, flags)

    # --- CALLS ---
    elif command == "call.log":
        lead_id = get_flag("lead-id")
        lead_name = get_flag("name") or "Lead"
        if not lead_id:
            return format_error('Usage: nm monday call log --lead-id <id> --name "Nom" --outcome "RDV pris" ...')
        flags = get_json_flags()
        flags.pop("lead-id", None)
        flags.pop("name", None)
        return svc.call_log(lead_id, lead_name, flags)

    elif command == "call.get":
        if not args:
            return format_error("Usage: nm monday call get <item_id>")
        return svc.call_get(args[0])

    # --- TASKS ---
    elif command == "tasks.today":
        return svc.tasks_today()

    elif command == "tasks.get":
        if not args:
            return format_error("Usage: nm monday tasks get <item_id>")
        return svc.tasks_get(args[0])

    elif command == "tasks.done":
        if not args:
            return format_error('Usage: nm monday tasks done <item_id> [--resultat "Fait"]')
        resultat = get_flag("resultat") or "Fait"
        return svc.tasks_done(args[0], resultat)

    # --- MEETINGS ---
    elif command == "meeting.create":
        lead_id = get_flag("lead-id")
        lead_name = get_flag("name") or "Lead"
        if not lead_id:
            return format_error('Usage: nm monday meeting create --lead-id <id> --name "Nom" --date 2026-05-15 --time 10:00')
        meeting_data = {
            "date": get_flag("date"),
            "time": get_flag("time"),
            "duration": int(get_flag("duration") or "30"),
            "email": get_flag("email") or "",
        }
        if not meeting_data["date"] or not meeting_data["time"]:
            return format_error("--date et --time sont obligatoires")
        return svc.meeting_create(lead_id, lead_name, meeting_data)

    else:
        return format_error(f"Commande Monday inconnue: {command}")
