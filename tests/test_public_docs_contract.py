from __future__ import annotations

from pathlib import Path
import unittest

from tests.bootstrap_test_utils import PRODUCT_ROOT


FORBIDDEN_TERMS = (
    " ".join(("Layer", "1")),
    " ".join(("Layer", "2")),
    " ".join(("Layer", "3")),
    " ".join(("private", "control", "repo")),
    " ".join(("source", "of", "truth", "repo")),
    "-".join(("source", "of", "truth")) + " repo",
    " ".join(("sibling", "repo")),
    " ".join(("upstream", "release", "workflow")),
)

FORBIDDEN_PATHS = (
    "/".join(("product", "config", "redmond.env")),
    "/".join(("product", "config", "redmond.env.example")),
    "./" + "/".join(("product", "scripts")) + "/",
    "/" + "/".join(("product", "scripts")) + "/",
    "/".join(("product", "scripts")) + "/",
    "/".join(("product", "CHANGELOG.md")),
)

PUBLIC_DOCS = (
    PRODUCT_ROOT / "README.md",
    PRODUCT_ROOT / "CONTRIBUTING.md",
    PRODUCT_ROOT / "CHANGELOG.md",
    PRODUCT_ROOT / "scripts" / "README.md",
    PRODUCT_ROOT / "scripts" / "CONTRIBUTING.md",
    PRODUCT_ROOT / "config" / "redmond.env.example",
    PRODUCT_ROOT / "docs" / "text-formatting.md",
    PRODUCT_ROOT
    / "src"
    / "redmond_server"
    / "game"
    / "server"
    / "logs"
    / "README.md",
)


class PublicDocsContractTest(unittest.TestCase):
    def test_public_docs_avoid_private_layer_terms(self) -> None:
        for path in PUBLIC_DOCS:
            with self.subTest(path=path.relative_to(PRODUCT_ROOT)):
                text = path.read_text(encoding="ascii")
                for term in FORBIDDEN_TERMS:
                    self.assertNotIn(term, text)

    def test_public_docs_avoid_private_root_paths(self) -> None:
        for path in PUBLIC_DOCS:
            with self.subTest(path=path.relative_to(PRODUCT_ROOT)):
                text = path.read_text(encoding="ascii")
                for term in FORBIDDEN_PATHS:
                    self.assertNotIn(term, text)

    def test_wrapper_docs_reference_exported_root_paths(self) -> None:
        readme_text = (PRODUCT_ROOT / "README.md").read_text(encoding="ascii")
        scripts_text = (
            PRODUCT_ROOT / "scripts" / "README.md"
        ).read_text(encoding="ascii")
        config_text = (
            PRODUCT_ROOT / "config" / "redmond.env.example"
        ).read_text(encoding="ascii")

        self.assertIn("config/redmond.env", readme_text)
        self.assertIn("config/redmond.env.example", readme_text)
        self.assertIn("./scripts/backup_create.sh", readme_text)
        self.assertIn("config/redmond.env", scripts_text)
        self.assertIn("config/redmond.env.example", scripts_text)
        self.assertIn("config/redmond.env", config_text)

    def test_public_root_paths_exist(self) -> None:
        expected_paths = (
            Path("README.md"),
            Path("CONTRIBUTING.md"),
            Path("CHANGELOG.md"),
            Path("config/redmond.env.example"),
            Path("scripts/README.md"),
            Path("scripts/CONTRIBUTING.md"),
        )

        for rel_path in expected_paths:
            with self.subTest(path=rel_path):
                self.assertTrue((PRODUCT_ROOT / rel_path).exists())
