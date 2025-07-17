import pytest

from custom_components.resmed_myair.client.helpers import REDACTED, redact_dict


@pytest.mark.parametrize(
    "input_data,expected",
    [
        # No redaction needed
        ({"foo": "bar"}, {"foo": "bar"}),
        # Redact a single key
        ({"username": "bob"}, {"username": REDACTED}),
        # Redact nested dict
        ({"outer": {"password": "abc"}}, {"outer": {"password": REDACTED}}),
        # Redact in list of dicts
        ([{"token": "abc"}, {"foo": "bar"}], [{"token": REDACTED}, {"foo": "bar"}]),
        # Redact in nested list
        ({"list": [{"username": "bob"}]}, {"list": [{"username": REDACTED}]}),
        # Ignore None and empty string
        ({"username": None, "password": ""}, {"username": None, "password": ""}),
        # Redact deeply nested
        (
            {"a": {"b": {"password": "abc"}}},
            {"a": {"b": {"password": REDACTED}}},
        ),
        # Non-dict/list input
        ("notadict", "notadict"),
        (None, None),
    ],
)
def test_redact_dict(monkeypatch, input_data, expected):
    """Test redact_dict redacts sensitive keys as expected."""
    monkeypatch.setattr(
        "custom_components.resmed_myair.client.helpers.KEYS_TO_REDACT",
        {"username", "password", "token"},
    )
    assert redact_dict(input_data) == expected


def test_redact_dict_empty_dict(monkeypatch):
    """Test redact_dict with an empty dict."""
    monkeypatch.setattr(
        "custom_components.resmed_myair.client.helpers.KEYS_TO_REDACT",
        {"username", "password", "token"},
    )
    assert redact_dict({}) == {}


def test_redact_dict_empty_list(monkeypatch):
    """Test redact_dict with an empty list."""
    monkeypatch.setattr(
        "custom_components.resmed_myair.client.helpers.KEYS_TO_REDACT",
        {"username", "password", "token"},
    )
    assert redact_dict([]) == []


def test_redact_dict_list_with_empty_dict(monkeypatch):
    """Test redact_dict with a list containing an empty dict."""
    monkeypatch.setattr(
        "custom_components.resmed_myair.client.helpers.KEYS_TO_REDACT",
        {"username", "password", "token"},
    )
    assert redact_dict([{}]) == [{}]


def test_redact_dict_nested_empty(monkeypatch):
    """Test redact_dict with nested empty dicts and lists."""
    monkeypatch.setattr(
        "custom_components.resmed_myair.client.helpers.KEYS_TO_REDACT",
        {"username", "password", "token"},
    )
    assert redact_dict({"a": {}, "b": []}) == {"a": {}, "b": []}


def test_redact_dict_skip_none_and_empty(monkeypatch):
    """Test redact_dict skips None and empty string values."""
    monkeypatch.setattr(
        "custom_components.resmed_myair.client.helpers.KEYS_TO_REDACT",
        {"username", "password", "token"},
    )
    data = {"username": None, "password": "", "token": "abc"}
    expected = {"username": None, "password": "", "token": REDACTED}
    assert redact_dict(data) == expected
