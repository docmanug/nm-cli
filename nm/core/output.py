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
        ns = deal.get("next_step", "")
        nsd = deal.get("next_step_date", "")
        if ns or nsd:
            lines.append(f"   Next Step: {ns or 'VIDE'} | Date: {nsd or 'VIDE'}")
        else:
            lines.append(f"   ⚠ Next Step: MANQUANT")
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
        f"  Next Step: {deal.get('next_step') or 'VIDE'}",
        f"  Next Step Date: {deal.get('next_step_date') or 'VIDE'}",
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


def format_nextcall_calls_list(calls: list, period: str = "") -> str:
    if not calls:
        return f"Aucun appel{' ' + period if period else ''}."
    lines = [f"{len(calls)} appels{' ' + period if period else ''} :\n"]
    for i, call in enumerate(calls, 1):
        duration = call.get("duration", "?")
        if isinstance(duration, (int, float)) and duration > 0:
            mins = int(duration) // 60
            secs = int(duration) % 60
            duration = f"{mins}m{secs:02d}s"
        lines.append(
            f"#{i} [{call.get('date', '?')}] {call.get('contact', '?')} "
            f"| {call.get('status', '?')} | {call.get('label', '')} "
            f"| {duration}"
        )
    return "\n".join(lines)


def format_nextcall_call_detail(call: dict) -> str:
    lines = [
        f"Appel #{call.get('id', '?')}",
        f"  Contact: {call.get('contact', 'N/A')}",
        f"  Date: {call.get('date', 'N/A')}",
        f"  Statut: {call.get('status', 'N/A')}",
        f"  Label: {call.get('label', 'N/A')}",
        f"  Duree: {call.get('duration', 'N/A')}s",
        f"  Direction: {call.get('direction', 'N/A')}",
    ]
    transcript = call.get("transcript", "")
    if transcript:
        lines.append(f"  Transcript:\n    {transcript[:2000]}")
    summary = call.get("summary", "")
    if summary:
        lines.append(f"  Resume IA: {summary}")
    coaching = call.get("coaching_tips", [])
    if coaching:
        lines.append("  Coaching:")
        for tip in coaching[:5]:
            lines.append(f"    - {tip}")
    return "\n".join(lines)


def format_nextcall_call_stats(stats: dict) -> str:
    lines = [
        f"Stats appels :",
        f"  Total: {stats.get('total', 0)}",
        f"  Connectes: {stats.get('connected', 0)}",
        f"  Pas repondu: {stats.get('no_answer', 0)}",
        f"  Duree moyenne: {stats.get('avg_duration', 0):.0f}s",
        f"  Duree totale: {stats.get('total_duration', 0):.0f}s",
    ]
    by_label = stats.get("by_label", {})
    if by_label:
        lines.append("  Par label:")
        for label, count in by_label.items():
            lines.append(f"    {label}: {count}")
    return "\n".join(lines)


def format_meeting_transcript(transcript: dict) -> str:
    lines = [
        f"Transcript #{transcript.get('id', '?')}",
        f"  Titre: {transcript.get('title', 'N/A')}",
        f"  Date: {transcript.get('date', 'N/A')}",
        f"  Participants: {', '.join(transcript.get('participants', []))}",
        f"  Statut: {transcript.get('status', 'N/A')}",
    ]
    summary = transcript.get("summary", "")
    if summary:
        lines.append(f"  Resume: {summary}")
    text = transcript.get("transcript", "")
    if text:
        lines.append(f"  Transcript:\n    {text[:3000]}")
    return "\n".join(lines)


