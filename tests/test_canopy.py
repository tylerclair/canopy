"""Tests for canopy/canopy.py — CanvasAPIError and CanvasSession."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from canopy import CanvasAPIError, CanvasSession

# ── Helpers ─────────────────────────────────────────────────────────


def _mock_response(
    status_code: int = 200,
    json_data=None,
    text: str = "",
    links: dict | None = None,
) -> MagicMock:
    """Build a mock httpx.Response."""
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.links = links or {}
    if json_data is not None:
        mock.json.return_value = json_data
    else:
        mock.json.side_effect = Exception("not JSON")
        mock.text = text
    return mock


def _mock_response_raise(status_code: int = 404, json_data=None) -> MagicMock:
    """Build a mock that raises HTTPStatusError on raise_for_status()."""
    inner = _mock_response(status_code, json_data or {"errors": [{"message": "not found"}]})
    error = httpx.HTTPStatusError("error", request=MagicMock(), response=inner)
    outer = MagicMock(spec=httpx.Response)
    outer.raise_for_status.side_effect = error
    return outer


# ── CanvasAPIError ───────────────────────────────────────────────────


class TestCanvasAPIError:
    def test_status_code_stored(self):
        resp = _mock_response(404, {"errors": [{"message": "not found"}]})
        err = CanvasAPIError(resp)
        assert err.status_code == 404

    def test_json_content_parsed(self):
        payload = {"errors": [{"message": "unauthorized"}]}
        resp = _mock_response(401, payload)
        err = CanvasAPIError(resp)
        assert err.content == payload

    def test_non_json_falls_back_to_text(self):
        resp = _mock_response(500, text="Internal Server Error")
        err = CanvasAPIError(resp)
        assert err.content == "Internal Server Error"

    def test_response_attribute_stored(self):
        resp = _mock_response(403, {"message": "forbidden"})
        err = CanvasAPIError(resp)
        assert err.response is resp

    def test_str_includes_status_and_content(self):
        resp = _mock_response(422, {"message": "invalid"})
        err = CanvasAPIError(resp)
        s = str(err)
        assert "422" in s
        assert "invalid" in s

    def test_to_json_structure(self):
        resp = _mock_response(404, {"errors": [{"message": "not found"}]})
        err = CanvasAPIError(resp)
        parsed = json.loads(err.to_json())
        assert parsed["status_code"] == 404
        assert parsed["content"] == {"errors": [{"message": "not found"}]}

    def test_to_json_is_valid_json_string(self):
        resp = _mock_response(500, text="oops")
        err = CanvasAPIError(resp)
        result = err.to_json()
        assert isinstance(result, str)
        json.loads(result)  # must not raise

    def test_is_exception_subclass(self):
        resp = _mock_response(400, {})
        err = CanvasAPIError(resp)
        assert isinstance(err, Exception)


# ── CanvasSession — init & properties ───────────────────────────────


class TestCanvasSessionInit:
    def test_trailing_slash_stripped(self):
        s = CanvasSession("https://canvas.example.com/", "token")
        assert s.instance_address == "https://canvas.example.com"

    def test_no_trailing_slash_unchanged(self):
        s = CanvasSession("https://canvas.example.com", "token")
        assert s.instance_address == "https://canvas.example.com"

    def test_access_token_stored(self):
        s = CanvasSession("https://canvas.example.com", "mytoken")
        assert s.access_token == "mytoken"

    def test_default_max_per_page(self):
        s = CanvasSession("https://canvas.example.com", "token")
        assert s.max_per_page == 100

    def test_custom_max_per_page(self):
        s = CanvasSession("https://canvas.example.com", "token", max_per_page=50)
        assert s.max_per_page == 50

    def test_auth_header_set(self):
        s = CanvasSession("https://canvas.example.com", "mytoken")
        assert s._headers == {"Authorization": "Bearer mytoken"}

    def test_clients_start_as_none(self):
        s = CanvasSession("https://canvas.example.com", "token")
        assert s._sync_client is None
        assert s._async_client is None

    def test_session_property_lazy_init(self):
        s = CanvasSession("https://canvas.example.com", "token")
        client = s.session
        assert isinstance(client, httpx.Client)
        assert s.session is client  # same instance on second access

    def test_async_session_property_lazy_init(self):
        s = CanvasSession("https://canvas.example.com", "token")
        client = s.async_session
        assert isinstance(client, httpx.AsyncClient)
        assert s.async_session is client


# ── CanvasSession — helpers ──────────────────────────────────────────


class TestCanvasSessionHelpers:
    def setup_method(self):
        self.session = CanvasSession("https://canvas.example.com", "token", max_per_page=50)

    def test_pagination_params_merges_per_page(self):
        result = self.session._pagination_params({"include": "teachers"})
        assert result == {"include": "teachers", "per_page": 50}

    def test_pagination_params_none_input(self):
        result = self.session._pagination_params(None)
        assert result == {"per_page": 50}

    def test_needs_pagination_all_pages(self):
        assert self.session._needs_pagination({"all_pages": True}) is True

    def test_needs_pagination_poly_response(self):
        assert self.session._needs_pagination({"poly_response": True}) is True

    def test_needs_pagination_false(self):
        assert self.session._needs_pagination({"single_item": True}) is False
        assert self.session._needs_pagination({}) is False

    def test_extract_data_list_response(self):
        resp = _mock_response(200, [{"id": 1}, {"id": 2}])
        assert self.session._extract_data(resp) == [{"id": 1}, {"id": 2}]

    def test_extract_data_dict_no_key(self):
        resp = _mock_response(200, {"id": 1, "name": "Test"})
        assert self.session._extract_data(resp) == {"id": 1, "name": "Test"}

    def test_extract_data_dict_with_key(self):
        resp = _mock_response(200, {"id": 1, "name": "Test"})
        assert self.session._extract_data(resp, data_key="name") == "Test"

    def test_next_url_present(self):
        resp = _mock_response(200, [], links={"next": {"url": "https://canvas.example.com/page=2"}})
        assert self.session._next_url(resp) == "https://canvas.example.com/page=2"

    def test_next_url_absent(self):
        resp = _mock_response(200, [])
        assert self.session._next_url(resp) is None


# ── CanvasSession — base_request ────────────────────────────────────


class TestBaseRequest:
    def setup_method(self):
        self.session = CanvasSession("https://canvas.example.com", "token")

    def _patch_request(self, json_data=None, links=None):
        resp = _mock_response(200, json_data or {"id": 1}, links=links)
        resp.raise_for_status = MagicMock()
        return patch.object(self.session.session, "request", return_value=resp)

    def test_returns_json_by_default(self):
        with self._patch_request({"id": 1}) as mock_req:
            result = self.session.base_request("GET", "/api/v1/accounts/1")
        assert result == {"id": 1}

    def test_do_not_process_returns_response(self):
        with self._patch_request({"id": 1}) as mock_req:
            result = self.session.base_request("GET", "/api/v1/accounts/1", do_not_process=True)
        assert isinstance(result, MagicMock)

    def test_no_data_returns_status_code(self):
        with self._patch_request({"id": 1}) as mock_req:
            result = self.session.base_request("DELETE", "/api/v1/accounts/1", no_data=True)
        assert result == 200

    def test_single_item_returns_dict(self):
        with self._patch_request({"id": 1, "name": "test"}):
            result = self.session.base_request("GET", "/api/v1/accounts/1", single_item=True)
        assert result == {"id": 1, "name": "test"}

    def test_single_item_with_data_key(self):
        with self._patch_request({"account": {"id": 1}}):
            result = self.session.base_request(
                "GET", "/api/v1/accounts/1", data_key="account", single_item=True
            )
        assert result == {"id": 1}

    def test_http_error_raises_canvas_api_error(self):
        mock_resp = _mock_response(404, {"errors": [{"message": "not found"}]})
        error = httpx.HTTPStatusError("not found", request=MagicMock(), response=mock_resp)
        with patch.object(self.session.session, "request") as mock_req:
            mock_req.return_value.raise_for_status.side_effect = error
            with pytest.raises(CanvasAPIError) as exc_info:
                self.session.base_request("GET", "/api/v1/accounts/99999")
        assert exc_info.value.status_code == 404

    def test_all_pages_depaginates(self):
        page1 = _mock_response(200, [{"id": 1}], links={"next": {"url": "https://canvas.example.com/page=2"}})
        page1.raise_for_status = MagicMock()
        page2 = _mock_response(200, [{"id": 2}])
        page2.raise_for_status = MagicMock()

        with patch.object(self.session.session, "request", return_value=page1):
            with patch.object(self.session.session, "get", return_value=page2):
                result = self.session.base_request("GET", "/api/v1/accounts", all_pages=True)
        assert result == [{"id": 1}, {"id": 2}]

    def test_force_urlencode_data(self):
        with self._patch_request({"id": 1}) as mock_req:
            self.session.base_request(
                "GET", "/api/v1/accounts", data={"foo": "bar"}, force_urlencode_data=True
            )
        call_args = mock_req.call_args
        # data should be passed as None when force_urlencode_data is True
        assert call_args.kwargs.get("data") is None or call_args[1].get("data") is None

    def test_poly_response_list_no_next_returns_list(self):
        with self._patch_request([{"id": 1}]):
            result = self.session.base_request("GET", "/api/v1/accounts", poly_response=True)
        assert result == [{"id": 1}]

    def test_poly_response_dict_returns_dict(self):
        with self._patch_request({"id": 1}):
            result = self.session.base_request("GET", "/api/v1/accounts/1", poly_response=True)
        assert result == {"id": 1}


# ── CanvasSession — convenience methods inject per_page ─────────────


class TestConvenienceMethods:
    def setup_method(self):
        self.session = CanvasSession("https://canvas.example.com", "token", max_per_page=75)

    def test_get_injects_per_page_for_all_pages(self):
        resp = _mock_response(200, [])
        resp.raise_for_status = MagicMock()
        with patch.object(self.session, "base_request", return_value=[]) as mock_br:
            self.session.get("/api/v1/accounts", all_pages=True)
        _, kwargs = mock_br.call_args
        assert kwargs["params"]["per_page"] == 75

    def test_get_injects_per_page_for_poly_response(self):
        with patch.object(self.session, "base_request", return_value=[]) as mock_br:
            self.session.get("/api/v1/accounts", poly_response=True)
        _, kwargs = mock_br.call_args
        assert kwargs["params"]["per_page"] == 75

    def test_get_no_pagination_does_not_inject_per_page(self):
        with patch.object(self.session, "base_request", return_value={}) as mock_br:
            self.session.get("/api/v1/accounts/1")
        _, kwargs = mock_br.call_args
        assert kwargs.get("params") is None or "per_page" not in (kwargs.get("params") or {})

    def test_post_calls_base_request(self):
        with patch.object(self.session, "base_request", return_value={"id": 1}) as mock_br:
            result = self.session.post("/api/v1/accounts", data={"name": "test"})
        mock_br.assert_called_once_with("POST", "/api/v1/accounts", data={"name": "test"})
        assert result == {"id": 1}

    def test_put_calls_base_request(self):
        with patch.object(self.session, "base_request", return_value={"id": 1}) as mock_br:
            self.session.put("/api/v1/accounts/1", data={"name": "updated"})
        mock_br.assert_called_once_with("PUT", "/api/v1/accounts/1", data={"name": "updated"})

    def test_delete_calls_base_request(self):
        with patch.object(self.session, "base_request", return_value=200) as mock_br:
            self.session.delete("/api/v1/accounts/1")
        mock_br.assert_called_once_with("DELETE", "/api/v1/accounts/1", params=None)


# ── CanvasSession — async convenience methods ────────────────────────


class TestAsyncConvenienceMethods:
    def setup_method(self):
        self.session = CanvasSession("https://canvas.example.com", "token", max_per_page=75)

    @pytest.mark.asyncio
    async def test_async_get_injects_per_page(self):
        with patch.object(self.session, "async_base_request", new_callable=AsyncMock, return_value=[]) as mock_br:
            await self.session.async_get("/api/v1/accounts", all_pages=True)
        _, kwargs = mock_br.call_args
        assert kwargs["params"]["per_page"] == 75

    @pytest.mark.asyncio
    async def test_async_post_calls_async_base_request(self):
        with patch.object(self.session, "async_base_request", new_callable=AsyncMock, return_value={"id": 1}) as mock_br:
            result = await self.session.async_post("/api/v1/accounts", data={"name": "test"})
        mock_br.assert_called_once_with("POST", "/api/v1/accounts", data={"name": "test"})
        assert result == {"id": 1}

    @pytest.mark.asyncio
    async def test_async_put_calls_async_base_request(self):
        with patch.object(self.session, "async_base_request", new_callable=AsyncMock, return_value={"id": 1}) as mock_br:
            await self.session.async_put("/api/v1/accounts/1", data={"name": "updated"})
        mock_br.assert_called_once_with("PUT", "/api/v1/accounts/1", data={"name": "updated"})

    @pytest.mark.asyncio
    async def test_async_delete_calls_async_base_request(self):
        with patch.object(self.session, "async_base_request", new_callable=AsyncMock, return_value=200) as mock_br:
            await self.session.async_delete("/api/v1/accounts/1")
        mock_br.assert_called_once_with("DELETE", "/api/v1/accounts/1", params=None)


# ── CanvasSession — context managers ────────────────────────────────


class TestContextManagers:
    def test_sync_context_manager_calls_close(self):
        s = CanvasSession("https://canvas.example.com", "token")
        with patch.object(s, "close") as mock_close, s:
            pass
        mock_close.assert_called_once()

    def test_sync_context_manager_returns_self(self):
        s = CanvasSession("https://canvas.example.com", "token")
        with s as ctx:
            assert ctx is s

    @pytest.mark.asyncio
    async def test_async_context_manager_calls_aclose(self):
        s = CanvasSession("https://canvas.example.com", "token")
        with patch.object(s, "aclose", new_callable=AsyncMock) as mock_aclose:
            async with s:
                pass
        mock_aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_returns_self(self):
        s = CanvasSession("https://canvas.example.com", "token")
        async with s as ctx:
            assert ctx is s

    def test_close_noop_when_no_client(self):
        s = CanvasSession("https://canvas.example.com", "token")
        s.close()  # should not raise

    def test_close_closes_sync_client(self):
        s = CanvasSession("https://canvas.example.com", "token")
        mock_client = MagicMock(spec=httpx.Client)
        s._sync_client = mock_client
        s.close()
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose_noop_when_no_client(self):
        s = CanvasSession("https://canvas.example.com", "token")
        await s.aclose()  # should not raise

    @pytest.mark.asyncio
    async def test_aclose_closes_async_client(self):
        s = CanvasSession("https://canvas.example.com", "token")
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        s._async_client = mock_client
        await s.aclose()
        mock_client.aclose.assert_called_once()
