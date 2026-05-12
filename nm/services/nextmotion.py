from __future__ import annotations
from datetime import datetime, timedelta
import requests
from nm.core.output import (
    format_error,
    format_send_confirmation,
    format_nm_patient,
    format_nm_patients_list,
    format_nm_appointment,
    format_nm_appointments_list,
    format_nm_lead,
    format_nm_leads_list,
    format_nm_quote_native,
    format_nm_quotes_list_native,
    format_nm_labels_list_native,
    format_nm_visit_types_list,
    format_nm_doctors_list,
    format_nm_chat_contacts_list,
)


class NextmotionService:
    """Direct REST client for Nextmotion Open API v4."""

    def __init__(self, api_url: str, access_token: str, clinic_id: str):
        self._base = api_url.rstrip("/")
        self._token = access_token
        self._clinic_id = clinic_id

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _get(self, path: str, params: dict = None) -> dict:
        resp = requests.get(f"{self._base}/{path}", headers=self._headers(),
                            params=params)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict = None) -> dict:
        resp = requests.post(f"{self._base}/{path}", headers=self._headers(),
                             json=data or {})
        if not resp.ok:
            detail = resp.text[:500] if resp.text else ""
            raise requests.HTTPError(
                f"{resp.status_code} {resp.reason} for url: {resp.url} — {detail}",
                response=resp,
            )
        return resp.json()

    def _patch(self, path: str, data: dict = None) -> dict:
        resp = requests.patch(f"{self._base}/{path}", headers=self._headers(),
                              json=data or {})
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> dict | None:
        resp = requests.delete(f"{self._base}/{path}", headers=self._headers())
        resp.raise_for_status()
        if resp.text.strip():
            return resp.json()
        return {}

    # ---- PATIENTS ----

    def patient_list(self, search: str | None = None, limit: int = 50) -> str:
        params = {"limit": limit}
        if search:
            params["search"] = search
        result = self._get(f"clinics/{self._clinic_id}/patients", params)
        patients = result.get("data", result.get("results", []))
        return format_nm_patients_list(patients if isinstance(patients, list) else [])

    def patient_get(self, patient_id: str) -> str:
        result = self._get(f"patients/{patient_id}")
        patient = result.get("data", result)
        return format_nm_patient(patient if isinstance(patient, dict) else {})

    def patient_create(self, first_name: str, last_name: str, email: str,
                       gender: int = 2, **kwargs) -> str:
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "gender": gender,
        }
        for key in ("phone_number", "birth_date", "postal_address",
                     "city", "zip_code", "doctor_comments"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        result = self._post(f"clinics/{self._clinic_id}/patients", data)
        d = result.get("data", result)
        pid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Patient cree : {first_name} {last_name} (ID: {pid})"

    def patient_update(self, patient_id: str, **kwargs) -> str:
        # Retrieve current patient to get required fields
        current = self._get(f"patients/{patient_id}")
        data = current.get("data", current)
        patch = {
            "first_name": kwargs.get("first_name", data.get("first_name", "")),
            "last_name": kwargs.get("last_name", data.get("last_name", "")),
            "email": kwargs.get("email", data.get("email", "")),
            "gender": kwargs.get("gender", data.get("gender", 2)),
        }
        for key in ("phone_number", "birth_date", "postal_address",
                     "city", "zip_code", "doctor_comments"):
            if key in kwargs and kwargs[key] is not None:
                patch[key] = kwargs[key]
        self._patch(f"patients/{patient_id}", patch)
        return f"Patient {patient_id} mis a jour."

    # ---- RDV (Appointments) ----

    def rdv_list(self, date_str: str | None = None,
                 patient_id: str | None = None, limit: int = 50) -> str:
        params = {"limit": limit}
        if date_str:
            params["date"] = date_str
        if patient_id:
            params["patient"] = patient_id
        result = self._get(f"clinics/{self._clinic_id}/calendar_appointments", params)
        appointments = result.get("data", result.get("results", []))
        return format_nm_appointments_list(
            appointments if isinstance(appointments, list) else [],
            date_str or "",
        )

    def rdv_get(self, appointment_id: str) -> str:
        result = self._get(f"calendar_appointments/{appointment_id}")
        data = result.get("data", result)
        return format_nm_appointment(data if isinstance(data, dict) else {})

    def rdv_update(self, appointment_id: str, **kwargs) -> str:
        patch = {}
        cal_event = {}
        if kwargs.get("start_time"):
            cal_event["start_time"] = kwargs["start_time"]
        if kwargs.get("end_time"):
            cal_event["end_time"] = kwargs["end_time"]
        if kwargs.get("title"):
            cal_event["title"] = kwargs["title"]
        if kwargs.get("notes"):
            cal_event["notes"] = kwargs["notes"]
        if cal_event:
            # start_time and end_time required — fetch current if missing
            if "start_time" not in cal_event or "end_time" not in cal_event:
                current = self._get(f"calendar_appointments/{appointment_id}")
                data = current.get("data", current)
                event = data.get("calendar_event", {}) if isinstance(data, dict) else {}
                cal_event.setdefault("start_time", event.get("start_time", ""))
                cal_event.setdefault("end_time", event.get("end_time", ""))
            patch["calendar_event"] = cal_event
        if kwargs.get("status"):
            patch["status"] = kwargs["status"]
        if kwargs.get("subject"):
            patch["subject"] = kwargs["subject"]
        patch["send_appointment_modified_email"] = kwargs.get("notify_email", True)
        patch["send_appointment_modified_sms"] = kwargs.get("notify_sms", True)
        self._patch(f"calendar_appointments/{appointment_id}", patch)
        return f"RDV {appointment_id} mis a jour."

    def rdv_delete(self, appointment_id: str) -> str:
        self._delete(f"calendar_appointments/{appointment_id}")
        return f"RDV {appointment_id} supprime."

    def rdv_reschedule(self, appointment_id: str, time_slot: str,
                       opening_hour_id: str) -> str:
        self._post(f"calendar_appointments/{appointment_id}/reschedule", {
            "time_slot": time_slot,
            "visit_type_opening_hour": opening_hour_id,
        })
        return f"RDV {appointment_id} replanifie a {time_slot}."

    def rdv_request(self, first_name: str, last_name: str, email: str,
                    phone: str, birth_date: str, time_slot: str,
                    opening_hour_id: str, **kwargs) -> str:
        data = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone_number": phone,
            "birth_date": birth_date,
            "time_slot": time_slot,
            "visit_type_opening_hour": opening_hour_id,
        }
        if kwargs.get("gender") is not None:
            data["gender"] = kwargs["gender"]
        if kwargs.get("doctor"):
            data["doctor"] = kwargs["doctor"]
        result = self._post("appointment_requests", data)
        d = result.get("data", result)
        rid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Demande RDV creee : {first_name} {last_name} le {time_slot} (ID: {rid})"

    # ---- LEADS ----

    def lead_list(self, search: str | None = None, limit: int = 50) -> str:
        params = {"limit": limit}
        if search:
            params["search"] = search
        result = self._get(f"clinics/{self._clinic_id}/leads", params)
        leads = result.get("data", result.get("results", []))
        return format_nm_leads_list(leads if isinstance(leads, list) else [])

    def lead_get(self, lead_id: str) -> str:
        result = self._get(f"leads/{lead_id}")
        data = result.get("data", result)
        return format_nm_lead(data if isinstance(data, dict) else {})

    def lead_create(self, first_name: str, last_name: str, **kwargs) -> str:
        data = {"first_name": first_name, "last_name": last_name}
        for key in ("email", "phone_number", "source", "status",
                     "desired_treatment", "notes", "treatment_zone"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        result = self._post(f"clinics/{self._clinic_id}/leads", data)
        d = result.get("data", result)
        lid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Lead cree : {first_name} {last_name} (ID: {lid})"

    def lead_update(self, lead_id: str, first_name: str, last_name: str,
                    **kwargs) -> str:
        data = {"first_name": first_name, "last_name": last_name}
        for key in ("email", "phone_number", "status", "notes",
                     "is_done", "follow_up_count", "last_channel_used",
                     "response_received"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        self._patch(f"leads/{lead_id}", data)
        return f"Lead {lead_id} mis a jour."

    def lead_convert(self, lead_id: str) -> str:
        result = self._post(f"leads/{lead_id}/convert_to_patient", {})
        d = result.get("data", result)
        pid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Lead {lead_id} converti en patient (patient ID: {pid})."

    # ---- CALLS (log) ----

    def call_log(self, **kwargs) -> str:
        data = {}
        for key in ("patient", "phone_number", "notes", "transcript",
                     "status", "time", "recording_url"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        result = self._post(f"clinics/{self._clinic_id}/calls", data)
        d = result.get("data", result)
        cid = d.get("id", "?") if isinstance(d, dict) else "?"
        phone = kwargs.get("phone_number", "?")
        return f"Appel logue (ID: {cid}, tel: {phone})"

    # ---- QUOTES ----

    def quote_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/quotes", {"limit": limit})
        quotes = result.get("data", result.get("results", []))
        return format_nm_quotes_list_native(quotes if isinstance(quotes, list) else [])

    def quote_get(self, quote_id: str) -> str:
        result = self._get(f"quotes/{quote_id}")
        data = result.get("data", result)
        return format_nm_quote_native(data if isinstance(data, dict) else {})

    def quote_update_followup(self, quote_id: str, **kwargs) -> str:
        data = {}
        for key in ("next_follow_up_time", "last_follow_up_time",
                     "follow_up_count", "last_channel_used",
                     "response_received", "next_step_date"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        self._patch(f"quotes/{quote_id}", data)
        return f"Devis {quote_id} suivi mis a jour."

    # ---- CHAT ----

    def chat_contacts(self, search: str | None = None) -> str:
        params = {"user_type": 2}
        if search:
            params["search"] = search
        result = self._get(f"clinics/{self._clinic_id}/chat_contacts", params)
        contacts = result.get("data", result.get("results", []))
        return format_nm_chat_contacts_list(
            contacts if isinstance(contacts, list) else [])

    def chat_send(self, contact_id: str, message: str,
                  system: str = "whatsapp") -> str:
        data = {
            "contact_id": contact_id,
            "text_body": message,
            "system": system,
            "clinic_id": self._clinic_id,
        }
        self._post("contact_messages", data)
        return format_send_confirmation(f"Chat NM ({system})", contact_id, "envoye")

    # ---- LABELS ----

    def labels_list(self, label_type: str | None = None) -> str:
        params = {}
        if label_type:
            params["type"] = label_type
        result = self._get(f"clinics/{self._clinic_id}/object_labels", params)
        labels = result.get("data", result.get("results", []))
        return format_nm_labels_list_native(labels if isinstance(labels, list) else [])

    # ---- VISIT TYPES & SLOTS ----

    def visit_types_list(self) -> str:
        result = self._get(f"clinics/{self._clinic_id}/visit_types")
        vts = result.get("data", result.get("results", []))
        return format_nm_visit_types_list(vts if isinstance(vts, list) else [])

    def slots_list(self, start_date: str | None = None,
                   end_date: str | None = None) -> str:
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        result = self._get(f"clinics/{self._clinic_id}/calendar_opening_hours", params)
        slots = result.get("data", result.get("results", []))
        if not slots or not isinstance(slots, list):
            return "Aucun creneau disponible."
        lines = [f"{len(slots)} creneaux disponibles :\n"]
        for i, s in enumerate(slots, 1):
            cal = s.get("calendar_event", {}) if isinstance(s.get("calendar_event"), dict) else {}
            start = cal.get("start_time", s.get("start_time", "?"))
            end = cal.get("end_time", s.get("end_time", ""))
            docs = cal.get("doctors", [])
            doctors = ", ".join(d.get("prefixed_name", "?") for d in docs) if isinstance(docs, list) else str(docs)
            svts = s.get("sub_visit_types", [])
            vt_names = ", ".join(sv.get("subject", "?") for sv in svts if isinstance(sv, dict)) if isinstance(svts, list) and svts else "Tous"
            lines.append(f"#{i} {start} - {end} | {doctors} | {vt_names} | ID: {s.get('id', '?')}")
        return "\n".join(lines)

    # ---- FIND AVAILABLE SLOTS ----

    def _match_sub_visit_type(self, query: str) -> tuple[str | None, str]:
        """Use LLM to match patient query to actual NM sub_visit_types.

        Fetches the clinic's sub_visit_types, sends them + query to
        gpt-4o-mini for semantic matching. Returns (id, name).
        """
        if not query or not query.strip():
            return None, query

        # Fetch all sub_visit_types
        try:
            result = self._get(f"clinics/{self._clinic_id}/sub_visit_types")
            svts = result.get("data", result.get("results", []))
        except Exception:
            svts = []
        if not isinstance(svts, list) or not svts:
            return None, query

        entries = []
        for svt in svts:
            name = svt.get("subject") or svt.get("name") or ""
            sid = svt.get("id", "")
            if name and sid:
                entries.append({"id": sid, "name": name})
        if not entries:
            return None, query

        # Build LLM prompt
        options = "\n".join(f"- {e['id']} | {e['name']}" for e in entries)
        prompt = (
            f"Le patient demande : \"{query}\"\n\n"
            f"Voici les motifs de consultation disponibles :\n{options}\n\n"
            f"Quel motif correspond le mieux a la demande du patient ?\n"
            f"Reponds UNIQUEMENT avec l'ID (UUID), rien d'autre.\n"
            f"Si aucun motif ne correspond, reponds : NONE"
        )

        # Try Gemini Flash first, fallback to OpenAI gpt-4o-mini
        import os
        answer = None

        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            try:
                resp = requests.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0, "maxOutputTokens": 50},
                    },
                    timeout=5,
                )
                if resp.ok:
                    answer = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            except Exception:
                pass

        if not answer:
            openai_key = os.environ.get("OPENAI_API_KEY")
            if openai_key:
                try:
                    resp = requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={"Authorization": f"Bearer {openai_key}"},
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 50,
                            "temperature": 0,
                        },
                        timeout=5,
                    )
                    if resp.ok:
                        answer = resp.json()["choices"][0]["message"]["content"].strip()
                except Exception:
                    pass

        if not answer or answer == "NONE" or len(answer) < 10:
            return None, query

        # Find the matched entry
        for e in entries:
            if e["id"] == answer:
                return e["id"], e["name"]

        return None, query

    def find_available_slots(self, visit_type_query: str, date_str: str,
                             doctor: str | None = None) -> str:
        """Use POST /visit_types/opening_hours to get bookable slots.

        Fuzzy-matches the patient's treatment query against actual NM
        sub_visit_types, then calls the API which handles opening hours,
        appointments, absences server-side.
        """
        if not date_str:
            return format_error("Date requise (YYYY-MM-DD)")

        svt_id, matched_name = self._match_sub_visit_type(visit_type_query)

        body = {
            "start_date": date_str,
            "end_date": date_str,
        }
        if svt_id:
            body["sub_visit_type_id"] = svt_id
        else:
            body["sub_visit_type_name"] = matched_name
        if doctor:
            body["doctor_name"] = doctor

        try:
            result = self._post(
                f"clinics/{self._clinic_id}/visit_types/opening_hours", body
            )
        except Exception as e:
            err = str(e)
            if "svt_not_found" in err:
                return (
                    f"Le traitement \"{visit_type_query}\" n'a pas ete trouve "
                    f"dans les motifs de consultation. Verifiez le nom exact."
                )
            raise

        slots = result.get("data", [])
        if not isinstance(slots, list) or not slots:
            return (
                f"Aucun creneau disponible le {date_str} "
                f"pour \"{matched_name}\". Le docteur est peut-etre absent ou "
                f"tous les creneaux sont pris. Essayez une autre date."
            )

        lines = [
            f"{len(slots)} creneau(x) disponible(s) le {date_str} "
            f"pour \"{matched_name}\" :\n"
        ]
        for i, s in enumerate(slots, 1):
            ts = s.get("time_slot", "")
            vt_oh_id = s.get("id", "")
            if "T" in ts:
                t = ts.split("T")[1][:5]
                h, m = t.split(":")
                time_fmt = f"{int(h)}h{m}" if m != "00" else f"{int(h)}h"
            else:
                time_fmt = ts
            lines.append(
                f"  {i}. {time_fmt} | visit_type_opening_hour_id: {vt_oh_id}"
            )
        return "\n".join(lines)

    # ---- DOCTORS ----

    def doctor_list(self) -> str:
        result = self._get(f"clinics/{self._clinic_id}/doctors")
        doctors = result.get("data", result.get("results", []))
        return format_nm_doctors_list(doctors if isinstance(doctors, list) else [])


