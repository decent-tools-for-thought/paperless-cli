from __future__ import annotations

import getpass
import json
import sys
from pathlib import Path
from typing import Any

from paperless_cli.client import ApiClient
from paperless_cli.client import ApiError
from paperless_cli.client import file_tuple
from paperless_cli.client import parse_data_arg
from paperless_cli.client import parse_key_value
from paperless_cli.config import Profile
from paperless_cli.config import config_path
from paperless_cli.config import get_profile
from paperless_cli.config import load_config
from paperless_cli.config import remove_profile
from paperless_cli.config import set_active_profile
from paperless_cli.config import upsert_profile
from paperless_cli.spec import DOCUMENT_ACTIONS
from paperless_cli.spec import RESOURCES
from paperless_cli.spec import SPECIAL_ENDPOINTS


def dispatch(args: Any) -> int:
    if args.command == "auth":
        return handle_auth(args)
    client = make_client(args)
    if args.command in RESOURCES:
        return handle_resource(client, args)
    if args.command == "search":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["search"], params=parse_key_value(args.query)).parsed)
    if args.command == "search-autocomplete":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["search-autocomplete"], params=parse_key_value(args.query)).parsed)
    if args.command == "statistics":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["statistics"], params=parse_key_value(args.query)).parsed)
    if args.command == "bulk-edit-objects":
        return emit(client.request("POST", SPECIAL_ENDPOINTS["bulk-edit-objects"], json_data=parse_data_arg(args.data)).parsed)
    if args.command == "remote-version":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["remote-version"], params=parse_key_value(args.query)).parsed)
    if args.command == "ui-settings":
        if args.ui_command == "get":
            return emit(client.request("GET", SPECIAL_ENDPOINTS["ui-settings"], params=parse_key_value(args.query)).parsed)
        return emit(client.request("POST", SPECIAL_ENDPOINTS["ui-settings"], json_data=parse_data_arg(args.data)).parsed)
    if args.command == "profile":
        return handle_profile(client, args)
    if args.command == "totp":
        return handle_totp(client, args)
    if args.command == "status":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["status"], params=parse_key_value(args.query)).parsed)
    if args.command == "trash":
        if args.trash_command == "list":
            return emit(client.request("GET", SPECIAL_ENDPOINTS["trash"], params=parse_key_value(args.query)).parsed)
        return emit(client.request("POST", SPECIAL_ENDPOINTS["trash"], json_data=parse_data_arg(args.data)).parsed)
    if args.command == "schema":
        response = client.request(
            "GET",
            SPECIAL_ENDPOINTS["schema"],
            accept="application/vnd.oai.openapi+json",
        )
        return emit(response.parsed, output=args.output)
    if args.command == "oauth-callback":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["oauth-callback"], params=parse_key_value(args.query)).parsed)
    if args.command == "raw":
        response = client.request(
            args.method,
            args.path,
            params=parse_key_value(args.query),
            json_data=parse_data_arg(args.data),
            accept=args.accept,
        )
        return emit(response.parsed, output=args.output, raw_bytes=response.body)
    raise SystemExit(f"Unhandled command: {args.command}")


def handle_auth(args: Any) -> int:
    if args.auth_command == "login":
        password = args.password or getpass.getpass("Password: ")
        scratch = Profile(
            name=args.profile,
            base_url=args.url,
            token="",
            username=args.username,
            api_version=args.api_version,
        )
        client = ApiClient(scratch)
        token = client.login(args.username, password)
        scratch.token = token
        profile_client = ApiClient(scratch)
        username = _extract_username(profile_client)
        scratch.username = username or args.username
        upsert_profile(scratch, activate=True)
        print(f"Saved profile {args.profile} to {config_path()}")
        return 0
    if args.auth_command == "use-token":
        profile = Profile(
            name=args.profile,
            base_url=args.url,
            token=args.token,
            api_version=args.api_version,
        )
        try:
            profile.username = _extract_username(ApiClient(profile))
        except ApiError:
            profile.username = None
        upsert_profile(profile, activate=True)
        print(f"Saved profile {args.profile} to {config_path()}")
        return 0
    if args.auth_command == "list":
        config = load_config()
        rows = []
        for name, profile in config.profiles.items():
            rows.append(
                {
                    "name": name,
                    "active": name == config.active_profile,
                    "base_url": profile.base_url,
                    "username": profile.username,
                    "api_version": profile.api_version,
                }
            )
        return emit(rows)
    if args.auth_command == "use":
        set_active_profile(args.profile)
        print(args.profile)
        return 0
    if args.auth_command == "remove":
        if not remove_profile(args.profile):
            raise SystemExit(f"Unknown profile: {args.profile}")
        return 0
    if args.auth_command == "show":
        profile = get_profile(
            args.profile,
            explicit_url=args.url,
            explicit_token=args.token,
            explicit_api_version=args.api_version,
        )
        return emit(
            {
                "name": profile.name,
                "base_url": profile.base_url,
                "username": profile.username,
                "api_version": profile.api_version,
                "token_present": bool(profile.token),
            }
        )
    raise SystemExit("Missing auth subcommand")


