from __future__ import annotations
import json
import os
import requests
from nm.core.output import format_error

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_URL = "https://www.googleapis.com/drive/v3"
GOOGLE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3"


class GDriveService:
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._access_token = None

    def _get_token(self) -> str:
        if self._access_token:
            return self._access_token
        resp = requests.post(GOOGLE_TOKEN_URL, data={
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "refresh_token": self._refresh_token,
            "grant_type": "refresh_token",
        })
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]
        return self._access_token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def _get(self, path: str, params: dict | None = None) -> dict:
        resp = requests.get(
            f"{GOOGLE_DRIVE_URL}{path}",
            headers=self._headers(),
            params=params or {},
        )
        resp.raise_for_status()
        return resp.json()

    def files_list(self, query: str = "", limit: int = 20,
                   folder_id: str = "") -> str:
        params = {
            "pageSize": limit,
            "fields": "files(id,name,mimeType,webViewLink,createdTime,size)",
            "orderBy": "modifiedTime desc",
        }
        q_parts = []
        if query:
            q_parts.append(f"name contains '{query}'")
        if folder_id:
            q_parts.append(f"'{folder_id}' in parents")
        q_parts.append("trashed = false")
        params["q"] = " and ".join(q_parts)

        data = self._get("/files", params)
        files = data.get("files", [])
        if not files:
            return "Aucun fichier trouve."
        lines = [f"{len(files)} fichiers :\n"]
        for f in files:
            size = f.get("size", "?")
            if size != "?" and size:
                size_mb = int(size) / 1024 / 1024
                size = f"{size_mb:.1f}MB"
            lines.append(
                f"  [{f.get('mimeType', '?').split('.')[-1]}] {f.get('name', '?')}"
            )
            lines.append(
                f"    ID: {f.get('id', '?')} | {size}"
            )
            link = f.get("webViewLink", "")
            if link:
                lines.append(f"    Link: {link}")
        return "\n".join(lines)

    def files_get(self, file_id: str) -> str:
        data = self._get(f"/files/{file_id}", {
            "fields": "id,name,mimeType,webViewLink,webContentLink,createdTime,modifiedTime,size,parents"
        })
        lines = [
            f"{data.get('name', '?')}",
            f"  ID: {data.get('id', '?')}",
            f"  Type: {data.get('mimeType', '?')}",
            f"  Size: {data.get('size', 'N/A')}",
            f"  Created: {(data.get('createdTime', '') or '')[:16]}",
            f"  Modified: {(data.get('modifiedTime', '') or '')[:16]}",
            f"  View: {data.get('webViewLink', 'N/A')}",
            f"  Download: {data.get('webContentLink', 'N/A')}",
        ]
        return "\n".join(lines)

    def files_upload(self, file_path: str, folder_id: str = "",
                     mime_type: str = "") -> str:
        if not os.path.exists(file_path):
            return format_error(f"Fichier introuvable: {file_path}")

        filename = os.path.basename(file_path)
        if not mime_type:
            ext = os.path.splitext(filename)[1].lower()
            mime_map = {
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
                ".pdf": "application/pdf", ".gif": "image/gif",
                ".svg": "image/svg+xml", ".webp": "image/webp",
            }
            mime_type = mime_map.get(ext, "application/octet-stream")

        # Metadata
        metadata = {"name": filename}
        if folder_id:
            metadata["parents"] = [folder_id]

        # Multipart upload
        file_size = os.path.getsize(file_path)

        # Simple upload for files < 5MB, resumable for larger
        if file_size < 5 * 1024 * 1024:
            resp = requests.post(
                f"{GOOGLE_UPLOAD_URL}/files?uploadType=multipart&fields=id,name,webViewLink",
                headers=self._headers(),
                files={
                    "metadata": ("metadata", json.dumps(metadata), "application/json"),
                    "file": (filename, open(file_path, "rb"), mime_type),
                },
            )
        else:
            # Resumable upload
            init_resp = requests.post(
                f"{GOOGLE_UPLOAD_URL}/files?uploadType=resumable",
                headers={**self._headers(), "Content-Type": "application/json"},
                json=metadata,
            )
            init_resp.raise_for_status()
            upload_url = init_resp.headers["Location"]

            with open(file_path, "rb") as f:
                resp = requests.put(
                    upload_url,
                    headers={"Content-Type": mime_type},
                    data=f,
                )

        resp.raise_for_status()
        data = resp.json()
        link = data.get("webViewLink", "")
        return f"Upload OK — {data.get('name', '?')} | ID: {data.get('id', '?')}" + \
               (f"\nLink: {link}" if link else "")

    def files_share(self, file_id: str) -> str:
        """Make a file publicly viewable and return the link."""
        resp = requests.post(
            f"{GOOGLE_DRIVE_URL}/files/{file_id}/permissions",
            headers={**self._headers(), "Content-Type": "application/json"},
            json={"role": "reader", "type": "anyone"},
        )
        resp.raise_for_status()

        # Get the webViewLink
        data = self._get(f"/files/{file_id}", {"fields": "webViewLink,webContentLink"})
        return f"Fichier partage publiquement\n  View: {data.get('webViewLink', 'N/A')}\n  Download: {data.get('webContentLink', 'N/A')}"

    def folders_list(self, parent_id: str = "") -> str:
        params = {
            "pageSize": 50,
            "fields": "files(id,name)",
            "orderBy": "name",
            "q": "mimeType = 'application/vnd.google-apps.folder' and trashed = false",
        }
        if parent_id:
            params["q"] += f" and '{parent_id}' in parents"
        data = self._get("/files", params)
        folders = data.get("files", [])
        if not folders:
            return "Aucun dossier."
        lines = [f"{len(folders)} dossiers :\n"]
        for f in folders:
            lines.append(f"  [{f.get('id', '?')}] {f.get('name', '?')}")
        return "\n".join(lines)

    def folders_create(self, name: str, parent_id: str = "") -> str:
        metadata = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            metadata["parents"] = [parent_id]
        resp = requests.post(
            f"{GOOGLE_DRIVE_URL}/files",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=metadata,
            params={"fields": "id,name,webViewLink"},
        )
        resp.raise_for_status()
        data = resp.json()
        return f"Dossier cree: {data.get('name', '?')} | ID: {data.get('id', '?')}\n  Link: {data.get('webViewLink', 'N/A')}"


