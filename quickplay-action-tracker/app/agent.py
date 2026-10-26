# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from typing import Any, Dict, List, Optional
from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.cloud import firestore
from google.genai import types

MODEL = "gemini-2.5-flash"
FIRESTORE_PROJECT = "qwiklabs-gcp-04-ddbf4b181b7a"
COLLECTION_NAME = "action_items"

# Initialize Firestore client with explicit string project ID
db = firestore.Client(project=FIRESTORE_PROJECT)

# User Profiles and Product Entitlement Registry
USER_PROFILES = {
    "alex@quickplay.com": {
        "email": "alex@quickplay.com",
        "name": "Alex Vance",
        "is_internal": True,
        "default_role": "internal",
        "allowed_orgs": ["customer-acme", "customer-globex", "customer-initech"],
        "product_entitlements": {},  # Internal user has access to all companies and products
    },
    "customer_a@acme.com": {
        "email": "customer_a@acme.com",
        "name": "Alice Stakeholder (Acme)",
        "is_internal": False,
        "default_role": "customer_edit",
        "allowed_orgs": ["customer-acme"],
        # Entitled to BOTH products: Video Streaming Platform & Cloud DVR
        "product_entitlements": {
            "customer-acme": ["prod-acme-streaming", "prod-acme-dvr"]
        },
    },
    "customer_b@acme.com": {
        "email": "customer_b@acme.com",
        "name": "Bob Streaming Tech (Acme)",
        "is_internal": False,
        "default_role": "customer_view",
        "allowed_orgs": ["customer-acme"],
        # Entitled ONLY to Video Streaming Platform (NOT Cloud DVR)
        "product_entitlements": {
            "customer-acme": ["prod-acme-streaming"]
        },
    },
    "executive@globex.com": {
        "email": "executive@globex.com",
        "name": "Grace Hopper (Globex)",
        "is_internal": False,
        "default_role": "customer_view",
        "allowed_orgs": ["customer-globex"],
        "product_entitlements": {
            "customer-globex": ["prod-globex-ott"]
        },
    },
}


def check_user_authorization(user_email: str, target_org_id: str, target_product_id: Optional[str] = None) -> Optional[str]:
    """Validates whether the user account is entitled to access the organization and product.
    Returns None if authorized, or a rejection error message if unauthorized.
    """
    profile = USER_PROFILES.get(user_email)
    if not profile:
        # Default fallback: check if internal by domain
        if user_email.endswith("@quickplay.com"):
            return None
        return f"Access Denied: User '{user_email}' is not registered in the entitlement directory."

    if profile.get("is_internal"):
        return None  # Quickplay internal has universal access

    allowed_orgs = profile.get("allowed_orgs", [])
    if target_org_id not in allowed_orgs:
        return (
            f"Access Denied: Your account ({user_email}) is strictly entitled to {allowed_orgs} "
            f"and does not have permission to access or view information for organization '{target_org_id}'."
        )

    if target_product_id:
        entitled_products = profile.get("product_entitlements", {}).get(target_org_id, [])
        if target_product_id not in entitled_products:
            return (
                f"Access Denied: Your account ({user_email}) is entitled to products {entitled_products} "
                f"in '{target_org_id}', and does not have access to inquire about product '{target_product_id}'."
            )

    return None


