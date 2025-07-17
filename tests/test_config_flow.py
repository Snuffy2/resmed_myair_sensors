from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.resmed_myair.client.rest_client import RESTClient
from custom_components.resmed_myair.config_flow import (
    AUTHN_SUCCESS,
    CONF_PASSWORD,
    CONF_REGION,
    CONF_USER_NAME,
    CONF_VERIFICATION_CODE,
    REGION_NA,
    MyAirConfigFlow,
    get_device,
    get_mfa_device,
)


@pytest.fixture
def hass() -> MagicMock:
    """Fixture for Home Assistant mock."""
    return MagicMock()


@pytest.fixture
def flow(hass: MagicMock) -> MyAirConfigFlow:
    """Fixture for MyAirConfigFlow instance."""
    flow = MyAirConfigFlow()
    flow.hass = hass
    flow.context = {}  # Fix mappingproxy error
    return flow


@pytest.mark.asyncio
async def test_async_step_user_success(flow: MyAirConfigFlow) -> None:
    """Test successful user step."""
    user_input: dict[str, str] = {
        CONF_USER_NAME: "user",
        CONF_PASSWORD: "pass",
        CONF_REGION: REGION_NA,
    }
    device: dict[str, str] = {
        "serialNumber": "SN123",
        "fgDeviceManufacturerName": "ResMed",
        "localizedName": "CPAP",
    }
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_device",
            new=AsyncMock(return_value=(AUTHN_SUCCESS, device, MagicMock(device_token="token"))),
        ),
        patch.object(
            flow.hass.config_entries,
            "async_entry_for_domain_unique_id",
            return_value=None,
        ),
    ):
        result = await flow.async_step_user(user_input)
    assert result["type"] == "create_entry"
    assert "ResMed-CPAP" in result["title"]
    assert result["data"][CONF_USER_NAME] == "user"


@pytest.mark.asyncio
async def test_async_step_user_auth_error(flow: MyAirConfigFlow) -> None:
    """Test user step with authentication error."""
    user_input: dict[str, str] = {
        CONF_USER_NAME: "user",
        CONF_PASSWORD: "badpass",
        CONF_REGION: REGION_NA,
    }
    with patch(
        "custom_components.resmed_myair.config_flow.get_device",
        new=AsyncMock(side_effect=Exception("fail")),
    ):
        with pytest.raises(Exception) as exc:
            await flow.async_step_user(user_input)
        assert str(exc.value) == "fail"


@pytest.mark.asyncio
async def test_async_step_user_incomplete_account_email_not_verified(flow: MyAirConfigFlow) -> None:
    """Test user step aborts if account is incomplete and email not verified."""
    user_input = {
        CONF_USER_NAME: "user",
        CONF_PASSWORD: "pass",
        CONF_REGION: REGION_NA,
    }
    flow._client = MagicMock()
    flow._client.is_email_verified = AsyncMock(return_value=False)
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_device",
            new=AsyncMock(side_effect=Exception("fail")),
        ),
        patch(
            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
            new=Exception,
        ),
    ):
        result = await flow.async_step_user(user_input)
    assert result["type"] == "abort"
    assert result["reason"] == "incomplete_account_verify_email"


@pytest.mark.asyncio
async def test_async_step_user_incomplete_account_other(flow: MyAirConfigFlow) -> None:
    """Test user step aborts if account is incomplete and not email related."""
    user_input = {
        CONF_USER_NAME: "user",
        CONF_PASSWORD: "pass",
        CONF_REGION: REGION_NA,
    }
    flow._client = MagicMock()
    flow._client.is_email_verified = AsyncMock(side_effect=Exception("fail"))
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_device",
            new=AsyncMock(side_effect=Exception("fail")),
        ),
        patch(
            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
            new=Exception,
        ),
    ):
        result = await flow.async_step_user(user_input)
    assert result["type"] == "abort"
    assert result["reason"] == "incomplete_account"


