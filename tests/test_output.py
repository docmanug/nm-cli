import pytest
from nm.core.output import format_leads_list, format_lead_detail, format_error, format_limit_hit


def test_format_leads_list_empty():
    result = format_leads_list([])
    assert "Aucun" in result

def test_format_leads_list():
    leads = [
        {"id": "123", "name": "Dr Dupont", "status": "New", "days": 3,
         "phone": "+33612345678", "last_contact": None},
        {"id": "456", "name": "Dr Martin", "status": "Nurturing", "days": 5,
         "phone": "+33698765432", "last_contact": "WhatsApp il y a 2j"},
    ]
    result = format_leads_list(leads)
    assert "2 leads" in result
    assert "Dr Dupont" in result
    assert "Dr Martin" in result
    assert "+33612345678" in result
    assert "aucun" in result.lower()

def test_format_lead_detail():
    lead = {
        "id": "123", "name": "Dr Dupont", "status": "Contacted",
        "phone": "+33612345678", "email": "dupont@clinic.fr",
        "company": "Clinique Dupont", "notes": ["Interesse par la v3"],
    }
    result = format_lead_detail(lead)
    assert "Dr Dupont" in result
    assert "Contacted" in result
    assert "Clinique Dupont" in result

def test_format_error():
    result = format_error("Commande 'boards.delete' non autorisee pour le profil sdr")
    assert result.startswith("Error:")

def test_format_limit_hit():
    result = format_limit_hit("whatsapp", 20, 20)
    assert "20/20" in result
    assert "whatsapp" in result.lower()
