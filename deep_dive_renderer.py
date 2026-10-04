import html as _html

d = data

# minimal_layout: opt-in for lean payloads (Deep Dive v2). When absent/false,
# output is unchanged. When true, each card section renders only if its data
# is present, so fields can be added back one at a time.
MIN = bool(d.get("minimal_layout"))

def has(sig, key):
    return (not MIN) or bool(sig.get(key))

NAVY = "#0d2b3f"; DEEP = "#1e4d6b"; TEAL = "#2e8b9e"; AQUA = "#4fb8c9"
BG1 = "#e6f2f5"; BG2 = "#c7e4ec"; BG3 = "#a9d4e0"
WARM = "#2f9e6a"; AMBER = "#e08a3c"; WATCH = "#3a7bb8"
TEXT = "#0d2b3f"; TEXT2 = "#436577"; MUTED = "#6f8898"; BLACK = "#000000"
BORDER = "#d5e2ea"; HOVER_BG = "#f3fafc"; CALLOUT_BG = "#f3fafc"
LINKEDIN_BLUE = "#0a66c2"
TEST_BG = "#FEF3C7"; TEST_FG = "#78350F"
SCOPED_BG = "#EDE9FE"; SCOPED_FG = "#5B21B6"
ATTR_GRAY = "#8a9aa8"
ICP_BG = "#FEE2E2"; ICP_FG = "#B91C1C"; ICP_ACCENT = "#DC2626"
NONTARGET_BG = "#F3F4F6"; NONTARGET_FG = "#4B5563"

LINKEDIN_SVG_DATA_URI = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' width='14' height='14'>"
    "<path fill='%230a66c2' d='M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.852 3.37-1.852 3.601 0 4.267 2.37 4.267 5.455v6.288zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.063 2.063 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z'/>"
    "</svg>"
)

STATUS_COLOR = {"warm": WARM, "net_new": AMBER, "watch": WATCH}
STATUS_LIGHT = {"warm": "#e8f5ee", "net_new": "#faeddd", "watch": "#e4eef8"}
PATH_COLOR = {"sfdc": WARM, "gmail": WATCH, "cold": AMBER}
PATH_LIGHT = {"sfdc": "#e8f5ee", "gmail": "#e4eef8", "cold": "#faeddd"}
REL_COLOR = {"direct": WARM, "internal": AMBER, "new": MUTED}
REL_LIGHT = {"direct": "#e8f5ee", "internal": "#faeddd", "new": "#eef2f4"}
REL_EMOJI = {"direct": "🟢", "internal": "🟡", "new": "⚪"}
CONF_COLOR = {"High": WARM, "Medium": AMBER, "Low": WATCH}
CONF_LIGHT = {"High": "#e8f5ee", "Medium": "#faeddd", "Low": "#e4eef8"}

def esc(s): return _html.escape(str(s or ""), quote=True)

def test_banner():
    if not d.get("is_test_run"): return ""
    return (
        f'<div style="font-size:12px;color:{TEST_FG};background:{TEST_BG};'
        f'padding:10px 14px;border-radius:8px;margin-top:20px;">'
        f'Test run — this report was manually triggered outside the scheduled 7 AM ET digest.'
        f'</div>'
    )

def scoped_banner():
    if not d.get("scoped_test_run"): return ""
    domains = d.get("scoped_test_domains", []) or []
    domains_str = ", ".join(domains) if domains else "(none matched)"
    return (
        f'<div style="font-size:12px;color:{SCOPED_FG};background:{SCOPED_BG};'
        f'padding:10px 14px;border-radius:8px;margin-top:12px;font-weight:600;">'
        f'⚠️ Scoped validation run — account universe filtered to test_account_domains: {esc(domains_str)}. '
        f'Not a normal Deep Dive; the "top 3–5" cap is not enforced.'
        f'</div>'
    )