def list_action_items(
    org_id: str,
    user_email: str = "alex@quickplay.com",
    product_id: Optional[str] = None,
    include_closed: bool = False,
) -> Dict[str, Any]:
    """Retrieves action items and their child nodes for a specific organization and product,
    enforcing account entitlements for company and product access.

    Args:
        org_id: The organization identifier (e.g., 'customer-acme', 'customer-globex', 'customer-initech').
        user_email: Email address of the requesting user (e.g., 'customer_a@acme.com', 'customer_b@acme.com').
        product_id: Optional product identifier (e.g., 'prod-acme-streaming', 'prod-acme-dvr', 'prod-globex-ott').
        include_closed: If False (default), only returns open / in-progress work items.

    Returns:
        A dictionary with the items list or an access denied message if unauthorized.
    """
    auth_err = check_user_authorization(user_email, org_id, product_id)
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    query = db.collection(COLLECTION_NAME).where(field_path="org_id", op_string="==", value=org_id)
    docs = query.stream()
    items = []

    # Also filter by user's product entitlements if customer didn't pass specific product_id
    profile = USER_PROFILES.get(user_email, {})
    allowed_prods = None
    if not profile.get("is_internal") and "product_entitlements" in profile:
        allowed_prods = profile.get("product_entitlements", {}).get(org_id)

    for doc in docs:
        data = doc.to_dict()
        item_prod = data.get("product_id")
        if product_id and item_prod != product_id:
            continue
        if allowed_prods is not None and item_prod and item_prod not in allowed_prods:
            continue
        if not include_closed and data.get("status") == "closed":
            continue
        items.append(data)
    return {"items": items, "count": len(items)}


def get_closed_action_items(org_id: str, user_email: str = "alex@quickplay.com") -> Dict[str, Any]:
    """Retrieves only closed/completed action items with audit history and closure dates,
    enforcing organization and product entitlements.

    Args:
        org_id: The organization identifier (e.g., 'customer-acme').
        user_email: Email of the requesting user.

    Returns:
        A dictionary of completed action items or access denied error.
    """
    auth_err = check_user_authorization(user_email, org_id)
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    profile = USER_PROFILES.get(user_email, {})
    allowed_prods = None
    if not profile.get("is_internal") and "product_entitlements" in profile:
        allowed_prods = profile.get("product_entitlements", {}).get(org_id)

    query = db.collection(COLLECTION_NAME).where(field_path="org_id", op_string="==", value=org_id).where(field_path="status", op_string="==", value="closed")
    docs = query.stream()
    items = []
    for doc in docs:
        data = doc.to_dict()
        item_prod = data.get("product_id")
        if allowed_prods is not None and item_prod and item_prod not in allowed_prods:
            continue
        items.append(data)
    return {"items": items, "count": len(items)}


