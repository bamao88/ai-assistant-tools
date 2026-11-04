# Publishing calendar views

Use the calendar as a readable view of the existing source records. Keep platform facts and metrics in their source ledger. Choose the calendar by project + work dimension from the separate calendar registry, located using [SKILL.md](../SKILL.md) independently of the Skill directory, so publishing need not share the project's product-development color.

## One content item on one date

- Group by established content identity and local publication date, within the intended calendar/workstream. Different platform titles may still refer to the same content; title similarity alone does not establish identity.
- Same content, same local date, multiple platforms: one all-day event. Small differences in posting times belong in notes.
- Same content on different dates: separate dated events, showing the platforms relevant to each date. Different content or a materially separate action keeps its own event.
- Use the actual publication date for confirmed publications, the scheduled date for platform-confirmed scheduled publications, and the submission date for pending submissions. Missing required dates remain a source gap; do not invent one.
- All-day publishing records show a day's output; they do not measure work duration. Preserve exact source timestamps in notes and use no alarms by default. A report about handling a batch today belongs in a retrospective progress block under [calendar record rules](calendar-records.md); keep it distinct from each item's release date.

## Compact titles and useful details

Use a short recognizable content name followed by platform/status labels, for example `短片名｜红✓ 抖✓ B✓`. Derive platform names and consistent short labels from the current sources; include only platforms represented in that day's group. Keep long titles, variant captions, internal evidence paths, and identifiers out of the headline.

Use `✓` for confirmed publication and for the scheduled-publication convention below; `?` means a submission whose result is still unknown. Explicit failures and cancellations get clear text labels. Do not label a mixed group as wholly completed. Keep the workstream's calendar color stable.

Use ordinary text or Unicode symbols supported by the actual calendar tools. Do not promise custom platform-logo icons without a verified native feature; attaching an image does not make it an event icon.

Put human-readable details first in notes, one platform per section:

- full platform name, displayed status, and whether that status is confirmed or assumed;
- actual, scheduled, or submission timestamp, labelled accurately;
- available published link; leave missing links absent;
- last verification time only when the source actually provides one.

Put stable group/member identities after the useful details for reconciliation. Link to existing source evidence instead of copying an audit log into every event.

## Scheduled publications need one maintenance pass

Once the platform has accepted and confirmed a schedule, render that platform with the published/completed style at the scheduled date on the first synchronization. Apply this to both past and future dates. Do not move it to today's date, create a second completion event, retain a pending-verification marker, or add a follow-up task merely to flip its status later.

Record `按定时默认已发布；未重新核验公开结果` in the platform's notes, with the original scheduled timestamp. This describes the calendar convention; it is not evidence that a future or unverified post is publicly visible. Do not manufacture an actual publication time or change the source record to published.

A draft, intended posting time, or submission awaiting review is not a confirmed schedule. Known rejection, failure, cancellation, or rescheduling supersedes the assumption; reconcile it when that information is supplied or encountered during authorized maintenance. Calendar synchronization itself does not require platform access, polling, or a recurring automation.

## Reconcile and verify

Read the target calendar and date range before writing. Use stable source content identities, local dates, and source member IDs to find managed events. Reuse existing event identifiers and preserve provenance when converting an older per-platform view.

For an authorized consolidation, save the original managed events and their returned identifiers before changes. Update or create one keeper per group, read it back, and only then delete the precisely identified redundant managed events. Never use title-only matching or a generic GUI Delete command to remove events. Do not remove unrelated or recurring events as part of grouping.

If a write result is unknown, re-read the identifier or stable marker before retrying. Verify member coverage, dates, platform labels, status basis, links, calendar/source, and absence of duplicate groups. Report actual writes and read-back separately from a prepared plan or a source-data simulation.

When only the rules have been edited, leave existing calendar events and historical sync receipts unchanged. An old script or saved plan may implement older rules: inspect its projection and migration behavior before reusing it, and do not claim the new display has been applied until an authorized write and read-back have completed.

## Method basis

[Planable's grouped-post model](https://changelog.planable.io/add-pages-to-grouped-posts-and-a-new-post-modal-275471) demonstrates associating multiple channels with a content group. The content + local-date rule here is a calendar projection policy: keep individual channel records in the source while simplifying the overview.
