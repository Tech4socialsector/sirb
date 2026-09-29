# Copyright (c) 2026, Ram and contributors
# For license information, please see license.txt
"""Completeness rules for an IRB Project proposal, in one place.

Frappe only enforces `reqd` on the server; `mandatory_depends_on` is a
Desk-browser-only rule, so the ~34 conditional questions (consent text,
risks, data confidentiality, animal protocols …) were never enforced
when a student submitted from the portal. This module evaluates the
DocType's own `depends_on` / `mandatory_depends_on` expressions on the
server so the rules stay defined in the DocType JSON, and returns every
problem at once with where to find it — instead of one cryptic message
per submit attempt.
"""

import re

import frappe
from frappe.utils import cstr, strip_html

PLACEHOLDER = "-- Select --"
HUMAN_DOMAINS = ("Humans", "BOTH Humans AND Non Humans")
NON_HUMAN_DOMAINS = ("Non Human Species", "BOTH Humans AND Non Humans")

# Questions the old validate() insisted on that have no mandatory_depends_on
# in the DocType. Values are the domains they apply to (None = always).
EXTRA_REQUIRED = {
	"project_domain": None,
	"will_data_be_gathered_through_digital_means": HUMAN_DOMAINS,
	"research_type": NON_HUMAN_DOMAINS,
	"i_hereby_confirm_the_above": None,
}

# Tabs the portal/Desk only show for some domains (see isTabVisible in
# the frontend's useProjectSchema).
TAB_DOMAINS = {
	"human_ethics_questionnaire_tab": HUMAN_DOMAINS,
	"animal_ethics_questionnaire_tab": NON_HUMAN_DOMAINS,
}

_INCLUDES = re.compile(r"(\[[^\[\]]*\])\s*\.includes\(\s*doc\.(\w+)\s*\)")
_DOC_ATTR = re.compile(r"\bdoc\.(\w+)")
_HAS_ROLE = re.compile(r"frappe\.user\.has_role\(")


def _to_python(expr):
	"""Translate the small JS subset used by IRB Project's eval: rules
	(`[..].includes(doc.x)`, `doc.x == 'y'`, `&&`, `||`, has_role) into a
	Python expression. Anything else is rejected rather than guessed."""
	e = expr.strip()
	if e.startswith("eval:"):
		e = e[5:].strip()
	e = _INCLUDES.sub(lambda m: f"(_get('{m.group(2)}') in {m.group(1)})", e)
	e = _DOC_ATTR.sub(lambda m: f"_get('{m.group(1)}')", e)
	e = _HAS_ROLE.sub("_has_role(", e)
	e = e.replace("===", "==").replace("!==", "!=").replace("&&", " and ").replace("||", " or ")
	if re.search(r"[;{}]|=>|\bnew\b|\bfunction\b", e):
		raise ValueError(f"Unsupported depends_on expression: {expr}")
	return e


def _evaluate(expr, doc, roles, cache):
	if not expr:
		return True
	if expr not in cache:
		cache[expr] = compile(_to_python(expr), "<depends_on>", "eval")
	scope = {
		"__builtins__": {},
		"_get": lambda f: doc.get(f),
		"_has_role": lambda r: r in roles,
	}
	return bool(eval(cache[expr], scope))  # noqa: S307 — DocType-authored expression, sandboxed scope


def _is_blank(df, value):
	if df.fieldtype == "Check":
		return not value
	text = cstr(value).strip()
	return not text or text == PLACEHOLDER or not strip_html(text).strip()


def _layout(meta):
	"""fieldname -> (tab_fieldname, tab_label, section_label, section_depends_on)."""
	out = {}
	tab = ("basic_details_tab", "Basic details")
	section = (None, None)
	for df in meta.fields:
		if df.fieldtype == "Tab Break":
			tab = (df.fieldname, df.label or df.fieldname)
			section = (None, None)
		elif df.fieldtype == "Section Break":
			section = (df.label, df.depends_on)
		else:
			out[df.fieldname] = (tab[0], tab[1], section[0], section[1])
	return out


def _question_label(df):
	label = strip_html(cstr(df.label)).strip()
	label = re.sub(r"\s+", " ", label)
	return label if len(label) <= 140 else label[:137].rstrip() + "…"


def get_proposal_issues(doc):
	"""Every unanswered question the student must fill before submitting,
	in form order. Each item: fieldname, tab, tab_label, section,
	question, kind ("choose" | "confirm" | "write"), message."""
	meta = frappe.get_meta("IRB Project")
	layout = _layout(meta)
	roles = set(frappe.get_roles())
	cache = {}
	domain = doc.get("project_domain")
	issues = []

	for df in meta.fields:
		if df.fieldtype in ("Tab Break", "Section Break", "Column Break", "HTML", "Button", "Table"):
			continue

		if df.fieldname in EXTRA_REQUIRED:
			domains = EXTRA_REQUIRED[df.fieldname]
			required = domains is None or domain in domains
		elif df.reqd:
			required = True
		elif df.mandatory_depends_on:
			try:
				required = _evaluate(df.mandatory_depends_on, doc, roles, cache)
			except Exception:
				frappe.log_error(title="IRB proposal check: bad mandatory_depends_on", message=df.mandatory_depends_on)
				required = False
		else:
			continue
		if not required:
			continue

		tab_name, tab_label, section_label, section_depends_on = layout.get(df.fieldname, (None, None, None, None))
		# Desk only enforces a mandatory field while it's on screen, so do the same.
		if tab_name in TAB_DOMAINS and domain not in TAB_DOMAINS[tab_name]:
			continue
		try:
			visible = _evaluate(df.depends_on, doc, roles, cache) and _evaluate(section_depends_on, doc, roles, cache)
		except Exception:
			visible = True
		if not visible or not _is_blank(df, doc.get(df.fieldname)):
			continue

		if df.fieldtype == "Check":
			kind, message = "confirm", "Tick this box to confirm."
		elif df.fieldtype in ("Select", "Link"):
			kind, message = "choose", "Choose an answer."
		else:
			kind, message = "write", "Write your answer."
		if df.fieldname == "i_hereby_confirm_the_above":
			section_label = section_label or "Student declaration"
			message = "Read the IRB policy and student declaration, then tick “I hereby confirm the above”."
		elif df.fieldname == "project_domain":
			message = "Choose who or what your research involves. This decides which questionnaire you need to fill."

		issues.append(
			{
				"fieldname": df.fieldname,
				"tab": tab_name,
				"tab_label": tab_label,
				"section": strip_html(cstr(section_label)).strip() or None,
				"question": _question_label(df),
				"kind": kind,
				"message": message,
			}
		)
	return issues


def format_issues(issues, limit=8):
	"""One readable sentence for Desk / API callers (the portal renders the
	structured list instead)."""
	parts = []
	for i in issues[:limit]:
		where = i["section"] or i["question"]
		parts.append(f"{where} ({i['tab_label']})")
	more = f"; and {len(issues) - limit} more" if len(issues) > limit else ""
	noun = "item" if len(issues) == 1 else "items"
	return f"Your proposal is not complete yet. Please answer these {len(issues)} {noun} before submitting: " + "; ".join(parts) + more + "."
