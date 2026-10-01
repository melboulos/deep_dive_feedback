import json

d = data

mode = d.get("mode", "")

# ─────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────

def _normalize_grade(raw_value):
    """Normalize one raw SFDC ICP Grade value → (icp_status, icp_grade).

    Rules (from Step 3b of the agent prompt):
    - coerce to string, strip, lowercase → v
    - if v is exactly one of a/b/c/d (single letter, no extras) → icp, uppercase grade
    - anything else (non-target, variants, null, empty, multi-letter, unknown) → non_target, null
    """
    if raw_value is None:
        return ("non_target", None)
    try:
        v = str(raw_value).strip().lower()
    except Exception:
        return ("non_target", None)
    if v in ("a", "b", "c", "d"):
        return ("icp", v.upper())
    return ("non_target", None)


def _is_valid_grade_candidate(sampled_values):
    """A candidate matches if its normalized value set contains at least one
    single-letter grade in {a, b, c, d}."""
    if not isinstance(sampled_values, list):
        return False
    normalized = set()
    for v in sampled_values:
        if v is None:
            continue
        try:
            s = str(v).strip().lower()
            if s:
                normalized.add(s)
        except Exception:
            continue
    return bool(normalized & {"a", "b", "c", "d"})


def _has_non_target_marker(sampled_values):
    """Does the sampled value set contain a value starting with 'non-target'?"""
    if not isinstance(sampled_values, list):
        return False
    for v in sampled_values:
        if v is None:
            continue
        try:
            s = str(v).strip().lower()
            if s.startswith("non-target"):
                return True
        except Exception:
            continue
    return False


def _contains_icp_grade_label(candidate):
    """Does the candidate's field_name or display_name contain 'icp grade'
    (case-insensitive)?"""
    name = (candidate.get("field_name") or "").lower()
    display = (candidate.get("display_name") or "").lower()
    return ("icp grade" in name) or ("icp grade" in display)


# ─────────────────────────────────────────────────────────────────────
# Mode: discover — pick the best ICP Grade field from candidates
# ─────────────────────────────────────────────────────────────────────
# Expected `data`:
#   {
#     "mode": "discover",
#     "candidates": [
#       {"field_name": "icp_grade_text", "display_name": "ICP Grade",
#        "sampled_values": ["A", "B", "C", "D", "Non-Target"]},
#       ...
#     ]
#   }
#
# Output JSON:
#   {"icp_field_discovered": true, "icp_field_name": "icp_grade_text"}
# OR
#   {"icp_field_discovered": false, "icp_field_name": null}

def _run_discover():
    candidates = d.get("candidates", []) or []
    if not isinstance(candidates, list):
        return {"icp_field_discovered": False, "icp_field_name": None}

    # Keep only candidates whose sampled values contain at least one A/B/C/D grade
    valid = []
    for c in candidates:
        if not isinstance(c, dict):
            continue
        if _is_valid_grade_candidate(c.get("sampled_values", [])):
            valid.append(c)

    if not valid:
        return {"icp_field_discovered": False, "icp_field_name": None}

    # Preference 1: field name or display name literally contains "icp grade"
    for c in valid:
        if _contains_icp_grade_label(c):
            return {
                "icp_field_discovered": True,
                "icp_field_name": c.get("field_name"),
            }

    # Preference 2: value set contains BOTH A/B/C/D grades AND a non-target marker
    for c in valid:
        if _has_non_target_marker(c.get("sampled_values", [])):
            return {
                "icp_field_discovered": True,
                "icp_field_name": c.get("field_name"),
            }

    # Preference 3: any remaining valid candidate
    return {
        "icp_field_discovered": True,
        "icp_field_name": valid[0].get("field_name"),
    }


# ─────────────────────────────────────────────────────────────────────
# Mode: normalize — map each account's raw grade to icp_status/icp_grade
# ─────────────────────────────────────────────────────────────────────
# Expected `data`:
#   {
#     "mode": "normalize",
#     "icp_field_discovered": true,
#     "accounts": [
#       {"account_id": "...", "raw_grade": "A"},
#       {"account_id": "...", "raw_grade": "Non-Target - Not Enough Info"},
#       {"account_id": "...", "raw_grade": null},
#       ...
#     ]
#   }
#
# Output JSON:
#   {"accounts": [
#     {"account_id": "...", "icp_status": "icp", "icp_grade": "A"},
#     {"account_id": "...", "icp_status": "non_target", "icp_grade": null},
#     ...
#   ]}
#
# If icp_field_discovered is false, every account becomes non_target/null,
# regardless of raw_grade.

def _run_normalize():
    icp_field_discovered = bool(d.get("icp_field_discovered", False))
    accounts = d.get("accounts", []) or []
    if not isinstance(accounts, list):
        return {"accounts": []}

    out = []
    for a in accounts:
        if not isinstance(a, dict):
            continue
        account_id = a.get("account_id")
        if not icp_field_discovered:
            out.append({
                "account_id": account_id,
                "icp_status": "non_target",
                "icp_grade": None,
            })
            continue
        status, grade = _normalize_grade(a.get("raw_grade"))
        out.append({
            "account_id": account_id,
            "icp_status": status,
            "icp_grade": grade,
        })

    return {"accounts": out}


# ─────────────────────────────────────────────────────────────────────
# Dispatch
# ─────────────────────────────────────────────────────────────────────

try:
    if mode == "discover":
        result = _run_discover()
    elif mode == "normalize":
        result = _run_normalize()
    else:
        result = {"error": f"unknown mode: {mode!r}; expected 'discover' or 'normalize'"}
    print(json.dumps(result))
except Exception as e:
    print(json.dumps({"error": f"icp_helper exception: {type(e).__name__}: {e}"}))
