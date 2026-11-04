# Apple Calendar MCP

The local MCP server is registered as `apple-calendar` and runs:

```text
npx -y @redpop/apple-calendar-mcp
```

It is macOS-only and uses EventKit through a signed local helper. It supports listing calendars, querying events, finding free time, and creating, updating, or deleting events. Calendar data stays on the Mac except for the event data returned to the MCP client as conversation context.

## First-use permission

The first real calendar request should trigger a macOS permission dialog for `calendar-helper`. The user must grant access, then verify **System Settings → Privacy & Security → Calendars → calendar-helper → Options… → Full Access**. Add-only access cannot support planning because the server must read events.

If tools are absent from the current session, first inspect the configured `apple-calendar` MCP server and the installed package. When local execution is available, the same configured server can be called through an MCP stdio client; use its actual tool schemas and perform a read-only calendar request to verify access. Do not assume that missing exposed tools mean missing macOS permissions, and do not require a restart before checking this route. Never bypass an actual permission denial. Restart Codex to reload server tools if needed. If calendar reads fail for permissions, check Full Access before changing configuration.

## Creation, color, and permission experience

Keep three layers separate: tool exposure, macOS Calendar privacy permission, and the host's command/tool guard. Missing tools do not prove missing macOS permission, and a host guard rejection is not an EventKit privacy failure.

The server's event tools do not create calendars or change their color. When those operations are authorized, use an existing reviewed native setup entry for that exact operation; otherwise prepare the smallest scoped setup action and resolve its actual permission before executing. Do not grant a general interpreter, GUI, browser, or shell access to solve one missing calendar operation.

A native setup entry should identify the intended calendar/source, require a unique writable target, and limit changes to the authorized name/color or creation. A color-only entry cannot create a missing calendar. Fixed-command exceptions bind the actual executable, arguments, directory, and reviewed files; they do not authorize changed arguments or unrelated apps. Look up the local installation's exact entry and evidence through the external calendar registry rather than embedding project commands here.

Native Calendar creation must explicitly use the intended account/source. An AppleScript default `make new calendar` may create a local calendar even if iCloud is selected in the sidebar. A previously authorized setup used Calendar's iCloud creation menu, then independently verified the source via MCP. That history does not imply temporary UI permissions remain available.

After native creation or color changes, open a fresh connection to the same configured MCP server if inventory is stale. Read back the actual ID, source, write access, and color before events are written. Store intended color and actual read-back color separately in the external registry; native color conversion can produce a different hexadecimal value while retaining the chosen visible color.

Temporary setup/UI/recovery permissions should be removed after use. Preserve other apps' restrictions. Do not use generic menu Delete for calendar cleanup: sidebar selection and focused event are separate targets.

## Safety and interpretation

- A long-lived helper may return an old calendar inventory after a calendar was created externally. Re-read through a fresh stdio connection to the same configured MCP server before assuming creation failed; inspect its actual tool schemas, and require the expected writable source before writing. Do not create a duplicate or switch accounts to work around stale inventory.
- Read a bounded date range relevant to the planning conversation.
- Do not reveal unrelated event details in summaries.
- Use stable event identifiers returned by the server for edits when available.
- For recurring events, require an explicit occurrence-versus-series choice before update or deletion.
- Follow the authorization rule in SKILL.md: clear calendar instructions, completed-task reports, and user-stated daily goals in a dated review-and-plan workflow authorize the corresponding routine write. Read for duplicates, execute, verify, and summarize without reconfirming. Preview and confirm only unrequested proposals or materially ambiguous/expanded changes.

Project source: https://github.com/redpop/apple-calendar-mcp (MIT).
