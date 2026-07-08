from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from redmond_server.game.server.conf import _runtime_env


PRODUCT_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_PATH = PRODUCT_ROOT / "compose.yaml"
COMPOSE_EXAMPLE_PATH = PRODUCT_ROOT / "compose.env.example"
TEST_COMPOSE_SCRIPT_PATH = PRODUCT_ROOT / "scripts" / "test_compose.sh"
README_PATH = PRODUCT_ROOT / "README.md"


class ComposeContractTest(unittest.TestCase):
    def test_runtime_secret_key_returns_trimmed_value(self) -> None:
        self.assertEqual(
            _runtime_env.runtime_secret_key("  local-secret  "),
            "local-secret",
        )

    def test_runtime_secret_key_ignores_blank_values(self) -> None:
        self.assertIsNone(_runtime_env.runtime_secret_key("   "))

    def test_apply_runtime_env_overrides_sets_secret_key(self) -> None:
        namespace: dict[str, object] = {"SECRET_KEY": "fallback"}

        _runtime_env.apply_runtime_env_overrides(
            namespace,
            raw_secret_key="override-secret",
        )

        self.assertEqual(namespace["SECRET_KEY"], "override-secret")

    def test_compose_uses_authoritative_database_url(self) -> None:
        compose_text = COMPOSE_PATH.read_text(encoding="ascii")
        self.assertIn(
            "REDMOND_DATABASE_URL: ${REDMOND_DATABASE_URL}",
            compose_text,
        )
        self.assertNotIn(
            'REDMOND_DATABASE_URL: "postgres://${POSTGRES_USER}:',
            compose_text,
        )

    def test_compose_example_includes_complete_sample_url(self) -> None:
        example_text = COMPOSE_EXAMPLE_PATH.read_text(encoding="ascii")
        self.assertIn(
            "REDMOND_DATABASE_URL=postgres://redmond:",
            example_text,
        )
        self.assertIn("POSTGRES_PASSWORD=", example_text)

    def test_compose_docs_require_percent_encoding(self) -> None:
        readme_text = README_PATH.read_text(encoding="ascii")
        self.assertIn("REDMOND_DATABASE_URL", readme_text)
        self.assertIn("percent-encode", readme_text)

    def test_compose_helper_does_not_source_env_file(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertIn("docker compose \\\n", script_text)
        self.assertIn('--env-file "$compose_env"', script_text)
        self.assertIn('--env-file "$overlay_env"', script_text)
        self.assertNotIn('. "$compose_env"', script_text)
        self.assertNotIn('. "$overlay_env"', script_text)
        self.assertNotIn("source \"$compose_env\"", script_text)
        self.assertNotIn("eval ", script_text)

    def test_compose_helper_uses_stdin_only_password_test_mode(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertIn("REDMOND_TEST_PASSWORD_INPUT=1", script_text)
        self.assertIn("printf 'compose-admin-pass", script_text)
        self.assertNotIn("--password compose-admin-pass", script_text)

    def test_compose_helper_uses_isolated_project_name(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertIn('validation_project="redmond-verify-', script_text)
        self.assertIn('--project-name "$validation_project"', script_text)
        self.assertNotIn("COMPOSE_PROJECT_NAME=", script_text)

    def test_compose_helper_preserves_then_destroys_volume(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        plain_down = script_text.index("compose down\n")
        postgres_restart = script_text.index(
            'compose up -d postgres\n',
            plain_down,
        )
        destructive_down = script_text.index(
            "compose down -v --remove-orphans",
            postgres_restart,
        )
        self.assertLess(plain_down, postgres_restart)
        self.assertLess(postgres_restart, destructive_down)

    def test_compose_helper_uses_overlay_after_primary_env(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        primary_index = script_text.index('--env-file "$compose_env"')
        overlay_index = script_text.index('--env-file "$overlay_env"')
        self.assertLess(primary_index, overlay_index)

    def test_compose_helper_neutralizes_host_port_vars(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertIn("-u REDMOND_TELNET_PORT", script_text)
        self.assertIn("-u REDMOND_WEB_PORT", script_text)
        self.assertIn("-u REDMOND_WEBSOCKET_PORT", script_text)

    def test_compose_helper_overlay_uses_ephemeral_ports(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertIn("REDMOND_TELNET_PORT=0", script_text)
        self.assertIn("REDMOND_WEB_PORT=0", script_text)
        self.assertIn("REDMOND_WEBSOCKET_PORT=0", script_text)

    def test_compose_helper_verifies_persistence_after_restart(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        restart_index = script_text.index(
            'compose up -d postgres\n',
            script_text.index("echo \"Checking safe shutdown"),
        )
        has_superuser_index = script_text.index(
            "python -m redmond_server.bootstrap has-superuser",
            restart_index,
        )
        doctor_index = script_text.index(
            "python -m redmond_server.bootstrap doctor",
            has_superuser_index,
        )
        restart_status_index = script_text.index(
            "compose exec -T redmond evennia status",
            doctor_index,
        )
        self.assertLess(restart_index, has_superuser_index)
        self.assertLess(has_superuser_index, doctor_index)
        self.assertLess(doctor_index, restart_status_index)

    def test_compose_helper_uses_bounded_http_readiness_wait(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertIn("wait_for_http_ready() {", script_text)
        self.assertIn("attempts=30", script_text)
        self.assertIn("sleep 2", script_text)
        self.assertNotIn(
            'with urlopen(f"http://127.0.0.1:{port}/", timeout=15)',
            script_text,
        )

    def test_compose_helper_runs_http_readiness_after_both_startups(
        self,
    ) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertEqual(script_text.count("wait_for_http_ready"), 3)
        first_start_index = script_text.index(
            "echo \"Starting Redmond service...\"",
        )
        first_readiness_index = script_text.index(
            "wait_for_http_ready",
            first_start_index,
        )
        restart_start_index = script_text.index(
            "compose up -d redmond\n",
            first_readiness_index,
        )
        second_readiness_index = script_text.index(
            "wait_for_http_ready",
            restart_start_index,
        )
        self.assertLess(first_start_index, first_readiness_index)
        self.assertLess(restart_start_index, second_readiness_index)

    def test_compose_helper_emits_runtime_diagnostics_before_cleanup(
        self,
    ) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertIn("print_runtime_diagnostics() {", script_text)
        self.assertIn('echo "Compose status:" >&2', script_text)
        self.assertIn('compose ps >&2 || true', script_text)
        self.assertIn('echo "Recent service logs:" >&2', script_text)
        self.assertIn(
            'compose logs --tail 100 redmond postgres >&2 || true',
            script_text,
        )
        self.assertIn(
            'echo "Published Redmond port mappings:" >&2',
            script_text,
        )
        self.assertIn('compose port redmond 4001 >&2 || true', script_text)
        self.assertIn('fail_post_start_check "$final_reason"', script_text)

    def test_compose_helper_discovers_web_port_via_compose(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        self.assertEqual(script_text.count("compose port redmond 4001"), 2)

    def test_compose_helper_removes_overlay_in_cleanup(self) -> None:
        script_text = TEST_COMPOSE_SCRIPT_PATH.read_text(encoding="ascii")
        cleanup_index = script_text.index("cleanup() {")
        rm_index = script_text.index('rm -f "$overlay_env"', cleanup_index)
        rmdir_index = script_text.index('rmdir "$overlay_dir"', rm_index)
        self.assertLess(cleanup_index, rm_index)
        self.assertLess(rm_index, rmdir_index)

    def test_compose_helper_shell_syntax_is_valid(self) -> None:
        subprocess.run(
            ["sh", "-n", str(TEST_COMPOSE_SCRIPT_PATH)],
            check=True,
            cwd=PRODUCT_ROOT,
            text=True,
            capture_output=True,
        )

    @unittest.skipUnless(shutil.which("docker"), "docker not available")
    def test_compose_config_renders_with_temp_env_file(self) -> None:
        temp_dir = Path(tempfile.mkdtemp(prefix="redmond-compose-test-"))
        env_path = temp_dir / "compose.env"
        env_path.write_text(
            "\n".join(
                [
                    "COMPOSE_PROJECT_NAME=redmond-compose-test",
                    "POSTGRES_DB=redmond",
                    "POSTGRES_USER=redmond",
                    "POSTGRES_PASSWORD=local-postgres-password",
                    (
                        "REDMOND_DATABASE_URL="
                        "postgres://redmond:local-postgres-password"
                        "@postgres:5432/redmond"
                    ),
                    "REDMOND_SECRET_KEY=local-redmond-secret-key",
                    "REDMOND_TELNET_PORT=4000",
                    "REDMOND_WEB_PORT=4001",
                    "REDMOND_WEBSOCKET_PORT=4002",
                    "",
                ]
            ),
            encoding="ascii",
        )
        overlay_path = temp_dir / "compose.validation.env"
        overlay_path.write_text(
            "\n".join(
                [
                    "REDMOND_TELNET_PORT=0",
                    "REDMOND_WEB_PORT=0",
                    "REDMOND_WEBSOCKET_PORT=0",
                    "",
                ]
            ),
            encoding="ascii",
        )

        result = subprocess.run(
            [
                "docker",
                "compose",
                "--env-file",
                str(env_path),
                "--env-file",
                str(overlay_path),
                "config",
            ],
            check=True,
            cwd=PRODUCT_ROOT,
            text=True,
            capture_output=True,
        )

        self.assertIn("REDMOND_DATABASE_URL", result.stdout)
        self.assertIn("postgres_data", result.stdout)
