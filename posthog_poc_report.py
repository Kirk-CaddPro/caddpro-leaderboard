
import requests
import datetime
import json
from collections import defaultdict
import os

# ===========================================
# CONFIG
# ===========================================

# ✅ API key now comes from environment variable (NOT stored in code)
POSTHOG_API_KEY = os.getenv("POSTHOG_API_KEY")

PROJECT_ID = "430329"
POSTHOG_URL = "https://us.i.posthog.com"

# ✅ Use real current time (production-ready)
TODAY = datetime.datetime.now(datetime.timezone.utc)

DAY_START = TODAY - datetime.timedelta(days=1)
WEEK_START = TODAY - datetime.timedelta(days=7)
MONTH_START = TODAY - datetime.timedelta(days=30)

# ===========================================
# FETCH EVENTS
# ===========================================

def fetch_events():
    url = f"{POSTHOG_URL}/api/projects/{PROJECT_ID}/events/"
    headers = {"Authorization": f"Bearer {POSTHOG_API_KEY}"}

    all_events = []
    next_url = f"{url}?limit=1000"

    while next_url:
        response = requests.get(next_url, headers=headers)
        data = response.json()

        events = data.get("results", [])
        all_events.extend(events)

        next_url = data.get("next")

    return all_events

# ===========================================
# PROCESS DATA
# ===========================================

def process(events):

    usage_daily = defaultdict(int)
    usage_weekly = defaultdict(int)
    usage_monthly = defaultdict(int)

    user_tools = defaultdict(set)
    user_days = defaultdict(set)
    user_org = {}

    for e in events:

        email = e.get("distinct_id")
        props = e.get("properties", {})
        org = props.get("organisation")

        timestamp = datetime.datetime.fromisoformat(
            e.get("timestamp").replace("Z", "+00:00")
        )

        if not org:
            continue

        user_org[email] = org

        if timestamp >= DAY_START:
            usage_daily[email] += 1

        if timestamp >= WEEK_START:
            usage_weekly[email] += 1

        if timestamp >= MONTH_START:
            usage_monthly[email] += 1

            app = props.get("application_name")
            if app:
                user_tools[email].add(app)

            user_days[email].add(timestamp.date())

    def build_ranks(usage_dict):

        org_ranks = defaultdict(list)

        for email, count in usage_dict.items():
            org = user_org.get(email)
            if org:
                org_ranks[org].append((email, count))

        for org in org_ranks:
            org_ranks[org].sort(key=lambda x: x[1], reverse=True)

        return org_ranks

    daily_ranks = build_ranks(usage_daily)
    weekly_ranks = build_ranks(usage_weekly)
    monthly_ranks = build_ranks(usage_monthly)

    output = []

    for email in user_org:

        org = user_org[email]

        def get_rank(ranking):
