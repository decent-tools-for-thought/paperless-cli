import argparse
import sys

from paperless_cli.client import ApiError
from paperless_cli.commands import dispatch
from paperless_cli.config import DEFAULT_API_VERSION
from paperless_cli.spec import DOCUMENT_ACTIONS, RESOURCES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="paperless")
    parser.add_argument("--profile")
    parser.add_argument("--url")
    parser.add_argument("--token")
    parser.add_argument("--api-version", type=int)
    parser.add_argument("--insecure", action="store_true")
    subparsers = parser.add_subparsers(dest="command")

    auth = subparsers.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="auth_command")
    login = auth_sub.add_parser("login")
    login.add_argument("--url", required=True)
    login.add_argument("--username", required=True)
    login.add_argument("--password")
    login.add_argument("--profile", default="default")
    login.add_argument("--api-version", type=int, default=DEFAULT_API_VERSION)
    token = auth_sub.add_parser("use-token")
    token.add_argument("--url", required=True)
    token.add_argument("--token", required=True)
    token.add_argument("--profile", default="default")
    token.add_argument("--api-version", type=int, default=DEFAULT_API_VERSION)
    auth_sub.add_parser("list")
    use = auth_sub.add_parser("use")
    use.add_argument("profile")
    remove = auth_sub.add_parser("remove")
    remove.add_argument("profile")
    auth_sub.add_parser("show")

    for name, spec in RESOURCES.items():
        resource = subparsers.add_parser(name)
        resource_sub = resource.add_subparsers(dest="resource_command")
        list_parser = resource_sub.add_parser("list")
        _add_query_options(list_parser)
        list_parser.add_argument("--all", action="store_true")
        get_parser = resource_sub.add_parser("get")
        get_parser.add_argument("id")
        _add_query_options(get_parser)
        if spec.allow_create:
            create_parser = resource_sub.add_parser("create")
            _add_data_options(create_parser, required=True)
        if spec.allow_update:
            update_parser = resource_sub.add_parser("update")
            update_parser.add_argument("id")
            _add_data_options(update_parser, required=True)
            patch_parser = resource_sub.add_parser("patch")
            patch_parser.add_argument("id")
            _add_data_options(patch_parser, required=True)
        if spec.allow_delete:
            delete_parser = resource_sub.add_parser("delete")
            delete_parser.add_argument("id")
            _add_query_options(delete_parser)

        if name == "documents":
            _add_documents_commands(resource_sub)
        if name == "storage-paths":
            test_parser = resource_sub.add_parser("test")
            _add_data_options(test_parser, required=True)
        if name == "tasks":
            ack_parser = resource_sub.add_parser("acknowledge")
            _add_data_options(ack_parser, required=True)
            run_parser = resource_sub.add_parser("run")
            run_parser.add_argument("--task-name", required=True)
        if name == "share-link-bundles":
            rebuild_parser = resource_sub.add_parser("rebuild")
            rebuild_parser.add_argument("id")
        if name == "users":
            deactivate = resource_sub.add_parser("deactivate-totp")
            deactivate.add_argument("id")
        if name == "mail-accounts":
            test_parser = resource_sub.add_parser("test")
            _add_data_options(test_parser, required=True)
            process_parser = resource_sub.add_parser("process")
            process_parser.add_argument("id")
        if name == "processed-mail":
            bulk_delete = resource_sub.add_parser("bulk-delete")
            _add_data_options(bulk_delete, required=True)

    _add_special_parsers(subparsers)

    raw = subparsers.add_parser("raw")
    raw.add_argument("method")
    raw.add_argument("path")
    _add_query_options(raw)
    _add_data_options(raw)
    raw.add_argument("--output")
    raw.add_argument("--accept")
    return parser