def handle_gdrive(command: str, args: list, profile) -> str:
    from nm.core.auth import get_credentials

    creds = get_credentials("gdrive")
    svc = GDriveService(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        refresh_token=creds["refresh_token"],
    )

    def _flag(name):
        for i, a in enumerate(args):
            if a == f"--{name}" and i + 1 < len(args):
                return args[i + 1]
        return ""

    if command == "files.list":
        query = _flag("query") or (_flag("search")) or ""
        if not query and args and not args[0].startswith("-"):
            query = args[0]
        folder_id = _flag("folder")
        limit = int(_flag("limit") or "20")
        return svc.files_list(query, limit, folder_id)

    elif command == "files.get":
        if not args:
            return format_error("Usage: nm gdrive files get <file_id>")
        return svc.files_get(args[0])

    elif command == "files.upload":
        file_path = _flag("file") or (args[0] if args else "")
        if not file_path:
            return format_error('Usage: nm gdrive files upload --file /path/to/file [--folder <folder_id>]')
        folder_id = _flag("folder")
        return svc.files_upload(file_path, folder_id)

    elif command == "files.share":
        if not args:
            return format_error("Usage: nm gdrive files share <file_id>")
        return svc.files_share(args[0])

    elif command == "folders.list":
        parent_id = _flag("parent") or ""
        return svc.folders_list(parent_id)

    elif command == "folders.create":
        name = _flag("name") or (args[0] if args else "")
        if not name:
            return format_error('Usage: nm gdrive folders create --name "Nom du dossier" [--parent <folder_id>]')
        parent_id = _flag("parent")
        return svc.folders_create(name, parent_id)

    else:
        return format_error(f"Commande GDrive inconnue: {command}")
