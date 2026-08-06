from __future__ import annotations
# ruff: noqa: E402

from pathlib import Path
import unittest

from tests.bootstrap_test_utils import (
    GAME_SOURCE,
    configure_isolated_django,
)


ISOLATED_GAME_DIR = configure_isolated_django()

from django.conf import settings  # type: ignore[import-untyped]
from django.db import connection  # type: ignore[import-untyped]
from evennia.objects.models import (  # type: ignore[import-untyped]
    ObjectDB,
)


class DjangoTestSetupTest(unittest.TestCase):
    def test_sqlite_database_uses_temporary_game_dir(self) -> None:
        database_path = Path(settings.DATABASES["default"]["NAME"])
        local_database_path = GAME_SOURCE / "server" / "evennia.db3"

        self.assertEqual(
            database_path,
            ISOLATED_GAME_DIR / "server" / "evennia.db3",
        )
        self.assertNotEqual(database_path, local_database_path)

    def test_isolated_database_has_product_migrations(self) -> None:
        table_names = set(connection.introspection.table_names())

        self.assertIn("chargen_chargensession", table_names)
        self.assertIn("sheets_charactersheet", table_names)

    def test_isolated_database_has_evennia_baseline_objects(self) -> None:
        self.assertTrue(ObjectDB.objects.filter(pk=1).exists())
        self.assertTrue(ObjectDB.objects.filter(pk=2).exists())
