"""Import Service for Quickplay Action Tracker.

Interprets work item data from Google Sheets / Docs, CSV/TSV, Word (.docx),
Excel (.xlsx), and raw text/meeting notes, translating them into structured
Action Items with milestones, statuses, and assignees using Gemini 2.5 Flash.
"""

import csv
import datetime
import io
import json
import os
import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List, Optional
import httpx
from google import genai

FIRESTORE_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "qwiklabs-gcp-04-ddbf4b181b7a")
VERTEX_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MODEL_NAME = "gemini-2.5-flash"

# Initialize genai client for Vertex AI
client = genai.Client(vertexai=True, project=FIRESTORE_PROJECT, location=VERTEX_LOCATION)


def extract_text_from_docx_bytes(data: bytes) -> str:
    """Extract plain text from a .docx file using standard library zipfile and XML parsing."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            texts = []
            for elem in tree.iter():
                if elem.tag.endswith("}t") and elem.text:
                    texts.append(elem.text)
                elif elem.tag.endswith("}p"):
                    texts.append("\n")
            return "".join(texts).strip()
    except Exception as e:
        return f"Error extracting DOCX: {e}"


def extract_text_from_xlsx_bytes(data: bytes) -> str:
    """Extract tabular text from a .xlsx file using standard library zipfile and XML parsing."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            shared_strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                sst_xml = z.read("xl/sharedStrings.xml")
                sst_tree = ET.fromstring(sst_xml)
                for si in sst_tree.iter():
                    if si.tag.endswith("}t") and si.text:
                        shared_strings.append(si.text)

            sheet_name = "xl/worksheets/sheet1.xml"
            if sheet_name not in z.namelist():
                for name in z.namelist():
                    if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"):
                        sheet_name = name
                        break

            sheet_xml = z.read(sheet_name)
            sheet_tree = ET.fromstring(sheet_xml)
            rows = []
            for row_elem in sheet_tree.iter():
                if row_elem.tag.endswith("}row"):
                    row_cells = []
                    for c in row_elem:
                        if c.tag.endswith("}c"):
                            cell_type = c.attrib.get("t")
                            val_elem = c.find("{*}v")
                            val = val_elem.text if val_elem is not None and val_elem.text is not None else ""
                            if cell_type == "s" and val.isdigit() and int(val) < len(shared_strings):
                                row_cells.append(shared_strings[int(val)])
                            else:
                                row_cells.append(val)
                    if any(row_cells):
                        rows.append("\t".join(row_cells))
            return "\n".join(rows)
    except Exception as e:
        return f"Error extracting XLSX: {e}"


def fetch_text_from_google_url(url: str) -> str:
    """Extract text/CSV from a Google Docs or Google Sheets shareable URL."""
    clean_url = url.strip()
    if "docs.google.com/spreadsheets" in clean_url:
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", clean_url)
        if match:
            doc_id = match.group(1)
            export_url = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
            try:
                resp = httpx.get(export_url, follow_redirects=True, timeout=10.0)
                if resp.status_code == 200 and resp.text:
                    return resp.text
            except Exception:
                pass
    elif "docs.google.com/document" in clean_url:
        match = re.search(r"/document/d/([a-zA-Z0-9-_]+)", clean_url)
        if match:
            doc_id = match.group(1)
            export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
            try:
                resp = httpx.get(export_url, follow_redirects=True, timeout=10.0)
                if resp.status_code == 200 and resp.text:
                    return resp.text
            except Exception:
                pass

    try:
        resp = httpx.get(clean_url, follow_redirects=True, timeout=10.0)
        return resp.text[:15000]
    except Exception as e:
        return f"Unable to fetch URL {clean_url}: {e}"


