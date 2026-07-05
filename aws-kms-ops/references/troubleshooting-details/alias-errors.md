# KMS Alias Errors — Detailed Recovery

## AlreadyExistsException (Alias)

Alias name already in use.

```bash
# Check existing alias
aws kms list-aliases --query "Aliases[?AliasName=='alias/{{name}}']"

# Use different name or update alias to point to new key
aws kms update-alias --alias-name alias/{{name}} --target-key-id {{new_key_id}}
```

## NotFoundException (Alias)

Alias does not exist (typo in name).

```bash
# List all aliases
aws kms list-aliases

# Search for similar names
aws kms list-aliases --query "Aliases[?contains(AliasName, '{{name}}')]"
```
