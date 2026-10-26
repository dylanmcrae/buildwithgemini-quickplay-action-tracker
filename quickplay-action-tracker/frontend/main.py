"""FastAPI Backend & Proxy for Quickplay Action Tracker.

Provides direct REST APIs for:
  - Account session / role entitlement switching (Google OAuth mock / user role)
  - Work item CRUD & subcategory/node updates
  - Work item creation & bulk import (Docs/Sheets/CSV)
  - Customer privilege management
  - Invite URL generation
  - Direct proxy / chat to the local or deployed agent
"""

import datetime
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore

FIRESTORE_PROJECT = "qwiklabs-gcp-04-ddbf4b181b7a"
COLLECTION_NAME = "action_items"

db = firestore.Client(project=FIRESTORE_PROJECT)

app = FastAPI(title="Quickplay Action Tracker App")


# --- Organizations & Product Directory Definition ---
COMPANIES_REGISTRY = {
    "customer-acme": {
        "org_id": "customer-acme",
        "name": "Acme Media Corp",
        "products": [
            {"product_id": "prod-acme-streaming", "name": "Video Streaming Platform", "description": "Core HLS/DASH streaming & user playback portal"},
            {"product_id": "prod-acme-dvr", "name": "Cloud DVR & Storage", "description": "Cloud recording ingestion and long-term asset archiving"},
        ]
    },
    "customer-globex": {
        "org_id": "customer-globex",
        "name": "Globex Media Group",
        "products": [
            {"product_id": "prod-globex-ott", "name": "OTT Multi-Screen App", "description": "Apple TV, Roku, FireTV and mobile applications"},
        ]
    },
    "customer-initech": {
        "org_id": "customer-initech",
        "name": "Initech Broadcasting",
        "products": [
            {"product_id": "prod-initech-linear", "name": "Linear 24/7 Playout", "description": "Continuous linear master feed with SSAI ad marker splicing"},
        ]
    }
}

# Pre-configured user persona accounts and their entitlements
USER_PROFILES = {
    "alex@quickplay.com": {
        "email": "alex@quickplay.com",
        "name": "Alex Vance",
        "is_internal": True,
        "default_role": "internal",
        "allowed_orgs": ["customer-acme", "customer-globex", "customer-initech"],
        "product_entitlements": {} # Internal has access to all
    },
    "customer_a@acme.com": {
        "email": "customer_a@acme.com",
        "name": "Alice Stakeholder (Acme)",
        "is_internal": False,
        "default_role": "customer_edit",
        "allowed_orgs": ["customer-acme"],
        # Entitled to BOTH products (Streaming + DVR)
        "product_entitlements": {
            "customer-acme": ["prod-acme-streaming", "prod-acme-dvr"]
        }
    },
    "customer_b@acme.com": {
        "email": "customer_b@acme.com",
        "name": "Bob Streaming Tech (Acme)",
        "is_internal": False,
        "default_role": "customer_view",
        "allowed_orgs": ["customer-acme"],
        # Entitled ONLY to Streaming Platform (NOT Cloud DVR)
        "product_entitlements": {
            "customer-acme": ["prod-acme-streaming"]
        }
    },
    "executive@globex.com": {
        "email": "executive@globex.com",
        "name": "Grace Hopper (Globex)",
        "is_internal": False,
        "default_role": "customer_view",
        "allowed_orgs": ["customer-globex"],
        "product_entitlements": {
            "customer-globex": ["prod-globex-ott"]
        }
    }
}

# --- API Routes for Action Items ---

@app.get("/api/organizations")
async def get_organizations():
    """Returns the company directory, products, and available user profiles."""
    return {
        "companies": list(COMPANIES_REGISTRY.values()),
        "user_profiles": USER_PROFILES
    }

@app.get("/api/items")
async def get_items(org_id: str = "customer-acme", product_id: Optional[str] = None, include_closed: bool = True):
    query = db.collection(COLLECTION_NAME).where(field_path="org_id", op_string="==", value=org_id)
    docs = query.stream()
    items = []
    for doc in docs:
        data = doc.to_dict()
        if product_id and data.get("product_id") != product_id:
            continue
        if not include_closed and data.get("status") == "closed":
            continue
        items.append(data)
    return {"items": items}