def icp_field_warning_banner():
    if d.get("empty"): return ""
    if d.get("icp_field_discovered", True): return ""
    return (
        f'<div style="font-size:12px;color:{AMBER};background:#fef4e9;'
        f'padding:10px 14px;border-radius:8px;margin-top:12px;font-weight:600;'
        f'border-left:3px solid {AMBER};">'
        f'⚠️ ICP Grade field not discovered in Salesforce — every account defaulted to Non-Target for this run. '
        f'The agent expects a company field (typically named "ICP Grade") whose values are letter grades A, B, C, or D for ICP accounts. '
        f"Confirm the field exists and is exposed in Rox's RQL surface, then Deep Dive will auto-discover it on the next run."
        f'</div>'
    )

def suppression_note():
    if d.get("empty"): return ""
    fb = d.get("suppressed_by_feedback", 0)
    nm = d.get("suppressed_no_material_change", 0)
    un = d.get("suppressed_uncertain", 0)
    if fb == 0 and nm == 0 and un == 0: return ""
    parts = []
    if fb: parts.append(f"{fb} previously acted on")
    if nm: parts.append(f"{nm} unchanged since last publish")
    if un: parts.append(f"{un} awaiting stronger evidence")
    inner = " · ".join(parts)
    return (
        f'<div style="font-size:11px;color:{MUTED};margin-top:10px;line-height:1.5;font-style:italic;">'
        f'🔁&nbsp;&nbsp;Suppressed {inner}. Deep Dive researches every run and only publishes what is materially new.'
        f'</div>'
    )

def attribution_lines():
    run_line = (
        f'<div style="font-size:11px;color:{ATTR_GRAY};margin-top:12px;line-height:1.5;">'
        f'🤿 Deep Dive · Run {esc(d.get("generated_at",""))}'
        + ("" if MIN and not (d.get("config_version") or d.get("design_spec_version")) else
           f' · config_version={esc(d.get("config_version",""))}'
           f' · design_spec_version={esc(d.get("design_spec_version",""))}')
        + f'</div>'
    )
    feedback_line = (
        f'<div style="font-size:11px;color:{ATTR_GRAY};margin-top:4px;line-height:1.5;">'
        f'Questions or feedback? '
        f'<a href="mailto:mel@couchbase.com" style="color:{ATTR_GRAY};text-decoration:underline;">mel@couchbase.com</a>'
        f'</div>'
    )
    return run_line + feedback_line

def button(action, label, sig):
    from urllib.parse import urlencode
    params = {
        "action": action, "signal_id": sig.get("signal_id",""),
        "account_id": sig.get("account_id",""), "account_name": sig.get("account_name",""),
        "motion_type": sig.get("motion_label",""), "score": sig.get("score",""),
        "primary_contact_email": sig.get("primary_contact_email","") or "",
        "primary_contact_name": sig.get("primary_contact_name","") or "",
        "user_email": d.get("target_rep_email",""), "user_id": d.get("target_rep_id",""),
        "workflow_run_id": d.get("workflow_run_id",""),
    }
    params = {k:v for k,v in params.items() if v not in (None,"")}
    href = d.get("feedback_url","") + "?" + urlencode(params)
    return (
        f'<a href="{esc(href)}" target="_blank" '
        f'style="display:inline-block;height:36px;line-height:36px;padding:0 18px;'
        f'border:1px solid {BORDER};border-radius:999px;box-sizing:border-box;'
        f'background:#ffffff;color:{TEXT};font-size:13px;font-weight:600;'
        f'letter-spacing:0.02em;text-decoration:none;text-align:center;vertical-align:middle;'
        f"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;"
        f'margin:0 6px 6px 0;">{label}</a>'
    )

def contact_pill(c):
    p = c.get("path","cold")
    color = PATH_COLOR.get(p, AMBER); light = PATH_LIGHT.get(p, "#faeddd")
    return (
        f'<span style="display:inline-block;padding:4px 12px;border-radius:999px;'
        f'background:{light};color:{color};font-size:11px;font-weight:600;'
        f'letter-spacing:0.04em;line-height:1.4;vertical-align:middle;">'
        f'{esc(c.get("path_label",""))}</span>'
    )

