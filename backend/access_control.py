"""
Classifier / Router  ->  Condition / Branch ('check the user access')

Classifier/Router inspects the retrieved documents and determines which
department(s) own that knowledge. Condition/Branch then checks the
requesting user's role against each retrieved document's access_roles
list. This mirrors the RBAC slide in the deck (Source Access Policies)
and the two orange/red nodes in the workflow screenshots.

IMPORTANT: "no documents were retrieved at all" (the question simply
isn't covered by anything in the knowledge base) is NOT the same thing
as "documents were retrieved but this user isn't allowed to see them".
The former should tell the user their question isn't covered; only the
latter should escalate to Human Handoff. Conflating the two causes every
off-topic question to look like an access violation.
"""
import json
import os

_USERS_PATH = os.path.join(os.path.dirname(__file__), "data", "users.json")
with open(_USERS_PATH, "r", encoding="utf-8") as f:
    USERS = json.load(f)


def classify(retrieved_docs):
    """Classifier / Router: label the request by the departments it touches."""
    departments = sorted({d["department"] for d in retrieved_docs})
    return departments or ["unclassified"]


ALL_STAFF_TAG = "all-staff"


def check_access(user_id: str, retrieved_docs):
    """
    Condition / Branch: 'check the user access'.
    Returns (branch, allowed_docs, denied_docs, user) where branch is one of:
      - 'not_found'    : nothing relevant was retrieved at all (not an
                          access problem — the knowledge base simply
                          doesn't have anything matching the question).
      - 'unauthorized' : relevant documents exist, but none of them are
                          visible to this user's role.
      - 'authorized'   : at least one relevant, permitted document exists.

    A document tagged with the special "all-staff" role is visible to any
    authenticated user regardless of their specific role — it's a wildcard,
    not a literal role name (no user actually has the role "all-staff").
    """
    user = USERS.get(user_id, {"name": "Unknown User", "role": "guest"})
    role = user["role"]

    if not retrieved_docs:
        return "not_found", [], [], user

    allowed, denied = [], []
    for doc in retrieved_docs:
        if role in doc["access_roles"] or ALL_STAFF_TAG in doc["access_roles"]:
            allowed.append(doc)
        else:
            denied.append(doc)

    branch = "authorized" if allowed else "unauthorized"
    return branch, allowed, denied, user
