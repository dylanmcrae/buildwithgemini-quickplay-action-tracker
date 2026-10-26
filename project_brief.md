# My agent: Quickplay Action Tracker (Task & Milestone Concierge)

One-liner: A conversational and structured action-tracking agent that helps internal project teams and client stakeholders manage hierarchical work items, track milestone nodes from ideation to production, and receive automated reminders and role-tailored daily status digests.

## Core Features & Requirements:
1. **Multi-Tenant / Organization Isolation**:
   - Customer-scoped data: Client accounts only access their respective organization's work items and progress.
   - Distinct Views & Entitlements:
     - **Customer View**: High-level milestone summaries, status cards for parent work items and their child nodes, and executive daily progress digests. Customer accounts have read-only access by default, but can be individually granted granular edit privileges within their workspace/spaces by an internal Quickplay account.
     - **Internal View (Quickplay)**: Detailed operational tracking (ideation -> analysis -> development -> QA -> production deployment), employee assignments, target and delivery dates, follow-up logs, and manual override/editing capabilities. Quickplay accounts have administrative authority to manage customer accounts, assign space access, and grant or revoke customer edit privileges.
2. **Account Onboarding & Links**:
   - Specific invitation/onboarding URLs for creating internal vs. customer-entitled accounts with Google Account authentication.
3. **Work Item Lifecycle & Statuses**:
   - Flexible lifecycle statuses on both parent items and granular sub-nodes:
     - Examples: `ideation`, `in progress`, `in review`, `QA`, `deploying to staging`, `deploying to production`, `closing`, `closed`, `blocked`, etc.
   - **Date & Audit Tracking**: Every update made to any work item or sub-node records timestamped audit entries (date/time, editor identity, status transition, notes).
4. **Completed / Closed Items Archive Space**:
   - Dedicated space/view to browse closed and completed work items.
   - Displays complete chronological audit timeline: dates of every update that took place, who modified it, and the explicit date/time the item was marked as closed.
5. **Data Ingestion & Attachments**:
   - Ingest work items via external documents/sheets (structured rows/markdown) or direct conversational & UI creation/editing.
   - **Artifact & Ticket Attachments**: Attach external reference links (Jira ticket links, Google Docs, Google Sheets, design files, or PR links) directly to a parent work item or to a specific granular node/subtask for contextual reference in tracking and updates.
6. **Reminders & Daily Summaries**:
   - Track approaching delivery dates, trigger milestone follow-ups, and generate daily executive client updates.

## Tool coverage:
- **Memory**: Remembers user identity, assigned organization/tenant, role entitlement (Internal vs Customer), granted permissions/privileges, alert preferences, and contextual conversation state across sessions.
- **Tools**:
  - `query_work_items(org_id, role, status_filter=None, item_id=None)`: Retrieve active or filtered action items by role entitlement and organization.
  - `get_closed_work_items(org_id, role)`: Dedicated retrieval of archived/closed work items complete with closure dates and full update timeline histories.
  - `update_work_item(item_id, node_id, status, assignee, target_date, note)`: Modify work items, node completion, and lifecycle stages, automatically appending timestamped audit records.
  - `attach_reference_link(item_id, node_id, link_type, url, label)`: Attach Jira tickets, Google Docs/Sheets, or specification links to an item or sub-node.
  - `manage_customer_privileges(customer_user_id, org_id, space_id, can_edit)`: Grant or revoke editing privileges for individual customer accounts within designated spaces (Quickplay internal only).
  - `generate_daily_update(org_id, date)`: Prepare tailored daily status reports (high-level executive digest for customers; technical breakdown for internals).
  - `generate_invite_link(org_id, role)`: Generate role-specific onboarding URL for internal team members or clients.
  - `import_work_items(data_source, raw_content)`: Parse and ingest action items from uploaded/shared document data.
- **Catalog/UI**: Hierarchical action items & milestone cards rendered via A2UI (progress bars, node checklist tables, status badges, clickable Jira/Doc attachment chips, and assignee tags).
- **Image gen**: Visual milestone roadmaps, burn-up/progress charts, or status badges generated dynamically.
- **Sandbox**: Timeline calculation, critical-path estimation, completion percentages, and days-to-deadline calculations.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): Code sandbox for critical path & timeline analytics, Vertex AI Memory Bank for cross-session stakeholder preferences.
