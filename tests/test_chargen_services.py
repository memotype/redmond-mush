from __future__ import annotations
# ruff: noqa: E402

from pathlib import Path
import os
from unittest.mock import patch

from redmond_server.bootstrap._backup import run_migrations
from redmond_server.bootstrap._env import configure_django


GAME_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "redmond_server"
    / "game"
)
ORIGINAL_CWD = Path.cwd()
configure_django(GAME_DIR, load_evennia=True)
os.chdir(ORIGINAL_CWD)
run_migrations(GAME_DIR)

from django.db import (  # type: ignore[import-untyped]
    IntegrityError,
    transaction,
)
from evennia.utils.test_resources import EvenniaCommandTest

from chargen.models import ChargenRulesProfile, ChargenSession
from chargen.models import ChargenSessionStatus
from chargen.queries import get_chargen_status
from chargen.services import (
    ActiveChargenSessionExistsError,
    ActiveChargenSessionNotFoundError,
    ChargenProfileImmutableError,
    ChargenProfileUnavailableError,
    ChargenSessionConflictError,
    ChargenValidationError,
    CreateChargenSessionInput,
    DefaultChargenProfileNotConfiguredError,
    EditChargenAttributeInput,
    EnsureChargenRulesProfileInput,
    UnknownDraftAttributeError,
    create_chargen_session,
    edit_chargen_attribute,
    ensure_chargen_rules_profile,
)