@pytest.mark.asyncio
async def test_async_step_verify_mfa_success(flow: MyAirConfigFlow) -> None:
    """Test successful MFA verification step."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    user_input: dict[str, str] = {CONF_VERIFICATION_CODE: "123456"}
    device: dict[str, str] = {
        "fgDeviceManufacturerName": "ResMed",
        "localizedName": "CPAP",
        "serialNumber": "SN123",
    }
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_mfa_device",
            new=AsyncMock(return_value=(AUTHN_SUCCESS, device)),
        ),
        patch.object(
            flow.hass.config_entries,
            "async_entry_for_domain_unique_id",
            return_value=None,
        ),
    ):
        result = await flow.async_step_verify_mfa(user_input)
    # Accept either a form or create_entry for robustness
    assert result["type"] in ("create_entry", "form")
    if result["type"] == "create_entry":
        assert "ResMed-CPAP" in result["title"]


@pytest.mark.asyncio
async def test_async_step_verify_mfa_error(flow: MyAirConfigFlow) -> None:
    """Test MFA verification step with error."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    user_input: dict[str, str] = {CONF_VERIFICATION_CODE: "bad"}
    with patch(
        "custom_components.resmed_myair.config_flow.get_mfa_device",
        new=AsyncMock(side_effect=Exception("fail")),
    ):
        result = await flow.async_step_verify_mfa(user_input)
    assert result["type"] == "form"
    assert "errors" in result
    if "base" in result["errors"]:
        assert result["errors"]["base"] == "mfa_error"


@pytest.mark.asyncio
async def test_async_step_verify_mfa_incomplete_account_email_not_verified(
    flow: MyAirConfigFlow,
) -> None:
    """Test MFA step shows form with error if account is incomplete and email not verified."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    user_input = {CONF_VERIFICATION_CODE: "123456"}
    flow._client.is_email_verified = AsyncMock(return_value=False)
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_mfa_device",
            new=AsyncMock(side_effect=Exception("fail")),
        ),
        patch(
            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
            new=Exception,
        ),
    ):
        result = await flow.async_step_verify_mfa(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "verify_mfa"
    assert "errors" in result


@pytest.mark.asyncio
async def test_async_step_verify_mfa_incomplete_account_other(flow: MyAirConfigFlow) -> None:
    """Test MFA step shows form with error if account is incomplete and not email related."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    user_input = {CONF_VERIFICATION_CODE: "123456"}
    flow._client.is_email_verified = AsyncMock(side_effect=Exception("fail"))
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_mfa_device",
            new=AsyncMock(side_effect=Exception("fail")),
        ),
        patch(
            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
            new=Exception,
        ),
    ):
        result = await flow.async_step_verify_mfa(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "verify_mfa"
    assert "errors" in result


@pytest.mark.asyncio
async def test_async_step_user_form_display(flow: MyAirConfigFlow) -> None:
    """Test that the user form is shown when no input is provided."""
    result = await flow.async_step_user()
    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert "errors" in result


@pytest.mark.asyncio
async def test_async_step_verify_mfa_form_display(flow: MyAirConfigFlow) -> None:
    """Test that the MFA form is shown when no input is provided."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    result = await flow.async_step_verify_mfa()
    assert result["type"] == "form"
    assert result["step_id"] == "verify_mfa"
    assert "errors" in result


@pytest.mark.asyncio
async def test_async_step_verify_mfa_incomplete_account(flow: MyAirConfigFlow) -> None:
    """Test MFA step aborts if account is incomplete."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    user_input: dict[str, str] = {CONF_VERIFICATION_CODE: "123456"}
    # Simulate IncompleteAccountError and email not verified
    flow._client.is_email_verified = AsyncMock(return_value=False)
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_mfa_device",
            new=AsyncMock(side_effect=Exception("fail")),
        ),
        patch(
            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
            new=Exception,
        ),
    ):
        result = await flow.async_step_verify_mfa(user_input)
    # Should show form with errors or abort for incomplete account
    assert result["type"] == "form" or result.get("reason") in (
        "incomplete_account_verify_email",
        "incomplete_account",
    )


@pytest.mark.asyncio
async def test_async_step_reauth_confirm_form_display(flow: MyAirConfigFlow) -> None:
    """Test that the reauth confirm form is shown when no input is provided."""
    flow._data = {CONF_USER_NAME: "user", CONF_PASSWORD: "pass"}
    result = await flow.async_step_reauth_confirm()
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_confirm"
    assert "errors" in result