def handle_nextmotion(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("nextmotion")
    config = profile.get_service_config("nextmotion") or {}
    clinic_id = config.get("clinic_id")
    if not clinic_id:
        return format_error("clinic_id requis dans le profil nextmotion")

    svc = NextmotionService(
        api_url=creds["api_url"],
        access_token=creds["access_token"],
        clinic_id=clinic_id,
    )

    def get_flag(flag: str) -> str | None:
        for i, a in enumerate(args):
            if a == f"--{flag}" and i + 1 < len(args):
                return args[i + 1]
        return None

    # ---- PATIENTS ----
    if command == "patient.list":
        search = get_flag("search") or (" ".join(args) if args and not args[0].startswith("--") else None)
        limit_str = get_flag("limit")
        limit = int(limit_str) if limit_str else 50
        return svc.patient_list(search=search, limit=limit)

    elif command == "patient.get":
        if not args:
            return format_error("Usage: nm nextmotion patient get <patient_id>")
        return svc.patient_get(args[0])

    elif command == "patient.create":
        first_name = get_flag("first") or (args[0] if len(args) >= 1 and not args[0].startswith("--") else None)
        last_name = get_flag("last") or (args[1] if len(args) >= 2 and not args[1].startswith("--") else None)
        email = get_flag("email") or ""
        if not first_name or not last_name:
            return format_error('Usage: nm nextmotion patient create <prenom> <nom> --email ... [--phone ...] [--birth ...]')
        gender_str = get_flag("gender")
        gender = int(gender_str) if gender_str else 2
        return svc.patient_create(
            first_name, last_name, email, gender=gender,
            phone_number=get_flag("phone"),
            birth_date=get_flag("birth"),
            postal_address=get_flag("address"),
            city=get_flag("city"),
            zip_code=get_flag("zip"),
        )

    elif command == "patient.update":
        if not args:
            return format_error("Usage: nm nextmotion patient update <patient_id> [--phone ...] [--email ...]")
        kwargs = {}
        for key in ("first_name", "last_name", "email", "phone_number",
                     "birth_date", "city", "zip_code"):
            flag = key.replace("_", "-")
            val = get_flag(flag)
            if val is not None:
                kwargs[key] = val
        gender_str = get_flag("gender")
        if gender_str:
            kwargs["gender"] = int(gender_str)
        return svc.patient_update(args[0], **kwargs)

    # ---- RDV ----
    elif command == "rdv.list":
        date_str = get_flag("date") or (args[0] if args and not args[0].startswith("--") else None)
        patient_id = get_flag("patient")
        limit_str = get_flag("limit")
        limit = int(limit_str) if limit_str else 50
        return svc.rdv_list(date_str=date_str, patient_id=patient_id, limit=limit)

    elif command == "rdv.get":
        if not args:
            return format_error("Usage: nm nextmotion rdv get <rdv_id>")
        return svc.rdv_get(args[0])

    elif command == "rdv.update":
        if not args:
            return format_error("Usage: nm nextmotion rdv update <rdv_id> [--start ...] [--end ...] [--title ...] [--status ...]")
        return svc.rdv_update(
            args[0],
            start_time=get_flag("start"),
            end_time=get_flag("end"),
            title=get_flag("title"),
            notes=get_flag("notes"),
            status=get_flag("status"),
            subject=get_flag("subject"),
            notify_email=get_flag("no-email") is None,
            notify_sms=get_flag("no-sms") is None,
        )

    elif command == "rdv.delete":
        if not args:
            return format_error("Usage: nm nextmotion rdv delete <rdv_id>")
        return svc.rdv_delete(args[0])

    elif command == "rdv.reschedule":
        if len(args) < 3:
            return format_error("Usage: nm nextmotion rdv reschedule <rdv_id> <datetime_iso> <opening_hour_id>")
        return svc.rdv_reschedule(args[0], args[1], args[2])

    elif command == "rdv.request":
        first = get_flag("first")
        last = get_flag("last")
        email = get_flag("email")
        phone = get_flag("phone")
        birth = get_flag("birth")
        slot = get_flag("slot")
        opening = get_flag("opening")
        if not all([first, last, email, phone, birth, slot, opening]):
            return format_error(
                "Usage: nm nextmotion rdv request --first <prenom> --last <nom> "
                "--email <email> --phone <tel> --birth <YYYY-MM-DD> "
                "--slot <datetime_iso> --opening <opening_hour_id>"
            )
        gender_str = get_flag("gender")
        gender = int(gender_str) if gender_str else None
        return svc.rdv_request(
            first, last, email, phone, birth, slot, opening,
            gender=gender, doctor=get_flag("doctor"),
        )

    # ---- CALLS (log) ----
    elif command == "call.log":
        return svc.call_log(
            patient=get_flag("patient"),
            phone_number=get_flag("phone") or (args[0] if args and not args[0].startswith("--") else None),
            notes=get_flag("notes"),
            transcript=get_flag("transcript"),
            status=get_flag("status"),
            time=get_flag("time"),
            recording_url=get_flag("recording"),
        )

    # ---- LEADS ----
    elif command == "lead.list":
        search = get_flag("search") or (" ".join(args) if args and not args[0].startswith("--") else None)
        return svc.lead_list(search=search)

    elif command == "lead.get":
        if not args:
            return format_error("Usage: nm nextmotion lead get <lead_id>")
        return svc.lead_get(args[0])

    elif command == "lead.create":
        first_name = get_flag("first") or (args[0] if len(args) >= 1 and not args[0].startswith("--") else None)
        last_name = get_flag("last") or (args[1] if len(args) >= 2 and not args[1].startswith("--") else None)
        if not first_name or not last_name:
            return format_error('Usage: nm nextmotion lead create <prenom> <nom> [--email ...] [--phone ...]')
        return svc.lead_create(
            first_name, last_name,
            email=get_flag("email"),
            phone_number=get_flag("phone"),
            notes=get_flag("notes"),
        )

    elif command == "lead.update":
        if not args:
            return format_error("Usage: nm nextmotion lead update <lead_id> --first <prenom> --last <nom> [--status ...] [--notes ...]")
        first = get_flag("first")
        last = get_flag("last")
        if not first or not last:
            # Fetch current
            current = svc._get(f"leads/{args[0]}")
            data = current.get("data", current)
            first = first or data.get("first_name", "")
            last = last or data.get("last_name", "")
        return svc.lead_update(
            args[0], first, last,
            email=get_flag("email"),
            phone_number=get_flag("phone"),
            status=get_flag("status"),
            notes=get_flag("notes"),
            is_done=get_flag("done") == "true" if get_flag("done") else None,
        )

    elif command == "lead.convert":
        if not args:
            return format_error("Usage: nm nextmotion lead convert <lead_id>")
        return svc.lead_convert(args[0])

    # ---- QUOTES ----
    elif command == "quote.list":
        limit_str = get_flag("limit")
        limit = int(limit_str) if limit_str else 50
        return svc.quote_list(limit=limit)

    elif command == "quote.get":
        if not args:
            return format_error("Usage: nm nextmotion quote get <quote_id>")
        return svc.quote_get(args[0])

    elif command == "quote.update-followup":
        if not args:
            return format_error("Usage: nm nextmotion quote update-followup <quote_id> [--next ...] [--channel ...]")
        return svc.quote_update_followup(
            args[0],
            next_follow_up_time=get_flag("next"),
            last_follow_up_time=get_flag("last"),
            follow_up_count=int(get_flag("count")) if get_flag("count") else None,
            last_channel_used=get_flag("channel"),
            response_received=get_flag("responded") == "true" if get_flag("responded") else None,
            next_step_date=get_flag("next-step-date"),
        )

    # ---- CHAT ----
    elif command == "chat.contacts":
        search = get_flag("search") or (" ".join(args) if args and not args[0].startswith("--") else None)
        return svc.chat_contacts(search=search)

    elif command == "chat.send":
        if len(args) < 2:
            return format_error('Usage: nm nextmotion chat send <contact_id> "message" [--channel whatsapp|sms|internal]')
        contact_id = args[0]
        msg_parts = []
        for a in args[1:]:
            if a.startswith("--"):
                break
            msg_parts.append(a)
        message = " ".join(msg_parts)
        channel = get_flag("channel") or "whatsapp"
        return svc.chat_send(contact_id, message, system=channel)

    # ---- LABELS ----
    elif command == "labels.list":
        label_type = get_flag("type")
        return svc.labels_list(label_type=label_type)

    # ---- VISIT TYPES & SLOTS ----
    elif command == "visit-types.list":
        return svc.visit_types_list()

    elif command == "slots.list":
        return svc.slots_list(
            start_date=get_flag("from"),
            end_date=get_flag("to"),
        )

    elif command == "find-slots":
        treatment = get_flag("treatment") or (" ".join(a for a in args if not a.startswith("--")) if args else None)
        date = get_flag("date")
        doctor = get_flag("doctor")
        if not treatment:
            return format_error("Usage: nm nextmotion find-slots --treatment \"botox\" --date 2026-05-19")
        return svc.find_available_slots(treatment, date, doctor)

    # ---- DOCTORS ----
    elif command == "doctor.list":
        return svc.doctor_list()

    else:
        return format_error(f"Commande Nextmotion inconnue: {command}")
