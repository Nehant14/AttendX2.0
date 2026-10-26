"""Tests for CSV export."""
import csv
import io
import pytest
from app.services.export import generate_csv, CSV_HEADER


class TestCSVExport:
    def _parse_csv(self, content: bytes) -> list[dict]:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        return list(reader)

    def test_csv_has_bom(self):
        content = generate_csv([])
        assert content[:3] == b"\xef\xbb\xbf"

    def test_csv_header(self):
        content = generate_csv([])
        text = content.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        assert header == CSV_HEADER

    def test_row_count(self):
        rows = [
            {
                "session_date": "2026-10-21",
                "period": 1,
                "course_code": "CS101",
                "roll_no": "S001",
                "full_name": "Alice",
                "status": "present",
                "similarity": 0.75,
                "marked_by": "auto",
            },
            {
                "session_date": "2026-10-21",
                "period": 1,
                "course_code": "CS101",
                "roll_no": "S002",
                "full_name": "Bob",
                "status": "absent",
                "similarity": None,
                "marked_by": "auto",
            },
        ]
        content = generate_csv(rows)
        parsed = self._parse_csv(content)
        assert len(parsed) == 2

    def test_absent_similarity_empty(self):
        rows = [
            {
                "session_date": "2026-10-21",
                "period": 1,
                "course_code": "CS101",
                "roll_no": "S001",
                "full_name": "Alice",
                "status": "absent",
                "similarity": None,
                "marked_by": "auto",
            }
        ]
        content = generate_csv(rows)
        parsed = self._parse_csv(content)
        assert parsed[0]["similarity"] == ""

    def test_present_similarity_formatted(self):
        rows = [
            {
                "session_date": "2026-10-21",
                "period": 1,
                "course_code": "CS101",
                "roll_no": "S001",
                "full_name": "Alice",
                "status": "present",
                "similarity": 0.756234,
                "marked_by": "auto",
            }
        ]
        content = generate_csv(rows)
        parsed = self._parse_csv(content)
        assert parsed[0]["similarity"] == "0.7562"

    def test_utf8_names(self):
        rows = [
            {
                "session_date": "2026-10-21",
                "period": 1,
                "course_code": "CS101",
                "roll_no": "S001",
                "full_name": "Aïcha Müller",
                "status": "present",
                "similarity": 0.80,
                "marked_by": "auto",
            }
        ]
        content = generate_csv(rows)
        parsed = self._parse_csv(content)
        assert parsed[0]["full_name"] == "Aïcha Müller"