def handle_resource(client: ApiClient, args: Any) -> int:
    command = args.resource_command
    spec = RESOURCES[args.command]
    base_path = spec.path
    if command == "list":
        params = parse_key_value(args.query)
        if args.all:
            return emit(client.paginate(base_path, params=params))
        return emit(client.request("GET", base_path, params=params).parsed)
    if command == "get":
        return emit(client.request("GET", f"{base_path}{args.id}/", params=parse_key_value(args.query)).parsed)
    if command == "create":
        return emit(client.request("POST", base_path, json_data=parse_data_arg(args.data)).parsed)
    if command == "update":
        return emit(client.request("PUT", f"{base_path}{args.id}/", json_data=parse_data_arg(args.data)).parsed)
    if command == "patch":
        return emit(client.request("PATCH", f"{base_path}{args.id}/", json_data=parse_data_arg(args.data)).parsed)
    if command == "delete":
        return emit(client.request("DELETE", f"{base_path}{args.id}/", params=parse_key_value(args.query)).parsed)
    if args.command == "documents":
        return handle_documents(client, args)
    if args.command == "storage-paths" and command == "test":
        return emit(client.request("POST", "/api/storage_paths/test/", json_data=parse_data_arg(args.data)).parsed)
    if args.command == "tasks" and command == "acknowledge":
        return emit(client.request("POST", "/api/tasks/acknowledge/", json_data=parse_data_arg(args.data)).parsed)
    if args.command == "tasks" and command == "run":
        return emit(client.request("POST", "/api/tasks/run/", json_data={"task_name": args.task_name}).parsed)
    if args.command == "share-link-bundles" and command == "rebuild":
        return emit(client.request("POST", f"/api/share_link_bundles/{args.id}/rebuild/").parsed)
    if args.command == "users" and command == "deactivate-totp":
        return emit(client.request("POST", f"/api/users/{args.id}/deactivate_totp/").parsed)
    if args.command == "mail-accounts" and command == "test":
        return emit(client.request("POST", "/api/mail_accounts/test/", json_data=parse_data_arg(args.data)).parsed)
    if args.command == "mail-accounts" and command == "process":
        return emit(client.request("POST", f"/api/mail_accounts/{args.id}/process/").parsed)
    if args.command == "processed-mail" and command == "bulk-delete":
        return emit(client.request("POST", "/api/processed_mail/bulk_delete/", json_data=parse_data_arg(args.data)).parsed)
    raise SystemExit(f"Unhandled resource command: {args.command} {command}")