def contact_name_html(c):
    name = esc(c.get("name",""))
    url = c.get("linkedin_url") or ""
    if url and (url.startswith("http://") or url.startswith("https://")):
        return (
            f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer" '
            f'style="font-weight:700;color:{LINKEDIN_BLUE};text-decoration:underline;'
            f'text-decoration-thickness:1px;text-underline-offset:2px;">{name}</a>'
            f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer" '
            f'style="display:inline-block;vertical-align:middle;margin-left:6px;'
            f'text-decoration:none;line-height:0;">'
            f'<img src="{LINKEDIN_SVG_DATA_URI}" width="14" height="14" '
            f'alt="LinkedIn" style="display:inline-block;vertical-align:middle;border:0;"></a>'
        )
    return f'<span style="font-weight:700;color:{BLACK};">{name}</span>'

def contact_line(c):
    return (
        f'<li style="margin:8px 0;color:{BLACK};font-size:14px;line-height:1.5;">'
        f'{contact_name_html(c)}'
        f' — {esc(c.get("title",""))} &nbsp;{contact_pill(c)}</li>'
    )

def relationship_chip(sig):
    st = sig.get("relationship_state")
    label = sig.get("relationship_label","")
    if not st or not label: return ""
    color = REL_COLOR.get(st, MUTED); light = REL_LIGHT.get(st, "#eef2f4")
    emoji = REL_EMOJI.get(st, "⚪")
    return (
        f'<div style="margin-top:8px;">'
        f'<span style="display:inline-block;padding:5px 12px;'
        f'background:{light};color:{color};border-radius:999px;font-size:11px;'
        f'font-weight:700;letter-spacing:0.06em;text-transform:uppercase;'
        f'line-height:1.4;vertical-align:middle;">'
        f'{emoji}&nbsp;&nbsp;Relationship · {esc(label)}</span></div>'
    )

def confidence_chip(sig):
    lvl = sig.get("hypothesis_confidence","")
    if lvl not in CONF_COLOR: return ""
    color = CONF_COLOR[lvl]; light = CONF_LIGHT[lvl]
    return (
        f'<span style="display:inline-block;margin-left:10px;padding:3px 10px;'
        f'background:{light};color:{color};border-radius:999px;font-size:10px;'
        f'font-weight:700;letter-spacing:0.06em;text-transform:uppercase;'
        f'line-height:1.4;vertical-align:middle;">Confidence · {esc(lvl)}</span>'
    )

def material_update_chip(sig):
    if not sig.get("is_material_update"): return ""
    return (
        f'<span style="display:inline-block;margin-left:8px;padding:3px 10px;'
        f'background:#e8f5ee;color:{WARM};border-radius:999px;font-size:10px;'
        f'font-weight:700;letter-spacing:0.06em;text-transform:uppercase;'
        f'line-height:1.4;vertical-align:middle;">🔄&nbsp;&nbsp;Update</span>'
    )

def icp_badge(sig):
    icp = sig.get("icp_status", "non_target")
    grade = sig.get("icp_grade") or ""
    if icp == "icp":
        grade_suffix = f'&nbsp;·&nbsp;{esc(grade.upper())}' if grade else ""
        return (
            f'<div style="display:inline-block;padding:5px 14px;'
            f'background:{ICP_BG};color:{ICP_FG};border-radius:999px;'
            f'font-size:11px;font-weight:800;letter-spacing:0.1em;'
            f'text-transform:uppercase;line-height:1.4;'
            f'margin-bottom:10px;border:1px solid {ICP_FG};">'
            f'🔥&nbsp;&nbsp;ICP{grade_suffix}</div>'
        )
    return (
        f'<div style="display:inline-block;padding:5px 14px;'
        f'background:{NONTARGET_BG};color:{NONTARGET_FG};border-radius:999px;'
        f'font-size:11px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;line-height:1.4;'
        f'margin-bottom:10px;">'
        f'⚪&nbsp;&nbsp;Non-Target</div>'
    )