def get_action_item_detail(item_id: str, user_email: str = "alex@quickplay.com") -> Dict[str, Any]:
    """Retrieves complete details of a specific action item, validating that the requesting user's account
    is entitled to view the item's organization and product.

    Args:
        item_id: The unique identifier of the action item (e.g., 'ACT-101').
        user_email: Email of the requesting user.

    Returns:
        The action item dictionary, or an access denied error.
    """
    doc_ref = db.collection(COLLECTION_NAME).document(item_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Action item '{item_id}' not found."}

    data = doc.to_dict()
    auth_err = check_user_authorization(user_email, data.get("org_id", ""), data.get("product_id"))
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    return data


def get_work_item_updates_today(
    item_id_or_title: str,
    user_email: str = "alex@quickplay.com",
    target_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieves all updates, status changes, milestone progress, and notes recorded today (or a specific date)
    for a specific work item (identified by ID like 'ACT-101' or title keywords), strictly enforcing the user's
    organization and product access entitlements.

    Args:
        item_id_or_title: The action item ID (e.g., 'ACT-101') or a keyword from its title.
        user_email: Email address of the requesting user.
        target_date: Date string 'YYYY-MM-DD' to check for updates (defaults to today UTC).

    Returns:
        A structured dictionary of updates recorded on the target date, current status,
        and current milestone state, or an access denied / not found error.
    """
    today_str = target_date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    # Locate the item by direct ID match or title match in Firestore
    target_item = None
    target_id_clean = item_id_or_title.strip()

    # Try direct document lookup first
    doc_ref = db.collection(COLLECTION_NAME).document(target_id_clean.upper())
    doc = doc_ref.get()
    if doc.exists:
        target_item = doc.to_dict()
    else:
        # Search all documents for title match
        all_docs = db.collection(COLLECTION_NAME).stream()
        search_lower = target_id_clean.lower()
        for d in all_docs:
            val = d.to_dict()
            if (val.get("item_id", "").lower() == search_lower or 
                search_lower in val.get("title", "").lower()):
                target_item = val
                break

    if not target_item:
        return {"error": f"Work item matching '{item_id_or_title}' was not found in the tracker."}

    # Verify authorization
    item_org = target_item.get("org_id", "")
    item_prod = target_item.get("product_id")
    auth_err = check_user_authorization(user_email, item_org, item_prod)
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    # Extract updates on target date from history
    updates_today = []
    for entry in target_item.get("history", []):
        ts = entry.get("timestamp", "")
        if ts.startswith(today_str):
            updates_today.append({
                "timestamp": ts,
                "field": entry.get("field"),
                "old_value": entry.get("old_value"),
                "new_value": entry.get("new_value"),
                "updated_by": entry.get("updated_by"),
                "note": entry.get("note", ""),
            })

    # Also check milestones completed today
    milestones_completed_today = []
    for n in target_item.get("nodes", []):
        comp = n.get("completed_at", "")
        if comp and comp.startswith(today_str):
            milestones_completed_today.append({
                "node_id": n.get("node_id"),
                "title": n.get("title"),
                "status": n.get("status"),
                "completed_at": comp
            })

    return {
        "item_id": target_item.get("item_id"),
        "title": target_item.get("title"),
        "org_id": item_org,
        "product_id": item_prod,
        "product_name": target_item.get("product_name"),
        "current_status": target_item.get("status"),
        "priority": target_item.get("priority"),
        "assignee": target_item.get("assignee"),
        "target_date": today_str,
        "total_updates_today": len(updates_today),
        "updates": updates_today,
        "milestones_completed_today": milestones_completed_today,
        "active_milestones": [
            {"title": n.get("title"), "status": n.get("status"), "target_date": n.get("target_date")}
            for n in target_item.get("nodes", [])
        ],
    }


def get_daily_update_summary(
    org_id: str,
    user_email: str = "alex@quickplay.com",
    product_id: Optional[str] = None,
    target_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates a comprehensive daily update summary for today (or a specific date) across all work items
    belonging to the specified company and product, strictly filtered to only the items the requesting user
    is entitled to view.

    Args:
        org_id: The company organization identifier (e.g., 'customer-acme', 'customer-globex', 'customer-initech').
        user_email: Email address of the requesting user.
        product_id: Optional product filter if the user is currently viewing a specific product.
        target_date: Date string 'YYYY-MM-DD' (defaults to today UTC).

    Returns:
        A structured summary containing all updates made today, closed items today, milestone movements,
        and high-priority items due soon, restricted strictly by user entitlements.
    """
    auth_err = check_user_authorization(user_email, org_id, product_id)
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    today_str = target_date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    profile = USER_PROFILES.get(user_email, {})
    allowed_prods = None
    if not profile.get("is_internal") and "product_entitlements" in profile:
        allowed_prods = profile.get("product_entitlements", {}).get(org_id)

    query = db.collection(COLLECTION_NAME).where(field_path="org_id", op_string="==", value=org_id)
    docs = query.stream()
    all_raw = [doc.to_dict() for doc in docs]

    items = []
    for it in all_raw:
        item_prod = it.get("product_id")
        if product_id and item_prod != product_id:
            continue
        if allowed_prods is not None and item_prod and item_prod not in allowed_prods:
            continue
        items.append(it)

    if not items:
        return {
            "org_id": org_id,
            "product_id": product_id,
            "target_date": today_str,
            "message": f"No work items found for organization '{org_id}' under your account entitlements.",
            "updates_today": [],
        }

    item_summaries = []
    items_updated_today = 0
    total_updates_today = 0

    for it in items:
        history_today = []
        for h in it.get("history", []):
            ts = h.get("timestamp", "")
            if ts.startswith(today_str):
                history_today.append({
                    "field": h.get("field"),
                    "old_value": h.get("old_value"),
                    "new_value": h.get("new_value"),
                    "note": h.get("note", ""),
                    "timestamp": ts,
                    "updated_by": h.get("updated_by") if profile.get("is_internal") else None,
                })

        closed_today = bool(it.get("closed_at", "") and it.get("closed_at", "").startswith(today_str))

        if history_today or closed_today:
            items_updated_today += 1
            total_updates_today += len(history_today)
            item_summaries.append({
                "item_id": it.get("item_id"),
                "title": it.get("title"),
                "product_name": it.get("product_name"),
                "current_status": it.get("status"),
                "priority": it.get("priority"),
                "closed_today": closed_today,
                "updates": history_today,
            })

    return {
        "org_id": org_id,
        "product_id": product_id or "All Entitled Products",
        "target_date": today_str,
        "total_entitled_items": len(items),
        "items_updated_today_count": items_updated_today,
        "total_updates_count": total_updates_today,
        "updated_items": item_summaries,
        "all_active_items_overview": [
            {
                "item_id": it.get("item_id"),
                "title": it.get("title"),
                "product_name": it.get("product_name"),
                "status": it.get("status"),
                "delivery_date": it.get("delivery_date"),
            }
            for it in items if it.get("status") != "closed"
        ],
    }


def update_action_item_status(
    item_id: str,
    status: str,
    updated_by: str,
    note: Optional[str] = None,
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Updates the status of an action item or one of its child nodes, recording a timestamped audit history entry,
    verifying caller entitlements for that item.

    Args:
        item_id: The action item identifier (e.g., 'ACT-101').
        status: The new status (e.g., 'ideation', 'in progress', 'in review', 'QA',
                'deploying to staging', 'deploying to production', 'closing', 'closed', 'blocked').
        updated_by: Email or identifier of the user making the update.
        note: Optional context or explanation for the update.
        node_id: Optional ID of a specific child node to update (e.g., 'node-2'). If omitted, updates the parent item.

    Returns:
        Status message with the updated item details or access denied error.
    """
    doc_ref = db.collection(COLLECTION_NAME).document(item_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Action item '{item_id}' not found."}

    data = doc.to_dict()
    auth_err = check_user_authorization(updated_by, data.get("org_id", ""), data.get("product_id"))
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    old_status = ""
    history_entry = {
        "timestamp": now,
        "updated_by": updated_by,
        "note": note or "",
    }

    if node_id:
        nodes = data.get("nodes", [])
        node_found = False
        for node in nodes:
            if node.get("node_id") == node_id:
                old_status = node.get("status", "")
                node["status"] = status
                if status == "closed":
                    node["completed_at"] = now
                node_found = True
                break
        if not node_found:
            return {"error": f"Node '{node_id}' not found in action item '{item_id}'."}
        data["nodes"] = nodes
        history_entry["field"] = f"node:{node_id}:status"
        history_entry["old_value"] = old_status
        history_entry["new_value"] = status
    else:
        old_status = data.get("status", "")
        data["status"] = status
        if status == "closed":
            data["closed_at"] = now
        history_entry["field"] = "status"
        history_entry["old_value"] = old_status
        history_entry["new_value"] = status

    history = data.get("history", [])
    history.append(history_entry)
    data["history"] = history

    doc_ref.set(data)
    return {
        "success": True,
        "item_id": item_id,
        "node_id": node_id,
        "old_status": old_status,
        "new_status": status,
        "updated_at": now,
    }


def attach_reference_link(
    item_id: str,
    link_type: str,
    url: str,
    label: str,
    updated_by: str = "alex@quickplay.com",
    node_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Attaches a reference link (Jira ticket, Google Doc, Google Sheet, etc.) to an action item or child node,
    verifying user entitlements.

    Args:
        item_id: The action item identifier (e.g., 'ACT-101').
        link_type: Type of reference ('jira', 'doc', 'sheet', 'pr', or 'link').
        url: The web URL of the ticket or document.
        label: A human-readable display label (e.g., 'Jira QP-402', 'Architecture Spec').
        updated_by: User making the attachment.
        node_id: Optional child node ID if attaching directly to a sub-node.

    Returns:
        Confirmation dictionary with the attached link details or access denied.
    """
    doc_ref = db.collection(COLLECTION_NAME).document(item_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Action item '{item_id}' not found."}

    data = doc.to_dict()
    auth_err = check_user_authorization(updated_by, data.get("org_id", ""), data.get("product_id"))
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    new_attachment = {
        "link_type": link_type,
        "url": url,
        "label": label,
        "node_id": node_id,
    }

    attachments = data.get("attachments", [])
    attachments.append(new_attachment)
    data["attachments"] = attachments

    doc_ref.set(data)
    return {
        "success": True,
        "item_id": item_id,
        "attachment": new_attachment,
    }


def generate_daily_executive_digest(
    org_id: str,
    user_email: str = "alex@quickplay.com",
    product_id: Optional[str] = None,
    target_role: str = "customer",
) -> Dict[str, Any]:
    """Generates an executive daily status digest for a given customer organization,
    enforcing the requesting user's company and product access boundaries.

    Args:
        org_id: The customer organization identifier (e.g., 'customer-acme').
        user_email: Email address of the requesting user.
        product_id: Optional product filter.
        target_role: 'customer' or 'internal'.

    Returns:
        A structured summary dictionary containing totals, key highlights, upcoming deliveries,
        and milestone progress, or access denied.
    """
    auth_err = check_user_authorization(user_email, org_id, product_id)
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    query = db.collection(COLLECTION_NAME).where(field_path="org_id", op_string="==", value=org_id)
    docs = query.stream()
    all_raw = [doc.to_dict() for doc in docs]

    profile = USER_PROFILES.get(user_email, {})
    allowed_prods = None
    if not profile.get("is_internal") and "product_entitlements" in profile:
        allowed_prods = profile.get("product_entitlements", {}).get(org_id)

    items = []
    for it in all_raw:
        item_prod = it.get("product_id")
        if product_id and item_prod != product_id:
            continue
        if allowed_prods is not None and item_prod and item_prod not in allowed_prods:
            continue
        items.append(it)

    if not items:
        return {"error": f"No action items found for organization '{org_id}' under user entitlements."}

    now = datetime.datetime.now(datetime.timezone.utc)
    recent_cutoff = (now - datetime.timedelta(hours=48)).isoformat()

    total_items = len(items)
    closed_items = sum(1 for it in items if it.get("status") == "closed")
    active_items = total_items - closed_items

    recent_updates = []
    upcoming_deliveries = []
    active_milestone_breakdown = []

    for item in items:
        deliv = item.get("delivery_date")
        if deliv and item.get("status") != "closed":
            upcoming_deliveries.append({
                "item_id": item.get("item_id"),
                "title": item.get("title"),
                "product_name": item.get("product_name"),
                "delivery_date": deliv,
                "status": item.get("status"),
                "priority": item.get("priority", "medium"),
            })

        for entry in item.get("history", []):
            if entry.get("timestamp", "") >= recent_cutoff:
                update_info = {
                    "item_id": item.get("item_id"),
                    "title": item.get("title"),
                    "field": entry.get("field"),
                    "new_value": entry.get("new_value"),
                    "timestamp": entry.get("timestamp"),
                    "note": entry.get("note", ""),
                }
                if target_role == "internal":
                    update_info["updated_by"] = entry.get("updated_by")
                recent_updates.append(update_info)

        if item.get("status") != "closed":
            nodes = item.get("nodes", [])
            completed_nodes = sum(1 for n in nodes if n.get("status") == "closed")
            total_nodes = len(nodes)
            node_progress = f"{completed_nodes}/{total_nodes}" if total_nodes else "N/A"
            active_milestone_breakdown.append({
                "item_id": item.get("item_id"),
                "title": item.get("title"),
                "product_name": item.get("product_name"),
                "status": item.get("status"),
                "milestone_progress": node_progress,
                "priority": item.get("priority", "medium"),
            })

    upcoming_deliveries.sort(key=lambda x: x["delivery_date"])

    digest = {
        "org_id": org_id,
        "user_email": user_email,
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "view_type": "Customer Executive Digest" if target_role == "customer" else "Internal Operations Digest",
        "health_summary": {
            "total_work_items": total_items,
            "active_work_items": active_items,
            "completed_work_items": closed_items,
            "completion_percentage": f"{round((closed_items / total_items) * 100, 1)}%" if total_items else "0%",
        },
        "upcoming_deliveries": upcoming_deliveries,
        "recent_highlights": recent_updates,
        "active_milestone_breakdown": active_milestone_breakdown,
    }
    return digest


def check_approaching_deadlines_and_reminders(
    org_id: str,
    user_email: str = "alex@quickplay.com",
    product_id: Optional[str] = None,
    days_threshold: int = 7,
) -> Dict[str, Any]:
    """Scans all active action items and milestone nodes for approaching delivery deadlines or overdue items,
    strictly restricted to the user's company and product entitlements.

    Args:
        org_id: The organization identifier (e.g., 'customer-acme').
        user_email: Email address of the requesting user.
        product_id: Optional product filter.
        days_threshold: Number of days to look ahead (default is 7 days).

    Returns:
        A structured dictionary of overdue items, items due soon within the threshold,
        or access denied error.
    """
    auth_err = check_user_authorization(user_email, org_id, product_id)
    if auth_err:
        return {"error": auth_err, "access_denied": True}

    query = db.collection(COLLECTION_NAME).where(field_path="org_id", op_string="==", value=org_id)
    docs = query.stream()
    all_raw = [doc.to_dict() for doc in docs]

    profile = USER_PROFILES.get(user_email, {})
    allowed_prods = None
    if not profile.get("is_internal") and "product_entitlements" in profile:
        allowed_prods = profile.get("product_entitlements", {}).get(org_id)

    items = []
    for it in all_raw:
        item_prod = it.get("product_id")
        if product_id and item_prod != product_id:
            continue
        if allowed_prods is not None and item_prod and item_prod not in allowed_prods:
            continue
        items.append(it)

    if not items:
        return {"error": f"No action items found for organization '{org_id}' under user entitlements."}

    today = datetime.datetime.now(datetime.timezone.utc).date()
    overdue_alerts = []
    due_soon_alerts = []

    for item in items:
        if item.get("status") == "closed":
            continue

        item_id = item.get("item_id")
        title = item.get("title")
        assignee = item.get("assignee")
        status = item.get("status")
        prod_name = item.get("product_name", "")

        deliv_str = item.get("delivery_date")
        if deliv_str:
            try:
                deliv_date = datetime.date.fromisoformat(deliv_str)
                diff_days = (deliv_date - today).days

                alert = {
                    "item_id": item_id,
                    "title": title,
                    "product": prod_name,
                    "target_type": "Work Item",
                    "due_date": deliv_str,
                    "days_remaining": diff_days,
                    "status": status,
                    "assignee": assignee,
                    "priority": item.get("priority", "medium"),
                }

                if diff_days < 0:
                    alert["urgency"] = "OVERDUE"
                    overdue_alerts.append(alert)
                elif diff_days <= days_threshold:
                    alert["urgency"] = "DUE SOON"
                    due_soon_alerts.append(alert)
            except ValueError:
                pass

        for node in item.get("nodes", []):
            if node.get("status") == "closed":
                continue

            node_target_str = node.get("target_date")
            if node_target_str:
                try:
                    node_target_date = datetime.date.fromisoformat(node_target_str)
                    diff_days = (node_target_date - today).days

                    node_alert = {
                        "item_id": item_id,
                        "title": f"{title} ➔ Node: {node.get('title')}",
                        "product": prod_name,
                        "target_type": "Milestone Node",
                        "node_id": node.get("node_id"),
                        "due_date": node_target_str,
                        "days_remaining": diff_days,
                        "status": node.get("status"),
                        "assignee": node.get("assignee") or assignee,
                        "priority": item.get("priority", "medium"),
                    }

                    if diff_days < 0:
                        node_alert["urgency"] = "OVERDUE"
                        overdue_alerts.append(node_alert)
                    elif diff_days <= days_threshold:
                        node_alert["urgency"] = "DUE SOON"
                        due_soon_alerts.append(node_alert)
                except ValueError:
                    pass

    overdue_alerts.sort(key=lambda x: x["days_remaining"])
    due_soon_alerts.sort(key=lambda x: x["days_remaining"])

    return {
        "org_id": org_id,
        "user_email": user_email,
        "as_of_date": today.isoformat(),
        "lookahead_days": days_threshold,
        "total_overdue": len(overdue_alerts),
        "total_due_soon": len(due_soon_alerts),
        "overdue_items": overdue_alerts,
        "due_soon_items": due_soon_alerts,
    }


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=(
        "You are the Quickplay Action Tracker Assistant. You help internal project teams and client "
        "stakeholders track, organize, and update hierarchical action items, milestone nodes, reference "
        "attachments (Jira tickets, Google Docs/Sheets), and status lifecycles.\n\n"
        "CORE USE CASES & BEHAVIOR:\n"
        "1. 'What are the updates about work item x today?':\n"
        "   - Use `get_work_item_updates_today` with `item_id_or_title=x` and the user's `user_email`.\n"
        "   - Highlight the current status, all history/audit logs recorded today, milestone completions today, "
        "     and current milestone progress.\n"
        "   - If no updates were recorded today, clearly summarize the item's current status, active milestones, "
        "     and mention that no status transitions occurred today.\n"
        "2. 'What is the update summary for today?':\n"
        "   - Use `get_daily_update_summary` with `org_id`, `user_email`, and optional `product_id`.\n"
        "   - Recognize which company and product the user is currently viewing (passed in the security context).\n"
        "   - Provide a concise summary of items updated or completed today, plus an active items overview.\n\n"
        "STRICT SECURITY & ACCESS CONTROL DIRECTIVES:\n"
        "1. Every interaction provides the requesting user's identity, role, and current organization context.\n"
        "2. Pass the user's email (`user_email`) and organization (`org_id`) to every tool call.\n"
        "3. COMPANY / TENANT RESTRICTIONS: A customer account for Company A must NEVER be allowed to see, query, "
        "or receive information about Company B. If a customer user asks about an organization other than their "
        "entitled organization, firmly refuse and explain that their account does not have access to that company.\n"
        "4. PRODUCT RESTRICTIONS: Some client companies have multiple distinct products (e.g. Acme has 'Video Streaming Platform' "
        "and 'Cloud DVR & Storage'). Customer accounts only have access to their entitled products. For example, if a user's "
        "account only has access to Product A, they must NEVER be allowed to see, query, or receive information about Product B. "
        "If they inquire about an unentitled product or if a tool returns an 'access_denied' / authorization error, "
        "state clearly that their account is not entitled to access that product's work items or data.\n"
        "5. Internal Quickplay team members (e.g. alex@quickplay.com) are operators with full visibility across companies and products.\n"
        "6. Always adhere strictly to tool responses. If an access denied error is returned, politely inform the user of their exact entitlement boundary."
    ),
    tools=[
        get_work_item_updates_today,
        get_daily_update_summary,
        list_action_items,
        get_closed_action_items,
        get_action_item_detail,
        update_action_item_status,
        attach_reference_link,
        generate_daily_executive_digest,
        check_approaching_deadlines_and_reminders,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
