"""Validation des fichiers envoyés : extension autorisée + signature binaire (magic bytes)."""

import os
import re

DOCUMENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain", ".csv": "text/csv",
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".mp3": "audio/mpeg", ".wav": "audio/wav",
    ".zip": "application/zip", ".psd": "image/vnd.adobe.photoshop",
}

# Types d'image acceptés pour le portfolio public (SVG exclu : il peut contenir du script).
IMAGE_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif",
}


def sniff_ok(ext: str, head: bytes) -> bool:
    """Contrôle la signature quand elle est connue ; accepte les formats sans signature simple."""
    ext = ext.lower()
    if ext == ".pdf":
        return head.startswith(b"%PDF-")
    if ext == ".png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if ext in (".jpg", ".jpeg"):
        return head.startswith(b"\xff\xd8\xff")
    if ext == ".gif":
        return head.startswith((b"GIF87a", b"GIF89a"))
    if ext == ".webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if ext in (".docx", ".xlsx", ".pptx", ".zip"):
        return head.startswith(b"PK")
    if ext == ".psd":
        return head.startswith(b"8BPS")
    return True


def safe_display_name(filename: str | None) -> str:
    """Nom d'affichage : sans chemin ni caractères de contrôle, 150 caractères max."""
    name = os.path.basename((filename or "fichier").replace("\\", "/"))
    name = re.sub(r"[\x00-\x1f\x7f]", "", name).strip() or "fichier"
    return name[:150]
