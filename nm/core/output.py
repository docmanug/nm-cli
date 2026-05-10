from __future__ import annotations


def format_leads_list(leads: list) -> str:
    if not leads:
        return "Aucun lead a contacter."
    lines = [f"{len(leads)} leads a contacter aujourd'hui :\n"]
    for i, lead in enumerate(leads, 1):
        last = lead.get("last_contact") or "aucun"
        lines.append(
            f"#{i} {lead['name']} | Statut: {lead['status']} "
            f"| Depuis: {lead.get('days', '?')}j | Tel: {lead.get('phone', 'N/A')}"
        )
        lines.append(f"   Dernier contact: {last}")
    return "\n".join(lines)


def format_lead_detail(lead: dict) -> str:
    lines = [
        f"{lead['name']}",
        f"  Statut: {lead.get('status', 'N/A')}",
        f"  Tel: {lead.get('phone', 'N/A')}",
        f"  Email: {lead.get('email', 'N/A')}",
        f"  Entreprise: {lead.get('company', 'N/A')}",
    ]
    notes = lead.get("notes", [])
    if notes:
        lines.append("  Notes:")
        for note in notes:
            lines.append(f"    - {note}")
    return "\n".join(lines)


def format_send_confirmation(channel: str, recipient: str, status: str) -> str:
    return f"{channel} envoye a {recipient} — {status}"


def format_call_result(call: dict) -> str:
    lines = [
        f"Appel #{call.get('id', '?')}",
        f"  Contact: {call.get('contact', 'N/A')}",
        f"  Duree: {call.get('duration', 'N/A')}",
        f"  Resultat: {call.get('result', 'N/A')}",
    ]
    summary = call.get("summary")
    if summary:
        lines.append(f"  Resume: {summary}")
    return "\n".join(lines)


def format_calls_list(calls: list) -> str:
    if not calls:
        return "Aucun appel aujourd'hui."
    lines = [f"{len(calls)} appels aujourd'hui :\n"]
    for i, call in enumerate(calls, 1):
        lines.append(
            f"#{i} {call.get('contact', '?')} | {call.get('result', '?')} "
            f"| {call.get('duration', '?')}"
        )
    return "\n".join(lines)


def format_calendar_slots(slots: list) -> str:
    if not slots:
        return "Aucun creneau disponible."
    lines = [f"{len(slots)} creneaux disponibles :\n"]
    for slot in slots:
        lines.append(f"  {slot['date']} {slot['start']}-{slot['end']}")
    return "\n".join(lines)


def format_error(message: str) -> str:
    return f"Error: {message}"


def format_limit_hit(category: str, current: int, max_limit: int) -> str:
    return f"Error: Limite atteinte : {current}/{max_limit} {category} aujourd'hui. Reset demain 00h."


def format_tasks_list(tasks: list) -> str:
    if not tasks:
        return "Aucune tache a traiter aujourd'hui."
    lines = [f"{len(tasks)} taches a traiter aujourd'hui :\n"]
    for i, task in enumerate(tasks, 1):
        lines.append(
            f"#{i} {task['name']} | Type: {task.get('type', '?')} "
            f"| Echeance: {task.get('due_date', '?')} | Tel: {task.get('phone', 'N/A')}"
        )
        desc = task.get("description", "")
        if desc:
            lines.append(f"   {desc[:100]}")
    return "\n".join(lines)


def format_task_detail(task: dict) -> str:
    lines = [
        f"{task['name']}",
        f"  Type: {task.get('type', 'N/A')}",
        f"  Statut: {task.get('status', 'N/A')}",
        f"  Echeance: {task.get('due_date', 'N/A')}",
        f"  Tel: {task.get('phone', 'N/A')}",
    ]
    desc = task.get("description", "")
    if desc:
        lines.append(f"  Description: {desc}")
    notes = task.get("notes", [])
    if notes:
        lines.append("  Notes:")
        for note in notes:
            lines.append(f"    - {note}")
    return "\n".join(lines)


def format_enrollment_detail(enrollment: dict) -> str:
    lines = [
        f"Enrollment #{enrollment['id']} — {enrollment['name']}",
        f"  Statut: {enrollment.get('statut', 'N/A')}",
        f"  Step: {enrollment.get('current_step', '?')} — {enrollment.get('step_name', 'N/A')}",
        f"  Tentatives: {enrollment.get('total_attempts', '0')}",
        f"  Dernier canal: {enrollment.get('dernier_canal', 'N/A')}",
    ]
    exit_reason = enrollment.get("exit_reason", "")
    if exit_reason:
        lines.append(f"  Raison de sortie: {exit_reason}")
    return "\n".join(lines)


