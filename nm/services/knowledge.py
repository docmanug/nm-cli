"""OpenAI Vector Store RAG search — base de connaissances cabinet.

Uses the OpenAI Responses API with file_search to query consultation
transcripts stored in an OpenAI Vector Store.
"""
from __future__ import annotations
import requests
from nm.core.output import format_error


class KnowledgeService:
    def __init__(self, api_key: str, vector_store_id: str):
        self._api_key = api_key
        self._vector_store_id = vector_store_id

    def search(self, query: str) -> str:
        resp = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "tools": [{"type": "file_search", "vector_store_ids": [self._vector_store_id]}],
                "input": (
                    f"Cherche dans les transcriptions de consultations du cabinet du "
                    f"Docteur Elard les informations pertinentes pour : {query}. "
                    f"Retourne les extraits les plus pertinents. "
                    f"REGLE ABSOLUE : ne JAMAIS inclure de noms, prenoms, dates de "
                    f"naissance, numeros de telephone ou emails de patients. "
                    f"Anonymise tout : remplace par 'un patient', 'une patiente'. "
                    f"Ne retourne que les informations medicales et pratiques."
                ),
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        output = data.get("output", [])
        texts = []
        for item in output:
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        texts.append(content["text"])
        if not texts:
            return "Aucune information pertinente trouvee dans la base de connaissances."
        return "\n".join(texts)


def handle_knowledge(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("knowledge")
    svc = KnowledgeService(
        api_key=creds["api_key"],
        vector_store_id=creds["vector_store_id"],
    )

    # nm-cli joins command parts with dots: "search botox" → command="search.botox"
    # For knowledge, only "search" is a command — everything after is the query
    if command.startswith("search"):
        # Extract query from dotted command + args
        query_from_cmd = command[len("search"):].lstrip(".")
        query_parts = ([query_from_cmd] if query_from_cmd else []) + list(args)
        query = " ".join(query_parts)
        if not query:
            return format_error('Usage: nm knowledge search "votre question"')
        return svc.search(query)
    else:
        return format_error(f"Commande knowledge inconnue: {command}")
