# Answer evaluation, 2026-11-19

- Model: openai/gpt-oss-120b | Questions: 29 | Date used as today: 2026-11-19
- Model calls this run: 29 (the rest came from the cache) | Tokens this run: 27,442
- Median answer time (original call): 3.7 s

## Overall

| Passed | Facts correct | Cites an expected source | Correct refusals | Answerable wrongly refused |
|---|---|---|---|---|
| 13/29 | 17/23 | 10/23 | 6/6 | 2 |

## By category

| Category | Passed |
|---|---|
| conflict | 5/8 |
| date | 1/3 |
| multi-doc | 0/6 |
| table | 1/6 |
| unanswerable | 6/6 |

## Failures (16)

### `hotel-boston` (table): failed citations_ok
- Question: What's the most I can pay per night for a hotel in Boston?
- Expected: $275 per night excluding taxes (Boston is a Tier 1 city). Source: Travel Policy 4.2 (a Word table).
- Cited documents: []
- Answer: The handbook does not specify Boston’s city tier, so it does not state the exact maximum nightly rate for that location. It does list the general tier caps: Tier 1 – $275, Tier 2 – $200, Tier 3 – $150 per night【1】.

### `per-diem-l3-chicago` (table): failed citations_ok
- Question: What is the daily per diem for an L3 employee travelling to Chicago?
- Expected: $75 per day (L3, Tier 2).
- Cited documents: []
- Answer: The daily per‑diem for an L3 employee traveling to Chicago (city tier 2) is **$75**【2】.

### `per-diem-l5-sf` (table): failed citations_ok
- Question: What per diem does an L5 get in San Francisco?
- Expected: $110 per day (L5, Tier 1).
- Cited documents: []
- Answer: An L5 employee traveling to San Francisco (city‑tier 1) receives a per‑diem of **$110** per day【1】.

### `payments-rto` (table): failed citations_ok
- Question: What is the RTO for the payments service?
- Expected: 4 hours (RPO 5 minutes).
- Cited documents: []
- Answer: The RTO for the payments service is 4 hours【1】.

### `orders-db-data-loss` (table): failed facts_ok, citations_ok, refusal_ok
- Question: How much data loss is acceptable for the orders database in a disaster?
- Expected: 30 minutes (the RPO); its RTO is 6 hours.
- Cited documents: []
- Answer: The handbook does not cover a specific acceptable data‑loss amount for the orders database. The only guidance on data loss is the generic definition of RPO in the Glossary, which describes it as “the maximum acceptable amount of data loss measured in time, for example 15 minutes of writes”【2】.

### `deploy-freeze-length` (conflict): failed citations_ok
- Question: How long before a release does the deploy freeze start?
- Expected: 72 hours before every scheduled release. The deprecated 2023 runbook's 36 hours must not be used.
- Cited documents: []
- Answer: Deploy freezes begin **72 hours before each scheduled release**【1】. (The release calendar also lists a 72‑hour freeze for each upcoming release【2】, and the all‑hands notes reiterate the same rule【3】.)

### `canary-stage` (conflict): failed citations_ok
- Question: Do production deploys go through a canary stage, and for how long?
- Expected: Yes: 5 percent of traffic for ten minutes, then full rollout. The deprecated runbook went straight to full rollout.
- Cited documents: []
- Answer: Yes. Production deploys run a canary stage that lasts ten minutes before full rollout【1】【4】.

### `voyagehub-trip-vp-approval` (conflict): failed facts_ok
- Question: I booked a $3,200 business trip through VoyageHub. Does it need VP approval?
- Expected: No. Travel booked through VoyageHub is pre-approved at booking; it needs only manager sign-off (no VP approval), even though the approval matrix says VP above $2,500 for expense claims.
- Cited documents: ['fin-expense-policy']
- Answer: No – because the trip was booked through VoyageHub, it is considered pre‑approved at booking time and only requires your manager’s sign‑off when you file the expense claim [2].

### `l2-trip-to-denver` (multi-doc): failed facts_ok, refusal_ok
- Question: I'm an L2 travelling to Denver. What are my hotel cap and my daily per diem?
- Expected: Denver is not listed, so it is Tier 3 ('any city not listed above'): hotel cap $150 per night, per diem $50 per day for L2.
- Cited documents: ['fin-per-diem-table', 'hr-travel-policy']
- Answer: The handbook does not cover this. The hotel caps are defined by city tier [1], and the per‑diem amounts are listed by grade and city tier in the Per‑Diem Tables [3][4]; however, Denver’s tier is not provided in any of the passages. You’ll need to know Denver’s city tier to determine the applicable hotel limit and per‑diem.

### `platform-laptop-approver` (multi-doc): failed citations_ok
- Question: I'm on the Platform team and my laptop broke. Who approves the replacement?
- Expected: Your team's engineering manager, Maya Brooks (Platform Team); IT does not approve replacements itself. IT then fulfils within 3 business days.
- Cited documents: []
- Answer: The approval for a laptop replacement comes from your team’s engineering manager — for the Platform team that is **Engineering Manager Maya Brooks**【1†L4-L6】【3†L1-L3】.

### `prod-db-access-approver` (multi-doc): failed facts_ok, citations_ok
- Question: Whose sign-off do I need for production database access? Give me a name.
- Expected: The system owner approves, and production database access also needs sign-off from the Security Lead, Tyler Rodriguez.
- Cited documents: []
- Answer: You need sign‑off from the **Security Lead** for production database access【1】.

### `customer-credit-approver` (multi-doc): failed citations_ok
- Question: Who approves service credits for customers after an outage?
- Expected: The Head of Product (Maya Park); Finance processes them.
- Cited documents: []
- Answer: Service credits for outages are approved by the Head of Product (and then processed by Finance)【1】.

### `orders-db-team-manager` (multi-doc): failed citations_ok
- Question: Who is the engineering manager of the team that owns the orders database?
- Expected: The Data Team owns the orders database; its engineering manager is Maya Rivera.
- Cited documents: []
- Answer: The orders database is owned by the Data Team, whose engineering manager is **Maya Rivera**【1】.

### `backup-restore-test-owner` (multi-doc): failed citations_ok
- Question: Who was asked to schedule the quarterly backup restore test?
- Expected: Maya Rivera (action from the March 2026 platform meeting notes). The Disaster Recovery Runbook says restores are tested quarterly by the Platform Team.
- Cited documents: []
- Answer: Maya Rivera was asked to schedule the quarterly backup restore test【1】.

### `deploy-today` (date): failed facts_ok
- Question: Can I deploy to production today?
- Expected: Not normally (today is 2026-11-19): today is release day for 2026.22, and its 72-hour freeze started on 2026-11-16. Exceptions need the on-call manager's approval in #deploys.
- Cited documents: ['eng-deploy-runbook']
- Answer: You cannot deploy to production today because deploys are allowed only on weekdays between 10:00 and 15:00 CT, and today (2026‑11‑19) is a Saturday [1].

### `release-today-and-next` (date): failed facts_ok, citations_ok
- Question: Is there a release today, and when is the one after it?
- Expected: Yes: release 2026.22 is today (2026-11-19). The next one is 2026.23 on 2026-12-03, with its freeze starting 72 hours before, on 2026-11-30.
- Cited documents: ['team-product']
- Answer: There is no release today because releases are scheduled only on Thursdays [2]. The next release will be on the upcoming Thursday, 2026‑11‑23.

