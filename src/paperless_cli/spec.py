from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceSpec:
    path: str
    allow_create: bool = True
    allow_update: bool = True
    allow_delete: bool = True


RESOURCES: dict[str, ResourceSpec] = {
    "correspondents": ResourceSpec("/api/correspondents/"),
    "document-types": ResourceSpec("/api/document_types/"),
    "documents": ResourceSpec("/api/documents/"),
    "logs": ResourceSpec("/api/logs/", allow_create=False, allow_update=False, allow_delete=False),
    "tags": ResourceSpec("/api/tags/"),
    "saved-views": ResourceSpec("/api/saved_views/"),
    "storage-paths": ResourceSpec("/api/storage_paths/"),
    "tasks": ResourceSpec("/api/tasks/", allow_create=False, allow_update=False, allow_delete=False),
    "users": ResourceSpec("/api/users/"),
    "groups": ResourceSpec("/api/groups/"),
    "mail-accounts": ResourceSpec("/api/mail_accounts/"),
    "mail-rules": ResourceSpec("/api/mail_rules/"),
    "share-link-bundles": ResourceSpec("/api/share_link_bundles/"),
    "share-links": ResourceSpec("/api/share_links/"),
    "workflow-triggers": ResourceSpec("/api/workflow_triggers/"),
    "workflow-actions": ResourceSpec("/api/workflow_actions/"),
    "workflows": ResourceSpec("/api/workflows/"),
    "custom-fields": ResourceSpec("/api/custom_fields/"),
    "config": ResourceSpec("/api/config/", allow_create=False, allow_delete=False),
    "processed-mail": ResourceSpec("/api/processed_mail/", allow_create=False, allow_update=False, allow_delete=False),
}


SPECIAL_ENDPOINTS = {
    "search": "/api/search/",
    "search-autocomplete": "/api/search/autocomplete/",
    "statistics": "/api/statistics/",
    "bulk-edit-objects": "/api/bulk_edit_objects/",
    "remote-version": "/api/remote_version/",
    "ui-settings": "/api/ui_settings/",
    "profile": "/api/profile/",
    "profile-generate-token": "/api/profile/generate_auth_token/",
    "profile-disconnect-social-account": "/api/profile/disconnect_social_account/",
    "profile-social-account-providers": "/api/profile/social_account_providers/",
    "totp": "/api/profile/totp/",
    "status": "/api/status/",
    "trash": "/api/trash/",
    "schema": "/api/schema/",
    "oauth-callback": "/api/oauth/callback/",
}


DOCUMENT_ACTIONS = {
    "next-asn": ("/api/documents/next_asn/", "GET"),
    "post-document": ("/api/documents/post_document/", "POST"),
    "bulk-edit": ("/api/documents/bulk_edit/", "POST"),
    "delete-bulk": ("/api/documents/delete/", "POST"),
    "reprocess": ("/api/documents/reprocess/", "POST"),
    "rotate": ("/api/documents/rotate/", "POST"),
    "merge": ("/api/documents/merge/", "POST"),
    "edit-pdf": ("/api/documents/edit_pdf/", "POST"),
    "remove-password": ("/api/documents/remove_password/", "POST"),
    "bulk-download": ("/api/documents/bulk_download/", "POST"),
    "selection-data": ("/api/documents/selection_data/", "POST"),
    "email": ("/api/documents/email/", "POST"),
    "chat": ("/api/documents/chat/", "POST"),
}
