"""Small server-free checks. Run unittest discover from the project root."""
import unittest
from datetime import date
from unittest.mock import patch
import psycopg2
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.main import app
from app.routes.telemetry import Reading


class SmokeChecks(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_dashboard_and_static_assets(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        for section in ('users', 'devices', 'challenges', 'metadata', 'telemetry', 'social', 'leaderboard'):
            self.assertIn(f'id="{section}"', response.text)
        self.assertEqual(self.client.get('/static/app.js').status_code, 200)
        self.assertEqual(self.client.get('/static/style.css').status_code, 200)

    def test_all_required_api_operations_exist(self):
        paths = self.client.get('/openapi.json').json()['paths']
        for resource, identifier in [('users', 'user_id'), ('devices', 'device_id'), ('challenges', 'challenge_id')]:
            self.assertTrue({'get', 'post'} <= paths[f'/{resource}'].keys())
            self.assertTrue({'get', 'put', 'delete'} <= paths[f'/{resource}/{{{identifier}}}'].keys())
        self.assertEqual(sum(len([m for m in methods if m in ('get', 'post', 'put', 'delete')])
                             for methods in paths.values()), 29)

    def test_validation_before_database_access(self):
        cases = [
            ('post', '/challenges', {'challenge_id': 'CH9', 'challenge_name': 'Run',
                                    'start_date': '2026-10-12', 'end_date': '2026-10-11'}),
            ('post', '/social/follow', {'user_id': 'U101', 'target_id': 'U101'}),
            ('put', '/leaderboard/U101', {'steps': -1}),
            ('post', '/users', {'user_id': 'U999', 'first_name': ' ', 'email': 'jiya@example.test'}),
            ('post', '/metadata', {'device_id': 'PB101', 'model': 'PulseBand X1',
                                   'sensors': [], 'settings': {'$bad': True}}),
        ]
        for method, path, body in cases:
            with self.subTest(path=path):
                self.assertEqual(self.client.request(method, path, json=body).status_code, 422)
        self.assertEqual(self.client.get('/telemetry/PB101').status_code, 422)

    def test_utc_partition_and_precision(self):
        data = dict(device_id='PB101', reading_date='2026-10-11',
                    reading_ts='2026-10-12T01:00:00+05:30', heart_rate=80, steps=160,
                    spo2=98, latitude=12.9718, longitude=80.2208)
        reading = Reading(**data)
        self.assertEqual(reading.reading_ts.date(), date(2026, 10, 11))
        for timestamp in ('2026-10-11T10:00:00', '2026-10-11T10:00:00.000001Z', '2026-10-12T10:00:00Z'):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValidationError):
                Reading(**{**data, 'reading_ts': timestamp})

    def test_database_errors_become_http_errors(self):
        for error, expected in [(psycopg2.OperationalError(), 503),
                                (psycopg2.errors.UniqueViolation(), 409),
                                (psycopg2.errors.ForeignKeyViolation(), 409)]:
            with patch('app.db.postgres.psycopg2.connect', side_effect=error):
                self.assertEqual(self.client.get('/users').status_code, expected)


if __name__ == '__main__':
    unittest.main()
