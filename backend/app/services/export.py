"""CSV export service."""
from __future__ import annotations

import csv
import io
from typing import Any

CSV_HEADER = [
    "session_date", "period", "course_code", "roll_no",
    "full_name", "status", "similarity", "marked_by",
]


def generate_csv(rows: list[dict[str, Any]]) -> bytes:
    """
    Generate a UTF-8-with-BOM CSV from attendance rows.

    Each row must contain: session_date, period, course_code, roll_no,
                            full_name, status, similarity, marked_by.

    similarity is formatted to 4 decimal places; empty for absent students.
    Returns bytes starting with the UTF-8 BOM (\\xef\\xbb\\xbf).
    """
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf, fieldnames=CSV_HEADER, extrasaction="ignore", lineterminator="\r\n"
    )
    writer.writeheader()

    for row in rows:
        sim = row.get("similarity")
        out = {k: row.get(k, "") for k in CSV_HEADER}
        out["similarity"] = f"{sim:.4f}" if sim is not None else ""
        out["session_date"] = str(row.get("session_date", ""))
        out["period"] = str(row.get("period", ""))
        writer.writerow(out)

    content = buf.getvalue()
    return "\ufeff".encode("utf-8") + content.encode("utf-8")