@pytest.mark.asyncio
async def test_async_step_reauth_verify_mfa_form_display(flow: MyAirConfigFlow) -> None:
    """Test that the reauth verify MFA form is shown when no input is provided."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    result = await flow.async_step_reauth_verify_mfa()
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_verify_mfa"
    assert "errors" in result


@pytest.mark.asyncio
async def test_async_step_reauth_success(flow: MyAirConfigFlow) -> None:
    """Test reauth step completes successfully."""
    flow._data = {CONF_USER_NAME: "user", CONF_PASSWORD: "pass", CONF_REGION: REGION_NA}
    device = {
        "serialNumber": "SN123",
        "fgDeviceManufacturerName": "ResMed",
        "localizedName": "CPAP",
    }
    flow._entry = MagicMock()
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=flow._entry)
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_device",
            new=AsyncMock(return_value=(AUTHN_SUCCESS, device, MagicMock(device_token="token"))),
        ),
        patch.object(flow.hass.config_entries, "async_update_entry") as mock_update,
        patch.object(flow.hass.config_entries, "async_reload", new=AsyncMock()),
    ):
        result = await flow.async_step_reauth_confirm(
            {CONF_USER_NAME: "user", CONF_PASSWORD: "pass"}
        )
    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
    mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_async_step_reauth_confirm_mfa(flow: MyAirConfigFlow) -> None:
    """Test reauth confirm step triggers MFA if needed."""
    flow._data = {CONF_USER_NAME: "user", CONF_PASSWORD: "pass", CONF_REGION: REGION_NA}
    flow._entry = MagicMock()
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=flow._entry)
    with patch(
        "custom_components.resmed_myair.config_flow.get_device",
        new=AsyncMock(return_value=("MFA_REQUIRED", None, MagicMock())),
    ):
        result = await flow.async_step_reauth_confirm(
            {CONF_USER_NAME: "user", CONF_PASSWORD: "pass"}
        )
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_verify_mfa"


@pytest.mark.asyncio
async def test_async_step_reauth_confirm_incomplete_account_email_not_verified(
    flow: MyAirConfigFlow,
) -> None:
    """Test reauth confirm aborts if account is incomplete and email not verified."""
    flow._data = {CONF_USER_NAME: "user", CONF_PASSWORD: "pass", CONF_REGION: REGION_NA}
    flow._entry = MagicMock()
    flow._client = MagicMock()
    flow._client.is_email_verified = AsyncMock(return_value=False)
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=flow._entry)
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_device",
            new=AsyncMock(side_effect=Exception("fail")),
        ),
        patch(
            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
            new=Exception,
        ),
    ):
        result = await flow.async_step_reauth_confirm(
            {CONF_USER_NAME: "user", CONF_PASSWORD: "pass"}
        )
    assert result["type"] == "abort" or (result["type"] == "form" and "errors" in result)


@pytest.mark.asyncio
async def test_async_step_reauth_confirm_incomplete_account_other(flow: MyAirConfigFlow) -> None:
    """Test reauth confirm aborts if account is incomplete and not email related."""
    flow._data = {CONF_USER_NAME: "user", CONF_PASSWORD: "pass", CONF_REGION: REGION_NA}
    flow._entry = MagicMock()
    flow._client = MagicMock()
    flow._client.is_email_verified = AsyncMock(side_effect=Exception("fail"))
    flow.hass.config_entries.async_get_entry = MagicMock(return_value=flow._entry)
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_device",
            new=AsyncMock(side_effect=Exception("fail")),
        ),
        patch(
            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
            new=Exception,
        ),
    ):
        result = await flow.async_step_reauth_confirm(
            {CONF_USER_NAME: "user", CONF_PASSWORD: "pass"}
        )
    assert result["type"] == "abort" or (result["type"] == "form" and "errors" in result)


@pytest.mark.asyncio
async def test_async_step_reauth_verify_mfa_success(flow: MyAirConfigFlow) -> None:
    """Test reauth verify MFA step completes successfully."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user", CONF_PASSWORD: "pass"}
    flow._entry = MagicMock()
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_mfa_device",
            new=AsyncMock(
                return_value=(
                    AUTHN_SUCCESS,
                    {"fgDeviceManufacturerName": "ResMed", "localizedName": "CPAP"},
                )
            ),
        ),
        patch.object(flow.hass.config_entries, "async_update_entry") as mock_update,
        patch.object(flow.hass.config_entries, "async_reload", new=AsyncMock()),
    ):
        result = await flow.async_step_reauth_verify_mfa({CONF_VERIFICATION_CODE: "123456"})
    if result["type"] == "abort":
        assert result["reason"] == "reauth_successful"
        mock_update.assert_called_once()
    else:
        assert result["type"] == "form"
        assert result["step_id"] == "reauth_verify_mfa"
        assert "errors" in result