def parse_work_items_with_gemini(raw_text: str, default_product_name: str = "") -> List[Dict[str, Any]]:
    """Uses Gemini 2.5 Flash to intelligently interpret and structure work items from
    unstructured or semi-structured notes, spreadsheets, or tables.
    """
    if not raw_text or not raw_text.strip():
        return []

    current_date = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")

    prompt = f"""You are the Quickplay Action Tracker intelligence agent.
Today's Date: {current_date}
Default Product: {default_product_name or 'Current Product'}

Your job is to read and interpret the input text below (which may be copied from Google Sheets, Google Docs, meeting notes, project plans, JIRA lists, or CSV tables) and extract every distinct action item or work item.

For each item:
- Identify the clear title.
- Synthesize an informative description capturing context, blockers, or deliverables.
- Lifecycle Status: must be one of ['ideation', 'in progress', 'in review', 'QA', 'deploying to staging', 'deploying to production', 'closing', 'closed', 'blocked']. If unclear, default to 'in progress' or 'ideation'.
- Priority: one of ['low', 'medium', 'high', 'critical']. Default: 'medium'.
- Assignee: internal engineer, manager, or email if noted. Default: 'unassigned'.
- Target Delivery Date: estimate in 'YYYY-MM-DD' format if mentioned (e.g. 'Nov 15' becomes '{current_date[:4]}-11-15'). If omitted, leave null.
- Space / Category: one of ['identity-space', 'analytics-space', 'cdn-space', 'playback-space', 'streaming-space', 'linear-space', 'general'].
- Milestones / Nodes: extract any milestone stages, substeps, or checklist items. For each milestone:
  - title (e.g. 'Architecture Design', 'Staging Deploy', 'QA Signoff')
  - status: one of ['in progress', 'in review', 'QA', 'deploying to staging', 'closed']
  - target_date: 'YYYY-MM-DD' or null
- Attachments / References: extract any referenced URLs, ticket codes (e.g., Jira JIRA-1234, PR links, Docs/Sheets links).

Return ONLY a JSON array of objects with the exact schema:
[
  {{
    "title": "string",
    "description": "string",
    "status": "string",
    "priority": "string",
    "assignee": "string",
    "delivery_date": "YYYY-MM-DD or null",
    "space_id": "string",
    "nodes": [
      {{
        "title": "string",
        "status": "string",
        "target_date": "YYYY-MM-DD or null"
      }}
    ],
    "attachments": [
      {{
        "link_type": "jira | doc | sheet | link",
        "label": "string",
        "url": "string"
      }}
    ]
  }}
]

Input Content:
\"\"\"
{raw_text[:30000]}
\"\"\"
"""

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=dict(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        content_text = response.text.strip()
        items = json.loads(content_text)
        if not isinstance(items, list):
            items = [items]
        return items
    except Exception as e:
        print(f"Gemini interpretation error: {e}. Falling back to basic CSV parsing.")
        return fallback_csv_parse(raw_text)


def fallback_csv_parse(raw_text: str) -> List[Dict[str, Any]]:
    """Fallback simple parser if Gemini is unavailable or text is basic CSV."""
    results = []
    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    for line in lines:
        parts = [p.strip() for p in line.split(",") if p.strip()]
        if not parts or parts[0].lower() in ["title", "item", "name", "action item"]:
            continue
        title = parts[0]
        status = parts[1] if len(parts) > 1 else "ideation"
        priority = parts[2] if len(parts) > 2 else "medium"
        assignee = parts[3] if len(parts) > 3 else "unassigned"
        results.append({
            "title": title,
            "description": "Imported from batch text",
            "status": status,
            "priority": priority,
            "assignee": assignee,
            "delivery_date": None,
            "space_id": "general",
            "nodes": [],
            "attachments": []
        })
    return results


def persist_imported_items(
    items: List[Dict[str, Any]],
    org_id: str,
    product_id: str,
    product_name: str,
    creator_email: str,
    db_client,
    collection_name: str = "action_items",
) -> List[Dict[str, Any]]:
    """Persists a list of interpreted items into Firestore with full audit records."""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    saved_items = []

    for it in items:
        item_id = f"ACT-IMP-{uuid.uuid4().hex[:5].upper()}"
        status = it.get("status") or "ideation"
        if status not in [
            "ideation", "in progress", "in review", "QA",
            "deploying to staging", "deploying to production",
            "closing", "closed", "blocked"
        ]:
            status = "in progress"

        # Format nodes
        formatted_nodes = []
        for idx, n in enumerate(it.get("nodes", [])):
            formatted_nodes.append({
                "node_id": f"node-{idx+1}",
                "title": n.get("title", f"Milestone {idx+1}"),
                "status": n.get("status") or "in progress",
                "target_date": n.get("target_date"),
                "assignee": n.get("assignee") or it.get("assignee") or "unassigned",
            })

        # Format attachments
        formatted_attachments = []
        for att in it.get("attachments", []):
            formatted_attachments.append({
                "link_type": att.get("link_type", "link"),
                "label": att.get("label", "Reference"),
                "url": att.get("url", "#"),
            })

        record = {
            "item_id": item_id,
            "org_id": org_id,
            "product_id": product_id,
            "product_name": product_name,
            "title": it.get("title", "Untitled Imported Item"),
            "description": it.get("description", "Imported work item"),
            "status": status,
            "priority": it.get("priority", "medium"),
            "assignee": it.get("assignee", "unassigned"),
            "delivery_date": it.get("delivery_date") or (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=14)).strftime("%Y-%m-%d"),
            "created_at": now,
            "closed_at": now if status == "closed" else None,
            "space_id": it.get("space_id", "general"),
            "nodes": formatted_nodes,
            "attachments": formatted_attachments,
            "history": [
                {
                    "timestamp": now,
                    "updated_by": creator_email,
                    "field": "batch_import",
                    "old_value": "",
                    "new_value": status,
                    "note": f"Intelligently parsed and imported via Agent Import Concierge",
                }
            ],
        }

        db_client.collection(collection_name).document(item_id).set(record)
        saved_items.append(record)

    return saved_items
