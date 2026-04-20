import json
import urllib.parse
from typing import Any

import httpx


class CanvasAPIError(Exception):
    def __init__(self, response: httpx.Response) -> None:
        super().__init__(f"CanvasAPIError: Status {response.status_code}")
        self.response = response
        self.status_code = response.status_code
        try:
            self.content: Any = response.json()
        except Exception:
            self.content = response.text

    def __str__(self) -> str:
        return f"CanvasAPIError: Status {self.status_code} - Content: {self.content}"

    def to_json(self) -> str:
        return json.dumps({"status_code": self.status_code, "content": self.content})


class CanvasSession:
    def __init__(
        self,
        instance_address: str,
        access_token: str,
        max_per_page: int = 100,
    ) -> None:
        self.instance_address = instance_address.rstrip("/")
        self.access_token = access_token
        self.max_per_page = max_per_page
        self._headers = {"Authorization": f"Bearer {self.access_token}"}
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None

    # ── Client properties (lazy init) ──────────────────────────────

    @property
    def session(self) -> httpx.Client:
        if self._sync_client is None:
            self._sync_client = httpx.Client(
                base_url=self.instance_address,
                headers=self._headers,
            )
        return self._sync_client

    @property
    def async_session(self) -> httpx.AsyncClient:
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                base_url=self.instance_address,
                headers=self._headers,
            )
        return self._async_client

    # ── Pagination helpers ──────────────────────────────────────────

    def _extract_data(self, response: httpx.Response, data_key: str | None = None) -> Any:
        data = response.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data if data_key is None else data[data_key]
        raise CanvasAPIError(response)

    def _next_url(self, response: httpx.Response) -> str | None:
        return response.links.get("next", {}).get("url")

    def _depaginate(self, response: httpx.Response, data_key: str | None = None) -> list[Any]:
        all_data: list[Any] = []
        while True:
            chunk = self._extract_data(response, data_key)
            if isinstance(chunk, list):
                all_data.extend(chunk)
            else:
                all_data.append(chunk)
            next_url = self._next_url(response)
            if not next_url:
                break
            response = self.session.get(next_url)
            response.raise_for_status()
        return all_data

    async def _depaginate_async(
        self, response: httpx.Response, data_key: str | None = None
    ) -> list[Any]:
        all_data: list[Any] = []
        while True:
            chunk = self._extract_data(response, data_key)
            if isinstance(chunk, list):
                all_data.extend(chunk)
            else:
                all_data.append(chunk)
            next_url = self._next_url(response)
            if not next_url:
                break
            response = await self.async_session.get(next_url)
            response.raise_for_status()
        return all_data

    # ── Core request dispatcher ─────────────────────────────────────

    def _pagination_params(self, params: dict[str, Any] | None, **extra: Any) -> dict[str, Any]:
        base = {"per_page": self.max_per_page}
        return {**base, **(params or {}), **extra}

    def _needs_pagination(self, kwargs: dict[str, Any]) -> bool:
        return kwargs.get("all_pages", False) or kwargs.get("poly_response", False)

    def base_request(
        self,
        method: str,
        uri: str,
        data_key: str | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        single_item: bool = False,
        all_pages: bool = False,
        do_not_process: bool = False,
        no_data: bool = False,
        poly_response: bool = False,
        force_urlencode_data: bool = False,
        per_page: int | None = None,
        page: int | None = None,
    ) -> Any:
        """Base Canvas sync request method."""
        if per_page is not None or page is not None:
            all_pages = False
            poly_response = False
        if per_page is not None:
            params = {**(params or {}), "per_page": per_page}
        if page is not None:
            params = {**(params or {}), "page": page}

        if force_urlencode_data and data:
            uri = uri + "?" + urllib.parse.urlencode(data)
            data = None

        try:
            response = self.session.request(
                method,
                uri,
                params=params,
                data=data if method not in ("GET", "DELETE") else None,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise CanvasAPIError(e.response) from e

        if do_not_process:
            return response
        if no_data:
            return response.status_code
        if single_item:
            r = response.json()
            return r[data_key] if data_key else r
        if all_pages:
            return self._depaginate(response, data_key)
        if poly_response:
            r = response.json()
            if isinstance(r, list) and self._next_url(response):
                return self._depaginate(response, data_key)
            return self._extract_data(response, data_key)
        return response.json()

    async def async_base_request(
        self,
        method: str,
        uri: str,
        data_key: str | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        single_item: bool = False,
        all_pages: bool = False,
        do_not_process: bool = False,
        no_data: bool = False,
        poly_response: bool = False,
        force_urlencode_data: bool = False,
        per_page: int | None = None,
        page: int | None = None,
    ) -> Any:
        """Base Canvas async request method."""
        if per_page is not None or page is not None:
            all_pages = False
            poly_response = False
        if per_page is not None:
            params = {**(params or {}), "per_page": per_page}
        if page is not None:
            params = {**(params or {}), "page": page}

        if force_urlencode_data and data:
            uri = uri + "?" + urllib.parse.urlencode(data)
            data = None

        try:
            response = await self.async_session.request(
                method,
                uri,
                params=params,
                data=data if method not in ("GET", "DELETE") else None,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise CanvasAPIError(e.response) from e

        if do_not_process:
            return response
        if no_data:
            return response.status_code
        if single_item:
            r = response.json()
            return r[data_key] if data_key else r
        if all_pages:
            return await self._depaginate_async(response, data_key)
        if poly_response:
            r = response.json()
            if isinstance(r, list) and self._next_url(response):
                return await self._depaginate_async(response, data_key)
            return self._extract_data(response, data_key)
        return response.json()

    # ── Sync convenience methods ────────────────────────────────────

    def get(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        if self._needs_pagination(kwargs) and "per_page" not in kwargs:
            params = self._pagination_params(params)
        return self.base_request("GET", url, params=params, **kwargs)

    def post(self, url: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return self.base_request("POST", url, data=data, **kwargs)

    def put(self, url: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return self.base_request("PUT", url, data=data, **kwargs)

    def delete(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return self.base_request("DELETE", url, params=params, **kwargs)

    # ── Async convenience methods ───────────────────────────────────

    async def async_get(self, url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        if self._needs_pagination(kwargs) and "per_page" not in kwargs:
            params = self._pagination_params(params)
        return await self.async_base_request("GET", url, params=params, **kwargs)

    async def async_post(self, url: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return await self.async_base_request("POST", url, data=data, **kwargs)

    async def async_put(self, url: str, data: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        return await self.async_base_request("PUT", url, data=data, **kwargs)

    async def async_delete(
        self, url: str, params: dict[str, Any] | None = None, **kwargs: Any
    ) -> Any:
        return await self.async_base_request("DELETE", url, params=params, **kwargs)

    # ── Lifecycle / context manager ─────────────────────────────────

    def close(self) -> None:
        if self._sync_client:
            self._sync_client.close()

    async def aclose(self) -> None:
        if self._async_client:
            await self._async_client.aclose()

    def __enter__(self) -> "CanvasSession":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    async def __aenter__(self) -> "CanvasSession":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