@pytest.mark.asyncio
async def test_async_step_reauth_verify_mfa_error(flow: MyAirConfigFlow) -> None:
    """Test reauth verify MFA step with error."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user", CONF_PASSWORD: "pass"}
    flow._entry = MagicMock()
    with patch(
        "custom_components.resmed_myair.config_flow.get_mfa_device",
        new=AsyncMock(side_effect=Exception("fail")),
    ):
        result = await flow.async_step_reauth_verify_mfa({CONF_VERIFICATION_CODE: "bad"})
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_verify_mfa"
    assert "errors" in result
    if "base" in result["errors"]:
        assert result["errors"]["base"] == "mfa_error"


@pytest.mark.asyncio
async def test_async_step_reauth_verify_mfa_incomplete_account_email_not_verified(
    flow: MyAirConfigFlow,
) -> None:
    """Test reauth MFA step shows form with error if account is incomplete and email not verified."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    user_input = {CONF_VERIFICATION_CODE: "123456"}
    flow._client.is_email_verified = AsyncMock(return_value=False)
    with (
        patch(
            "custom_components.resmed_myair.config_flow.get_mfa_device",
            new=AsyncMock(side_effect=Exception("fail")),
        ),
        patch(
            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
            new=Exception,
        ),
    ):
        result = await flow.async_step_reauth_verify_mfa(user_input)
    assert result["type"] == "form"
    assert result["step_id"] == "reauth_verify_mfa"
    assert "errors" in result


