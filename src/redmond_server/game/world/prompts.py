"""Prompt rendering and delivery helpers for Redmond."""

from __future__ import annotations

from dataclasses import dataclass


ACCOUNT_PROMPT_ATTR = "redmond_prompt_template"
DEFAULT_LOGGED_IN_PROMPT = "%r%n @ %l > "
DEFAULT_UNLOGGED_IN_PROMPT = "%rRedmond> "
OOC_CONTEXT_LABEL = "OOC"
PROMPT_EMITTED_ATTR = "_redmond_prompt_emitted"
PROMPT_SUPPRESSED_ATTR = "_redmond_prompt_suppressed"


@dataclass(frozen=True)
class PromptContext:
    """Resolved values used for prompt rendering."""

    account_name: str
    character_name: str | None
    context_label: str
    logged_in: bool


def build_prompt_context(
    session=None,
    *,
    account=None,
    character=None,
) -> PromptContext:
    """Build a prompt context from the current session state."""
    if session is not None:
        if account is None:
            account = getattr(session, "account", None)
        if character is None:
            character = getattr(session, "puppet", None)
    if character is not None and account is None:
        account = getattr(character, "account", None)

    if account is None:
        return PromptContext(
            account_name="",
            character_name=None,
            context_label=OOC_CONTEXT_LABEL,
            logged_in=False,
        )

    context_label = OOC_CONTEXT_LABEL
    if character is not None:
        location = getattr(character, "location", None)
        location_name = getattr(location, "key", "")
        if location_name:
            context_label = location_name

    return PromptContext(
        account_name=account.key,
        character_name=getattr(character, "key", None),
        context_label=context_label,
        logged_in=True,
    )


def render_prompt_template(template: str, context: PromptContext) -> str:
    """Render a MUSH-style prompt template in one left-to-right pass."""
    tokens = {
        "%": "%",
        "l": context.context_label,
        "n": context.character_name or context.account_name,
        "r": "\n",
        "t": "\t",
    }
    rendered: list[str] = []
    index = 0
    while index < len(template):
        if template[index] != "%" or index + 1 >= len(template):
            rendered.append(template[index])
            index += 1
            continue

        token = template[index + 1]
        replacement = tokens.get(token)
        if replacement is None:
            rendered.append("%")
            rendered.append(token)
        else:
            rendered.append(replacement)
        index += 2
    return "".join(rendered)


def get_account_prompt_template(account) -> str:
    """Return the account-scoped prompt template or the default."""
    template = account.attributes.get(ACCOUNT_PROMPT_ATTR)
    if isinstance(template, str):
        return template
    return DEFAULT_LOGGED_IN_PROMPT


def build_prompt_text(session=None, *, account=None, character=None) -> str:
    """Resolve and render the prompt for the current session state."""
    context = build_prompt_context(
        session,
        account=account,
        character=character,
    )
    if not context.logged_in:
        template = DEFAULT_UNLOGGED_IN_PROMPT
    else:
        template = get_account_prompt_template(account)
    return render_prompt_template(template, context)


def clear_prompt_emitted(session) -> None:
    """Clear the per-session prompt-emitted flag."""
    if session is None:
        return
    if hasattr(session, PROMPT_EMITTED_ATTR):
        delattr(session, PROMPT_EMITTED_ATTR)


def mark_prompt_emitted(session) -> None:
    """Mark that a prompt has already been emitted for this command cycle."""
    if session is None:
        return
    setattr(session, PROMPT_EMITTED_ATTR, True)


def prompt_was_emitted(session) -> bool:
    """Return whether a prompt has already been emitted this cycle."""
    if session is None:
        return False
    return bool(getattr(session, PROMPT_EMITTED_ATTR, False))


def set_prompt_suppressed(session, suppressed: bool) -> None:
    """Toggle temporary prompt suppression on a session."""
    if session is None:
        return
    if suppressed:
        setattr(session, PROMPT_SUPPRESSED_ATTR, True)
        return
    if hasattr(session, PROMPT_SUPPRESSED_ATTR):
        delattr(session, PROMPT_SUPPRESSED_ATTR)


def prompt_is_suppressed(session) -> bool:
    """Return whether prompt emission is currently suppressed."""
    if session is None:
        return False
    return bool(getattr(session, PROMPT_SUPPRESSED_ATTR, False))


def send_prompt(
    target,
    session=None,
    *,
    account=None,
    character=None,
) -> str | None:
    """Emit a real Evennia prompt to the active session."""
    resolved_session = session
    if resolved_session is None and hasattr(target, "sessions"):
        sessions = list(target.sessions.all())
        if sessions:
            resolved_session = sessions[-1]
    if resolved_session is None and hasattr(target, "msg"):
        resolved_session = target
    if resolved_session is None or prompt_is_suppressed(resolved_session):
        return None

    if account is None and resolved_session is not None:
        account = getattr(resolved_session, "account", None)
    if character is None and resolved_session is not None:
        character = getattr(resolved_session, "puppet", None)

    prompt = build_prompt_text(
        resolved_session,
        account=account,
        character=character,
    )
    if hasattr(target, "msg") and target is not resolved_session:
        target.msg(prompt=prompt, session=resolved_session)
    else:
        resolved_session.msg(prompt=prompt)
    mark_prompt_emitted(resolved_session)
    return prompt