def section_header(kind, count):
    plural = "s" if count != 1 else ""
    if kind == "icp":
        return (
            f'<div style="margin:32px 0 16px 0;padding:20px 26px;'
            f'background:{ICP_BG};color:{ICP_FG};border-radius:14px;'
            f'font-weight:800;font-size:17px;letter-spacing:0.03em;'
            f'border-left:5px solid {ICP_ACCENT};">'
            f'🔥&nbsp;&nbsp;ICP Accounts — Priority · {count} account{plural}</div>'
        )
    return (
        f'<div style="margin:32px 0 16px 0;padding:20px 26px;'
        f'background:{NONTARGET_BG};color:{NONTARGET_FG};border-radius:14px;'
        f'font-weight:800;font-size:17px;letter-spacing:0.03em;'
        f'border-left:5px solid {NONTARGET_FG};">'
        f'⚪&nbsp;&nbsp;Non-Target Accounts · {count} account{plural}</div>'
    )

def bullets(items):
    if not items: return ""
    lis = "".join(f'<li style="margin:5px 0;color:{BLACK};font-size:14px;line-height:1.55;">{esc(x)}</li>' for x in items)
    return f'<ul style="padding-left:20px;margin:6px 0 0 0;">{lis}</ul>'

def numbered(items):
    if not items: return ""
    lis = "".join(f'<li style="margin:5px 0;color:{BLACK};font-size:14px;line-height:1.55;">{esc(x)}</li>' for x in items)
    return f'<ol style="padding-left:22px;margin:6px 0 0 0;">{lis}</ol>'