def handle_documents(client: ApiClient, args: Any) -> int:
    command = args.resource_command
    if command in DOCUMENT_ACTIONS:
        path, method = DOCUMENT_ACTIONS[command]
        if command == "post-document":
            fields: dict[str, Any] = {
                "title": args.title,
                "created": args.created,
                "correspondent": args.correspondent,
                "document_type": args.document_type,
                "storage_path": args.storage_path,
                "archive_serial_number": args.archive_serial_number,
            }
            if args.tag:
                fields["tags"] = args.tag
            if args.custom_fields:
                fields["custom_fields"] = json.loads(args.custom_fields)
            fields = {key: value for key, value in fields.items() if value is not None}
            return emit(
                client.request(
                    method,
                    path,
                    form_data=fields,
                    files={"document": file_tuple(args.file)},
                ).parsed
            )
        if command == "bulk-download":
            response = client.request(method, path, json_data=parse_data_arg(args.data))
            return emit(response.parsed, output=args.output, raw_bytes=response.body)
        if command == "chat":
            response = client.request(method, path, json_data=parse_data_arg(args.data), accept="application/json")
            return emit(response.parsed, output=args.output, raw_bytes=response.body)
        return emit(client.request(method, path, json_data=parse_data_arg(args.data)).parsed)
    if command == "root":
        return emit(client.request("GET", f"/api/documents/{args.id}/root/", params=parse_key_value(args.query)).parsed)
    if command == "metadata":
        return emit(client.request("GET", f"/api/documents/{args.id}/metadata/", params=parse_key_value(args.query)).parsed)
    if command == "suggestions":
        return emit(client.request("GET", f"/api/documents/{args.id}/suggestions/", params=parse_key_value(args.query)).parsed)
    if command == "preview":
        response = client.request("GET", f"/api/documents/{args.id}/preview/", params=parse_key_value(args.query), accept="application/octet-stream")
        return emit(response.parsed, output=args.output, raw_bytes=response.body)
    if command == "thumb":
        response = client.request("GET", f"/api/documents/{args.id}/thumb/", params=parse_key_value(args.query), accept="image/webp")
        return emit(response.parsed, output=args.output, raw_bytes=response.body)
    if command == "download":
        response = client.request("GET", f"/api/documents/{args.id}/download/", params=parse_key_value(args.query), accept="application/octet-stream")
        return emit(response.parsed, output=args.output, raw_bytes=response.body)
    if command == "notes-list":
        return emit(client.request("GET", f"/api/documents/{args.id}/notes/").parsed)
    if command == "notes-create":
        return emit(client.request("POST", f"/api/documents/{args.id}/notes/", json_data=parse_data_arg(args.data)).parsed)
    if command == "notes-delete":
        return emit(client.request("DELETE", f"/api/documents/{args.id}/notes/", params={"id": args.note_id}).parsed)
    if command == "share-links":
        return emit(client.request("GET", f"/api/documents/{args.id}/share_links/").parsed)
    if command == "history":
        return emit(client.request("GET", f"/api/documents/{args.id}/history/").parsed)
    if command == "email-item":
        return emit(client.request("POST", f"/api/documents/{args.id}/email/", json_data=parse_data_arg(args.data)).parsed)
    if command == "update-version":
        return emit(
            client.request(
                "POST",
                f"/api/documents/{args.id}/update_version/",
                form_data={"version_label": args.version_label} if args.version_label else {},
                files={"document": file_tuple(args.file)},
            ).parsed
        )
    if command == "delete-version":
        return emit(client.request("DELETE", f"/api/documents/{args.id}/versions/{args.version_id}/").parsed)
    if command == "update-version-label":
        return emit(client.request("PATCH", f"/api/documents/{args.id}/versions/{args.version_id}/", json_data=parse_data_arg(args.data)).parsed)
    raise SystemExit(f"Unhandled documents command: {command}")


def handle_profile(client: ApiClient, args: Any) -> int:
    if args.profile_command == "get":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["profile"]).parsed)
    if args.profile_command == "patch":
        return emit(client.request("PATCH", SPECIAL_ENDPOINTS["profile"], json_data=parse_data_arg(args.data)).parsed)
    if args.profile_command == "generate-token":
        return emit(client.request("POST", SPECIAL_ENDPOINTS["profile-generate-token"]).parsed)
    if args.profile_command == "disconnect-social-account":
        return emit(client.request("POST", SPECIAL_ENDPOINTS["profile-disconnect-social-account"], json_data=parse_data_arg(args.data)).parsed)
    if args.profile_command == "social-account-providers":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["profile-social-account-providers"]).parsed)
    raise SystemExit("Missing profile subcommand")


def handle_totp(client: ApiClient, args: Any) -> int:
    if args.totp_command == "get":
        return emit(client.request("GET", SPECIAL_ENDPOINTS["totp"]).parsed)
    if args.totp_command == "activate":
        return emit(client.request("POST", SPECIAL_ENDPOINTS["totp"], json_data=parse_data_arg(args.data)).parsed)
    if args.totp_command == "deactivate":
        return emit(client.request("DELETE", SPECIAL_ENDPOINTS["totp"]).parsed)
    raise SystemExit("Missing totp subcommand")


def make_client(args: Any) -> ApiClient:
    profile = get_profile(
        args.profile,
        explicit_url=args.url,
        explicit_token=args.token,
        explicit_api_version=args.api_version,
    )
    return ApiClient(profile, verify_tls=not args.insecure)


def emit(value: Any, *, output: str | None = None, raw_bytes: bytes | None = None) -> int:
    if output:
        path = Path(output)
        if raw_bytes is not None and isinstance(value, (bytes, bytearray)):
            path.write_bytes(bytes(value))
        elif raw_bytes is not None and not isinstance(value, (dict, list, str, int, float, bool, type(None))):
            path.write_bytes(raw_bytes)
        elif isinstance(value, (bytes, bytearray)):
            path.write_bytes(bytes(value))
        elif isinstance(value, str):
            path.write_text(value)
        else:
            path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        return 0
    if isinstance(value, (dict, list)):
        print(json.dumps(value, indent=2, sort_keys=True))
        return 0
    if isinstance(value, bytes):
        sys.stdout.buffer.write(value)
        return 0
    if value is None:
        return 0
    print(value)
    return 0


def _extract_username(client: ApiClient) -> str | None:
    try:
        response = client.request("GET", SPECIAL_ENDPOINTS["profile"])
    except ApiError:
        return None
    parsed = response.parsed
    if isinstance(parsed, dict):
        return parsed.get("username")
    return None
