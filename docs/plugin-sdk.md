# Plugin SDK

MIST plugins are deliberately small contracts. A plugin can be a deterministic parser, an external forensic tool wrapper, a verifier, or a report transformer.

## Manifest

Each plugin directory contains `manifest.json`:

```json
{
  "id": "mist.disk.sleuthkit",
  "name": "Disk Filesystem Analysis",
  "category": "disk",
  "version": "0.1.0",
  "description": "Enumerates partitions and filesystem artifacts.",
  "inputs": ["E01", "dd", "raw"],
  "outputs": ["partitions", "filesystem", "files"],
  "tools": ["mmls", "fsstat", "fls"],
  "enabled": true,
  "sandbox": {
    "mount": "read-only",
    "network": "disabled"
  }
}
```

## Result Shape

Executable plugins should return:

```json
{
  "plugin_id": "mist.disk.sleuthkit",
  "evidence_id": "uuid",
  "status": "completed",
  "facts": [],
  "tool_version": "x.y.z",
  "commands": [],
  "stderr": "",
  "started_at": "ISO-8601",
  "completed_at": "ISO-8601"
}
```

## Forensic Rules

- Treat source evidence as read-only.
- Include the command, tool version, offset, and source evidence ID for every fact.
- Return structured facts, not prose.
- Keep stdout/stderr as attachments when useful.
- Hash exported artifacts.
- Fail closed when a parser is uncertain.
