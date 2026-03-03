# Copyright (c) 2025, Mania and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CallHistoryLog(Document):

	def after_insert(self):
		"""After a call log is saved, find a matching Lead and add a comment activity."""
		try:
			lead_name = self._find_matching_lead()
			if lead_name:
				self._add_lead_comment(lead_name)
		except Exception:
			# Never let this block the main insert — just log and move on
			frappe.log_error(frappe.get_traceback(), "Callyzer: Failed to link Call History Log to Lead")

	def _find_matching_lead(self):
		"""
		Look up a Lead whose mobile_no matches client_number.
		Callyzer strips the leading zero, so we try both:
		  - exact match:     712345678  (as stored in Callyzer)
		  - with leading 0:  0712345678 (as stored in the Lead)
		Returns the Lead name (docname) or None.
		"""
		client_number = self.client_number
		if not client_number:
			return None

		candidates = [client_number, "0" + client_number]

		for number in candidates:
			lead = frappe.db.get_value("Lead", {"mobile_no": number}, "name")
			if lead:
				return lead

		return None

	def _add_lead_comment(self, lead_name):
		"""Add a Comment (timeline activity) on the Lead."""
		employee = self.employee_name or self.employee or "Unknown Employee"
		call_type = self.call_type or "Call"
		call_date = frappe.utils.formatdate(self.call_date) if self.call_date else ""
		call_time = self.call_time or ""
		duration_sec = self.duration or 0

		# Format duration as mm:ss
		minutes, seconds = divmod(int(duration_sec), 60)
		duration_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

		note_text = self.note or ""
		remarks_line = f"<br><b>Remarks:</b> {note_text}" if note_text else ""

		content = (
			f"<b>{employee}</b> made a <b>{call_type}</b> call to the client"
			f" on <b>{call_date}</b> at <b>{call_time}</b>"
			f" (Duration: {duration_str})."
			f"{remarks_line}"
		)

		comment = frappe.get_doc({
			"doctype": "Comment",
			"comment_type": "Comment",
			"reference_doctype": "Lead",
			"reference_name": lead_name,
			"content": content,
		})
		comment.insert(ignore_permissions=True)
