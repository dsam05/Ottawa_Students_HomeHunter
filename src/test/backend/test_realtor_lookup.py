from __future__ import annotations

import pytest

from src.main.backend import realtor_lookup


def test_realtor_url_allowlist_accepts_listing_urls() -> None:
    assert realtor_lookup.is_allowed_realtor_url(
        "https://www.realtor.ca/real-estate/29717564/example-listing"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://www.realtor.ca/real-estate/29717564/example-listing",
        "https://example.com/real-estate/29717564/example-listing",
        "https://www.realtor.ca/search",
        "https://user:pass@www.realtor.ca/real-estate/29717564/example-listing",
    ],
)
def test_realtor_url_allowlist_rejects_unsafe_urls(url: str) -> None:
    assert not realtor_lookup.is_allowed_realtor_url(url)


def test_request_text_rejects_disallowed_hosts_before_network(monkeypatch) -> None:
    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("urlopen should not be called for blocked hosts")

    monkeypatch.setattr(realtor_lookup.urllib.request, "urlopen", fail_if_called)

    with pytest.raises(ValueError):
        realtor_lookup.request_text("https://example.com/not-allowed")
