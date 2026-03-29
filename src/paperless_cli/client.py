from __future__ import annotations

import json
import mimetypes
import ssl
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.parse import urljoin
from urllib.request import Request
from urllib.request import urlopen

from paperless_cli.config import Profile


JSON = dict[str, Any] | list[Any] | str | int | float | bool | None


@dataclass
class ResponseData:
    status: int
    headers: dict[str, str]
    body: bytes
    parsed: Any


class ApiError(RuntimeError):
    def __init__(self, status: int, message: str, body: bytes | None = None):
        super().__init__(message)
        self.status = status
        self.body = body or b""


def parse_key_value(items: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"Expected KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        result[key] = value
    return result


def parse_data_arg(value: str | None) -> JSON:
    if value is None:
        return None
    if value.startswith("@"):
        return json.loads(Path(value[1:]).read_text())
    return json.loads(value)


def encode_multipart(
    *,
    fields: dict[str, Any] | None = None,
    files: dict[str, tuple[str, bytes, str]] | None = None,
) -> tuple[str, bytes]:
    boundary = f"paperless-cli-{uuid.uuid4().hex}"
    lines: list[bytes] = []
    for key, value in (fields or {}).items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            lines.extend(
                [
                    f"--{boundary}".encode(),
                    f'Content-Disposition: form-data; name="{key}"'.encode(),
                    b"",
                    _stringify_form_value(item).encode(),
                ]
            )
    for key, (filename, data, content_type) in (files or {}).items():
        lines.extend(
            [
                f"--{boundary}".encode(),
                (
                    f'Content-Disposition: form-data; name="{key}"; '
                    f'filename="{filename}"'
                ).encode(),
                f"Content-Type: {content_type}".encode(),
                b"",
                data,
            ]
        )
    lines.append(f"--{boundary}--".encode())
    lines.append(b"")
    return f"multipart/form-data; boundary={boundary}", b"\r\n".join(lines)


def _stringify_form_value(value: Any) -> str:
    if isinstance(value, (dict, list, bool, int, float)) or value is None:
        return json.dumps(value)
    return str(value)


class ApiClient:
    def __init__(self, profile: Profile, *, verify_tls: bool = True):
        self.profile = profile
        self.verify_tls = verify_tls

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_data: JSON = None,
        form_data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
        accept: str | None = None,
    ) -> ResponseData:
        url = urljoin(f"{self.profile.base_url}/", path.lstrip("/"))
        if params:
            encoded = urlencode(
                [(key, value) for key, value in params.items() if value is not None],
                doseq=True,
            )
            if encoded:
                url = f"{url}?{encoded}"
        headers = {
            "Accept": accept or f"application/json; version={self.profile.api_version}",
            "User-Agent": "paperless-cli/0.1.0",
        }
        if self.profile.token:
            headers["Authorization"] = f"Token {self.profile.token}"
        data = None
        if files:
            content_type, data = encode_multipart(fields=form_data, files=files)
            headers["Content-Type"] = content_type
        elif form_data is not None:
            data = urlencode(form_data, doseq=True).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_data is not None:
            data = json.dumps(json_data).encode()
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, method=method.upper(), headers=headers)
        context = None if self.verify_tls else ssl._create_unverified_context()
        try:
            with urlopen(request, context=context) as response:
                body = response.read()
                return ResponseData(
                    status=response.status,
                    headers=dict(response.headers.items()),
                    body=body,
                    parsed=_parse_response_body(body, response.headers.get("Content-Type")),
                )
        except HTTPError as exc:
            body = exc.read()
            detail = _parse_response_body(body, exc.headers.get("Content-Type"))
            if isinstance(detail, (dict, list)):
                message = json.dumps(detail, indent=2)
            elif isinstance(detail, str) and detail.strip():
                message = detail.strip()
            else:
                message = f"HTTP {exc.code}"
            raise ApiError(exc.code, message, body) from exc

    def paginate(self, path: str, *, params: dict[str, Any] | None = None) -> list[Any]:
        page = self.request("GET", path, params=params).parsed
        if not isinstance(page, dict) or "results" not in page:
            return page if isinstance(page, list) else [page]
        results = list(page.get("results", []))
        next_url = page.get("next")
        while next_url:
            response = self._request_absolute("GET", next_url)
            page = response.parsed
            results.extend(page.get("results", []))
            next_url = page.get("next")
        return results

    def _request_absolute(self, method: str, url: str) -> ResponseData:
        headers = {
            "Accept": f"application/json; version={self.profile.api_version}",
            "User-Agent": "paperless-cli/0.1.0",
        }
        if self.profile.token:
            headers["Authorization"] = f"Token {self.profile.token}"
        request = Request(url, method=method.upper(), headers=headers)
        with urlopen(request) as response:
            body = response.read()
            return ResponseData(
                status=response.status,
                headers=dict(response.headers.items()),
                body=body,
                parsed=_parse_response_body(body, response.headers.get("Content-Type")),
            )

    def login(self, username: str, password: str) -> str:
        response = self.request(
            "POST",
            "/api/token/",
            json_data={"username": username, "password": password},
            accept="application/json",
        )
        parsed = response.parsed
        if not isinstance(parsed, dict) or "token" not in parsed:
            raise SystemExit("Unexpected token response")
        return str(parsed["token"])


def file_tuple(path: str) -> tuple[str, bytes, str]:
    file_path = Path(path)
    return (
        file_path.name,
        file_path.read_bytes(),
        mimetypes.guess_type(file_path.name)[0] or "application/octet-stream",
    )


def _parse_response_body(body: bytes, content_type: str | None) -> Any:
    if not body:
        return None
    content_type = (content_type or "").split(";", 1)[0].strip().lower()
    if content_type in {"application/json", "application/vnd.oai.openapi+json"}:
        return json.loads(body.decode())
    if content_type.startswith("text/") or content_type in {"application/xml"}:
        return body.decode()
    return body
