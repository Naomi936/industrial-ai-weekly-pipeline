"""Offline boundary regression; does not verify journalism or Office compatibility."""
import csv
import datetime as dt
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('validator', ROOT / 'skills/industrial-ai-weekly-pipeline/scripts/generate_report.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class SourceValidation(unittest.TestCase):
    def setUp(self):
        with (ROOT / 'examples/synthetic_sources.csv').open(encoding='utf-8', newline='') as f:
            self.rows = list(csv.DictReader(f))

    def validate(self, rows, header=None):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'sources.csv'
            fields = header or MODULE.REQUIRED_COLUMNS
            with path.open('w', encoding='utf-8', newline='') as f:
                w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
                w.writeheader();w.writerows(rows)
            return MODULE.read_sources(path, dt.date(2026,10,19), dt.date(2026,10,25))

    def test_accepts_minimum_balanced_sample(self):
        self.assertEqual(len(self.validate(self.rows)),25)

    def test_accepts_maximum(self):
        extra=[]
        for i in range(5):
            row=dict(self.rows[i*5]);row['title'] += ' extra';row['link'] += '-extra';extra.append(row)
        self.assertEqual(len(self.validate(self.rows+extra)),30)

    def test_rejects_too_few(self):
        with self.assertRaises(SystemExit): self.validate(self.rows[:-1])

    def test_rejects_too_many(self):
        with self.assertRaises(SystemExit): self.validate(self.rows+self.rows[:6])

    def test_rejects_sparse_category_with_valid_total(self):
        self.rows[0]['category']=MODULE.CATEGORIES[1]
        with self.assertRaises(SystemExit): self.validate(self.rows)

    def test_rejects_outside_publication_date(self):
        self.rows[0]['published_at']='2026-10-18'
        with self.assertRaises(SystemExit): self.validate(self.rows)

    def test_rejects_outside_event_date(self):
        self.rows[0]['event_date']='2026-10-26'
        with self.assertRaises(SystemExit): self.validate(self.rows)

    def test_rejects_wrong_schema(self):
        with self.assertRaises(SystemExit): self.validate(self.rows, ['title','content','link','category'])

    def test_rejects_unknown_category(self):
        self.rows[0]['category']='unknown'
        with self.assertRaises(SystemExit): self.validate(self.rows)

    def test_rejects_empty_link(self):
        self.rows[0]['link']=''
        with self.assertRaises(SystemExit): self.validate(self.rows)

if __name__ == '__main__': unittest.main()