@app.post("/api/items")
async def create_item(req: Request):
    body = await req.json()
    item_id = body.get("item_id") or f"ACT-{uuid.uuid4().hex[:6].upper()}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    new_item = {
        "item_id": item_id,
        "org_id": body.get("org_id", "customer-acme"),
        "product_id": body.get("product_id", "prod-acme-streaming"),
        "product_name": body.get("product_name", ""),
        "title": body.get("title", "Untitled Action Item"),
        "description": body.get("description", ""),
        "status": body.get("status", "ideation"),
        "priority": body.get("priority", "medium"),
        "assignee": body.get("assignee", "unassigned"),
        "delivery_date": body.get("delivery_date", ""),
        "created_at": now,
        "closed_at": now if body.get("status") == "closed" else None,
        "space_id": body.get("space_id", "general"),
        "nodes": body.get("nodes", []),
        "attachments": body.get("attachments", []),
        "history": [
            {
                "timestamp": now,
                "updated_by": body.get("creator", "admin@quickplay.com"),
                "field": "created",
                "old_value": "",
                "new_value": body.get("status", "ideation"),
                "note": "Work item created.",
            }
        ],
    }
    db.collection(COLLECTION_NAME).document(item_id).set(new_item)
    return {"success": True, "item": new_item}


@app.post("/api/items/{item_id}/update")
async def update_item(item_id: str, req: Request):
    body = await req.json()
    doc_ref = db.collection(COLLECTION_NAME).document(item_id)
    doc = doc_ref.get()
    if not doc.exists:
        return JSONResponse(status_code=404, content={"error": "Item not found"})

    data = doc.to_dict()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    updated_by = body.get("updated_by", "user@quickplay.com")
    note = body.get("note", "Item details edited")

    # Editable core fields
    editable_fields = ["title", "description", "space_id", "product_id", "product_name", "priority", "assignee", "delivery_date", "nodes", "attachments"]
    changed_fields = []
    for field in editable_fields:
        if field in body and body[field] != data.get(field):
            changed_fields.append(field)
            data[field] = body[field]

    # Handle status change & closed_at logic
    if "status" in body and body["status"] != data.get("status"):
        old_status = data.get("status")
        new_status = body["status"]
        data["status"] = new_status
        if new_status == "closed":
            data["closed_at"] = now
        elif data.get("closed_at"):
            data["closed_at"] = None

        data["history"].append({
            "timestamp": now,
            "updated_by": updated_by,
            "field": "status",
            "old_value": old_status,
            "new_value": new_status,
            "note": note,
        })
    elif changed_fields:
        data["history"].append({
            "timestamp": now,
            "updated_by": updated_by,
            "field": f"edit:{','.join(changed_fields)}",
            "old_value": "",
            "new_value": "updated",
            "note": note,
        })

    doc_ref.set(data)
    return {"success": True, "item": data}


@app.delete("/api/items/{item_id}")
async def delete_item(item_id: str):
    db.collection(COLLECTION_NAME).document(item_id).delete()
    return {"success": True, "item_id": item_id}


@app.post("/api/items/{item_id}/attachments")
async def add_attachment(item_id: str, req: Request):
    body = await req.json()
    doc_ref = db.collection(COLLECTION_NAME).document(item_id)
    doc = doc_ref.get()
    if not doc.exists:
        return JSONResponse(status_code=404, content={"error": "Item not found"})

    data = doc.to_dict()
    new_att = {
        "link_type": body.get("link_type", "link"),
        "url": body.get("url", ""),
        "label": body.get("label", "Attachment"),
        "node_id": body.get("node_id"),
    }
    data.setdefault("attachments", []).append(new_att)
    doc_ref.set(data)
    return {"success": True, "attachment": new_att}


