"""Read-only list optimizations against isolated SQLite, never production."""
from sqlalchemy import event
from test_website_deployment import full_client
from test_permissions import login
import main as website


def test_novel_compact_list_keeps_default_and_detail_compatible(full_client):
    original = full_client.get('/api/novels').json()[0]
    compact = full_client.get('/api/novels?include_content=false').json()[0]
    assert original['content'] == '第一章\nUnicode 内容 ✨'
    assert compact == {**original, 'content': ''}
    assert full_client.get('/api/novels/8').json()['novel'] == original


def test_compact_search_still_matches_body_and_preserves_user_metadata(full_client):
    headers, _ = login(full_client)
    assert full_client.post('/api/novels/8/favorite', headers=headers).status_code == 200
    assert full_client.put('/api/novels/8/progress', headers=headers, json={'progress': 42, 'font_size': 21, 'theme': 'light'}).status_code == 200
    rows = full_client.get('/api/novels?q=Unicode&include_content=false', headers=headers).json()
    assert len(rows) == 1 and rows[0]['content'] == ''
    assert rows[0]['is_favorited'] and rows[0]['favorite_count'] == 1
    assert (rows[0]['progress'], rows[0]['font_size'], rows[0]['theme']) == (42, 21, 'light')
    assert full_client.get('/api/novels?q=absent&include_content=false').json() == []


def test_compact_list_does_not_select_body_or_write_database(full_client):
    statements = []
    def record(connection, cursor, statement, parameters, context, many):
        statements.append(statement)
    event.listen(website.engine, 'before_cursor_execute', record)
    try:
        assert full_client.get('/api/novels?include_content=false').status_code == 200
    finally:
        event.remove(website.engine, 'before_cursor_execute', record)
    assert not any('xs_content' in sql for sql in statements)
    assert not any(sql.lstrip().upper().startswith(('INSERT', 'UPDATE', 'DELETE')) for sql in statements)
