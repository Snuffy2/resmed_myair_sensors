from unittest.mock import MagicMock

import pytest

from custom_components.resmed_myair.const import (
    CONF_DEVICE_TOKEN,
    CONF_PASSWORD,
    CONF_REGION,
    CONF_USER_NAME,
    REGION_NA,
)


@pytest.fixture
def config_entry():
    """Fixture for a mock ConfigEntry."""
    entry = MagicMock()
    entry.data = {
        CONF_USER_NAME: "user",
        CONF_PASSWORD: "pass",
        CONF_REGION: REGION_NA,
        CONF_DEVICE_TOKEN: "token",
    }
    entry.version = 1
    entry.runtime_data = None
    return entry
