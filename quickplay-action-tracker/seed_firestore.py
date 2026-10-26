import datetime
from google.cloud import firestore

FIRESTORE_PROJECT = "qwiklabs-gcp-04-ddbf4b181b7a"
COLLECTION_NAME = "action_items"

def seed():
    db = firestore.Client(project=FIRESTORE_PROJECT)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    yesterday = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).isoformat()
    two_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).isoformat()
    
    sample_items = [
        # --- Acme Corp: Video Streaming Platform (prod-acme-streaming) ---
        {
            "item_id": "ACT-101",
            "org_id": "customer-acme",
            "product_id": "prod-acme-streaming",
            "product_name": "Video Streaming Platform",
            "title": "SSO & SAML Authentication Integration",
            "description": "Enterprise Okta and Google Workspace SSO integration for customer streaming portal.",
            "status": "in progress",
            "priority": "high",
            "assignee": "alex@quickplay.com",
            "delivery_date": "2026-11-05",
            "created_at": yesterday,
            "closed_at": None,
            "space_id": "identity-space",
            "nodes": [
                {
                    "node_id": "node-1",
                    "title": "SAML metadata exchange",
                    "status": "closed",
                    "assignee": "alex@quickplay.com",
                    "target_date": "2026-10-25",
                    "completed_at": yesterday
                },
                {
                    "node_id": "node-2",
                    "title": "OAuth2 / OIDC token verification callback",
                    "status": "in progress",
                    "assignee": "alex@quickplay.com",
                    "target_date": "2026-11-01",
                    "completed_at": None
                },
                {
                    "node_id": "node-3",
                    "title": "End-to-end staging validation",
                    "status": "deploying to staging",
                    "assignee": "sarah@quickplay.com",
                    "target_date": "2026-11-04",
                    "completed_at": None
                }
            ],
            "attachments": [
                {
                    "link_type": "jira",
                    "url": "https://quickplay.atlassian.net/browse/QP-402",
                    "label": "Jira QP-402"
                },
                {
                    "link_type": "doc",
                    "url": "https://docs.google.com/document/d/1sso-spec-qp-acme",
                    "label": "SSO Technical Architecture Spec"
                }
            ],
            "history": [
                {
                    "timestamp": yesterday,
                    "updated_by": "alex@quickplay.com",
                    "field": "status",
                    "old_value": "ideation",
                    "new_value": "in progress",
                    "note": "Kicked off authentication implementation."
                }
            ]
        },
        {
            "item_id": "ACT-103",
            "org_id": "customer-acme",
            "product_id": "prod-acme-streaming",
            "product_name": "Video Streaming Platform",
            "title": "Cloud CDN Edge Caching Rule Tuning",
            "description": "Optimize cache hit ratio for low-latency live HLS/DASH manifest requests.",
            "status": "closed",
            "priority": "medium",
            "assignee": "morgan@quickplay.com",
            "delivery_date": "2026-10-25",
            "created_at": yesterday,
            "closed_at": now,
            "space_id": "cdn-space",
            "nodes": [
                {
                    "node_id": "node-1",
                    "title": "TTL optimization rules",
                    "status": "closed",
                    "assignee": "morgan@quickplay.com",
                    "target_date": "2026-10-22",
                    "completed_at": yesterday
                },
                {
                    "node_id": "node-2",
                    "title": "Production rollout verification",
                    "status": "closed",
                    "assignee": "morgan@quickplay.com",
                    "target_date": "2026-10-25",
                    "completed_at": now
                }
            ],
            "attachments": [
                {
                    "link_type": "jira",
                    "url": "https://quickplay.atlassian.net/browse/QP-389",
                    "label": "Jira QP-389"
                }
            ],
            "history": [
                {
                    "timestamp": now,
                    "updated_by": "morgan@quickplay.com",
                    "field": "status",
                    "old_value": "deploying to production",
                    "new_value": "closed",
                    "note": "Verified 98.4% cache hit ratio in prod. Marking completed."
                }
            ]
        },

        # --- Acme Corp: Cloud DVR & Storage (prod-acme-dvr) ---
        {
            "item_id": "ACT-102",
            "org_id": "customer-acme",
            "product_id": "prod-acme-dvr",
            "product_name": "Cloud DVR & Storage",
            "title": "Real-time Video Analytics & DVR Ingestion Pipeline",
            "description": "Stream QoS and QoE analytics ingestion pipeline for Cloud DVR recordings.",
            "status": "QA",
            "priority": "critical",
            "assignee": "jordan@quickplay.com",
            "delivery_date": "2026-11-12",
            "created_at": yesterday,
            "closed_at": None,
            "space_id": "analytics-space",
            "nodes": [
                {
                    "node_id": "node-1",
                    "title": "Kafka stream consumers",
                    "status": "closed",
                    "assignee": "jordan@quickplay.com",
                    "target_date": "2026-10-24",
                    "completed_at": yesterday
                },
                {
                    "node_id": "node-2",
                    "title": "Aggregation rules & alerts",
                    "status": "QA",
                    "assignee": "taylor@quickplay.com",
                    "target_date": "2026-11-08",
                    "completed_at": None
                }
            ],
            "attachments": [
                {
                    "link_type": "sheet",
                    "url": "https://docs.google.com/spreadsheets/d/1kpi-qos-metrics",
                    "label": "QoS Metric Schema Sheet"
                }
            ],
            "history": [
                {
                    "timestamp": now,
                    "updated_by": "taylor@quickplay.com",
                    "field": "status",
                    "old_value": "in review",
                    "new_value": "QA",
                    "note": "Passed staging unit tests, moving to QA stress testing."
                }
            ]
        },
        {
            "item_id": "ACT-104",
            "org_id": "customer-acme",
            "product_id": "prod-acme-dvr",
            "product_name": "Cloud DVR & Storage",
            "title": "DVR Storage Lifecycle Auto-Purge Policy",
            "description": "Configure 90-day retention policies with tiering to Cloud Storage Archive.",
            "status": "in review",
            "priority": "medium",
            "assignee": "sarah@quickplay.com",
            "delivery_date": "2026-11-18",
            "created_at": two_days_ago,
            "closed_at": None,
            "space_id": "storage-space",
            "nodes": [
                {
                    "node_id": "node-1",
                    "title": "Retention rule specification",
                    "status": "closed",
                    "assignee": "sarah@quickplay.com",
                    "target_date": "2026-10-24",
                    "completed_at": yesterday
                },
                {
                    "node_id": "node-2",
                    "title": "Dry-run simulation on sandbox buckets",
                    "status": "in review",
                    "assignee": "sarah@quickplay.com",
                    "target_date": "2026-11-02",
                    "completed_at": None
                }
            ],
            "attachments": [
                {
                    "link_type": "jira",
                    "url": "https://quickplay.atlassian.net/browse/QP-415",
                    "label": "Jira QP-415"
                }
            ],
            "history": [
                {
                    "timestamp": yesterday,
                    "updated_by": "sarah@quickplay.com",
                    "field": "status",
                    "old_value": "in progress",
                    "new_value": "in review",
                    "note": "Sandbox simulation results submitted for review."
                }
            ]
        },

        # --- Globex Media: OTT Multi-Screen App (prod-globex-ott) ---
        {
            "item_id": "ACT-201",
            "org_id": "customer-globex",
            "product_id": "prod-globex-ott",
            "product_name": "OTT Multi-Screen App",
            "title": "Apple TV & Roku 4K HDR Profile Activation",
            "description": "HEVC and Dolby Vision playback profiling for big screen devices.",
            "status": "in progress",
            "priority": "critical",
            "assignee": "alex@quickplay.com",
            "delivery_date": "2026-11-20",
            "created_at": yesterday,
            "closed_at": None,
            "space_id": "playback-space",
            "nodes": [
                {
                    "node_id": "node-1",
                    "title": "Apple TV AVPlayer HDR test harness",
                    "status": "closed",
                    "assignee": "alex@quickplay.com",
                    "target_date": "2026-10-25",
                    "completed_at": yesterday
                },
                {
                    "node_id": "node-2",
                    "title": "Roku SceneGraph bitrate stepping test",
                    "status": "in progress",
                    "assignee": "alex@quickplay.com",
                    "target_date": "2026-11-06",
                    "completed_at": None
                }
            ],
            "attachments": [
                {
                    "link_type": "jira",
                    "url": "https://quickplay.atlassian.net/browse/GLX-102",
                    "label": "Jira GLX-102"
                },
                {
                    "link_type": "doc",
                    "url": "https://docs.google.com/document/d/1globex-profile-matrix",
                    "label": "Globex Encoding Matrix Doc"
                }
            ],
            "history": [
                {
                    "timestamp": yesterday,
                    "updated_by": "alex@quickplay.com",
                    "field": "status",
                    "old_value": "ideation",
                    "new_value": "in progress",
                    "note": "Profiles provisioned in transcoding cluster."
                }
            ]
        },
        {
            "item_id": "ACT-202",
            "org_id": "customer-globex",
            "product_id": "prod-globex-ott",
            "product_name": "OTT Multi-Screen App",
            "title": "Low Latency HLS (LL-HLS) Segmenter Rollout",
            "description": "Sub-2-second broadcast glass-to-glass latency implementation.",
            "status": "deploying to staging",
            "priority": "high",
            "assignee": "jordan@quickplay.com",
            "delivery_date": "2026-11-10",
            "created_at": yesterday,
            "closed_at": None,
            "space_id": "streaming-space",
            "nodes": [
                {
                    "node_id": "node-1",
                    "title": "Chunked transfer encoding benchmark",
                    "status": "closed",
                    "assignee": "jordan@quickplay.com",
                    "target_date": "2026-10-23",
                    "completed_at": yesterday
                },
                {
                    "node_id": "node-2",
                    "title": "Deploy staging origin packagers",
                    "status": "deploying to staging",
                    "assignee": "jordan@quickplay.com",
                    "target_date": "2026-10-29",
                    "completed_at": None
                }
            ],
            "attachments": [
                {
                    "link_type": "jira",
                    "url": "https://quickplay.atlassian.net/browse/GLX-88",
                    "label": "Jira GLX-88"
                }
            ],
            "history": [
                {
                    "timestamp": now,
                    "updated_by": "jordan@quickplay.com",
                    "field": "status",
                    "old_value": "QA",
                    "new_value": "deploying to staging",
                    "note": "Staging packagers initiated."
                }
            ]
        },

        # --- Initech Broadcasting: Linear Playout (prod-initech-linear) ---
        {
            "item_id": "ACT-301",
            "org_id": "customer-initech",
            "product_id": "prod-initech-linear",
            "product_name": "Linear 24/7 Playout",
            "title": "Dynamic SCTE-35 Ad Marker Splicing",
            "description": "Server-side ad insertion (SSAI) cue marker synchronization with linear master feed.",
            "status": "in progress",
            "priority": "critical",
            "assignee": "taylor@quickplay.com",
            "delivery_date": "2026-11-15",
            "created_at": yesterday,
            "closed_at": None,
            "space_id": "linear-space",
            "nodes": [
                {
                    "node_id": "node-1",
                    "title": "SCTE-35 payload validator",
                    "status": "closed",
                    "assignee": "taylor@quickplay.com",
                    "target_date": "2026-10-24",
                    "completed_at": yesterday
                },
                {
                    "node_id": "node-2",
                    "title": "Ad decision server (ADS) integration",
                    "status": "in progress",
                    "assignee": "taylor@quickplay.com",
                    "target_date": "2026-11-05",
                    "completed_at": None
                }
            ],
            "attachments": [
                {
                    "link_type": "jira",
                    "url": "https://quickplay.atlassian.net/browse/INI-50",
                    "label": "Jira INI-50"
                }
            ],
            "history": [
                {
                    "timestamp": yesterday,
                    "updated_by": "taylor@quickplay.com",
                    "field": "status",
                    "old_value": "ideation",
                    "new_value": "in progress",
                    "note": "Integration started with Initech ADS endpoint."
                }
            ]
        }
    ]

    for item in sample_items:
        db.collection(COLLECTION_NAME).document(item["item_id"]).set(item)
        print(f"Seeded document: {item['item_id']} [{item['org_id']}|{item['product_id']}] - {item['title']}")

    print("Firestore multi-company/multi-product seeding completed successfully.")

if __name__ == "__main__":
    seed()
