# UX Polish — Design Spec

> Date: 2026-03-31
> Goal: Fix 5 UX issues found during user testing

---

## 1. Job Detail Page — Full Width

### Problem
`max-w-4xl` (960px) leaves large right margin. Charts hardcoded at 860px.

### Solution
- Change container from `max-w-4xl` to `max-w-6xl`
- Charts: remove hardcoded CHART_WIDTH, use `w-full` with viewBox auto-scaling (already uses `preserveAspectRatio`)

### Files
- `apps/web/app/jobs/[id]/page.tsx`: change max-w class, update CHART_WIDTH to larger value or use container width

---

## 2. Job Detail Page — Show Portfolio Composition

### Problem
User can't see which assets and weights were used for a completed backtest.

### Solution
Add a "组合配置" card above the metrics section showing:
- Asset code + name + weight (as inline tags/pills)
- Date range and rebalance frequency

Data source: `status.payload_summary` already contains `weights`, `start_date`, `end_date`, `rebalance_frequency`. The `assets` list with names is available if the payload included it.

### Files
- `apps/web/app/jobs/[id]/page.tsx`: add portfolio summary card using `status.payload_summary`

---

## 3. Jobs List — Loading Skeleton

### Problem
Page loads empty, data appears after a delay with no visual feedback.

### Solution
Add skeleton loading state (same pattern as AssetPicker): show 5 skeleton rows on initial load, replace with real data when ready.

### Files
- `apps/web/app/jobs/page.tsx`: add `loading` state, show skeleton when true

---

## 4. Jobs List — Remove Auto-Polling

### Problem
3-second polling causes page flicker and feels weird.

### Solution
Remove `setInterval` polling entirely. Data fetches on:
- Initial page load
- User clicks "刷新" button
- Status filter change
- Search query change
- Page change

### Files
- `apps/web/app/jobs/page.tsx`: remove setInterval, keep manual refresh triggers

---

## 5. Async Job Submission — No Blocking, No Redirect

### Problem
Clicking "一键分析" blocks the UI for 10+ seconds while backtest runs synchronously, then force-redirects to detail page.

### Solution

**Backend**: In `POST /jobs/auto`, stop calling `inline_worker.process_job()` synchronously. Just create the snapshot + queue the job, return immediately. The background worker (`apps/worker/runner.py`) picks up and processes the job.

**Frontend**: After receiving job_id:
- Don't call `router.push()` — stay on the submit page
- Show a success toast/banner below the submit button: "任务已创建" with a link to `/jobs/{job_id}`
- Reset the loading state so user can submit another task
- Keep the form state intact (user might want to tweak and resubmit)

### Files
- `apps/api/main.py`: remove `inline_worker.process_job(result["job_id"])` from `/jobs/auto` handler
- `apps/web/app/page.tsx`: remove `router.push()`, show inline success message with link

---

## Out of Scope
- Job detail page chart interactivity (tooltips, zoom)
- Mobile layout optimization
- Any backend logic changes beyond removing inline worker call