def format_meeting_transcripts_list(transcripts: list) -> str:
    if not transcripts:
        return "Aucun transcript."
    lines = [f"{len(transcripts)} transcripts :\n"]
    for i, t in enumerate(transcripts, 1):
        lines.append(
            f"#{i} {t.get('id', '?')} [{t.get('date', '?')}] {t.get('title', '?')} "
            f"| {t.get('status', '?')} | {t.get('duration', '?')}min"
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


def format_patient(patient: dict) -> str:
    name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
    lines = [
        name or "N/A",
        f"  ID: {patient.get('id', 'N/A')}",
        f"  Tel: {patient.get('phone', patient.get('mobile', 'N/A'))}",
        f"  Email: {patient.get('email', 'N/A')}",
        f"  Date naissance: {patient.get('birth_date', patient.get('birthdate', 'N/A'))}",
        f"  Sexe: {patient.get('gender', patient.get('sex', 'N/A'))}",
    ]
    address = patient.get("address", "")
    if address:
        lines.append(f"  Adresse: {address}")
    notes = patient.get("notes", patient.get("medical_notes", ""))
    if notes:
        lines.append(f"  Notes: {str(notes)[:500]}")
    return "\n".join(lines)


def format_quote(quote: dict) -> str:
    patient = quote.get("patient", {})
    patient_name = patient.get("name", patient.get("full_name", "N/A")) if isinstance(patient, dict) else str(patient)
    lines = [
        f"Devis #{quote.get('id', '?')}",
        f"  Patient: {quote.get('patient_name', patient_name)}",
        f"  Date: {quote.get('created_at', quote.get('date', 'N/A'))}",
        f"  Montant: {quote.get('total_amount', quote.get('amount', 'N/A'))} EUR",
        f"  Statut: {quote.get('status', 'N/A')}",
    ]
    treatments = quote.get("treatments", quote.get("items", []))
    if treatments:
        lines.append("  Traitements:")
        for t in treatments[:10]:
            if isinstance(t, dict):
                name = t.get("name", t.get("treatment_name", "?"))
                price = t.get("price", t.get("amount", "?"))
                lines.append(f"    - {name}: {price} EUR")
            else:
                lines.append(f"    - {t}")
    followup = quote.get("last_follow_up_time", "")
    if followup:
        lines.append(f"  Dernier suivi: {followup}")
    next_followup = quote.get("next_follow_up_time", "")
    if next_followup:
        lines.append(f"  Prochain suivi: {next_followup}")
    return "\n".join(lines)


def format_quotes_list(quotes: list) -> str:
    if not quotes:
        return "Aucun devis."
    lines = [f"{len(quotes)} devis :\n"]
    for i, q in enumerate(quotes, 1):
        patient = q.get("patient", {})
        patient_name = patient.get("name", "?") if isinstance(patient, dict) else str(patient)
        patient_name = q.get("patient_name", patient_name)
        amount = q.get("total_amount", q.get("amount", "?"))
        status = q.get("status", "?")
        dt = q.get("created_at", q.get("date", "?"))
        if isinstance(dt, str) and len(dt) > 10:
            dt = dt[:10]
        lines.append(f"#{i} [{dt}] {patient_name} | {amount} EUR | {status}")
    return "\n".join(lines)


def format_labels_list(labels: list) -> str:
    if not labels:
        return "Aucun label."
    lines = [f"{len(labels)} labels :\n"]
    for i, label in enumerate(labels, 1):
        if isinstance(label, dict):
            lines.append(f"  {i}. {label.get('name', label.get('label', '?'))} (ID: {label.get('id', '?')})")
        else:
            lines.append(f"  {i}. {label}")
    return "\n".join(lines)


def format_chat_contacts(contacts: list) -> str:
    if not contacts:
        return "Aucun contact chat."
    lines = [f"{len(contacts)} contacts :\n"]
    for i, c in enumerate(contacts, 1):
        name = c.get("name", c.get("full_name", "?"))
        phone = c.get("phone", c.get("mobile", "N/A"))
        lines.append(f"#{i} {name} | Tel: {phone} | ID: {c.get('id', '?')}")
    return "\n".join(lines)


# ---- Nextmotion Native Formatters ----


def format_nm_patient(p: dict) -> str:
    name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or "N/A"
    lines = [
        name,
        f"  ID: {p.get('id', 'N/A')}",
        f"  Tel: {p.get('phone_number', 'N/A')}",
        f"  Email: {p.get('email', 'N/A')}",
        f"  Date naissance: {p.get('birth_date', 'N/A')}",
        f"  Sexe: {['F', 'M', 'Autre'][p['gender']] if isinstance(p.get('gender'), int) and p['gender'] < 3 else 'N/A'}",
    ]
    city = p.get("city", "")
    if city:
        lines.append(f"  Ville: {city}")
    comments = p.get("doctor_comments", "")
    if comments:
        # Strip HTML tags for display
        import re
        clean = re.sub(r'<[^>]+>', ' ', str(comments)).strip()
        if clean:
            lines.append(f"  Notes medecin: {clean[:500]}")
    return "\n".join(lines)


def format_nm_patients_list(patients: list) -> str:
    if not patients:
        return "Aucun patient."
    lines = [f"{len(patients)} patients :\n"]
    for i, p in enumerate(patients, 1):
        name = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or "?"
        phone = p.get("phone_number", "N/A")
        email = p.get("email", "")
        lines.append(f"#{i} {name} | Tel: {phone} | ID: {p.get('id', '?')}")
    return "\n".join(lines)


def _utc_to_local(time_str: str, event: dict) -> str:
    """Convert UTC time string to local time using utc_offset from event."""
    if not time_str or not isinstance(time_str, str) or "T" not in time_str:
        return time_str or "?"
    hhmm = time_str.split("T")[1][:5]
    try:
        h, m = int(hhmm.split(":")[0]), int(hhmm.split(":")[1])
        offset_s = event.get("start_time_utc_offset_seconds", 0)
        if offset_s:
            h += offset_s // 3600
        elif event.get("start_time_utc_offset"):
            off = event["start_time_utc_offset"]
            h += int(off.split(":")[0])
        else:
            h += 2  # Default Paris CEST
        return f"{h:02d}:{m:02d}"
    except (ValueError, IndexError):
        return hhmm


def format_nm_appointment(a: dict) -> str:
    event = a.get("calendar_event", {})
    patient = a.get("patient", {})
    patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() if isinstance(patient, dict) else str(patient)
    start = _utc_to_local(event.get("start_time", ""), event)
    end = _utc_to_local(event.get("end_time", ""), event)
    lines = [
        f"RDV #{a.get('id', '?')}",
        f"  Patient: {patient_name or 'N/A'}",
        f"  Debut: {start}",
        f"  Fin: {end}",
        f"  Titre: {event.get('title', 'N/A')}",
        f"  Statut: {a.get('status', 'N/A')}",
        f"  Type: {a.get('subject', a.get('visit_type_name', 'N/A'))}",
    ]
    notes = event.get("notes", "")
    if notes:
        lines.append(f"  Notes: {notes[:500]}")
    return "\n".join(lines)


def format_nm_appointments_list(appointments: list, date_str: str = "") -> str:
    if not appointments:
        return f"Aucun RDV{' le ' + date_str if date_str else ''}."
    lines = [f"{len(appointments)} RDV{' le ' + date_str if date_str else ''} :\n"]
    for i, a in enumerate(appointments, 1):
        event = a.get("calendar_event", {})
        patient = a.get("patient", {})
        patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() if isinstance(patient, dict) else "?"
        start = _utc_to_local(event.get("start_time", ""), event)
        end = _utc_to_local(event.get("end_time", ""), event)
        status = a.get("status", "?")
        subject = a.get("subject", "")
        lines.append(f"#{i} {start}-{end} {patient_name} | {subject} | {status} | ID: {a.get('id', '?')}")
    return "\n".join(lines)


def format_nm_lead(lead: dict) -> str:
    name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() or "N/A"
    lines = [
        name,
        f"  ID: {lead.get('id', 'N/A')}",
        f"  Tel: {lead.get('phone_number', 'N/A')}",
        f"  Email: {lead.get('email', 'N/A')}",
        f"  Source: {lead.get('source_name', lead.get('source', 'N/A'))}",
        f"  Statut: {lead.get('status_name', lead.get('status', 'N/A'))}",
        f"  Traitement souhaite: {lead.get('desired_treatment_name', lead.get('desired_treatment', 'N/A'))}",
        f"  Suivis: {lead.get('follow_up_count', 0)}",
        f"  Traite: {'Oui' if lead.get('is_done') else 'Non'}",
    ]
    notes = lead.get("notes", "")
    if notes:
        lines.append(f"  Notes: {str(notes)[:500]}")
    return "\n".join(lines)


def format_nm_leads_list(leads: list) -> str:
    if not leads:
        return "Aucun lead."
    lines = [f"{len(leads)} leads :\n"]
    for i, l in enumerate(leads, 1):
        name = f"{l.get('first_name', '')} {l.get('last_name', '')}".strip() or "?"
        phone = l.get("phone_number", "N/A")
        status = l.get("status_name", l.get("status", "?"))
        lines.append(f"#{i} {name} | Tel: {phone} | Statut: {status} | ID: {l.get('id', '?')}")
    return "\n".join(lines)


def format_nm_quote_native(q: dict) -> str:
    patient = q.get("patient", {})
    patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() if isinstance(patient, dict) else str(patient)
    lines = [
        f"Devis #{q.get('id', '?')}",
        f"  Patient: {patient_name or 'N/A'}",
        f"  Date: {q.get('created_time', q.get('created_at', 'N/A'))}",
        f"  Titre: {q.get('title', 'N/A')}",
        f"  Montant: {q.get('total_amount', q.get('amount', 'N/A'))} EUR",
        f"  Statut: {q.get('status', 'N/A')}",
    ]
    followup = q.get("last_follow_up_time", "")
    if followup:
        lines.append(f"  Dernier suivi: {followup}")
    next_fu = q.get("next_follow_up_time", "")
    if next_fu:
        lines.append(f"  Prochain suivi: {next_fu}")
    return "\n".join(lines)


def format_nm_quotes_list_native(quotes: list) -> str:
    if not quotes:
        return "Aucun devis."
    lines = [f"{len(quotes)} devis :\n"]
    for i, q in enumerate(quotes, 1):
        patient = q.get("patient", {})
        patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip() if isinstance(patient, dict) else "?"
        amount = q.get("total_amount", q.get("amount", "?"))
        dt = q.get("created_time", q.get("created_at", "?"))
        if isinstance(dt, str) and len(dt) > 10:
            dt = dt[:10]
        lines.append(f"#{i} [{dt}] {patient_name} | {amount} EUR | ID: {q.get('id', '?')}")
    return "\n".join(lines)


def format_nm_labels_list_native(labels: list) -> str:
    if not labels:
        return "Aucun label."
    lines = [f"{len(labels)} labels :\n"]
    for i, label in enumerate(labels, 1):
        if isinstance(label, dict):
            ltype = label.get("type", "")
            lines.append(f"  {i}. [{ltype}] {label.get('name', '?')} (ID: {label.get('id', '?')})")
        else:
            lines.append(f"  {i}. {label}")
    return "\n".join(lines)


def format_nm_visit_types_list(vts: list) -> str:
    if not vts:
        return "Aucun type de visite."
    lines = [f"{len(vts)} types de visite :\n"]
    for i, vt in enumerate(vts, 1):
        duration = vt.get("duration", "?")
        lines.append(f"  {i}. {vt.get('name', vt.get('subject', '?'))} | Duree: {duration}min | ID: {vt.get('id', '?')}")
    return "\n".join(lines)


def format_nm_doctors_list(doctors: list) -> str:
    if not doctors:
        return "Aucun praticien."
    lines = [f"{len(doctors)} praticiens :\n"]
    for i, d in enumerate(doctors, 1):
        name = f"{d.get('first_name', '')} {d.get('last_name', '')}".strip() or "?"
        kind = d.get("kind", "?")
        lines.append(f"  {i}. {name} | Type: {kind} | ID: {d.get('id', '?')}")
    return "\n".join(lines)


def format_nm_chat_contacts_list(contacts: list) -> str:
    if not contacts:
        return "Aucun contact chat."
    lines = [f"{len(contacts)} contacts chat :\n"]
    for i, c in enumerate(contacts, 1):
        name = f"{c.get('first_name', '')} {c.get('last_name', '')}".strip() or c.get("name", "?")
        phone = c.get("phone_number", c.get("phone", "N/A"))
        last_msg = c.get("last_message", {})
        last_text = ""
        if isinstance(last_msg, dict):
            last_text = (last_msg.get("text_body", "") or "")[:80]
        lines.append(f"#{i} {name} | Tel: {phone} | ID: {c.get('id', '?')}")
        if last_text:
            lines.append(f"    Dernier msg: {last_text}")
    return "\n".join(lines)


def format_enrich_result(result: dict) -> str:
    lead_name = result.get("name", "?")
    item_id = result.get("item_id", "")
    header = f"Enrichissement: {lead_name}"
    if item_id:
        header += f" (#{item_id})"
    lines = [header]
    filled = result.get("filled_columns", [])
    if filled:
        lines.append(f"  Colonnes remplies: {', '.join(filled)}")
    skipped = result.get("skipped_columns", [])
    if skipped:
        lines.append(f"  Colonnes ignorees (deja remplies): {', '.join(skipped)}")
    errors = result.get("errors", [])
    if errors:
        lines.append(f"  Erreurs: {', '.join(errors)}")
    briefing = result.get("briefing", "")
    if briefing:
        lines.append(f"\n{briefing}")
    return "\n".join(lines)


def format_enrich_batch(results: list) -> str:
    total = len(results)
    enriched = [r for r in results if not r.get("errors") and not r.get("already_enriched")]
    errored = [r for r in results if r.get("errors")]
    already = [r for r in results if r.get("already_enriched")]
    lines = [
        f"Batch enrichissement: {total} leads traites",
        f"  Enrichis: {len(enriched)}",
        f"  Erreurs: {len(errored)}",
        f"  Deja enrichis: {len(already)}",
    ]
    if enriched:
        ids = [r.get("item_id", "?") for r in enriched]
        lines.append(f"  IDs enrichis: {', '.join(str(i) for i in ids)}")
    return "\n".join(lines)


def format_enrich_status(status: dict) -> str:
    enriched = status.get("enriched", False)
    lines = [
        f"Lead {status.get('name', '?')}: {'Enrichi' if enriched else 'Non enrichi'}",
    ]
    filled = status.get("filled", [])
    empty = status.get("empty", [])
    if filled:
        lines.append(f"  Rempli: {', '.join(filled)}")
    if empty:
        lines.append(f"  Vide: {', '.join(empty)}")
    return "\n".join(lines)
