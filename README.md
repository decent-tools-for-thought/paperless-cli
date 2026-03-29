# paperless-cli

CLI for the Paperless-ngx REST API.

Features:

- XDG config profiles in `$XDG_CONFIG_HOME/paperless-cli/config.json`
- token-based login via `/api/token/`
- generic CRUD commands for routed API resources
- explicit commands for Paperless custom endpoints and actions
- pagination support with `list --all`
- binary download support for preview, thumbnails, downloads, and bulk archives

Examples:

```bash
paperless auth login --url https://paperless.example --username alice
paperless documents list --all --query title__icontains=invoice
paperless documents get 123
paperless documents download 123 --output invoice.pdf
paperless documents post-document ./scan.pdf --title "Utility bill"
paperless tasks run --task-name train_classifier
```
