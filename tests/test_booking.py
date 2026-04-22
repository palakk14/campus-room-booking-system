import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import patch, MagicMock
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret'
    with app.test_client() as c:
        yield c


@pytest.fixture
def logged_in_client(client):
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['name'] = 'Test User'
        sess['role'] = 'user'
        sess['csrf_token'] = 'test-csrf-token'
    return client


# ─────────────────────────────────────────────
# AUTH ROUTE TESTS
# ─────────────────────────────────────────────

class TestAuthRoutes:

    def test_home_page_loads(self, client):
        resp = client.get('/')
        assert resp.status_code == 200

    def test_login_page_loads(self, client):
        resp = client.get('/login')
        assert resp.status_code == 200

    def test_register_page_loads(self, client):
        resp = client.get('/register')
        assert resp.status_code == 200

    def test_dashboard_redirects_when_not_logged_in(self, client):
        resp = client.get('/dashboard')
        assert resp.status_code == 302
        assert '/login' in resp.headers['Location']

    def test_rooms_redirects_when_not_logged_in(self, client):
        resp = client.get('/rooms')
        assert resp.status_code == 302

    def test_mybookings_redirects_when_not_logged_in(self, client):
        resp = client.get('/mybookings')
        assert resp.status_code == 302

    def test_logout_clears_session(self, logged_in_client):
        resp = logged_in_client.get('/logout')
        assert resp.status_code == 302
        with logged_in_client.session_transaction() as sess:
            assert 'user_id' not in sess


# ─────────────────────────────────────────────
# ADMIN ROUTE TESTS
# ─────────────────────────────────────────────

class TestAdminRoutes:

    def test_admin_redirects_non_admin(self, logged_in_client):
        # user role is 'user', not 'admin'
        resp = logged_in_client.get('/admin')
        assert resp.status_code == 302
        assert '/dashboard' in resp.headers['Location']

    def test_addroom_redirects_non_admin(self, logged_in_client):
        resp = logged_in_client.get('/addroom')
        assert resp.status_code == 302

    def test_analytics_redirects_non_admin(self, logged_in_client):
        resp = logged_in_client.get('/analytics')
        assert resp.status_code == 302


# ─────────────────────────────────────────────
# BOOKING LOGIC TESTS
# ─────────────────────────────────────────────

class TestBookingValidation:

    def test_end_time_before_start_time_is_rejected(self, logged_in_client):
        with patch('booking.get_db_connection') as mock_conn:
            mock_cur = MagicMock()
            mock_conn.return_value.cursor.return_value = mock_cur
            mock_cur.fetchone.return_value = None

            resp = logged_in_client.post('/book/1', data={
                'date': '2026-05-01',
                'start_time': '14:00',
                'end_time': '10:00',   # end before start
                'purpose': 'Test',
                'csrf_token': 'test-csrf-token'
            })
            # Should redirect back (not process booking)
            assert resp.status_code == 302

    def test_book_room_page_loads_for_logged_in_user(self, logged_in_client):
        resp = logged_in_client.get('/book/1')
        assert resp.status_code == 200
