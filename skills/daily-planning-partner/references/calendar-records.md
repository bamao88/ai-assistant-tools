# Calendar record types and readable daily history

Use two independent decisions: the record type determines placement; the registered project/work dimension determines color. The external calendar registry owns concrete mappings; locate it using [SKILL.md](../SKILL.md), independently of this Skill's installation directory.

## Choose the record type

| User meaning | Calendar representation | Time basis |
| --- | --- | --- |
| A clear daily goal, milestone, or dated result | All-day entry | Goal/result date; no invented work duration |
| A content item published on a date | All-day entry, grouped by content + date | Publication date; exact platform timestamps in notes |
| Work performed, partial progress, or a batch operation | Timed retrospective display block | Known actual time, or the display-slot convention below |
| A meeting, deadline, or an agreed future work session | Real timed commitment | Actual or agreed start/end |

An unfinished daily goal stays gray in the plan layer; its completion moves it to the registered dimension. Progress is useful history even when the goal remains unfinished. Wording such as “today I worked on / advanced / processed a batch” usually describes progress; a completed verb alone does not turn it into a milestone.

For example, “today I prepared and published a week's content across three platforms” is one work summary on the day of that batch operation. It is not three process records or one process record for every eventual release date. The individual content releases may separately appear as all-day outcomes on their respective release dates because those convey different information. Do not create the same summary in both locations by default.

Examples, proposals, and “for instance, if I did...” are not completed-work reports. A request to improve these rules does not authorize adding the illustrative event.

## Retrospective display slots

When actual work times are absent, use 10:00–10:30 for the day's first progress record, then 10:30–11:00, 11:00–11:30, and so on. Allocate slots across all workstreams for that local day, not from 10:00 separately for every project. Reuse existing stable slots when updating; append new records rather than reshuffling unrelated history.

Each block has a 30-minute display duration. Apple Calendar uses event start/end times to size timed blocks; the MCP has no separate event-height field. This convention sets a comfortable height in Day/Week view, not a claim about when or how long the work occurred. If the user supplies actual times or an explicit layout duration, preserve that basis instead.

Read the day's events before allocation. Keep real appointments and intended future work blocks at their actual times; skip conflicting slots on the half-hour grid. Preserve already allocated progress slots. Do not move unrelated events to make the display tidy.

Use a short activity/result summary as the title. Put what advanced, scope or count when known, remaining gaps, and source links in notes. Missing counts remain unspecified.

For synthetic slots, put this explanation near the top of notes:

> 回顾展示块：本条按半小时排版，所示时段不代表实际工作时间或耗时。

Also retain `record_type=retrospective-progress` and `time_basis=display-slot` in notes for reconciliation and availability filtering. Use no alarm. The slot's date is the reported work date, not the future publication date of every item handled.

## Availability and review

Synthetic display slots are retrospective history and do not consume future planning capacity. Exclude records marked `time_basis=display-slot` when deriving busy time; retain real appointments and agreed future work blocks. Do not exclude a whole project calendar merely because some entries are display records.

The MCP free-time tool cannot filter individual events by notes. When a relevant calendar mixes real commitments and display blocks, read the bounded event list and calculate availability from genuine commitments instead of blindly treating all returned blocks as busy. Dated all-day output records likewise differ from genuine all-day commitments such as travel; preserve that distinction.

Keep a few meaningful progress summaries rather than every operational step. Reconcile partial progress, completed goals, and deferrals without losing the unfinished goal or appending duplicate summaries.

## Method basis

[GTD's calendar guidance](https://gettingthingsdone.com/wp-content/uploads/2018/08/GTD_Outlook_2013-2016_sample.pdf) distinguishes time-specific actions, day-specific actions, and day-specific information, with supporting detail kept elsewhere. [Apple's event guide](https://support.apple.com/en-gb/guide/calendar/icalwr13-events/16.0/mac/26) describes all-day placement and changing timed events through their start/end edges. The 10:00/30-minute retrospective layout is the user's chosen display convention; it is not a measured time log or a rule prescribed by GTD.
