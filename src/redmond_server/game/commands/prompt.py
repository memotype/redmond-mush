# mypy: ignore-errors
"""Prompt customization command."""

from commands.command import MuxAccountCommand
from world.prompts import (
    ACCOUNT_PROMPT_ATTR,
    build_prompt_context,
    get_account_prompt_template,
    render_prompt_template,
)


def _quote_visible(value: str) -> str:
    """Wrap a value in quotes so trailing spaces remain visible."""
    return f"'{value}'"


class CmdPrompt(MuxAccountCommand):
    """
    View or customize the logged-in prompt.

    Usage:
      @prompt
      @prompt <template>
      @prompt/test <template>
      @prompt/reset
    """

    key = "@prompt"
    aliases = ["prompt"]
    help_category = "General"
    switch_options = ("reset", "test")

    def _extract_raw_template(self) -> str | None:
        """
        Extract the raw template argument without trimming trailing spaces.
        """
        raw_string = self.raw_string or ""
        raw_cmdname = self.raw_cmdname or self.cmdname or self.key
        if not raw_string.startswith(raw_cmdname):
            return None

        remainder = raw_string[len(raw_cmdname) :]
        if remainder.startswith("/"):
            _switches, separator, tail = remainder.partition(" ")
            if not separator:
                return None
            return tail
        if remainder.startswith(" "):
            return remainder[1:]
        return None

    def _format_summary(self, template: str, *, override: bool) -> str:
        """Render the current template and preview summary."""
        context = build_prompt_context(self.session, account=self.account)
        preview = render_prompt_template(template, context)
        status = "yes" if override else "no"
        return (
            f"Saved override: {status}\n"
            f"Template: {_quote_visible(template)}\n"
            f"Preview:\n{preview}"
        )

    def func(self):
        """Show, set, test, or reset the logged-in prompt template."""
        if "reset" in self.switches:
            self.account.attributes.remove(ACCOUNT_PROMPT_ATTR)
            template = get_account_prompt_template(self.account)
            self.msg(
                "Prompt reset to the default logged-in template.\n"
                + self._format_summary(template, override=False)
            )
            return

        raw_template = self._extract_raw_template()
        if "test" in self.switches:
            if raw_template is None:
                self.msg("Usage: @prompt/test <template>")
                return

            context = build_prompt_context(self.session, account=self.account)
            rendered = render_prompt_template(raw_template, context)
            self.msg(
                "Prompt preview only; no changes were saved.\n"
                f"Template: {_quote_visible(raw_template)}\n"
                f"Preview:\n{rendered}"
            )
            return

        if raw_template is None:
            template = get_account_prompt_template(self.account)
            override = self.account.attributes.has(ACCOUNT_PROMPT_ATTR)
            self.msg(self._format_summary(template, override=override))
            return

        self.account.attributes.add(ACCOUNT_PROMPT_ATTR, raw_template)
        self.msg(
            "Prompt updated.\n"
            + self._format_summary(raw_template, override=True)
        )