def format_item_created(item_type: str, item_id, item_name: str) -> str:
    return f"{item_type} cree : #{item_id} — {item_name}"


def format_deals_list(deals: list, board_name: str = "") -> str:
    if not deals:
        return f"Aucun deal actif{' dans ' + board_name if board_name else ''}."
    lines = [f"{len(deals)} deals{' dans ' + board_name if board_name else ''} :\n"]
    for i, deal in enumerate(deals, 1):
        arr = deal.get("arr", "?")
        lines.append(
            f"#{i} {deal['name']} | Stage: {deal.get('stage', 'N/A')} "
            f"| ARR: {arr} EUR | Close: {deal.get('close_date', 'N/A')}"
        )
        owner = deal.get("owner", "")
        if owner:
            lines.append(f"   Owner: {owner}")
    return "\n".join(lines)


def format_deal_detail(deal: dict) -> str:
    lines = [
        f"{deal['name']}",
        f"  Board: {deal.get('board', 'N/A')}",
        f"  Stage: {deal.get('stage', 'N/A')}",
        f"  Contract Status: {deal.get('contract_status', 'N/A')}",
        f"  ARR: {deal.get('arr', 'N/A')} EUR",
        f"  MRR: {deal.get('mrr', 'N/A')} EUR",
        f"  TCV: {deal.get('tcv', 'N/A')} EUR",
        f"  Terms: {deal.get('terms', 'N/A')} mois",
        f"  Close Date: {deal.get('close_date', 'N/A')}",
        f"  Contract End: {deal.get('contract_end_date', 'N/A')}",
        f"  Payment Date: {deal.get('payment_date', 'N/A')}",
        f"  Owner: {deal.get('owner', 'N/A')}",
        f"  Company: {deal.get('company', 'N/A')}",
    ]
    notes = deal.get("notes", [])
    if notes:
        lines.append("  Notes:")
        for note in notes:
            lines.append(f"    - {note}")
    return "\n".join(lines)


def format_pipeline_summary(stages: dict, board_name: str = "",
                            total_arr: float = 0, total_deals: int = 0) -> str:
    lines = [f"Pipeline {board_name} — {total_deals} deals | ARR total: {total_arr:.0f} EUR\n"]
    for stage, data in stages.items():
        lines.append(
            f"  {stage}: {data['count']} deals | ARR: {data['arr']:.0f} EUR"
        )
    return "\n".join(lines)


def format_company_detail(company: dict) -> str:
    lines = [
        f"{company['name']}",
        f"  Statut: {company.get('status', 'N/A')}",
        f"  Tel: {company.get('phone', 'N/A')}",
        f"  Ville: {company.get('city', 'N/A')}",
        f"  Pays: {company.get('country', 'N/A')}",
        f"  CS: {company.get('cs', 'N/A')}",
        f"  SA matching: {company.get('superadmin_matching', 'N/A')}",
    ]
    contacts = company.get("contacts", [])
    if contacts:
        lines.append(f"  Contacts: {', '.join(contacts)}")
    return "\n".join(lines)


def format_meetings_list(meetings: list) -> str:
    if not meetings:
        return "Aucun meeting."
    lines = [f"{len(meetings)} meetings :\n"]
    for i, m in enumerate(meetings, 1):
        lines.append(
            f"#{i} {m.get('title', m.get('name', '?'))} | {m.get('date', '?')} "
            f"| {m.get('type', '?')} | Statut: {m.get('status', '?')}"
        )
        people = m.get("people", "")
        if people:
            lines.append(f"   Avec: {people}")
    return "\n".join(lines)


def format_calls_list_detailed(calls: list) -> str:
    if not calls:
        return "Aucun appel."
    lines = [f"{len(calls)} appels :\n"]
    for i, call in enumerate(calls, 1):
        lines.append(
            f"#{i} {call.get('name', '?')} | {call.get('date', '?')} "
            f"| Outcome: {call.get('outcome', '?')} | Duree: {call.get('duration', '?')} min"
        )
    return "\n".join(lines)


def format_contact(contact: dict) -> str:
    lines = [
        f"{contact.get('name', 'N/A')}",
        f"  Tel: {contact.get('phone', 'N/A')}",
        f"  Email: {contact.get('email', 'N/A')}",
        f"  Entreprise: {contact.get('company', 'N/A')}",
    ]
    history = contact.get("history", [])
    if history:
        lines.append("  Historique recent:")
        for h in history[:5]:
            lines.append(f"    {h.get('date', '?')} | {h.get('channel', '?')} | {h.get('summary', '?')}")
    return "\n".join(lines)
