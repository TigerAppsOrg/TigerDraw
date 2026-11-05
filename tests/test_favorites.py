"""Favorites persistence regressions, using SQLite without production credentials.

Run: python -m unittest discover -s tests
"""
import os
import unittest
from unittest.mock import patch

from sqlalchemy import JSON, create_engine
from sqlalchemy.orm import sessionmaker

# Load the real model and functions, but never connect to the configured DB.
engine = create_engine('sqlite:///:memory:')
with patch.dict(os.environ, {
    'DATABASE_URL': 'sqlite:///:memory:',
    'CONSUMER_KEY': 'test',
    'CONSUMER_SECRET': 'test',
}), patch('sqlalchemy.create_engine', return_value=engine):
    import display

# SQLite JSON provides the same Python list semantics as PostgreSQL arrays.
for name in ('rooms', 'group_ids'):
    column = display.User.__table__.c[name]
    column.type = column.type.with_variant(JSON(), 'sqlite')


class FavoriteTests(unittest.TestCase):
    def setUp(self):
        display.User.__table__.create(engine)
        self.session = sessionmaker(bind=engine)()
        self.session_patch = patch.object(display, 'db_session', self.session)
        self.session_patch.start()

    def tearDown(self):
        self.session_patch.stop()
        self.session.close()
        display.User.__table__.drop(engine)

    def seed(self, rooms):
        self.session.add(display.User(username='student', rooms=rooms, group_ids=[]))
        self.session.commit()

    def saved_rooms(self):
        # Discard ORM state to verify what was actually committed.
        self.session.expunge_all()
        return self.session.query(display.User).filter_by(username='student').one().rooms

    def test_first_favorite_creates_user_and_persists(self):
        display.addFavorite('123', ' student\n')
        self.assertEqual(self.saved_rooms(), [123])

    def test_repeated_add_is_idempotent(self):
        self.seed([456])
        display.addFavorite(123, 'student')
        display.addFavorite(123, 'student')
        self.assertEqual(self.saved_rooms(), [456, 123])

    def test_remove_clears_legacy_duplicates_and_preserves_other_rooms(self):
        self.seed([123, 456, 123])
        display.removeFavorite('123', 'student')
        self.assertEqual(self.saved_rooms(), [456])
        display.removeFavorite('123', 'student')
        self.assertEqual(self.saved_rooms(), [456])

    def test_null_favorites_can_be_added_to(self):
        self.seed(None)
        display.addFavorite(123, 'student')
        self.assertEqual(self.saved_rooms(), [123])

    def test_null_favorites_can_be_removed_from(self):
        self.seed(None)
        display.removeFavorite(123, 'student')
        self.assertEqual(self.saved_rooms(), [])


if __name__ == '__main__':
    unittest.main()