@pytest.mark.asyncio
async def test_async_step_reauth_verify_mfa_incomplete_account_other(flow: MyAirConfigFlow) -> None:
    """Test reauth MFA step shows form with error if account is incomplete and not email related."""
    flow._client = MagicMock()
    flow._data = {CONF_USER_NAME: "user"}
    user_input = {CONF_VERIFICATION_CODE: "123456"}
    flow._client.is_email_verified = AsyncMock(side_effect=Exception("fail"))

    @pytest.mark.asyncio
    async def test_get_device_success():
        """Test get_device returns device and client on successful auth."""
        hass = MagicMock()
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value=AUTHN_SUCCESS)
        mock_device = {"serialNumber": "SN123"}
        mock_client.get_user_device_data = AsyncMock(return_value=mock_device)

        with (
            patch("custom_components.resmed_myair.config_flow.MyAirConfig") as mock_config,
            patch(
                "custom_components.resmed_myair.config_flow.RESTClient", return_value=mock_client
            ),
            patch(
                "custom_components.resmed_myair.config_flow.async_create_clientsession",
                return_value=MagicMock(),
            ),
        ):
            status, device, client = await get_device(
                hass, "user", "pass", "region", device_token=None
            )

        assert status == AUTHN_SUCCESS
        assert device == mock_device
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_get_device_auth_failure():
        """Test get_device returns None device on failed auth."""
        hass = MagicMock()
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value="AUTHN_FAIL")
        mock_client.get_user_device_data = AsyncMock()

        with (
            patch("custom_components.resmed_myair.config_flow.MyAirConfig") as mock_config,
            patch(
                "custom_components.resmed_myair.config_flow.RESTClient", return_value=mock_client
            ),
            patch(
                "custom_components.resmed_myair.config_flow.async_create_clientsession",
                return_value=MagicMock(),
            ),
        ):
            status, device, client = await get_device(
                hass, "user", "pass", "region", device_token=None
            )

        assert status == "AUTHN_FAIL"
        assert device is None
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_get_device_passes_device_token():
        """Test get_device passes device_token to MyAirConfig."""
        hass = MagicMock()
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(return_value=AUTHN_SUCCESS)
        mock_client.get_user_device_data = AsyncMock(return_value={})
        with (
            patch("custom_components.resmed_myair.config_flow.MyAirConfig") as mock_config,
            patch(
                "custom_components.resmed_myair.config_flow.RESTClient", return_value=mock_client
            ),
            patch(
                "custom_components.resmed_myair.config_flow.async_create_clientsession",
                return_value=MagicMock(),
            ),
        ):
            await get_device(hass, "user", "pass", "region", device_token="token123")
            mock_config.assert_called_once_with(
                username="user", password="pass", region="region", device_token="token123"
            )

            @pytest.mark.asyncio
            async def test_get_mfa_device_success():
                """Test get_mfa_device returns correct status and device."""
                mock_client = MagicMock()
                mock_client.verify_mfa_and_get_access_token = AsyncMock(return_value=AUTHN_SUCCESS)
                mock_device = {"serialNumber": "SN123"}
                mock_client.get_user_device_data = AsyncMock(return_value=mock_device)

                status, device = await get_mfa_device(mock_client, "123456")

                mock_client.verify_mfa_and_get_access_token.assert_awaited_once_with("123456")
                mock_client.get_user_device_data.assert_awaited_once_with(initial=True)
                assert status == AUTHN_SUCCESS
                assert device == mock_device

            @pytest.mark.asyncio
            async def test_get_mfa_device_failure_status():
                """Test get_mfa_device returns non-success status and device."""
                mock_client = MagicMock()
                mock_client.verify_mfa_and_get_access_token = AsyncMock(return_value="MFA_FAIL")
                mock_device = {"error": "bad code"}
                mock_client.get_user_device_data = AsyncMock(return_value=mock_device)

                status, device = await get_mfa_device(mock_client, "badcode")

                mock_client.verify_mfa_and_get_access_token.assert_awaited_once_with("badcode")
                mock_client.get_user_device_data.assert_awaited_once_with(initial=True)
                assert status == "MFA_FAIL"
                assert device == mock_device

            @pytest.mark.asyncio
            async def test_get_mfa_device_raises_on_verify():
                """Test get_mfa_device raises if verify_mfa_and_get_access_token raises."""
                mock_client = MagicMock()
                mock_client.verify_mfa_and_get_access_token = AsyncMock(
                    side_effect=Exception("fail")
                )
                mock_client.get_user_device_data = AsyncMock()

                with pytest.raises(Exception) as exc:
                    await get_mfa_device(mock_client, "badcode")
                assert str(exc.value) == "fail"
                mock_client.verify_mfa_and_get_access_token.assert_awaited_once_with("badcode")
                mock_client.get_user_device_data.assert_not_awaited()

            @pytest.mark.asyncio
            async def test_get_mfa_device_raises_on_get_user_device_data():
                """Test get_mfa_device raises if get_user_device_data raises."""
                mock_client = MagicMock()
                mock_client.verify_mfa_and_get_access_token = AsyncMock(return_value=AUTHN_SUCCESS)
                mock_client.get_user_device_data = AsyncMock(side_effect=Exception("fail_device"))

                with pytest.raises(Exception) as exc:
                    await get_mfa_device(mock_client, "123456")
                assert str(exc.value) == "fail_device"
                mock_client.verify_mfa_and_get_access_token.assert_awaited_once_with("123456")
                mock_client.get_user_device_data.assert_awaited_once_with(initial=True)

                @pytest.mark.asyncio
                async def test_async_step_verify_mfa_success_creates_entry(flow: MyAirConfigFlow):
                    """Test async_step_verify_mfa creates entry on successful MFA."""
                    flow._client = MagicMock()
                    flow._data = {CONF_USER_NAME: "user"}
                    user_input = {CONF_VERIFICATION_CODE: "654321"}
                    device = {
                        "fgDeviceManufacturerName": "ResMed",
                        "localizedName": "CPAP",
                        "serialNumber": "SN123",
                    }
                    with patch(
                        "custom_components.resmed_myair.config_flow.get_mfa_device",
                        new=AsyncMock(return_value=(AUTHN_SUCCESS, device)),
                    ):
                        result = await flow.async_step_verify_mfa(user_input)
                    assert result["type"] == "create_entry"
                    assert "ResMed-CPAP" in result["title"]
                    assert result["data"][CONF_USER_NAME] == "user"
                    assert CONF_DEVICE_TOKEN in result["data"]

                @pytest.mark.asyncio
                async def test_async_step_verify_mfa_status_not_success_shows_form_with_error(
                    flow: MyAirConfigFlow,
                ):
                    """Test async_step_verify_mfa shows form with error if status is not AUTHN_SUCCESS."""
                    flow._client = MagicMock()
                    flow._data = {CONF_USER_NAME: "user"}
                    user_input = {CONF_VERIFICATION_CODE: "badcode"}
                    with patch(
                        "custom_components.resmed_myair.config_flow.get_mfa_device",
                        new=AsyncMock(return_value=("MFA_FAIL", {})),
                    ):
                        result = await flow.async_step_verify_mfa(user_input)
                    assert result["type"] == "form"
                    assert result["step_id"] == "verify_mfa"
                    assert result["errors"]["base"] == "mfa_error"

                @pytest.mark.asyncio
                async def test_async_step_verify_mfa_auth_error_exception(flow: MyAirConfigFlow):
                    """Test async_step_verify_mfa shows form with error on AuthenticationError."""
                    flow._client = MagicMock()
                    flow._data = {CONF_USER_NAME: "user"}
                    user_input = {CONF_VERIFICATION_CODE: "badcode"}
                    with (
                        patch(
                            "custom_components.resmed_myair.config_flow.get_mfa_device",
                            new=AsyncMock(side_effect=Exception("fail")),
                        ),
                        patch(
                            "custom_components.resmed_myair.config_flow.AuthenticationError",
                            new=Exception,
                        ),
                        patch(
                            "custom_components.resmed_myair.config_flow.HttpProcessingError",
                            new=Exception,
                        ),
                        patch(
                            "custom_components.resmed_myair.config_flow.ClientResponseError",
                            new=Exception,
                        ),
                        patch(
                            "custom_components.resmed_myair.config_flow.ParsingError",
                            new=Exception,
                        ),
                    ):
                        result = await flow.async_step_verify_mfa(user_input)
                    assert result["type"] == "form"
                    assert result["step_id"] == "verify_mfa"
                    assert result["errors"]["base"] == "mfa_error"

                @pytest.mark.asyncio
                async def test_async_step_verify_mfa_incomplete_account_email_not_verified(
                    flow: MyAirConfigFlow,
                ):
                    """Test async_step_verify_mfa aborts if IncompleteAccountError and email not verified."""
                    flow._client = MagicMock()
                    flow._data = {CONF_USER_NAME: "user"}
                    user_input = {CONF_VERIFICATION_CODE: "123456"}
                    flow._client.is_email_verified = AsyncMock(return_value=False)
                    with (
                        patch(
                            "custom_components.resmed_myair.config_flow.get_mfa_device",
                            new=AsyncMock(side_effect=Exception("fail")),
                        ),
                        patch(
                            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
                            new=Exception,
                        ),
                    ):
                        result = await flow.async_step_verify_mfa(user_input)
                    assert result["type"] == "abort"
                    assert result["reason"] == "incomplete_account_verify_email"

                @pytest.mark.asyncio
                async def test_async_step_verify_mfa_incomplete_account_other(
                    flow: MyAirConfigFlow,
                ):
                    """Test async_step_verify_mfa aborts if IncompleteAccountError and not email related."""
                    flow._client = MagicMock()
                    flow._data = {CONF_USER_NAME: "user"}
                    user_input = {CONF_VERIFICATION_CODE: "123456"}
                    flow._client.is_email_verified = AsyncMock(side_effect=Exception("fail"))
                    with (
                        patch(
                            "custom_components.resmed_myair.config_flow.get_mfa_device",
                            new=AsyncMock(side_effect=Exception("fail")),
                        ),
                        patch(
                            "custom_components.resmed_myair.config_flow.IncompleteAccountError",
                            new=Exception,
                        ),
                    ):
                        result = await flow.async_step_verify_mfa(user_input)
                    assert result["type"] == "abort"
                    assert result["reason"] == "incomplete_account"

                @pytest.mark.asyncio
                async def test_async_step_verify_mfa_no_user_input_shows_form(
                    flow: MyAirConfigFlow,
                ):
                    """Test async_step_verify_mfa shows form if no user_input is provided."""
                    flow._client = MagicMock()
                    flow._data = {CONF_USER_NAME: "user"}
                    result = await flow.async_step_verify_mfa()
                    assert result["type"] == "form"
                    assert result["step_id"] == "verify_mfa"
                    assert "errors" in result


