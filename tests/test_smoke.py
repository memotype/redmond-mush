import unittest

from redmond_server import __doc__


class PackageImportSmokeTest(unittest.TestCase):
    def test_package_import_smoke(self) -> None:
        self.assertIsNotNone(__doc__)