def render_card(sig):
    st = sig.get("status","net_new")
    st_color = STATUS_COLOR.get(st, AMBER); st_light = STATUS_LIGHT.get(st, "#faeddd")
    if MIN and not sig.get("status"):
        st_color = TEAL
    status_label = sig.get("status_label","") or ("New signal" if MIN else "")
    score_html = ""
    if has(sig, "score"):
        score_html = f'<span style="display:inline-block;background:rgba(255,255,255,0.22);padding:4px 12px;border-radius:999px;letter-spacing:0.04em;font-weight:700;">SCORE {sig.get("score","")}</span>'
    parent_line = ""
    if sig.get("account_parent"):
        parent_line = (f'<div style="color:{MUTED};font-size:14px;margin-top:2px;">'
                       f'subsidiary of {esc(sig["account_parent"])}</div>')
    if sig.get("watch_target_roles"):
        contacts_html = (
            f'<div style="color:{BLACK};font-size:14px;padding:10px 14px;'
            f'background:{st_light};border-radius:8px;">'
            f'🔍&nbsp;No specific contact identified yet — target roles: '
            f'{esc(sig["watch_target_roles"])}</div>'
        )
    else:
        contacts_html = ('<ul style="list-style:none;padding:0;margin:8px 0 0 0;">'
                        + "".join(contact_line(c) for c in sig.get("contacts",[])) + '</ul>')
    buttons_html = (
        button("pursue", "🎯&nbsp;&nbsp;Pursue", sig)
        + button("watch", "👀&nbsp;&nbsp;Watch", sig)
        + button("wrong", "❌&nbsp;&nbsp;Wrong", sig)
        + button("already_working", "Already Working", sig)
    )

    conf_rat = sig.get("hypothesis_confidence_rationale","")
    conf_rat_html = ""
    if conf_rat:
        conf_rat_html = (f'<div style="font-size:12px;color:{MUTED};margin-top:6px;'
                         f'line-height:1.5;font-style:italic;">{esc(conf_rat)}</div>')

    cap_primary_html = esc(sig.get("capability_primary","") or "—")
    cap_secondary = sig.get("capability_secondary") or ""
    cap_secondary_html = ""
    if cap_secondary:
        cap_secondary_html = (
            f'<div style="font-size:14px;line-height:1.55;color:{TEXT2};margin-top:4px;">'
            f'<strong style="color:{DEEP};">Secondary:</strong> {esc(cap_secondary)}</div>'
        )

    fork = sig.get("next_discovery_fork") or ""
    fork_html = ""
    if fork:
        fork_html = (
            f'<div style="margin-top:18px;">'
            f'<div style="font-size:12px;font-weight:700;letter-spacing:0.08em;'
            f'text-transform:uppercase;color:{TEAL};margin-bottom:6px;">🌿&nbsp;&nbsp;Next Discovery Fork</div>'
            f'<div style="font-size:14px;line-height:1.55;color:{BLACK};">{esc(fork)}</div>'
            f'</div>'
        )

    material_rat = sig.get("material_change_rationale") or ""
    material_rat_html = ""
    if sig.get("is_material_update") and material_rat:
        material_rat_html = (
            f'<div style="margin-top:6px;font-size:12px;color:{WARM};line-height:1.5;font-weight:600;">'
            f'What is new vs. the last time you saw this: {esc(material_rat)}'
            f'</div>'
        )

    reasoning_html = f'''
    <div style="margin-top:18px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:6px;">🧪&nbsp;&nbsp;Internal Couchbase Hypothesis{confidence_chip(sig)}</div>
      <div style="font-size:15px;line-height:1.6;color:{BLACK};font-weight:500;">{esc(sig.get("internal_couchbase_hypothesis",""))}</div>
      {conf_rat_html}
    </div>
    <div style="margin-top:18px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:6px;">🔗&nbsp;&nbsp;Why Couchbase Could Be Relevant</div>
      <div style="font-size:15px;line-height:1.6;color:{BLACK};font-weight:500;">{esc(sig.get("why_couchbase_could_be_relevant",""))}</div>
    </div>
    <div style="margin-top:18px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:6px;">🧰&nbsp;&nbsp;Relevant Couchbase Capability</div>
      <div style="font-size:15px;line-height:1.55;color:{BLACK};"><strong style="color:{DEEP};">Primary:</strong> {cap_primary_html}</div>
      {cap_secondary_html}
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;margin-top:18px;">
      <tr>
        <td valign="top" style="width:50%;padding-right:10px;">
          <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
               text-transform:uppercase;color:{WARM};margin-bottom:6px;">✅&nbsp;&nbsp;What Would Have to Be True</div>
          {bullets(sig.get("what_would_have_to_be_true", []))}
        </td>
        <td valign="top" style="width:50%;padding-left:10px;">
          <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
               text-transform:uppercase;color:{AMBER};margin-bottom:6px;">🚫&nbsp;&nbsp;What Would Disqualify</div>
          {bullets(sig.get("what_would_disqualify", []))}
        </td>
      </tr>
    </table>
    <div style="margin:18px 0 0 0;padding:16px 20px;background:{CALLOUT_BG};
         border-left:3px solid {TEAL};border-radius:6px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:8px;">❓&nbsp;&nbsp;Customer Discovery Question</div>
      <div style="font-size:17px;line-height:1.5;color:{BLACK};font-weight:600;">{esc(sig.get("customer_discovery_question",""))}</div>
    </div>
    <div style="margin-top:18px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:6px;">🎓&nbsp;&nbsp;Internal Discovery Questions (rep prep)</div>
      {numbered(sig.get("internal_discovery_questions", []))}
    </div>
    {fork_html}
    '''


    motion_html = (f'''    <div style="display:inline-block;margin-top:12px;padding:6px 14px;
         background:{HOVER_BG};color:{DEEP};border-radius:999px;font-size:12px;
         font-weight:600;letter-spacing:0.04em;line-height:1.4;vertical-align:middle;">
      {sig.get("motion_emoji","")}&nbsp;&nbsp;{esc(sig.get("motion_label",""))}
    </div>
''') if has(sig, "motion_label") else ""
    what_changed = sig.get("what_changed_html","")
    if MIN and not what_changed:
        what_changed = esc(sig.get("summary",""))
    source_html = ""
    if MIN and sig.get("source_url"):
        _u = str(sig.get("source_url") or "")
        if _u.startswith("http://") or _u.startswith("https://"):
            _d = sig.get("published_date") or ""
            source_html = (
                f'<div style="margin-top:12px;font-size:13px;color:{MUTED};line-height:1.5;">'
                f'Source: <a href="{esc(_u)}" target="_blank" rel="noopener noreferrer" '
                f'style="color:{DEEP};text-decoration:underline;">{esc(sig.get("source_name") or _u)}</a>'
                + (f' &nbsp;·&nbsp; {esc(_d)}' if _d else '') + '</div>')
    where_html = (f'''    <div style="margin-top:18px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:6px;">🎯&nbsp;&nbsp;Where to Go</div>
      <div style="font-size:15px;line-height:1.55;color:{BLACK};font-weight:600;">
        {esc(sig.get("where_to_go",""))}
      </div>
    </div>
''') if has(sig, "where_to_go") else ""
    who_html = (f'''    <div style="margin-top:18px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:6px;">👤&nbsp;&nbsp;Who to Talk To</div>
      {contacts_html}
    </div>
''') if (not MIN or sig.get("contacts") or sig.get("watch_target_roles")) else ""
    action_html = (f'''    <div style="margin-top:18px;padding:14px 18px;background:#fef4e9;
         border-left:3px solid {AMBER};border-radius:6px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{AMBER};margin-bottom:6px;">⚓&nbsp;&nbsp;Recommended Action</div>
      <div style="font-size:15px;line-height:1.55;color:{BLACK};">{esc(sig.get("recommended_action",""))}</div>
    </div>
''') if has(sig, "recommended_action") else ""
    survived_html = (f'''    <div style="margin-top:18px;padding-top:14px;border-top:1px dashed {BORDER};">
      <div style="font-size:11px;font-weight:600;color:{MUTED};line-height:1.5;">
        🧭&nbsp;&nbsp;{esc(sig.get("why_survived",""))}
      </div>
    </div>
''') if has(sig, "why_survived") else ""
    buttons_block = (f'''    <div style="margin-top:18px;">
      {buttons_html}
    </div>
''') if (not MIN or d.get("feedback_url")) else ""
    return f'''
<div style="background:#ffffff;border-radius:16px;overflow:hidden;
     box-shadow:0 4px 16px rgba(13,43,63,0.08);margin-bottom:24px;">
  <div style="background:{st_color};color:#ffffff;padding:10px 24px;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;">
      <tr>
        <td style="font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#ffffff;">
          {esc(status_label)}{material_update_chip(sig)}
        </td>
        <td align="right" style="font-size:11px;color:#ffffff;">
          {score_html}
        </td>
      </tr>
    </table>
  </div>
  <div style="padding:24px;">
    {icp_badge(sig) if has(sig, "icp_status") else ""}
    <div style="font-size:22px;font-weight:700;color:{BLACK};letter-spacing:-0.01em;">
      {esc(sig.get("account_name",""))}
    </div>
    {parent_line}
{motion_html}    {relationship_chip(sig)}
    <div style="margin:16px 0;padding:14px 18px;background:{CALLOUT_BG};
         border-left:3px solid {AQUA};border-radius:6px;font-size:18px;
         font-weight:600;color:{BLACK};line-height:1.4;">
      {esc(sig.get("motion_sentence") or (sig.get("headline") if MIN else ""))}
    </div>
    {material_rat_html}
    <div style="margin-top:18px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:6px;">🌊&nbsp;&nbsp;What Changed</div>
      <div style="font-size:15px;line-height:1.6;color:{BLACK};font-weight:500;">{what_changed}</div>
    </div>
    <div style="margin-top:18px;">
      <div style="font-size:12px;font-weight:700;letter-spacing:0.08em;
           text-transform:uppercase;color:{TEAL};margin-bottom:6px;">💡&nbsp;&nbsp;Why It Matters</div>
      <div style="font-size:15px;line-height:1.6;color:{BLACK};font-weight:500;">{esc(sig.get("why_it_matters",""))}</div>
    </div>
    {reasoning_html if has(sig, "internal_couchbase_hypothesis") else ""}{source_html}
{where_html}{who_html}{action_html}{survived_html}{buttons_block}  </div>
</div>'''.strip()