def _add_documents_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    for action in DOCUMENT_ACTIONS:
        parser = subparsers.add_parser(action)
        if action == "next-asn":
            continue
        if action == "post-document":
            parser.add_argument("file")
            parser.add_argument("--title")
            parser.add_argument("--created")
            parser.add_argument("--correspondent", type=int)
            parser.add_argument("--document-type", type=int)
            parser.add_argument("--storage-path", type=int)
            parser.add_argument("--archive-serial-number", type=int)
            parser.add_argument("--tag", action="append", default=[])
            parser.add_argument("--custom-fields")
            continue
        if action in {"bulk-download"}:
            _add_data_options(parser, required=True)
            parser.add_argument("--output", required=True)
            continue
        if action in {"chat"}:
            _add_data_options(parser, required=True)
            parser.add_argument("--output")
            continue
        _add_data_options(parser, required=True)

    for action in [
        "root",
        "metadata",
        "suggestions",
        "preview",
        "thumb",
        "download",
        "notes-list",
        "notes-create",
        "notes-delete",
        "share-links",
        "history",
        "email-item",
        "update-version",
        "delete-version",
        "update-version-label",
    ]:
        parser = subparsers.add_parser(action)
        parser.add_argument("id")
        if action in {"preview", "thumb", "download"}:
            parser.add_argument("--output", required=True)
            _add_query_options(parser)
        elif action == "notes-delete":
            parser.add_argument("--note-id", required=True)
        elif action in {"notes-create", "email-item", "update-version-label"}:
            _add_data_options(parser, required=True)
        elif action == "update-version":
            parser.add_argument("file")
            parser.add_argument("--version-label")
        elif action in {"delete-version", "update-version-label"}:
            parser.add_argument("version_id")
        else:
            _add_query_options(parser)


def _add_special_parsers(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    search = subparsers.add_parser("search")
    _add_query_options(search)
    autocomplete = subparsers.add_parser("search-autocomplete")
    _add_query_options(autocomplete)
    statistics = subparsers.add_parser("statistics")
    _add_query_options(statistics)
    bulk = subparsers.add_parser("bulk-edit-objects")
    _add_data_options(bulk, required=True)
    remote = subparsers.add_parser("remote-version")
    _add_query_options(remote)
    ui = subparsers.add_parser("ui-settings")
    ui_sub = ui.add_subparsers(dest="ui_command")
    ui_get = ui_sub.add_parser("get")
    _add_query_options(ui_get)
    ui_post = ui_sub.add_parser("update")
    _add_data_options(ui_post, required=True)
    profile = subparsers.add_parser("profile")
    profile_sub = profile.add_subparsers(dest="profile_command")
    profile_sub.add_parser("get")
    profile_patch = profile_sub.add_parser("patch")
    _add_data_options(profile_patch, required=True)
    profile_sub.add_parser("generate-token")
    profile_disconnect = profile_sub.add_parser("disconnect-social-account")
    _add_data_options(profile_disconnect, required=True)
    profile_sub.add_parser("social-account-providers")
    totp = subparsers.add_parser("totp")
    totp_sub = totp.add_subparsers(dest="totp_command")
    totp_sub.add_parser("get")
    totp_post = totp_sub.add_parser("activate")
    _add_data_options(totp_post, required=True)
    totp_sub.add_parser("deactivate")
    status = subparsers.add_parser("status")
    _add_query_options(status)
    trash = subparsers.add_parser("trash")
    trash_sub = trash.add_subparsers(dest="trash_command")
    trash_list = trash_sub.add_parser("list")
    _add_query_options(trash_list)
    trash_action = trash_sub.add_parser("action")
    _add_data_options(trash_action, required=True)
    schema = subparsers.add_parser("schema")
    schema.add_argument("--output")
    oauth = subparsers.add_parser("oauth-callback")
    _add_query_options(oauth)


def _add_query_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--query", action="append", default=[], metavar="KEY=VALUE")


def _add_data_options(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    parser.add_argument("--data", required=required, help="JSON string or @file.json")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0
    try:
        return dispatch(args)
    except ApiError as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
