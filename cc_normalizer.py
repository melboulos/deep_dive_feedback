import json

d = data

support_by_rep_raw = d.get("support_by_rep", {}) or {}
user_email = d.get("user_email", "") or ""

cc_list = []

try:
    # Rule 1: lowercase user email
    user_email_lc = user_email.strip().lower()

    if not user_email_lc:
        print(json.dumps([]))
    else:
        # Rule 2: coerce support_by_rep to dict, lowercase its keys
        if not isinstance(support_by_rep_raw, dict):
            lowered = {}
        else:
            lowered = {}
            for k, v in support_by_rep_raw.items():
                if isinstance(k, str):
                    lowered[k.strip().lower()] = v

        # Rule 3: lookup user_email_lc; if missing, no CC
        raw_value = lowered.get(user_email_lc)

        if raw_value is None:
            cc_list = []
        else:
            # Rule 4: coerce mapped value
            if isinstance(raw_value, str):
                candidates = [raw_value]
            elif isinstance(raw_value, list):
                candidates = raw_value
            else:
                candidates = []

            # Rule 5: filter to strings with "@" and "." after "@"
            filtered = []
            for item in candidates:
                if not isinstance(item, str):
                    continue
                s = item.strip()
                if "@" not in s:
                    continue
                at_idx = s.index("@")
                if "." not in s[at_idx + 1:]:
                    continue
                filtered.append(s)

            # Rule 6: lowercase every remaining address
            lowered_list = [a.lower() for a in filtered]

            # Rule 7: remove user_email_lc (no self-CC)
            no_self = [a for a in lowered_list if a != user_email_lc]

            # Rule 8: deduplicate while preserving order
            seen = set()
            deduped = []
            for a in no_self:
                if a not in seen:
                    seen.add(a)
                    deduped.append(a)

            cc_list = deduped

        # Final output: JSON list of CC addresses (empty list if none)
        print(json.dumps(cc_list))

except Exception:
    # Rules 9 + 10: any exception -> empty CC, never raise
    print(json.dumps([]))