def status_chip(key, label, count):
    color = STATUS_COLOR[key]; light = STATUS_LIGHT[key]
    return (
        f'<span style="display:inline-block;padding:7px 14px;'
        f'border-radius:999px;background:{light};color:{color};font-size:13px;'
        f'font-weight:700;letter-spacing:0.04em;margin:4px 6px 4px 0;'
        f'line-height:1.3;vertical-align:middle;">'
        f'{label}&nbsp;&nbsp;·&nbsp;&nbsp;{count}</span>'
    )

def motion_chip(m):
    return (
        f'<span style="display:inline-block;padding:6px 12px;'
        f'border-radius:999px;background:{HOVER_BG};color:{DEEP};font-size:12px;'
        f'font-weight:600;letter-spacing:0.03em;margin:4px 6px 4px 0;'
        f'line-height:1.3;vertical-align:middle;">'
        f'{m.get("emoji","")}&nbsp;&nbsp;{esc(m.get("label",""))}&nbsp;&nbsp;×&nbsp;{m.get("count",0)}</span>'
    )

def icp_priority_callout():
    if d.get("empty"): return ""
    icp_n = d.get("icp_count", 0)
    non_n = d.get("non_target_count", 0)
    if icp_n == 0 and non_n == 0: return ""
    return (
        f'<div style="background:#ffffff;border-radius:16px;padding:18px 24px;margin-top:16px;'
        f'box-shadow:0 4px 16px rgba(13,43,63,0.06);border-left:5px solid {ICP_ACCENT};">'
        f'<div style="font-size:11px;font-weight:700;letter-spacing:0.1em;'
        f'text-transform:uppercase;color:{MUTED};margin-bottom:8px;">'
        f'🎯&nbsp;&nbsp;Rep Priority</div>'
        f'<div style="font-size:20px;font-weight:800;color:{BLACK};line-height:1.4;">'
        f'<span style="color:{ICP_FG};">🔥&nbsp;&nbsp;{icp_n} ICP</span>'
        f'&nbsp;&nbsp;·&nbsp;&nbsp;'
        f'<span style="color:{NONTARGET_FG};">⚪&nbsp;&nbsp;{non_n} Non-Target</span>'
        f'</div>'
        f'<div style="font-size:12px;color:{MUTED};margin-top:6px;">ICP accounts appear first.</div>'
        f'{suppression_note()}'
        f'</div>'
    )

