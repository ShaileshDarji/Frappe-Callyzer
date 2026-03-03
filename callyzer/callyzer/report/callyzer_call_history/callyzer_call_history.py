import frappe

def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	conditions = "1=1"
	params = {}

	if filters.get("company"):
		conditions += " AND company = %(company)s"
		params["company"] = filters["company"]

	if filters.get("from_date"):
		conditions += " AND call_date >= %(from_date)s"
		params["from_date"] = filters["from_date"]

	if filters.get("to_date"):
		conditions += " AND call_date <= %(to_date)s"
		params["to_date"] = filters["to_date"]

	if filters.get("employee"):
		conditions += " AND employee_name = %(employee)s"
		params["employee"] = filters["employee"]

	data = frappe.db.sql(f"""
		SELECT
			employee_name,
			employee_number,
			client_name,
			client_number,
			call_type,
			duration,
			call_date,
			call_time,
			call_recording_url,
			note,
			crm_status,
			company
		FROM `tabCall History Log`
		WHERE {conditions}
		ORDER BY call_date DESC, call_time DESC
	""", params, as_dict=True)

	return columns, data

def get_columns():
	return [
		{"label": "Employee", "fieldname": "employee_name", "fieldtype": "Data", "width": 140},
		{"label": "Emp Number", "fieldname": "employee_number", "fieldtype": "Data", "width": 120},
		{"label": "Client", "fieldname": "client_name", "fieldtype": "Data", "width": 140},
		{"label": "Client Number", "fieldname": "client_number", "fieldtype": "Data", "width": 130},
		{"label": "Call Type", "fieldname": "call_type", "fieldtype": "Data", "width": 100},
		{"label": "Duration (sec)", "fieldname": "duration", "fieldtype": "Int", "width": 100},
		{"label": "Call Date", "fieldname": "call_date", "fieldtype": "Date", "width": 110},
		# Set as 'Data' to avoid timedelta summing error
		{"label": "Call Time", "fieldname": "call_time", "fieldtype": "Data", "width": 100},
		{"label": "Recording", "fieldname": "call_recording_url", "fieldtype": "Data", "width": 200},
		{"label": "Note", "fieldname": "note", "fieldtype": "Data", "width": 180},
		{"label": "CRM Status", "fieldname": "crm_status", "fieldtype": "Data", "width": 120},
		{"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 130},
	]
