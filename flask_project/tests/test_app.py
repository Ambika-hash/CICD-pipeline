import pytest
from app import create_app, db


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(client):
    client.post('/auth/register', json={'username': 'testuser', 'password': 'testpass123'})
    res = client.post('/auth/login', json={'username': 'testuser', 'password': 'testpass123'})
    token = res.get_json()['access_token']
    return {'Authorization': f'Bearer {token}'}


# ── Health ────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        res = client.get('/health')
        assert res.status_code == 200
        assert res.get_json()['status'] == 'ok'


# ── Auth ──────────────────────────────────────────────────

class TestAuth:
    def test_register(self, client):
        res = client.post('/auth/register', json={'username': 'alice', 'password': 'pass123'})
        assert res.status_code == 201
        assert res.get_json()['user']['username'] == 'alice'

    def test_register_duplicate(self, client):
        client.post('/auth/register', json={'username': 'alice', 'password': 'pass123'})
        res = client.post('/auth/register', json={'username': 'alice', 'password': 'pass123'})
        assert res.status_code == 409

    def test_register_missing_fields(self, client):
        res = client.post('/auth/register', json={'username': 'alice'})
        assert res.status_code == 400

    def test_login_success(self, client):
        client.post('/auth/register', json={'username': 'alice', 'password': 'pass123'})
        res = client.post('/auth/login', json={'username': 'alice', 'password': 'pass123'})
        assert res.status_code == 200
        assert 'access_token' in res.get_json()

    def test_login_wrong_password(self, client):
        client.post('/auth/register', json={'username': 'alice', 'password': 'pass123'})
        res = client.post('/auth/login', json={'username': 'alice', 'password': 'wrong'})
        assert res.status_code == 401

    def test_me_authenticated(self, client, auth_headers):
        res = client.get('/auth/me', headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()['username'] == 'testuser'

    def test_me_unauthenticated(self, client):
        res = client.get('/auth/me')
        assert res.status_code == 401


# ── Items ─────────────────────────────────────────────────

class TestItems:
    def test_create_item(self, client, auth_headers):
        res = client.post('/api/items', json={'name': 'Widget', 'category': 'tools'}, headers=auth_headers)
        assert res.status_code == 201
        assert res.get_json()['item']['name'] == 'Widget'

    def test_create_item_no_name(self, client, auth_headers):
        res = client.post('/api/items', json={'description': 'no name'}, headers=auth_headers)
        assert res.status_code == 400

    def test_get_items_empty(self, client, auth_headers):
        res = client.get('/api/items', headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()['items'] == []

    def test_get_items_with_data(self, client, auth_headers):
        client.post('/api/items', json={'name': 'A'}, headers=auth_headers)
        client.post('/api/items', json={'name': 'B'}, headers=auth_headers)
        res = client.get('/api/items', headers=auth_headers)
        assert res.get_json()['total'] == 2

    def test_get_item_by_id(self, client, auth_headers):
        created = client.post('/api/items', json={'name': 'Gadget'}, headers=auth_headers).get_json()
        item_id = created['item']['id']
        res = client.get(f'/api/items/{item_id}', headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()['name'] == 'Gadget'

    def test_get_nonexistent_item(self, client, auth_headers):
        res = client.get('/api/items/9999', headers=auth_headers)
        assert res.status_code == 404

    def test_update_item(self, client, auth_headers):
        created = client.post('/api/items', json={'name': 'Old'}, headers=auth_headers).get_json()
        item_id = created['item']['id']
        res = client.put(f'/api/items/{item_id}', json={'name': 'New'}, headers=auth_headers)
        assert res.status_code == 200
        assert res.get_json()['item']['name'] == 'New'

    def test_delete_item(self, client, auth_headers):
        created = client.post('/api/items', json={'name': 'ToDelete'}, headers=auth_headers).get_json()
        item_id = created['item']['id']
        res = client.delete(f'/api/items/{item_id}', headers=auth_headers)
        assert res.status_code == 200
        assert client.get(f'/api/items/{item_id}', headers=auth_headers).status_code == 404

    def test_pagination(self, client, auth_headers):
        for i in range(15):
            client.post('/api/items', json={'name': f'Item {i}'}, headers=auth_headers)
        res = client.get('/api/items?page=1&per_page=10', headers=auth_headers).get_json()
        assert len(res['items']) == 10
        assert res['total'] == 15
        assert res['pages'] == 2

    def test_search(self, client, auth_headers):
        client.post('/api/items', json={'name': 'Apple'}, headers=auth_headers)
        client.post('/api/items', json={'name': 'Banana'}, headers=auth_headers)
        res = client.get('/api/items?search=app', headers=auth_headers).get_json()
        assert res['total'] == 1
        assert res['items'][0]['name'] == 'Apple'

    def test_filter_by_category(self, client, auth_headers):
        client.post('/api/items', json={'name': 'X', 'category': 'tools'}, headers=auth_headers)
        client.post('/api/items', json={'name': 'Y', 'category': 'food'}, headers=auth_headers)
        res = client.get('/api/items?category=tools', headers=auth_headers).get_json()
        assert res['total'] == 1

    def test_unauthenticated_access(self, client):
        res = client.get('/api/items')
        assert res.status_code == 401