def cards_with_section_headers():
    current_group = None
    parts = []
    for s in d.get("signals", []):
        icp = s.get("icp_status", "non_target")
        if MIN and not s.get("icp_status"):
            parts.append(render_card(s))
            continue
        if icp != current_group:
            count = d.get("icp_count", 0) if icp == "icp" else d.get("non_target_count", 0)
            parts.append(section_header(icp, count))
            current_group = icp
        parts.append(render_card(s))
    return "".join(parts)

if d.get("empty"):
    body = f'''
<div style="max-width:640px;margin:80px auto;padding:40px;background:#ffffff;
     border-radius:16px;box-shadow:0 4px 24px rgba(13,43,63,0.1);text-align:center;">
  <div style="font-size:64px;line-height:1;margin-bottom:16px;">🌊</div>
  <div style="font-size:24px;font-weight:700;color:{BLACK};margin-bottom:8px;">Calm waters today.</div>
  <div style="font-size:15px;color:{TEXT2};line-height:1.55;">
    No signals cleared the Deep Dive gates for {esc(d.get("target_rep_name",""))}'s book.
    That's a legitimate outcome — Deep Dive doesn't pad the report to hit a count.
  </div>
  <div style="font-size:14px;color:{MUTED};margin-top:16px;">{"See you at the next scheduled run." if MIN else "See you tomorrow morning."}</div>
  {scoped_banner()}
  {test_banner()}
  {attribution_lines()}
</div>'''
else:
    _sc = d.get("status_counts") or {}
    status_chips = "".join([
        status_chip("warm","🟢 Warm path", _sc.get("warm",0)),
        status_chip("net_new","🟠 Net-new", _sc.get("net_new",0)),
        status_chip("watch","🔵 Watch", _sc.get("watch",0)),
    ])
    motion_chips = "".join(motion_chip(m) for m in d.get("motion_chips",[]))
    cards = cards_with_section_headers()
    disclaimer = ""
    if d.get("gmail_disclaimer"):
        disclaimer = (f'<div style="font-size:12px;color:{MUTED};margin-top:8px;">'
                     f'{esc(d["gmail_disclaimer"])}</div>')
    haul_html = (f'''  <div style="background:#ffffff;border-radius:16px;padding:24px;margin-top:20px;
       box-shadow:0 4px 16px rgba(13,43,63,0.06);">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;">
      <tr>
        <td valign="top" style="padding-right:20px;width:120px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{MUTED};">
            🌊&nbsp;&nbsp;The Haul
          </div>
          <div style="font-size:36px;font-weight:800;color:{BLACK};line-height:1.1;">
            {d.get("haul_count",0)}
          </div>
        </td>
        <td valign="top" style="padding-right:20px;">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{MUTED};margin-bottom:6px;">Status</div>
          {status_chips}
        </td>
        <td valign="top">
          <div style="font-size:11px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{MUTED};margin-bottom:6px;">Motion Types</div>
          {motion_chips}
        </td>
      </tr>
    </table>
  </div>
''') if (not MIN or d.get("status_counts")) else ""
    body = f'''
<div style="max-width:880px;margin:0 auto;padding:24px;">
  <div style="background:linear-gradient(135deg,{NAVY} 0%,{DEEP} 55%,{TEAL} 100%);
       background-color:{DEEP};
       border-radius:20px;padding:36px 32px 44px 32px;color:#ffffff;
       box-shadow:0 8px 32px rgba(13,43,63,0.25);">
    <div style="font-size:56px;line-height:1;margin-bottom:12px;">🤿</div>
    <div style="font-size:30px;font-weight:700;letter-spacing:-0.02em;line-height:1.15;color:#ffffff;">
      Today's Deep Dive — {esc(d.get("target_rep_name",""))}
    </div>
    <div style="font-size:16px;color:#c7e4ec;margin-top:8px;font-weight:500;">
      {esc(d.get("date_line",""))}
    </div>
    <div style="font-size:14px;color:{AQUA};margin-top:16px;font-style:italic;">
      Deep Dive finds new business inside logos we already own.
    </div>
  </div>
  {scoped_banner()}
  {icp_priority_callout()}
  {icp_field_warning_banner()}
{haul_html}  <div style="margin-top:12px;">
    {cards}
  </div>
  <div style="margin-top:32px;padding:20px 24px;border-top:2px solid {BORDER};color:{MUTED};font-size:12px;line-height:1.6;text-align:center;">
    <div style="font-size:14px;color:{TEXT2};margin-bottom:6px;">
      🌊 Quality over quantity. If nothing meets the bar, this report will be short — or empty — by design.
    </div>
    <div>{"Sources: Rox insights · Web research" if MIN else "Sources: Salesforce · Rox insights · Web research · Gmail"}</div>
    {disclaimer}
    <div style="margin-top:8px;">Generated {esc(d.get("generated_at",""))}</div>
    {test_banner()}
    {attribution_lines()}
  </div>
</div>'''

html_doc = f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Today's Deep Dive — {esc(d.get("target_rep_name",""))}</title></head>
<body style="margin:0;padding:0;background:{BG2};background-image:linear-gradient(180deg,{BG1} 0%,{BG2} 50%,{BG3} 100%);
     min-height:100vh;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
     color:{TEXT};">
{body}
</body></html>'''

print(html_doc)
