# The dock disturbances and their two weekly clocks

**English** · [Deutsch](dock.de.md) · [← README](../README.md)

What you need to know about the dock is in the [README](../README.md#dock-and-link-what-you-need-to-know). This page is the investigation behind the dropout bullet there.

## Follow-up 21 Oct 2026: the disturbances follow two weekly clocks

Logged with second resolution since 15 Oct (`messen/dock-mitschnitt.sh`, read-only: kernel messages, link changes, AER counters of the dock port, the NVMe port and the 10 GbE port, link state and power of the card). Going back through the kernel log, the events fall into two series:

| series | events | step per week | reading |
|---|---|---|---|
| Sunday | 13 Sep 17:14:33 · 20 Sep :36 · 27 Sep :39 · 4 Oct :43 · 18 Oct :49.8 | +3.3 s (about 5.5 ppm) | a free-running clock, like a quartz without time sync |
| Wednesday | 23 Sep 17:40:00 · 30 Sep 18:01:10 · 7 Oct 18:22:22 · 14 Oct 18:43:32 · **21 Oct 19:04:41** | +21 min 9-12 s | a fixed interval of 7 days 21 min 10 s: **the UPS's weekly battery self-test** (see below) |

**The Wednesday prediction hit within 2 s.** Predicted 19:04:43, measured: the 10 GbE NIC lost its link at 19:04:41.3 for 5.1 s, and 1.5 s later the dock port logged a corrected receiver error (`RxErr`). The OCuLink link stayed at 16 GT/s x4, no model was loaded, the card idled at 17 W. On 14 Oct the 10 GbE link dropped on schedule while the card was not even on the bus, so the source sits outside the NAS. Both the copper network cable and the OCuLink cable pick it up; the dock is one victim, not the cause. The router's event log shows nothing at these times. Excerpt: `messen/daten/dock-2026-10-21/`.

**Update, same night: the Wednesday series is the UPS testing its battery.** The NAS and the dock are the only loads on an Eaton Ellipse PRO 1200, read via NUT once a minute. In six weeks its battery charge left 100 % exactly six times, each time in the minute right after a Wednesday event (16 Sep 17:18:58, 23 Sep 17:40:12, 30 Sep 18:01:49, 7 Oct 18:22:49, 14 Oct 18:44:14, 21 Oct 19:05:29): 100 → 99 %, runtime 3,814 → 3,775 s, back to 100 % about 20 minutes later. Three of these samples even caught the runtime estimate on battery (1,037 s and 2,812 s instead of 3,814 s). The datasheet lists an automatic battery test once a week; the extra 21 minutes per week are the UPS's own timer. So the NAS is not disturbed from outside on Wednesdays, its own UPS switches it to battery for a few seconds, and that switch is what the copper network link and the OCuLink link pick up (5 of 6 tests; on 16 Sep nothing was logged). The status read once a minute stays `OL`, which is why this was missed at first. NUT on this model offers no command to start or schedule the test. The Sunday series shows no such trace and remains open.

Next: on 25 Oct (end of daylight saving time) the Sunday series tells whether its device switches to winter time (17:14:53) or not (16:14:53); on 28 Oct the Wednesday series is due at 18:25:51 CET if it really is a fixed interval. If you see repeated `RxErr` on an OCuLink port, log with second resolution and look for a weekly pattern before you replace cables or the dock.