class ChargenServiceTest(EvenniaCommandTest):
    def setUp(self) -> None:
        super().setUp()
        ChargenSession.objects.all().delete()
        ChargenRulesProfile.objects.all().delete()

    def _profile_input(
        self,
        **overrides,
    ) -> EnsureChargenRulesProfileInput:
        payload = EnsureChargenRulesProfileInput(
            profile_key="redmond_standard",
            version=1,
            display_name="Redmond Standard",
            is_available_for_new_sessions=True,
            is_default_for_new_sessions=True,
            starting_karma=50,
        )
        return EnsureChargenRulesProfileInput(
            **{**payload.__dict__, **overrides}
        )

    def _session_input(
        self,
        **overrides,
    ) -> CreateChargenSessionInput:
        payload = CreateChargenSessionInput(character=self.char1)
        return CreateChargenSessionInput(**{**payload.__dict__, **overrides})

    def test_ensure_profile_persists_versioned_identity(self) -> None:
        result = ensure_chargen_rules_profile(self._profile_input())
        profile = ChargenRulesProfile.objects.get(pk=result.profile_id)
        self.assertEqual(profile.profile_key, "redmond_standard")
        self.assertEqual(profile.version, 1)
        self.assertTrue(profile.is_default_for_new_sessions)

    def test_only_one_default_profile_is_kept(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        ensure_chargen_rules_profile(
            self._profile_input(
                profile_key="redmond_alt",
                version=1,
                display_name="Redmond Alt",
            )
        )
        defaults = list(
            ChargenRulesProfile.objects.filter(
                is_default_for_new_sessions=True
            )
        )
        self.assertEqual(len(defaults), 1)
        self.assertEqual(defaults[0].profile_key, "redmond_alt")

    def test_referenced_profile_keeps_immutable_fields(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        with self.assertRaises(ChargenProfileImmutableError):
            ensure_chargen_rules_profile(
                self._profile_input(display_name="Changed Name")
            )

    def test_referenced_profile_allows_availability_toggle(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        result = ensure_chargen_rules_profile(
            self._profile_input(
                is_available_for_new_sessions=False,
                is_default_for_new_sessions=False,
            )
        )
        self.assertFalse(result.is_available_for_new_sessions)

    def test_create_chargen_session_uses_default_profile(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        result = create_chargen_session(self._session_input())
        session = ChargenSession.objects.get(pk=result.session_id)
        self.assertEqual(session.status, ChargenSessionStatus.DRAFT)
        self.assertEqual(session.starting_karma_snapshot, 50)
        self.assertEqual(session.backstory, "")

    def test_create_chargen_session_requires_default_profile(self) -> None:
        with self.assertRaises(DefaultChargenProfileNotConfiguredError):
            create_chargen_session(self._session_input())

    def test_create_chargen_session_rejects_unavailable_profile(self) -> None:
        ensure_chargen_rules_profile(
            self._profile_input(
                is_available_for_new_sessions=False,
                is_default_for_new_sessions=False,
            )
        )
        with self.assertRaises(ChargenProfileUnavailableError):
            create_chargen_session(
                self._session_input(
                    profile_key="redmond_standard",
                    version=1,
                )
            )

    def test_one_active_session_per_character_is_enforced(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        with self.assertRaises(ActiveChargenSessionExistsError):
            create_chargen_session(self._session_input())

    def test_final_historical_session_allows_new_active_session(self) -> None:
        profile = ensure_chargen_rules_profile(self._profile_input())
        ChargenSession.objects.create(
            character=self.char1,
            status=ChargenSessionStatus.ABANDONED,
            rules_profile=ChargenRulesProfile.objects.get(
                pk=profile.profile_id
            ),
            starting_karma_snapshot=50,
            backstory="",
        )
        result = create_chargen_session(self._session_input())
        self.assertEqual(result.status, ChargenSessionStatus.DRAFT)

    def test_create_chargen_session_translates_integrity_race(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        with patch(
            "chargen.services.ChargenSession.objects.create",
            side_effect=IntegrityError("chargen_active_session_unique"),
        ):
            with self.assertRaises(ActiveChargenSessionExistsError):
                create_chargen_session(self._session_input())

    def test_transaction_rolls_back_create_failure(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        with patch(
            "chargen.services.ChargenSession.objects.create",
            side_effect=IntegrityError("boom"),
        ):
            with self.assertRaises(ChargenSessionConflictError):
                create_chargen_session(self._session_input())
        self.assertFalse(
            ChargenSession.objects.filter(character=self.char1).exists()
        )

    def test_status_query_returns_active_draft_session(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        status = get_chargen_status(self.char1)
        assert status is not None
        self.assertEqual(status.profile_key, "redmond_standard")
        self.assertEqual(status.starting_karma, 50)
        self.assertEqual(status.completion_state, "Incomplete")
        self.assertEqual(status.backstory_state, "Required")

    def test_status_query_ignores_only_historical_sessions(self) -> None:
        profile = ensure_chargen_rules_profile(self._profile_input())
        ChargenSession.objects.create(
            character=self.char1,
            status=ChargenSessionStatus.SUPERSEDED,
            rules_profile=ChargenRulesProfile.objects.get(
                pk=profile.profile_id
            ),
            starting_karma_snapshot=50,
            backstory="",
        )
        self.assertIsNone(get_chargen_status(self.char1))

    def test_profile_delete_is_protected(self) -> None:
        result = ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        profile = ChargenRulesProfile.objects.get(pk=result.profile_id)
        with self.assertRaises(Exception):
            profile.delete()

    def test_character_delete_cascades_sessions(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        created = create_chargen_session(self._session_input())
        self.char1.delete()
        self.assertFalse(
            ChargenSession.objects.filter(pk=created.session_id).exists()
        )

    def test_incomplete_profile_identity_is_rejected(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        with self.assertRaises(ChargenValidationError):
            create_chargen_session(
                self._session_input(profile_key="redmond_standard")
            )

    def test_active_session_constraint_rejects_direct_duplicate_rows(
        self,
    ) -> None:
        result = ensure_chargen_rules_profile(self._profile_input())
        profile = ChargenRulesProfile.objects.get(pk=result.profile_id)
        ChargenSession.objects.create(
            character=self.char1,
            status=ChargenSessionStatus.DRAFT,
            rules_profile=profile,
            starting_karma_snapshot=50,
            backstory="",
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ChargenSession.objects.create(
                    character=self.char1,
                    status=ChargenSessionStatus.SUBMITTED,
                    rules_profile=profile,
                    starting_karma_snapshot=50,
                    backstory="",
                )

    def test_edit_chargen_attribute_persists_value(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        created = create_chargen_session(self._session_input())
        result = edit_chargen_attribute(
            EditChargenAttributeInput(
                character=self.char1,
                attribute_name="body",
                value=8,
            )
        )
        session = ChargenSession.objects.get(pk=created.session_id)
        self.assertEqual(result.session_id, created.session_id)
        self.assertEqual(result.attribute_id, "body")
        self.assertEqual(result.value, 8)
        self.assertEqual(session.body, 8)

    def test_edit_chargen_attribute_accepts_aliases(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        result = edit_chargen_attribute(
            EditChargenAttributeInput(
                character=self.char1,
                attribute_name="bod",
                value=7,
            )
        )
        session = ChargenSession.objects.get(character=self.char1)
        self.assertEqual(result.attribute_id, "body")
        self.assertEqual(session.body, 7)

    def test_edit_chargen_attribute_overwrites_existing_value(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        edit_chargen_attribute(
            EditChargenAttributeInput(
                character=self.char1,
                attribute_name="logic",
                value=4,
            )
        )
        edit_chargen_attribute(
            EditChargenAttributeInput(
                character=self.char1,
                attribute_name="logic",
                value=6,
            )
        )
        session = ChargenSession.objects.get(character=self.char1)
        self.assertEqual(session.logic, 6)

    def test_edit_chargen_attribute_requires_active_session(self) -> None:
        with self.assertRaises(ActiveChargenSessionNotFoundError):
            edit_chargen_attribute(
                EditChargenAttributeInput(
                    character=self.char1,
                    attribute_name="body",
                    value=8,
                )
            )

    def test_edit_chargen_attribute_rejects_unknown_attribute(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        with self.assertRaises(UnknownDraftAttributeError):
            edit_chargen_attribute(
                EditChargenAttributeInput(
                    character=self.char1,
                    attribute_name="luck",
                    value=8,
                )
            )

    def test_edit_chargen_attribute_rejects_invalid_value(self) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        with self.assertRaises(ChargenValidationError):
            edit_chargen_attribute(
                EditChargenAttributeInput(
                    character=self.char1,
                    attribute_name="body",
                    value=100,
                )
            )

    def test_status_query_reports_complete_when_all_attributes_are_set(
        self,
    ) -> None:
        ensure_chargen_rules_profile(self._profile_input())
        create_chargen_session(self._session_input())
        session = ChargenSession.objects.get(character=self.char1)
        session.body = 1
        session.agility = 2
        session.reaction = 3
        session.strength = 4
        session.willpower = 5
        session.logic = 6
        session.intuition = 7
        session.charisma = 8
        session.edge = 2
        session.save()
        status = get_chargen_status(self.char1)
        assert status is not None
        self.assertEqual(status.completion_state, "Complete")
        self.assertEqual(status.missing_attribute_ids, ())
