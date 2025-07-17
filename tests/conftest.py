from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def config_entry():
    return MagicMock()


@pytest.fixture
def coordinator():
    return AsyncMock()


@pytest.fixture
def hass():
    hass_instance = MagicMock()
    hass_instance.config_entries = AsyncMock()
    return hass_instance
