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
