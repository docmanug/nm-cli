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
    format_nm_patient_stats,
    format_nm_treatments_list,
    format_nm_prescriptions_list,
    format_nm_media_list,
    format_nm_consultation,
    format_nm_consultations_list,
    format_nm_invoice,
    format_nm_invoices_list,
    format_nm_payment,
    format_nm_payments_list,
    format_nm_treatment,
    format_nm_prescription,
    format_nm_stats_income,
    format_nm_visits_list,
    format_nm_absences_list,
    format_nm_journeys_list,
    format_nm_generic_list,
    format_nm_generic_detail,
    format_nm_products_list,
    format_nm_webhooks_list,
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

    def patient_delete(self, patient_id: str) -> str:
        self._delete(f"patients/{patient_id}")
        return f"Patient {patient_id} supprime."

    def patient_stats(self, patient_id: str) -> str:
        result = self._get(f"patients/{patient_id}/stats")
        data = result.get("data", result)
        return format_nm_patient_stats(data if isinstance(data, dict) else {})

    def patient_medical_history(self, patient_id: str) -> str:
        result = self._get(f"patients/{patient_id}/medical_history")
        data = result.get("data", result)
        if not data or not isinstance(data, dict):
            return "Aucun historique medical."
        lines = ["Historique medical :"]
        for key, val in data.items():
            if key == "id":
                continue
            if isinstance(val, (str, int, float, bool)) and val:
                lines.append(f"  {key}: {val}")
        return "\n".join(lines) if len(lines) > 1 else "Historique medical vide."

    def patient_update_medical_history(self, patient_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"patients/{patient_id}/medical_history", data)
        return f"Historique medical du patient {patient_id} mis a jour."

    def patient_treatments(self, patient_id: str, limit: int = 50) -> str:
        result = self._get(f"patients/{patient_id}/treatments", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_treatments_list(items if isinstance(items, list) else [])

    def patient_prescriptions(self, patient_id: str, limit: int = 50) -> str:
        result = self._get(f"patients/{patient_id}/prescriptions", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_prescriptions_list(items if isinstance(items, list) else [])

    def patient_media(self, patient_id: str, limit: int = 50) -> str:
        result = self._get(f"patients/{patient_id}/media_records", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_media_list(items if isinstance(items, list) else [])

    def patient_photos(self, patient_id: str, limit: int = 50) -> str:
        result = self._get(f"patients/{patient_id}/photo_compares", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_media_list(items if isinstance(items, list) else [])

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

    # ---- CONSULTATIONS ----

    def consultation_list(self, patient_id: str | None = None, limit: int = 50) -> str:
        params = {"limit": limit}
        if patient_id:
            params["patient"] = patient_id
        result = self._get(f"clinics/{self._clinic_id}/consultations", params)
        items = result.get("data", result.get("results", []))
        return format_nm_consultations_list(items if isinstance(items, list) else [])

    def consultation_get(self, consultation_id: str) -> str:
        result = self._get(f"consultations/{consultation_id}")
        data = result.get("data", result)
        return format_nm_consultation(data if isinstance(data, dict) else {})

    def consultation_create(self, patient_id: str, name: str) -> str:
        result = self._post(f"clinics/{self._clinic_id}/consultations", {
            "patient": patient_id, "name": name,
        })
        d = result.get("data", result)
        cid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Consultation creee (ID: {cid})"

    def consultation_update(self, consultation_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"consultations/{consultation_id}", data)
        return f"Consultation {consultation_id} mise a jour."

    def consultation_delete(self, consultation_id: str) -> str:
        self._delete(f"consultations/{consultation_id}")
        return f"Consultation {consultation_id} supprimee."

    # ---- INVOICES ----

    def invoice_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/invoices", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_invoices_list(items if isinstance(items, list) else [])

    def invoice_get(self, invoice_id: str) -> str:
        result = self._get(f"invoices/{invoice_id}")
        data = result.get("data", result)
        return format_nm_invoice(data if isinstance(data, dict) else {})

    def invoice_create(self, consultation_id: str) -> str:
        result = self._post(f"consultations/{consultation_id}/invoices", {})
        d = result.get("data", result)
        iid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Facture creee depuis consultation {consultation_id} (ID: {iid})"

    def invoice_update(self, invoice_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"invoices/{invoice_id}", data)
        return f"Facture {invoice_id} mise a jour."

    def invoice_delete(self, invoice_id: str) -> str:
        self._delete(f"invoices/{invoice_id}")
        return f"Facture {invoice_id} supprimee."

    def invoice_validate(self, invoice_id: str) -> str:
        self._post(f"invoices/{invoice_id}/validate", {})
        return f"Facture {invoice_id} validee."

    def invoice_pay(self, invoice_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._post(f"invoices/{invoice_id}/pay", data)
        return f"Facture {invoice_id} payee."

    # ---- PAYMENTS ----

    def payment_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/payments", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_payments_list(items if isinstance(items, list) else [])

    def payment_get(self, payment_id: str) -> str:
        result = self._get(f"payments/{payment_id}")
        data = result.get("data", result)
        return format_nm_payment(data if isinstance(data, dict) else {})

    def payment_update(self, payment_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"payments/{payment_id}", data)
        return f"Paiement {payment_id} mis a jour."

    def payment_delete(self, payment_id: str) -> str:
        self._delete(f"payments/{payment_id}")
        return f"Paiement {payment_id} supprime."

    # ---- CREDIT NOTES ----

    def credit_note_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/credit_notes", {"limit": limit})
        items = result.get("data", result.get("results", []))
        if not items or not isinstance(items, list):
            return "Aucun avoir."
        lines = [f"{len(items)} avoirs :\n"]
        for i, cn in enumerate(items, 1):
            lines.append(f"#{i} {cn.get('title', '?')} | {str(cn.get('created_time', ''))[:10]} | ID: {cn.get('id', '?')}")
        return "\n".join(lines)

    def credit_note_create(self, invoice_id: str) -> str:
        result = self._post(f"clinics/{self._clinic_id}/credit_notes", {"invoice": invoice_id})
        d = result.get("data", result)
        cnid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Avoir cree depuis facture {invoice_id} (ID: {cnid})"

    # ---- TREATMENTS (standalone) ----

    def treatment_get(self, treatment_id: str) -> str:
        result = self._get(f"treatments/{treatment_id}")
        data = result.get("data", result)
        return format_nm_treatment(data if isinstance(data, dict) else {})

    def treatment_create(self, patient_id: str, **kwargs) -> str:
        data = {"patient": patient_id}
        for key in ("name", "treatment_type", "price", "quantity", "details"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        result = self._post(f"patients/{patient_id}/treatments", data)
        d = result.get("data", result)
        tid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Traitement cree pour patient {patient_id} (ID: {tid})"

    def treatment_update(self, treatment_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"treatments/{treatment_id}", data)
        return f"Traitement {treatment_id} mis a jour."

    def treatment_delete(self, treatment_id: str) -> str:
        self._delete(f"treatments/{treatment_id}")
        return f"Traitement {treatment_id} supprime."

    def treatment_consent_upload(self, treatment_id: str, file_path: str) -> str:
        import os
        if not os.path.exists(file_path):
            return format_error(f"Fichier non trouve: {file_path}")
        with open(file_path, "rb") as f:
            resp = requests.post(
                f"{self._base}/treatments/{treatment_id}/consent_forms/upload",
                headers={"Authorization": f"Bearer {self._token}"},
                files={"file": f},
            )
        resp.raise_for_status()
        return f"Formulaire de consentement uploade pour traitement {treatment_id}."

    # ---- PRESCRIPTIONS (standalone) ----

    def prescription_get(self, prescription_id: str) -> str:
        result = self._get(f"prescriptions/{prescription_id}")
        data = result.get("data", result)
        return format_nm_prescription(data if isinstance(data, dict) else {})

    def prescription_create(self, patient_id: str, **kwargs) -> str:
        data = {}
        for key in ("name", "content", "doctor"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        result = self._post(f"patients/{patient_id}/prescriptions", data)
        d = result.get("data", result)
        pid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Ordonnance creee pour patient {patient_id} (ID: {pid})"

    def prescription_update(self, prescription_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"prescriptions/{prescription_id}", data)
        return f"Ordonnance {prescription_id} mise a jour."

    def prescription_delete(self, prescription_id: str) -> str:
        self._delete(f"prescriptions/{prescription_id}")
        return f"Ordonnance {prescription_id} supprimee."

    def prescription_sign(self, prescription_id: str) -> str:
        self._post(f"prescriptions/{prescription_id}/sign", {})
        return f"Ordonnance {prescription_id} signee."

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
            utc_offset = s.get("utc_offset", "")
            vt_oh_id = s.get("id", "")
            if "T" in ts:
                t = ts.split("T")[1][:5]
                h, m = int(t.split(":")[0]), int(t.split(":")[1])
                # Apply UTC offset to get local time
                if utc_offset:
                    try:
                        off_h = int(utc_offset.split(":")[0])
                        h += off_h
                    except (ValueError, IndexError):
                        pass
                time_fmt = f"{h}h{m:02d}" if m != 0 else f"{h}h"
            else:
                time_fmt = ts
            lines.append(
                f"  {i}. {time_fmt} | time_slot: {ts} | visit_type_opening_hour_id: {vt_oh_id}"
            )
        return "\n".join(lines)

    # ---- DOCTORS ----

    def doctor_list(self) -> str:
        result = self._get(f"clinics/{self._clinic_id}/doctors")
        doctors = result.get("data", result.get("results", []))
        return format_nm_doctors_list(doctors if isinstance(doctors, list) else [])

    # ---- STATISTICS ----

    def stats_income(self, period_type: str = "month", start_time: str | None = None,
                     end_time: str | None = None) -> str:
        params = {"period_type": period_type}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        result = self._get(f"clinics/{self._clinic_id}/statistics/appointment_income", params)
        return format_nm_stats_income(result)

    def stats_treatments(self, period_type: str = "month", start_time: str | None = None,
                         end_time: str | None = None) -> str:
        params = {"period_type": period_type}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        result = self._get(f"clinics/{self._clinic_id}/statistics/treatment_types", params)
        data = result.get("data", result.get("results", []))
        if not isinstance(data, list) or not data:
            return "Aucune statistique traitement."
        lines = ["Statistiques par type de traitement :\n"]
        for t in data:
            name = t.get("name", t.get("treatment_type", "?"))
            count = t.get("count", t.get("total", "?"))
            lines.append(f"  {name}: {count}")
        return "\n".join(lines)

    def stats_treatments_income(self, period_type: str = "month", start_time: str | None = None,
                                end_time: str | None = None) -> str:
        params = {"period_type": period_type}
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        result = self._get(f"clinics/{self._clinic_id}/statistics/treatment_types/income", params)
        return format_nm_stats_income(result)

    # ---- VISITS ----

    def visit_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/visits", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_visits_list(items if isinstance(items, list) else [])

    def visit_get(self, visit_id: str) -> str:
        result = self._get(f"visits/{visit_id}")
        data = result.get("data", result)
        if not data or not isinstance(data, dict):
            return "Visite non trouvee."
        lines = [
            f"Visite #{data.get('id', '?')}",
            f"  Patient: {data.get('patient', 'N/A')}",
            f"  Date: {str(data.get('created_time', ''))[:10]}",
        ]
        return "\n".join(lines)

    def visit_create(self, patient_id: str, **kwargs) -> str:
        data = {"patient": patient_id}
        data.update({k: v for k, v in kwargs.items() if v is not None})
        result = self._post(f"clinics/{self._clinic_id}/visits", data)
        d = result.get("data", result)
        vid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Visite creee pour patient {patient_id} (ID: {vid})"

    def visit_update(self, visit_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"visits/{visit_id}", data)
        return f"Visite {visit_id} mise a jour."

    def visit_delete(self, visit_id: str) -> str:
        self._delete(f"visits/{visit_id}")
        return f"Visite {visit_id} supprimee."

    # ---- ABSENCES ----

    def absences_list(self, start_date: str | None = None, end_date: str | None = None,
                      limit: int = 50) -> str:
        params = {"limit": limit}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        result = self._get(f"clinics/{self._clinic_id}/calendar_absences", params)
        items = result.get("data", result.get("results", []))
        return format_nm_absences_list(items if isinstance(items, list) else [])

    # ---- JOURNEYS ----

    def journeys_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/calendar_journeys", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_journeys_list(items if isinstance(items, list) else [])

    # ---- VISIT TYPE CATEGORIES ----

    def visit_type_category_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/visit_type_categories", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "categorie")

    def visit_type_category_get(self, category_id: str) -> str:
        result = self._get(f"visit_type_categories/{category_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Categorie")

    def visit_type_category_create(self, name: str) -> str:
        result = self._post(f"clinics/{self._clinic_id}/visit_type_categories", {"name": name})
        d = result.get("data", result)
        return f"Categorie creee : {name} (ID: {d.get('id', '?') if isinstance(d, dict) else '?'})"

    def visit_type_category_update(self, category_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"visit_type_categories/{category_id}", data)
        return f"Categorie {category_id} mise a jour."

    def visit_type_category_delete(self, category_id: str) -> str:
        self._delete(f"visit_type_categories/{category_id}")
        return f"Categorie {category_id} supprimee."

    # ---- VISIT TYPE EXTENSIONS ----

    def visit_type_get(self, visit_type_id: str) -> str:
        result = self._get(f"visit_types/{visit_type_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Type de visite")

    def visit_type_create(self, name: str, **kwargs) -> str:
        data = {"name": name}
        data.update({k: v for k, v in kwargs.items() if v is not None})
        result = self._post(f"clinics/{self._clinic_id}/visit_types", data)
        d = result.get("data", result)
        return f"Type de visite cree : {name} (ID: {d.get('id', '?') if isinstance(d, dict) else '?'})"

    def visit_type_update(self, visit_type_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"visit_types/{visit_type_id}", data)
        return f"Type de visite {visit_type_id} mis a jour."

    def visit_type_delete(self, visit_type_id: str) -> str:
        self._delete(f"visit_types/{visit_type_id}")
        return f"Type de visite {visit_type_id} supprime."

    # ---- SUB VISIT TYPES ----

    def sub_visit_type_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/sub_visit_types", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "sous-type de visite")

    def sub_visit_type_get(self, svt_id: str) -> str:
        result = self._get(f"sub_visit_types/{svt_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Sous-type de visite")

    # ---- TREATMENT TYPES ----

    def treatment_type_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/treatment_types", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "type de traitement")

    def treatment_type_get(self, tt_id: str) -> str:
        result = self._get(f"treatment_types/{tt_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Type de traitement")

    def treatment_type_create(self, name: str, **kwargs) -> str:
        data = {"name": name}
        data.update({k: v for k, v in kwargs.items() if v is not None})
        result = self._post(f"clinics/{self._clinic_id}/treatment_types", data)
        d = result.get("data", result)
        return f"Type de traitement cree : {name} (ID: {d.get('id', '?') if isinstance(d, dict) else '?'})"

    def treatment_type_update(self, tt_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"treatment_types/{tt_id}", data)
        return f"Type de traitement {tt_id} mis a jour."

    def treatment_type_delete(self, tt_id: str) -> str:
        self._delete(f"treatment_types/{tt_id}")
        return f"Type de traitement {tt_id} supprime."

    # ---- TREATMENT PRICINGS ----

    def treatment_pricing_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/treatment_pricings", {"limit": limit})
        items = result.get("data", result.get("results", []))
        if not items or not isinstance(items, list):
            return "Aucun tarif."
        lines = [f"{len(items)} tarifs :\n"]
        for i, p in enumerate(items, 1):
            name = p.get("name", p.get("treatment_type_name", "?"))
            price = p.get("price", "?")
            lines.append(f"#{i} {name} | {price} | ID: {p.get('id', '?')}")
        return "\n".join(lines)

    def treatment_pricing_get(self, tp_id: str) -> str:
        result = self._get(f"treatment_pricings/{tp_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Tarif")

    # ---- TREATMENT PACKAGES ----

    def treatment_package_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/treatment_packages", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "forfait")

    def treatment_package_get(self, tp_id: str) -> str:
        result = self._get(f"treatment_packages/{tp_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Forfait")

    def treatment_package_create(self, name: str, **kwargs) -> str:
        data = {"name": name}
        data.update({k: v for k, v in kwargs.items() if v is not None})
        result = self._post(f"clinics/{self._clinic_id}/treatment_packages", data)
        d = result.get("data", result)
        return f"Forfait cree : {name} (ID: {d.get('id', '?') if isinstance(d, dict) else '?'})"

    def treatment_package_update(self, tp_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"treatment_packages/{tp_id}", data)
        return f"Forfait {tp_id} mis a jour."

    def treatment_package_delete(self, tp_id: str) -> str:
        self._delete(f"treatment_packages/{tp_id}")
        return f"Forfait {tp_id} supprime."

    def treatment_package_extract(self, tp_id: str) -> str:
        result = self._post(f"treatment_packages/{tp_id}/extract", {})
        return f"Forfait {tp_id} extrait."

    # ---- DOCTOR EXTENSIONS ----

    def doctor_get(self, doctor_id: str) -> str:
        result = self._get(f"doctors/{doctor_id}")
        data = result.get("data", result)
        if not data or not isinstance(data, dict):
            return "Docteur non trouve."
        name = data.get("prefixed_name", f"{data.get('first_name', '')} {data.get('last_name', '')}".strip())
        lines = [
            f"Docteur #{data.get('id', '?')}",
            f"  Nom: {name}",
            f"  Email: {data.get('email', 'N/A')}",
            f"  Specialite: {data.get('specialty', 'N/A')}",
        ]
        return "\n".join(lines)

    def doctor_create(self, first_name: str, last_name: str, **kwargs) -> str:
        data = {"first_name": first_name, "last_name": last_name}
        for key in ("email", "specialty", "phone_number"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        result = self._post(f"clinics/{self._clinic_id}/doctors", data)
        d = result.get("data", result)
        did = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Docteur cree : {first_name} {last_name} (ID: {did})"

    def doctor_update(self, doctor_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"doctors/{doctor_id}", data)
        return f"Docteur {doctor_id} mis a jour."

    def doctor_delete(self, doctor_id: str) -> str:
        self._delete(f"doctors/{doctor_id}")
        return f"Docteur {doctor_id} supprime."

    # ---- PRODUCTS ----

    def product_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/products", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_products_list(items if isinstance(items, list) else [])

    def product_get(self, product_id: str) -> str:
        result = self._get(f"products/{product_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Produit")

    def product_create(self, name: str, **kwargs) -> str:
        data = {"name": name}
        for key in ("price", "description", "reference"):
            if key in kwargs and kwargs[key] is not None:
                data[key] = kwargs[key]
        result = self._post(f"clinics/{self._clinic_id}/products", data)
        d = result.get("data", result)
        pid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Produit cree : {name} (ID: {pid})"

    def product_update(self, product_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"products/{product_id}", data)
        return f"Produit {product_id} mis a jour."

    def product_delete(self, product_id: str) -> str:
        self._delete(f"products/{product_id}")
        return f"Produit {product_id} supprime."

    def global_product_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/global_products", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_products_list(items if isinstance(items, list) else [])

    # ---- WEBHOOKS ----

    def webhook_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/webhooks", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_webhooks_list(items if isinstance(items, list) else [])

    def webhook_get(self, webhook_id: str) -> str:
        result = self._get(f"webhooks/{webhook_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Webhook")

    def webhook_create(self, url: str, events: list) -> str:
        result = self._post(f"clinics/{self._clinic_id}/webhooks", {
            "url": url, "events": events,
        })
        d = result.get("data", result)
        wid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Webhook cree : {url} (ID: {wid})"

    def webhook_update(self, webhook_id: str, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        self._patch(f"webhooks/{webhook_id}", data)
        return f"Webhook {webhook_id} mis a jour."

    def webhook_delete(self, webhook_id: str) -> str:
        self._delete(f"webhooks/{webhook_id}")
        return f"Webhook {webhook_id} supprime."

    # ---- COMMUNICATION TEMPLATES ----

    def comm_template_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/communication_templates", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "template communication")

    def comm_template_get(self, template_id: str) -> str:
        result = self._get(f"communication_templates/{template_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Template communication")

    def comm_record_create(self, **kwargs) -> str:
        data = {k: v for k, v in kwargs.items() if v is not None}
        result = self._post(f"clinics/{self._clinic_id}/communication_records", data)
        d = result.get("data", result)
        cid = d.get("id", "?") if isinstance(d, dict) else "?"
        return f"Communication creee (ID: {cid})"

    # ---- DOCUMENT TEMPLATES ----

    def doc_template_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/document_templates", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "modele document")

    def doc_template_get(self, template_id: str) -> str:
        result = self._get(f"document_templates/{template_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Modele document")

    def doc_template_create(self, name: str, **kwargs) -> str:
        data = {"name": name}
        data.update({k: v for k, v in kwargs.items() if v is not None})
        result = self._post(f"clinics/{self._clinic_id}/document_templates", data)
        d = result.get("data", result)
        return f"Modele document cree : {name} (ID: {d.get('id', '?') if isinstance(d, dict) else '?'})"

    def doc_template_delete(self, template_id: str) -> str:
        self._delete(f"document_templates/{template_id}")
        return f"Modele document {template_id} supprime."

    # ---- SURVEY FORMS ----

    def survey_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/survey_forms", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "formulaire")

    def survey_get(self, survey_id: str) -> str:
        result = self._get(f"survey_forms/{survey_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Formulaire")

    # ---- ROOMS ----

    def room_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/appointment_rooms", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "salle")

    def room_get(self, room_id: str) -> str:
        result = self._get(f"appointment_rooms/{room_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Salle")

    # ---- DEVICES ----

    def device_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/appointment_devices", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "appareil")

    def device_get(self, device_id: str) -> str:
        result = self._get(f"appointment_devices/{device_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Appareil")

    # ---- PAYMENT MEDIUMS ----

    def payment_medium_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/payment_mediums", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "moyen de paiement")

    def payment_medium_get(self, pm_id: str) -> str:
        result = self._get(f"payment_mediums/{pm_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Moyen de paiement")

    # ---- ACCOUNTING DISTRIBUTIONS ----

    def accounting_list(self, limit: int = 50) -> str:
        result = self._get(f"clinics/{self._clinic_id}/accounting_distributions", {"limit": limit})
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "distribution comptable")

    def accounting_get(self, dist_id: str) -> str:
        result = self._get(f"accounting_distributions/{dist_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Distribution comptable")

    # ---- FEATURES ----

    def feature_list(self) -> str:
        result = self._get(f"clinics/{self._clinic_id}/features")
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "fonctionnalite")

    # ---- CLINIC ----

    def clinic_list(self) -> str:
        result = self._get("clinics")
        items = result.get("data", result.get("results", []))
        return format_nm_generic_list(items if isinstance(items, list) else [], "clinique")

    # ---- USER ----

    def user_me(self) -> str:
        result = self._get("users/me")
        data = result.get("data", result)
        if not data or not isinstance(data, dict):
            return "Utilisateur non trouve."
        lines = [
            f"Utilisateur : {data.get('first_name', '')} {data.get('last_name', '')}".strip(),
            f"  ID: {data.get('id', 'N/A')}",
            f"  Email: {data.get('email', 'N/A')}",
        ]
        return "\n".join(lines)

    # ---- LEAD DELETE ----

    def lead_delete(self, lead_id: str) -> str:
        self._delete(f"leads/{lead_id}")
        return f"Lead {lead_id} supprime."

    # ---- QUOTE EXTENSIONS ----

    def quote_delete(self, quote_id: str) -> str:
        self._delete(f"quotes/{quote_id}")
        return f"Devis {quote_id} supprime."

    def quote_validate(self, quote_id: str) -> str:
        self._post(f"quotes/{quote_id}/validate", {})
        return f"Devis {quote_id} valide."

    # ---- OPENING HOUR ----

    def opening_hour_get(self, oh_id: str) -> str:
        result = self._get(f"calendar_opening_hours/{oh_id}")
        data = result.get("data", result)
        return format_nm_generic_detail(data if isinstance(data, dict) else {}, "Creneau d'ouverture")

    # ---- RDV TREATMENTS ----

    def rdv_treatments(self, appointment_id: str) -> str:
        result = self._get(f"calendar_appointments/{appointment_id}/treatments")
        items = result.get("data", result.get("results", []))
        return format_nm_treatments_list(items if isinstance(items, list) else [])

    # ---- MEDICAL HISTORY (clinic level) ----

    def clinic_medical_history(self) -> str:
        result = self._get(f"clinics/{self._clinic_id}/medical_history")
        data = result.get("data", result)
        if not data or not isinstance(data, dict):
            return "Aucune configuration historique medical."
        lines = ["Configuration historique medical clinique :"]
        for key, val in data.items():
            if isinstance(val, (str, int, float, bool)):
                lines.append(f"  {key}: {val}")
        return "\n".join(lines) if len(lines) > 1 else "Configuration vide."


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

    elif command == "patient.delete":
        if not args:
            return format_error("Usage: nm nextmotion patient.delete <patient_id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — patient.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.patient_delete(args[0])

    elif command == "patient.stats":
        if not args:
            return format_error("Usage: nm nextmotion patient.stats <patient_id>")
        return svc.patient_stats(args[0])

    elif command == "patient.medical-history":
        if not args:
            return format_error("Usage: nm nextmotion patient.medical-history <patient_id>")
        return svc.patient_medical_history(args[0])

    elif command == "patient.update-medical-history":
        if not args:
            return format_error("Usage: nm nextmotion patient.update-medical-history <patient_id> --field value --confirm")
        if "--confirm" not in args:
            fields = {k: v for k, v in [(args[j+1].lstrip("-"), args[j+2]) for j in range(1, len(args)-1, 2) if args[j].startswith("--") and args[j] != "--confirm"] if k != "confirm"}
            return f"DRY RUN — patient.update-medical-history : {args[0]}, fields={fields}\nAjouter --confirm pour executer."
        kwargs = {}
        for j in range(1, len(args) - 1):
            if args[j].startswith("--") and args[j] != "--confirm" and j + 1 < len(args):
                kwargs[args[j].lstrip("-").replace("-", "_")] = args[j + 1]
        return svc.patient_update_medical_history(args[0], **kwargs)

    elif command == "patient.treatments":
        if not args:
            return format_error("Usage: nm nextmotion patient.treatments <patient_id>")
        limit = int(get_flag("limit") or "50")
        return svc.patient_treatments(args[0], limit=limit)

    elif command == "patient.prescriptions":
        if not args:
            return format_error("Usage: nm nextmotion patient.prescriptions <patient_id>")
        limit = int(get_flag("limit") or "50")
        return svc.patient_prescriptions(args[0], limit=limit)

    elif command == "patient.media":
        if not args:
            return format_error("Usage: nm nextmotion patient.media <patient_id>")
        limit = int(get_flag("limit") or "50")
        return svc.patient_media(args[0], limit=limit)

    elif command == "patient.photos":
        if not args:
            return format_error("Usage: nm nextmotion patient.photos <patient_id>")
        limit = int(get_flag("limit") or "50")
        return svc.patient_photos(args[0], limit=limit)

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

    # ---- CONSULTATIONS ----
    elif command == "consultation.list":
        patient_id = get_flag("patient")
        limit = int(get_flag("limit") or "50")
        return svc.consultation_list(patient_id=patient_id, limit=limit)

    elif command == "consultation.get":
        if not args:
            return format_error("Usage: nm nextmotion consultation.get <id>")
        return svc.consultation_get(args[0])

    elif command == "consultation.create":
        patient_id = get_flag("patient")
        name = get_flag("name")
        if not patient_id or not name:
            return format_error("Usage: nm nextmotion consultation.create --patient <id> --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — consultation.create : patient={patient_id}, name={name}\nAjouter --confirm pour executer."
        return svc.consultation_create(patient_id, name)

    elif command == "consultation.update":
        if not args:
            return format_error("Usage: nm nextmotion consultation.update <id> --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — consultation.update : {args[0]}\nAjouter --confirm pour executer."
        kwargs = {}
        name = get_flag("name")
        if name:
            kwargs["name"] = name
        return svc.consultation_update(args[0], **kwargs)

    elif command == "consultation.delete":
        if not args:
            return format_error("Usage: nm nextmotion consultation.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — consultation.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.consultation_delete(args[0])

    # ---- INVOICES ----
    elif command == "invoice.list":
        limit = int(get_flag("limit") or "50")
        return svc.invoice_list(limit=limit)

    elif command == "invoice.get":
        if not args:
            return format_error("Usage: nm nextmotion invoice.get <id>")
        return svc.invoice_get(args[0])

    elif command == "invoice.create":
        consultation_id = get_flag("consultation")
        if not consultation_id:
            return format_error("Usage: nm nextmotion invoice.create --consultation <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — invoice.create : consultation={consultation_id}\nAjouter --confirm pour executer."
        return svc.invoice_create(consultation_id)

    elif command == "invoice.update":
        if not args:
            return format_error("Usage: nm nextmotion invoice.update <id> --title <titre> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — invoice.update : {args[0]}\nAjouter --confirm pour executer."
        kwargs = {}
        title = get_flag("title")
        if title:
            kwargs["title"] = title
        return svc.invoice_update(args[0], **kwargs)

    elif command == "invoice.delete":
        if not args:
            return format_error("Usage: nm nextmotion invoice.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — invoice.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.invoice_delete(args[0])

    elif command == "invoice.validate":
        if not args:
            return format_error("Usage: nm nextmotion invoice.validate <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — invoice.validate : {args[0]}\nAjouter --confirm pour executer."
        return svc.invoice_validate(args[0])

    elif command == "invoice.pay":
        if not args:
            return format_error("Usage: nm nextmotion invoice.pay <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — invoice.pay : {args[0]}\nAjouter --confirm pour executer."
        amount = get_flag("amount")
        method = get_flag("method")
        kwargs = {}
        if amount:
            kwargs["amount"] = amount
        if method:
            kwargs["payment_medium"] = method
        return svc.invoice_pay(args[0], **kwargs)

    # ---- PAYMENTS ----
    elif command == "payment.list":
        limit = int(get_flag("limit") or "50")
        return svc.payment_list(limit=limit)

    elif command == "payment.get":
        if not args:
            return format_error("Usage: nm nextmotion payment.get <id>")
        return svc.payment_get(args[0])

    elif command == "payment.update":
        if not args:
            return format_error("Usage: nm nextmotion payment.update <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — payment.update : {args[0]}\nAjouter --confirm pour executer."
        kwargs = {}
        amount = get_flag("amount")
        if amount:
            kwargs["amount"] = amount
        return svc.payment_update(args[0], **kwargs)

    elif command == "payment.delete":
        if not args:
            return format_error("Usage: nm nextmotion payment.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — payment.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.payment_delete(args[0])

    # ---- CREDIT NOTES ----
    elif command == "credit-note.list":
        limit = int(get_flag("limit") or "50")
        return svc.credit_note_list(limit=limit)

    elif command == "credit-note.create":
        invoice_id = get_flag("invoice")
        if not invoice_id:
            return format_error("Usage: nm nextmotion credit-note.create --invoice <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — credit-note.create : invoice={invoice_id}\nAjouter --confirm pour executer."
        return svc.credit_note_create(invoice_id)

    # ---- TREATMENTS (standalone) ----
    elif command == "treatment.get":
        if not args:
            return format_error("Usage: nm nextmotion treatment.get <id>")
        return svc.treatment_get(args[0])

    elif command == "treatment.create":
        patient_id = get_flag("patient")
        if not patient_id:
            return format_error("Usage: nm nextmotion treatment.create --patient <id> [--name ...] [--price ...] --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment.create : patient={patient_id}\nAjouter --confirm pour executer."
        return svc.treatment_create(patient_id, name=get_flag("name"),
            treatment_type=get_flag("type"), price=get_flag("price"),
            quantity=get_flag("quantity"), details=get_flag("details"))

    elif command == "treatment.update":
        if not args:
            return format_error("Usage: nm nextmotion treatment.update <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment.update : {args[0]}\nAjouter --confirm pour executer."
        kwargs = {}
        for key in ("name", "price", "quantity", "details"):
            val = get_flag(key)
            if val:
                kwargs[key] = val
        return svc.treatment_update(args[0], **kwargs)

    elif command == "treatment.delete":
        if not args:
            return format_error("Usage: nm nextmotion treatment.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.treatment_delete(args[0])

    elif command == "treatment.consent-upload":
        if len(args) < 2:
            return format_error("Usage: nm nextmotion treatment.consent-upload <treatment_id> <file_path> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment.consent-upload : treatment={args[0]}, file={args[1]}\nAjouter --confirm pour executer."
        return svc.treatment_consent_upload(args[0], args[1])

    # ---- PRESCRIPTIONS (standalone) ----
    elif command == "prescription.get":
        if not args:
            return format_error("Usage: nm nextmotion prescription.get <id>")
        return svc.prescription_get(args[0])

    elif command == "prescription.create":
        patient_id = get_flag("patient")
        if not patient_id:
            return format_error("Usage: nm nextmotion prescription.create --patient <id> [--name ...] --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — prescription.create : patient={patient_id}\nAjouter --confirm pour executer."
        return svc.prescription_create(patient_id, name=get_flag("name"),
            content=get_flag("content"), doctor=get_flag("doctor"))

    elif command == "prescription.update":
        if not args:
            return format_error("Usage: nm nextmotion prescription.update <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — prescription.update : {args[0]}\nAjouter --confirm pour executer."
        kwargs = {}
        for key in ("name", "content"):
            val = get_flag(key)
            if val:
                kwargs[key] = val
        return svc.prescription_update(args[0], **kwargs)

    elif command == "prescription.delete":
        if not args:
            return format_error("Usage: nm nextmotion prescription.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — prescription.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.prescription_delete(args[0])

    elif command == "prescription.sign":
        if not args:
            return format_error("Usage: nm nextmotion prescription.sign <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — prescription.sign : {args[0]}\nAjouter --confirm pour executer."
        return svc.prescription_sign(args[0])

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

    # ---- STATISTICS ----
    elif command == "stats.income":
        period = get_flag("period") or "month"
        return svc.stats_income(period_type=period, start_time=get_flag("from"), end_time=get_flag("to"))

    elif command == "stats.treatments":
        period = get_flag("period") or "month"
        return svc.stats_treatments(period_type=period, start_time=get_flag("from"), end_time=get_flag("to"))

    elif command == "stats.treatments-income":
        period = get_flag("period") or "month"
        return svc.stats_treatments_income(period_type=period, start_time=get_flag("from"), end_time=get_flag("to"))

    # ---- VISITS ----
    elif command == "visit.list":
        limit = int(get_flag("limit") or "50")
        return svc.visit_list(limit=limit)

    elif command == "visit.get":
        if not args:
            return format_error("Usage: nm nextmotion visit.get <id>")
        return svc.visit_get(args[0])

    elif command == "visit.create":
        patient_id = get_flag("patient")
        if not patient_id:
            return format_error("Usage: nm nextmotion visit.create --patient <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit.create : patient={patient_id}\nAjouter --confirm pour executer."
        return svc.visit_create(patient_id)

    elif command == "visit.update":
        if not args:
            return format_error("Usage: nm nextmotion visit.update <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit.update : {args[0]}\nAjouter --confirm pour executer."
        return svc.visit_update(args[0])

    elif command == "visit.delete":
        if not args:
            return format_error("Usage: nm nextmotion visit.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.visit_delete(args[0])

    # ---- ABSENCES & JOURNEYS ----
    elif command == "absences.list":
        return svc.absences_list(start_date=get_flag("from"), end_date=get_flag("to"),
                                  limit=int(get_flag("limit") or "50"))

    elif command == "journeys.list":
        return svc.journeys_list(limit=int(get_flag("limit") or "50"))

    # ---- DOCTORS ----
    elif command == "doctor.list":
        return svc.doctor_list()

    elif command == "doctor.get":
        if not args:
            return format_error("Usage: nm nextmotion doctor.get <id>")
        return svc.doctor_get(args[0])

    elif command == "doctor.create":
        first = get_flag("first")
        last = get_flag("last")
        if not first or not last:
            return format_error("Usage: nm nextmotion doctor.create --first <prenom> --last <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — doctor.create : {first} {last}\nAjouter --confirm pour executer."
        return svc.doctor_create(first, last, email=get_flag("email"),
            specialty=get_flag("specialty"))

    elif command == "doctor.update":
        if not args:
            return format_error("Usage: nm nextmotion doctor.update <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — doctor.update : {args[0]}\nAjouter --confirm pour executer."
        kwargs = {}
        for key in ("first_name", "last_name", "email", "specialty"):
            val = get_flag(key.replace("_", "-"))
            if val:
                kwargs[key] = val
        return svc.doctor_update(args[0], **kwargs)

    elif command == "doctor.delete":
        if not args:
            return format_error("Usage: nm nextmotion doctor.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — doctor.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.doctor_delete(args[0])

    # ---- PRODUCTS ----
    elif command == "product.list":
        return svc.product_list(limit=int(get_flag("limit") or "50"))

    elif command == "product.get":
        if not args:
            return format_error("Usage: nm nextmotion product.get <id>")
        return svc.product_get(args[0])

    elif command == "product.create":
        name = get_flag("name")
        if not name:
            return format_error("Usage: nm nextmotion product.create --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — product.create : name={name}\nAjouter --confirm pour executer."
        return svc.product_create(name, price=get_flag("price"),
            description=get_flag("description"))

    elif command == "product.update":
        if not args:
            return format_error("Usage: nm nextmotion product.update <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — product.update : {args[0]}\nAjouter --confirm pour executer."
        kwargs = {}
        for key in ("name", "price", "description"):
            val = get_flag(key)
            if val:
                kwargs[key] = val
        return svc.product_update(args[0], **kwargs)

    elif command == "product.delete":
        if not args:
            return format_error("Usage: nm nextmotion product.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — product.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.product_delete(args[0])

    elif command == "global-product.list":
        return svc.global_product_list(limit=int(get_flag("limit") or "50"))

    # ---- WEBHOOKS ----
    elif command == "webhook.list":
        return svc.webhook_list(limit=int(get_flag("limit") or "50"))

    elif command == "webhook.get":
        if not args:
            return format_error("Usage: nm nextmotion webhook.get <id>")
        return svc.webhook_get(args[0])

    elif command == "webhook.create":
        url = get_flag("url")
        events_str = get_flag("events")
        if not url or not events_str:
            return format_error("Usage: nm nextmotion webhook.create --url <url> --events <evt1,evt2> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — webhook.create : url={url}, events={events_str}\nAjouter --confirm pour executer."
        events = [e.strip() for e in events_str.split(",")]
        return svc.webhook_create(url, events)

    elif command == "webhook.update":
        if not args:
            return format_error("Usage: nm nextmotion webhook.update <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — webhook.update : {args[0]}\nAjouter --confirm pour executer."
        kwargs = {}
        url = get_flag("url")
        if url:
            kwargs["url"] = url
        events_str = get_flag("events")
        if events_str:
            kwargs["events"] = [e.strip() for e in events_str.split(",")]
        return svc.webhook_update(args[0], **kwargs)

    elif command == "webhook.delete":
        if not args:
            return format_error("Usage: nm nextmotion webhook.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — webhook.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.webhook_delete(args[0])

    # ---- COMMUNICATION TEMPLATES ----
    elif command == "comm-template.list":
        return svc.comm_template_list(limit=int(get_flag("limit") or "50"))

    elif command == "comm-template.get":
        if not args:
            return format_error("Usage: nm nextmotion comm-template.get <id>")
        return svc.comm_template_get(args[0])

    elif command == "comm-record.create":
        template = get_flag("template")
        patient = get_flag("patient")
        if not template:
            return format_error("Usage: nm nextmotion comm-record.create --template <id> --patient <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — comm-record.create : template={template}\nAjouter --confirm pour executer."
        return svc.comm_record_create(template=template, patient=patient)

    # ---- VISIT TYPE CATEGORIES ----
    elif command == "visit-type-category.list":
        return svc.visit_type_category_list(limit=int(get_flag("limit") or "50"))

    elif command == "visit-type-category.get":
        if not args:
            return format_error("Usage: nm nextmotion visit-type-category.get <id>")
        return svc.visit_type_category_get(args[0])

    elif command == "visit-type-category.create":
        name = get_flag("name")
        if not name:
            return format_error("Usage: nm nextmotion visit-type-category.create --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit-type-category.create : name={name}\nAjouter --confirm pour executer."
        return svc.visit_type_category_create(name)

    elif command == "visit-type-category.update":
        if not args:
            return format_error("Usage: nm nextmotion visit-type-category.update <id> --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit-type-category.update : {args[0]}\nAjouter --confirm pour executer."
        return svc.visit_type_category_update(args[0], name=get_flag("name"))

    elif command == "visit-type-category.delete":
        if not args:
            return format_error("Usage: nm nextmotion visit-type-category.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit-type-category.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.visit_type_category_delete(args[0])

    # ---- VISIT TYPE EXTENSIONS ----
    elif command == "visit-type.get":
        if not args:
            return format_error("Usage: nm nextmotion visit-type.get <id>")
        return svc.visit_type_get(args[0])

    elif command == "visit-type.create":
        name = get_flag("name")
        if not name:
            return format_error("Usage: nm nextmotion visit-type.create --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit-type.create : name={name}\nAjouter --confirm pour executer."
        return svc.visit_type_create(name, category=get_flag("category"))

    elif command == "visit-type.update":
        if not args:
            return format_error("Usage: nm nextmotion visit-type.update <id> --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit-type.update : {args[0]}\nAjouter --confirm pour executer."
        return svc.visit_type_update(args[0], name=get_flag("name"))

    elif command == "visit-type.delete":
        if not args:
            return format_error("Usage: nm nextmotion visit-type.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — visit-type.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.visit_type_delete(args[0])

    # ---- SUB VISIT TYPES ----
    elif command == "sub-visit-type.list":
        return svc.sub_visit_type_list(limit=int(get_flag("limit") or "50"))

    elif command == "sub-visit-type.get":
        if not args:
            return format_error("Usage: nm nextmotion sub-visit-type.get <id>")
        return svc.sub_visit_type_get(args[0])

    # ---- TREATMENT TYPES ----
    elif command == "treatment-type.list":
        return svc.treatment_type_list(limit=int(get_flag("limit") or "50"))

    elif command == "treatment-type.get":
        if not args:
            return format_error("Usage: nm nextmotion treatment-type.get <id>")
        return svc.treatment_type_get(args[0])

    elif command == "treatment-type.create":
        name = get_flag("name")
        if not name:
            return format_error("Usage: nm nextmotion treatment-type.create --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment-type.create : name={name}\nAjouter --confirm pour executer."
        return svc.treatment_type_create(name)

    elif command == "treatment-type.update":
        if not args:
            return format_error("Usage: nm nextmotion treatment-type.update <id> --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment-type.update : {args[0]}\nAjouter --confirm pour executer."
        return svc.treatment_type_update(args[0], name=get_flag("name"))

    elif command == "treatment-type.delete":
        if not args:
            return format_error("Usage: nm nextmotion treatment-type.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment-type.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.treatment_type_delete(args[0])

    # ---- TREATMENT PRICINGS ----
    elif command == "treatment-pricing.list":
        return svc.treatment_pricing_list(limit=int(get_flag("limit") or "50"))

    elif command == "treatment-pricing.get":
        if not args:
            return format_error("Usage: nm nextmotion treatment-pricing.get <id>")
        return svc.treatment_pricing_get(args[0])

    # ---- TREATMENT PACKAGES ----
    elif command == "treatment-package.list":
        return svc.treatment_package_list(limit=int(get_flag("limit") or "50"))

    elif command == "treatment-package.get":
        if not args:
            return format_error("Usage: nm nextmotion treatment-package.get <id>")
        return svc.treatment_package_get(args[0])

    elif command == "treatment-package.create":
        name = get_flag("name")
        if not name:
            return format_error("Usage: nm nextmotion treatment-package.create --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment-package.create : name={name}\nAjouter --confirm pour executer."
        return svc.treatment_package_create(name)

    elif command == "treatment-package.update":
        if not args:
            return format_error("Usage: nm nextmotion treatment-package.update <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment-package.update : {args[0]}\nAjouter --confirm pour executer."
        return svc.treatment_package_update(args[0], name=get_flag("name"))

    elif command == "treatment-package.delete":
        if not args:
            return format_error("Usage: nm nextmotion treatment-package.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment-package.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.treatment_package_delete(args[0])

    elif command == "treatment-package.extract":
        if not args:
            return format_error("Usage: nm nextmotion treatment-package.extract <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — treatment-package.extract : {args[0]}\nAjouter --confirm pour executer."
        return svc.treatment_package_extract(args[0])

    # ---- DOCUMENT TEMPLATES ----
    elif command == "doc-template.list":
        return svc.doc_template_list(limit=int(get_flag("limit") or "50"))

    elif command == "doc-template.get":
        if not args:
            return format_error("Usage: nm nextmotion doc-template.get <id>")
        return svc.doc_template_get(args[0])

    elif command == "doc-template.create":
        name = get_flag("name")
        if not name:
            return format_error("Usage: nm nextmotion doc-template.create --name <nom> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — doc-template.create : name={name}\nAjouter --confirm pour executer."
        return svc.doc_template_create(name)

    elif command == "doc-template.delete":
        if not args:
            return format_error("Usage: nm nextmotion doc-template.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — doc-template.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.doc_template_delete(args[0])

    # ---- SURVEY FORMS ----
    elif command == "survey.list":
        return svc.survey_list(limit=int(get_flag("limit") or "50"))

    elif command == "survey.get":
        if not args:
            return format_error("Usage: nm nextmotion survey.get <id>")
        return svc.survey_get(args[0])

    # ---- ROOMS ----
    elif command == "room.list":
        return svc.room_list(limit=int(get_flag("limit") or "50"))

    elif command == "room.get":
        if not args:
            return format_error("Usage: nm nextmotion room.get <id>")
        return svc.room_get(args[0])

    # ---- DEVICES ----
    elif command == "device.list":
        return svc.device_list(limit=int(get_flag("limit") or "50"))

    elif command == "device.get":
        if not args:
            return format_error("Usage: nm nextmotion device.get <id>")
        return svc.device_get(args[0])

    # ---- PAYMENT MEDIUMS ----
    elif command == "payment-medium.list":
        return svc.payment_medium_list(limit=int(get_flag("limit") or "50"))

    elif command == "payment-medium.get":
        if not args:
            return format_error("Usage: nm nextmotion payment-medium.get <id>")
        return svc.payment_medium_get(args[0])

    # ---- ACCOUNTING ----
    elif command == "accounting.list":
        return svc.accounting_list(limit=int(get_flag("limit") or "50"))

    elif command == "accounting.get":
        if not args:
            return format_error("Usage: nm nextmotion accounting.get <id>")
        return svc.accounting_get(args[0])

    # ---- FEATURES ----
    elif command == "feature.list":
        return svc.feature_list()

    # ---- CLINIC ----
    elif command == "clinic.list":
        return svc.clinic_list()

    # ---- USER ----
    elif command == "user.me":
        return svc.user_me()

    # ---- LEAD DELETE ----
    elif command == "lead.delete":
        if not args:
            return format_error("Usage: nm nextmotion lead.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — lead.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.lead_delete(args[0])

    # ---- QUOTE EXTENSIONS ----
    elif command == "quote.delete":
        if not args:
            return format_error("Usage: nm nextmotion quote.delete <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — quote.delete : {args[0]}\nAjouter --confirm pour executer."
        return svc.quote_delete(args[0])

    elif command == "quote.validate":
        if not args:
            return format_error("Usage: nm nextmotion quote.validate <id> --confirm")
        if "--confirm" not in args:
            return f"DRY RUN — quote.validate : {args[0]}\nAjouter --confirm pour executer."
        return svc.quote_validate(args[0])

    # ---- OPENING HOURS ----
    elif command == "opening-hour.get":
        if not args:
            return format_error("Usage: nm nextmotion opening-hour.get <id>")
        return svc.opening_hour_get(args[0])

    # ---- RDV TREATMENTS ----
    elif command == "rdv.treatments":
        if not args:
            return format_error("Usage: nm nextmotion rdv.treatments <rdv_id>")
        return svc.rdv_treatments(args[0])

    # ---- MEDICAL HISTORY (clinic) ----
    elif command == "medical-history.config":
        return svc.clinic_medical_history()

    else:
        return format_error(f"Commande Nextmotion inconnue: {command}")