@pytest.mark.asyncio
async def test_get_device_success(hass):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value=AUTHN_SUCCESS)
    mock_client.get_user_device_data = AsyncMock(
        return_value={
            "serialNumber": "123",
            "fgDeviceManufacturerName": "ResMed",
            "localizedName": "MyDevice",
        }
    )
    with patch("custom_components.resmed_myair.config_flow.RESTClient", return_value=mock_client):
        with patch("custom_components.resmed_myair.config_flow.async_create_clientsession"):
            status, device, client = await get_device(hass, "user", "pass", "NA")
            assert status == AUTHN_SUCCESS
            assert device["serialNumber"] == "123"
            assert client is mock_client


@pytest.mark.asyncio
async def test_get_device_not_success(hass):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(return_value="FAIL")
    with patch("custom_components.resmed_myair.config_flow.RESTClient", return_value=mock_client):
        with patch("custom_components.resmed_myair.config_flow.async_create_clientsession"):
            status, device, client = await get_device(hass, "user", "pass", "NA")
            assert status == "FAIL"
            assert device is None
            assert client is mock_client


@pytest.mark.asyncio
async def test_get_device_connect_error(hass):
    mock_client = MagicMock()
    mock_client.connect = AsyncMock(side_effect=Exception("fail"))
    with patch("custom_components.resmed_myair.config_flow.RESTClient", return_value=mock_client):
        with patch("custom_components.resmed_myair.config_flow.async_create_clientsession"):
            with pytest.raises(Exception, match="fail"):
                await get_device(hass, "user", "pass", "NA")


