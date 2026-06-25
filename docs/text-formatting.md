# Text Formatting

This guide describes Redmond's house style for player-facing formatted text.
Use native Evennia text markup by default and keep custom conventions to a
minimum.

This document is intentionally brief. For the full markup surface and parser
details, use the upstream Evennia references linked at the end.

## How It Works

Redmond writes formatted output with Evennia markup tags embedded directly in
strings, such as `|g`, `|y`, `|w`, and `|n`.

Evennia parses those tags when sending text to the client:

- ANSI-capable telnet and common MUD clients receive terminal styling.
- The Evennia webclient receives translated HTML and CSS output.
- Clients that do not support color should still receive readable plain text.

This keeps one source string portable across the main client surfaces without
requiring Redmond-specific formatting code.

## Use This, Not That

Use:

- native Evennia markup tags in output strings
- short, readable formatting with explicit `|n` resets
- Evennia defaults unless a strong project need justifies more complexity

Avoid:

- raw ANSI escape sequences such as `\x1b[31m`
- a custom Redmond formatting syntax layered on top of Evennia
- formatting that only works in one client surface

## Common Tags

These are the tags Redmond authors should reach for most often:

- `|n`: reset formatting
- `|r`: bright red foreground
- `|g`: bright green foreground
- `|y`: bright yellow foreground
- `|b`: bright blue foreground
- `|c`: bright cyan foreground
- `|w`: bright white foreground
- `|x`: dark gray foreground

Evennia supports additional colors and richer color systems, but Redmond
should document and use only the common subset unless a real product need
appears.

## Examples

Stylized MOTD or connection text:

```python
LOGIN_MOTD = """
|b========================================|n
|gWelcome to Redmond.|n

This server is unofficial and noncommercial.
Use |whelp legal|n for the legal notice.
|b========================================|n
""".strip()
```

Room-description keyword emphasis:

```python
desc = (
    "The |cneon sign|n flickers above the bar while a "
    "|rred EXIT light|n hums over the back door."
)
```

Short help text:

```python
help_text = (
    "|yUsage:|n Use |wlook|n to re-show the room and "
    "|whelp legal|n for the project legal notice."
)
```

## Redmond Style Guidance

- Prefer restrained color over rainbow output.
- Reserve stronger colors for headings, warnings, legal notices, and
  important interaction cues.
- Keep room descriptions readable if all color is stripped.
- Do not rely on color alone when a keyword or warning must still be clear in
  plain text.
- Keep ASCII art legible without assuming a specific background color.
- Prefer high-contrast foreground colors and avoid bright-background effects
  that may render poorly across clients.
- Highlight recurring keyword categories consistently across room text, help
  text, and similar player-facing surfaces.

## Formatting Cautions

- Markup can affect wrapping, padding, and visual alignment.
- For layout-sensitive code, use Evennia-aware helpers instead of assuming
  naive string length matches rendered width.
- Prompt customization is a separate feature area. Follow the prompt-specific
  command and implementation docs for prompts rather than expanding this guide
  into prompt policy.

## Upstream References

- Evennia Colors:
  <https://www.evennia.com/docs/latest/Concepts/Colors.html>
- Evennia ANSI parser:
  <https://www.evennia.com/docs/latest/api/evennia.utils.ansi.html>
