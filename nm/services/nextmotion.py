from __future__ import annotations
import requests
import json as _json
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
    def __init__(self, api_url: str, access_token: str, clinic_id: str):
        self._api_url = api_url
        self._access_token = access_token
        self._clinic_id = clinic_id

    _rpc_id = 0

    def _call_tool(self, tool: str, params: dict = None) -> dict:
        NextmotionService._rpc_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": NextmotionService._rpc_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": params or {}},
        }
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }
        resp = requests.post(self._api_url, headers=headers, json=payload)
        resp.raise_for_status()

        text = resp.text.strip()
        if text.startswith("event:"):
            data_line = ""
            for line in text.split("\n"):
                if line.startswith("data: "):
                    data_line = line[6:]
            if data_line:
                data = _json.loads(data_line)
            else:
                raise RuntimeError(f"SSE response without data: {text[:200]}")
        else:
            data = resp.json()

        if "error" in data:
            raise RuntimeError(f"Nextmotion error: {data['error']}")

        result = data.get("result", data)
        if isinstance(result, dict) and "content" in result:
            content = result["content"]
            if isinstance(content, list) and content:
                text_content = content[0].get("text", "{}")
                try:
                    return _json.loads(text_content)
                except (_json.JSONDecodeError, TypeError):
                    return {"text": text_content}
        return result

    # ---- PATIENTS ----

    def patient_list(self, search: str | None = None, limit: int = 50) -> str:
        params = {"clinic_id": self._clinic_id, "limit": limit}
        if search:
            params["search"] = search
        result = self._call_tool("oapi_clinic_patient_list", params)
        patients = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(patients, dict):
            patients = patients.get("data", [patients])
        return format_nm_patients_list(patients if isinstance(patients, list) else [])

    def patient_get(self, patient_id: str) -> str:
        result = self._call_tool("oapi_patient_retrieve", {"patient_id": patient_id})
        patient = result.get("data", result) if isinstance(result, dict) else result
        return format_nm_patient(patient if isinstance(patient, dict) else {})

    def patient_create(self, first_name: str, last_name: str, email: str,
                       gender: int = 2, **kwargs) -> str:
        params = {
            "clinic_id": self._clinic_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "gender": gender,
        }
        for key in ("phone_number", "birth_date", "postal_address",
                     "city", "zip_code", "doctor_comments"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        result = self._call_tool("oapi_clinic_patient_create", params)
        data = result.get("data", result) if isinstance(result, dict) else result
        pid = data.get("id", "?") if isinstance(data, dict) else "?"
        name = f"{first_name} {last_name}"
        return f"Patient cree : {name} (ID: {pid})"

    def patient_update(self, patient_id: str, **kwargs) -> str:
        # Retrieve current patient to get required fields
        current = self._call_tool("oapi_patient_retrieve", {"patient_id": patient_id})
        data = current.get("data", current) if isinstance(current, dict) else current
        params = {
            "patient_id": patient_id,
            "first_name": kwargs.get("first_name", data.get("first_name", "")),
            "last_name": kwargs.get("last_name", data.get("last_name", "")),
            "email": kwargs.get("email", data.get("email", "")),
            "gender": kwargs.get("gender", data.get("gender", 2)),
        }
        for key in ("phone_number", "birth_date", "postal_address",
                     "city", "zip_code", "doctor_comments"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        self._call_tool("oapi_patient_update", params)
        return f"Patient {patient_id} mis a jour."

    # ---- RDV (Appointments) ----

    def rdv_list(self, date_str: str | None = None,
                 patient_id: str | None = None, limit: int = 50) -> str:
        params = {"clinic_id": self._clinic_id, "limit": limit}
        if date_str:
            params["date"] = date_str
        if patient_id:
            params["patient"] = patient_id
        result = self._call_tool("oapi_clinic_calendar_appointment_list", params)
        appointments = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(appointments, dict):
            appointments = appointments.get("data", [appointments])
        return format_nm_appointments_list(
            appointments if isinstance(appointments, list) else [],
            date_str or "",
        )

    def rdv_get(self, appointment_id: str) -> str:
        result = self._call_tool("oapi_calendar_appointment_retrieve",
                                 {"calendar_appointment_id": appointment_id})
        data = result.get("data", result) if isinstance(result, dict) else result
        return format_nm_appointment(data if isinstance(data, dict) else {})

    def rdv_update(self, appointment_id: str, **kwargs) -> str:
        params = {"calendar_appointment_id": appointment_id}
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
            # start_time and end_time are required for calendar_event
            if "start_time" not in cal_event or "end_time" not in cal_event:
                # Fetch current to fill missing
                current = self._call_tool("oapi_calendar_appointment_retrieve",
                                          {"calendar_appointment_id": appointment_id})
                data = current.get("data", current) if isinstance(current, dict) else current
                event = data.get("calendar_event", {})
                cal_event.setdefault("start_time", event.get("start_time", ""))
                cal_event.setdefault("end_time", event.get("end_time", ""))
            params["calendar_event"] = cal_event
        if kwargs.get("status"):
            params["status"] = kwargs["status"]
        if kwargs.get("subject"):
            params["subject"] = kwargs["subject"]
        notify_email = kwargs.get("notify_email", True)
        notify_sms = kwargs.get("notify_sms", True)
        params["send_appointment_modified_email"] = notify_email
        params["send_appointment_modified_sms"] = notify_sms
        self._call_tool("oapi_calendar_appointment_update", params)
        return f"RDV {appointment_id} mis a jour."

    def rdv_delete(self, appointment_id: str) -> str:
        self._call_tool("oapi_calendar_appointment_destroy",
                        {"calendar_appointment_id": appointment_id})
        return f"RDV {appointment_id} supprime."

    def rdv_reschedule(self, appointment_id: str, time_slot: str,
                       opening_hour_id: str) -> str:
        self._call_tool("oapi_calendar_appointment_reschedule", {
            "calendar_appointment_id": appointment_id,
            "time_slot": time_slot,
            "visit_type_opening_hour": opening_hour_id,
        })
        return f"RDV {appointment_id} replanifie a {time_slot}."

    # ---- LEADS ----

    def lead_list(self, search: str | None = None, limit: int = 50) -> str:
        params = {"clinic_id": self._clinic_id, "limit": limit}
        if search:
            params["search"] = search
        result = self._call_tool("oapi_clinic_lead_list", params)
        leads = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(leads, dict):
            leads = leads.get("data", [leads])
        return format_nm_leads_list(leads if isinstance(leads, list) else [])

    def lead_get(self, lead_id: str) -> str:
        result = self._call_tool("oapi_lead_retrieve", {"lead_id": lead_id})
        data = result.get("data", result) if isinstance(result, dict) else result
        return format_nm_lead(data if isinstance(data, dict) else {})

    def lead_create(self, first_name: str, last_name: str, **kwargs) -> str:
        params = {
            "clinic_id": self._clinic_id,
            "first_name": first_name,
            "last_name": last_name,
        }
        for key in ("email", "phone_number", "source", "status",
                     "desired_treatment", "notes", "treatment_zone"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        result = self._call_tool("oapi_clinic_lead_create", params)
        data = result.get("data", result) if isinstance(result, dict) else result
        lid = data.get("id", "?") if isinstance(data, dict) else "?"
        return f"Lead cree : {first_name} {last_name} (ID: {lid})"

    def lead_update(self, lead_id: str, first_name: str, last_name: str,
                    **kwargs) -> str:
        params = {
            "lead_id": lead_id,
            "first_name": first_name,
            "last_name": last_name,
        }
        for key in ("email", "phone_number", "status", "notes",
                     "is_done", "follow_up_count", "last_channel_used",
                     "response_received"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        self._call_tool("oapi_lead_update", params)
        return f"Lead {lead_id} mis a jour."

    def lead_convert(self, lead_id: str) -> str:
        result = self._call_tool("oapi_lead_convert_to_patient", {"lead_id": lead_id})
        data = result.get("data", result) if isinstance(result, dict) else result
        pid = data.get("id", "?") if isinstance(data, dict) else "?"
        return f"Lead {lead_id} converti en patient (patient ID: {pid})."

    # ---- QUOTES ----

    def quote_list(self, limit: int = 50) -> str:
        params = {"clinic_id": self._clinic_id, "limit": limit}
        result = self._call_tool("oapi_clinic_quote_list", params)
        quotes = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(quotes, dict):
            quotes = quotes.get("data", [quotes])
        return format_nm_quotes_list_native(quotes if isinstance(quotes, list) else [])

    def quote_get(self, quote_id: str) -> str:
        result = self._call_tool("oapi_quote_retrieve", {"quote_id": quote_id})
        data = result.get("data", result) if isinstance(result, dict) else result
        return format_nm_quote_native(data if isinstance(data, dict) else {})

    def quote_update_followup(self, quote_id: str, **kwargs) -> str:
        params = {"quote_id": quote_id}
        for key in ("next_follow_up_time", "last_follow_up_time",
                     "follow_up_count", "last_channel_used",
                     "response_received", "next_step_date"):
            if key in kwargs and kwargs[key] is not None:
                params[key] = kwargs[key]
        self._call_tool("oapi_quote_update", params)
        return f"Devis {quote_id} suivi mis a jour."

    # ---- CHAT ----

    def chat_contacts(self, search: str | None = None) -> str:
        params = {"clinic_id": self._clinic_id, "user_type": [2]}
        if search:
            params["search"] = search
        result = self._call_tool("oapi_clinic_chat_contact_list", params)
        contacts = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(contacts, dict):
            contacts = contacts.get("data", [contacts])
        return format_nm_chat_contacts_list(
            contacts if isinstance(contacts, list) else [])

    def chat_send(self, contact_id: str, message: str,
                  system: str = "whatsapp") -> str:
        params = {
            "contact_id": contact_id,
            "text_body": message,
            "system": system,
            "clinic_id": self._clinic_id,
        }
        self._call_tool("oapi_contact_message_create", params)
        return format_send_confirmation(f"Chat NM ({system})", contact_id, "envoye")

    # ---- LABELS ----

    def labels_list(self, label_type: str | None = None) -> str:
        params = {"clinic_id": self._clinic_id}
        if label_type:
            params["type"] = [label_type]
        result = self._call_tool("oapi_clinic_object_label_list", params)
        labels = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(labels, dict):
            labels = labels.get("data", [labels])
        return format_nm_labels_list_native(labels if isinstance(labels, list) else [])

    # ---- VISIT TYPES & SLOTS ----

    def visit_types_list(self) -> str:
        result = self._call_tool("oapi_clinic_visit_type_list",
                                 {"clinic_id": self._clinic_id})
        vts = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(vts, dict):
            vts = vts.get("data", [vts])
        return format_nm_visit_types_list(vts if isinstance(vts, list) else [])

    def slots_list(self, start_date: str | None = None,
                   end_date: str | None = None) -> str:
        params = {"clinic_id": self._clinic_id}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        result = self._call_tool("oapi_clinic_visit_type_opening_hour_list", params)
        slots = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(slots, dict):
            slots = slots.get("data", [slots])
        if not slots or not isinstance(slots, list):
            return "Aucun creneau disponible."
        lines = [f"{len(slots)} creneaux disponibles :\n"]
        for i, s in enumerate(slots, 1):
            dt = s.get("time_slot", s.get("start_time", "?"))
            vt = s.get("visit_type_name", s.get("visit_type", "?"))
            lines.append(f"#{i} {dt} | {vt} | ID: {s.get('id', '?')}")
        return "\n".join(lines)

    # ---- DOCTORS ----

    def doctor_list(self) -> str:
        result = self._call_tool("oapi_clinic_doctor_list",
                                 {"clinic_id": self._clinic_id})
        doctors = result.get("data", result) if isinstance(result, dict) else result
        if isinstance(doctors, dict):
            doctors = doctors.get("data", [doctors])
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
            current = svc._call_tool("oapi_lead_retrieve", {"lead_id": args[0]})
            data = current.get("data", current) if isinstance(current, dict) else current
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

    # ---- DOCTORS ----
    elif command == "doctor.list":
        return svc.doctor_list()

    else:
        return format_error(f"Commande Nextmotion inconnue: {command}")