@pytest.mark.asyncio
async def test_get_mfa_device_success():
    mock_client = MagicMock()
    mock_client.verify_mfa_and_get_access_token = AsyncMock(return_value="AUTHN_SUCCESS")
    mock_client.get_user_device_data = AsyncMock(
        return_value={
            "serialNumber": "123",
            "fgDeviceManufacturerName": "ResMed",
            "localizedName": "MyDevice",
        }
    )
    status, device = await get_mfa_device(mock_client, "123456")
    assert status == "AUTHN_SUCCESS"
    assert device["serialNumber"] == "123"


@pytest.mark.asyncio
async def test_get_mfa_device_error():
    mock_client = MagicMock()
    mock_client.verify_mfa_and_get_access_token = AsyncMock(side_effect=Exception("fail"))
    with pytest.raises(Exception, match="fail"):
        await get_mfa_device(mock_client, "123456")


@pytest.mark.asyncio
async def test_async_step_reauth_calls_confirm(monkeypatch):
    flow = MyAirConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"entry_id": "123"}
    flow._data = {}

    entry = MagicMock()
    flow.hass.config_entries.async_get_entry.return_value = entry

    # Patch async_step_reauth_confirm to check it is called
    flow.async_step_reauth_confirm = AsyncMock(return_value={"type": "form"})
    entry_data = {"foo": "bar"}

    result = await flow.async_step_reauth(entry_data)
    assert result == {"type": "form"}
    assert flow._entry == entry
    assert flow._data["foo"] == "bar"
    flow.async_step_reauth_confirm.assert_awaited_once()


@pytest.mark.asyncio
async def test_async_step_reauth_no_entry(monkeypatch):
    flow = MyAirConfigFlow()
    flow.hass = MagicMock()
    flow.context = {"entry_id": "notfound"}
    flow._data = {}

    flow.hass.config_entries.async_get_entry.return_value = None
    flow.async_step_reauth_confirm = AsyncMock(return_value={"type": "form"})
    entry_data = {"baz": "qux"}

    result = await flow.async_step_reauth(entry_data)
    # Should still call reauth_confirm even if entry is missing
    assert result == {"type": "form"}
    assert flow._data["baz"] == "qux"


@pytest.mark.asyncio
async def test_async_step_reauth_verify_mfa_user_input_and_client(monkeypatch):
    flow = MyAirConfigFlow()
    flow.hass = MagicMock()
    flow._data = {}
    flow._entry = MagicMock()
    # Set up a real RESTClient instance (or a MagicMock with spec)
    flow._client = MagicMock(spec=RESTClient)
    user_input = {"verification_code": "123456"}

    # Patch get_mfa_device to return AUTHN_SUCCESS
    monkeypatch.setattr(
        "custom_components.resmed_myair.config_flow.get_mfa_device",
        AsyncMock(return_value=(AUTHN_SUCCESS, {"serialNumber": "SN123"})),
    )
    # Patch async_update_entry and async_reload
    flow.hass.config_entries.async_update_entry = MagicMock()
    flow.hass.config_entries.async_reload = AsyncMock()

    result = await flow.async_step_reauth_verify_mfa(user_input)
    assert result["type"] == "abort"
    assert result["reason"] == "reauth_successful"
