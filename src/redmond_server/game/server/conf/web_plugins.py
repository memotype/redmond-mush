# mypy: ignore-errors
"""Web plugin hooks for future Redmond web customizations."""


def at_webserver_root_creation(web_root):
    """Return the default web root unchanged."""
    return web_root


def at_webproxy_root_creation(web_root):
    """Return the default web proxy root unchanged."""
    return web_root