@app.post("/api/items/import")
async def bulk_import(req: Request):
    body = await req.json()
    raw_text = body.get("raw_text", "")
    org_id = body.get("org_id", "customer-acme")
    creator = body.get("creator", "importer@quickplay.com")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    imported_count = 0

    for i, line in enumerate(lines):
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if not parts or parts[0].lower() in ["title", "item", "name"]:
            continue

        item_id = f"ACT-IMP-{uuid.uuid4().hex[:4].upper()}"
        title = parts[0]
        status = parts[1] if len(parts) > 1 else "ideation"
        priority = parts[2] if len(parts) > 2 else "medium"
        assignee = parts[3] if len(parts) > 3 else "unassigned"

        item = {
            "item_id": item_id,
            "org_id": org_id,
            "title": title,
            "description": f"Imported entry from batch upload",
            "status": status,
            "priority": priority,
            "assignee": assignee,
            "delivery_date": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=14)).strftime("%Y-%m-%d"),
            "created_at": now,
            "closed_at": now if status == "closed" else None,
            "space_id": "imported",
            "nodes": [],
            "attachments": [],
            "history": [
                {
                    "timestamp": now,
                    "updated_by": creator,
                    "field": "batch_import",
                    "old_value": "",
                    "new_value": status,
                    "note": "Imported via CSV/Sheet import tool",
                }
            ],
        }
        db.collection(COLLECTION_NAME).document(item_id).set(item)
        imported_count += 1

    return {"success": True, "imported_count": imported_count}


@app.get("/api/daily-summary")
async def get_daily_summary_endpoint(
    org_id: str = "customer-acme",
    user_email: str = "alex@quickplay.com",
    product_id: Optional[str] = None,
    target_date: Optional[str] = None,
):
    from app.agent import get_daily_update_summary
    result = get_daily_update_summary(
        org_id=org_id,
        user_email=user_email,
        product_id=product_id if product_id and product_id != "null" and product_id != "undefined" else None,
        target_date=target_date,
    )
    return JSONResponse(result)


# --- Assistant Chat Endpoint ---
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from app.agent import root_agent

chat_session_service = InMemorySessionService()
chat_runner = Runner(agent=root_agent, session_service=chat_session_service, app_name="quickplay_tracker")
active_chat_sessions = {}

@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    org_id = body.get("org_id", "customer-acme")
    role = body.get("role", "customer")
    user_email = body.get("user_email", "customer_a@acme.com")
    product_id = body.get("product_id")

    user_profile = USER_PROFILES.get(user_email, {})
    user_name = user_profile.get("name", user_email)
    allowed_orgs = user_profile.get("allowed_orgs", [org_id])
    product_entitlements = user_profile.get("product_entitlements", {}).get(org_id, "ALL" if user_profile.get("is_internal") else [])

    prompt_context = (
        f"[Security Context: Authenticated User: {user_email} ({user_name}), "
        f"Role: {role}, Current Org: {org_id}, Active Product View: {product_id or 'All'}, "
        f"Account Entitled Orgs: {allowed_orgs}, Entitled Products for {org_id}: {product_entitlements}]\n\n"
        f"User Query: {message}"
    )

    try:
        # Maintain or get active user session
        if user_email not in active_chat_sessions:
            sess = await chat_session_service.create_session(app_name="quickplay_tracker", user_id=user_email)
            active_chat_sessions[user_email] = sess.id
        session_id = active_chat_sessions[user_email]

        content = types.Content(role="user", parts=[types.Part.from_text(text=prompt_context)])
        response_texts = []

        async for event in chat_runner.run_async(
            session_id=session_id,
            user_id=user_email,
            new_message=content,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_texts.append(part.text)

        agent_reply = "".join(response_texts).strip() or "Request processed."
        return JSONResponse({"parts": [{"kind": "text", "text": agent_reply}]})
    except Exception as e:
        return JSONResponse({
            "parts": [
                {
                    "kind": "text",
                    "text": f"Agent error for {user_email}: {e}",
                }
            ]
        })


# Serve static web assets
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8088)))
