import frappe
import requests
import json
import calendar
from callyzer.callyzer.utils import get_callyzer_settings, normalize_payload, get_employees, format_time_timestamp_, get_endpoint, update_last_fetched_time
from callyzer.api.fetch_employee import parse_datetime, process_employee
from frappe import _
from frappe.utils import getdate
import time

#Tested working
@frappe.whitelist()
def fetch_summary_report():
	end_point_name = "Summary Report"
	endpoint, call_from, call_to = get_endpoint(end_point_name) 
	settings = get_callyzer_settings()
	employee_ids = get_employees()
	
	for setting in settings:
		company = setting["company"]
		url = setting['domain_api']+endpoint
		token = setting["api_key"]
		payload = {
			"call_from": int(call_from),
			"call_to": int(call_to),
			"call_types": ["Missed", "Rejected", "Incoming", "Outgoing"],
			"emp_numbers": employee_ids,
			# "duration_les_than": 200,
			"emp_tags": [],
			"is_exclude_numbers": True
		}
		
		update_last_fetched_time(end_point_name)
		results = post_api(url, token, payload)
		
		process_total_summary_calls(results, company)
		
	return results

#Tested working
@frappe.whitelist()
def process_total_summary_calls(result, company):
	
	doc = frappe.new_doc("Callyzer Total Summary")
	doc.total_incoming_calls = result.get("total_incoming_calls", 0)
	doc.total_incoming_duration = result.get("total_incoming_duration", 0)
	doc.total_outgoing_calls = result.get("total_outgoing_calls", 0)
	doc.total_outgoing_duration = result.get("total_outgoing_duration", 0)
	doc.total_missed_calls = result.get("total_missed_calls", 0)
	doc.total_rejected_calls = result.get("total_rejected_calls", 0)
	doc.total_calls = result.get("total_calls", 0)
	doc.total_duration = result.get("total_duration", 0)
	doc.total_never_attended_calls = result.get("total_never_attended_calls", 0)
	doc.total_not_pickup_by_clients_calls = result.get("total_not_pickup_by_clients_calls", 0)
	doc.total_unique_clients = result.get("total_unique_clients", 0)
	doc.total_working_hours = result.get("total_working_hours", "00:00:00")
	doc.total_connected_calls = result.get("total_connected_calls", 0)
	doc.company = company
	doc.insert(ignore_permissions=True)
	return doc.name
   
#Tested working
def process_call_logs(employee_name, call_logs, company):
	"""Create new call logs for the employee and return the number created."""
	count = 0
	for call in call_logs:
		if frappe.db.exists("Callyzer Call Log", {"external_id": call["id"]}):
			continue

		doc = frappe.new_doc("Callyzer Call Log")
		doc.employee = employee_name
		doc.call_log_id = call["id"]
		doc.client_name = call["client_name"]
		doc.client_country_code = call["client_country_code"]
		doc.client_no = call["client_number"]
		doc.duration = call["duration"]
		doc.call_type = call["call_type"]
		call_date = call["call_date"]
		doc.call_date = getdate(call_date)
		doc.call_time = call["call_time"]
		doc.note = json.dumps(call.get("note", ""))
		doc.call_recording_url = call["call_recording_url"]
		doc.crm_status = call.get("crm_status")
		doc.reminder_date = call.get("reminder_date")
		doc.reminder_time = call.get("reminder_time")
		doc.synced_at = parse_datetime(call.get("synced_at"))
		doc.modified_at = parse_datetime(call.get("modified_at"))
		doc.company = company

		doc.insert(ignore_permissions=True)
		count += 1

	return count


#Tested working
@frappe.whitelist()
def fetch_employee_summary_report():
	end_point_name = "Employee Summary"
	endpoint, call_from, call_to = get_endpoint(end_point_name)
	employee_ids = get_employees()

	settings = get_callyzer_settings()
	
	for setting in settings:
		company = setting["company"]
		
		url = setting['domain_api'].rstrip('/') + endpoint
		token = setting["api_key"]
		payload = {
			"call_from": int(call_from),
			"call_to": int(call_to),
			"call_types": ["Missed", "Rejected", "Incoming", "Outgoing"],
			"emp_numbers": employee_ids,
			"emp_tags": [],
			"is_exclude_numbers": True
		}
		update_last_fetched_time(end_point_name)
		result = post_api(url, token, payload)
		handle_employee_summary_response(result, company)
		
	return {"status": "success", "message": "Employee summary report fetched successfully"}

#Tested working
def handle_employee_summary_response(result, company):
	count = 0
	for emp in result:
		if not frappe.db.exists("Callyzer Employee", {"employee_no": emp.get("emp_number")}):
			process_employee(emp)

		doc = frappe.new_doc("Callyzer Employee Summary")
		doc.employee_name = emp.get("emp_name")
		doc.employee_code = emp.get("emp_code")
		doc.emp_country_code = emp.get("emp_country_code")
		doc.employee = emp.get("emp_number")
		doc.emp_tags = ", ".join(emp.get("emp_tags", []))
		doc.total_incoming_calls = emp.get("total_incoming_calls")
		doc.total_outgoing_calls = emp.get("total_outgoing_calls")
		doc.total_missed_calls = emp.get("total_missed_calls")
		doc.total_rejected_calls = emp.get("total_rejected_calls")
		doc.total_calls = emp.get("total_calls")
		doc.total_duration = emp.get("total_duration")
		doc.total_connected_calls = emp.get("total_connected_calls")
		doc.total_never_attended_calls = emp.get("total_never_attended_calls")
		doc.total_not_pickup_by_clients_calls = emp.get("total_not_pickup_by_clients_calls")
		doc.total_unique_clients = emp.get("total_unique_clients")
		doc.total_working_hours = emp.get("total_working_hours")
		doc.avg_duration_per_call = emp.get("avg_duration_per_call")
		doc.avg_incoming_duration = emp.get("avg_incoming_duration")
		doc.avg_outgoing_duration = emp.get("avg_outgoing_duration")
		doc.company = company

		doc.last_call_log = json.dumps(emp.get("last_call_log", {}))

		doc.insert(ignore_permissions=True)
		count += 1

	return {"status": "success", "inserted": count}

# Fetch analysis report => Has an issue
@frappe.whitelist()
def fetch_analysis_report():
	end_point_name = "Analysis Report"
	endpoint, call_from, call_to = get_endpoint(end_point_name)

	settings = get_callyzer_settings()
	for setting in settings:
		company = setting["company"]

		url = setting['domain_api'] + endpoint
		token = setting["api_key"]

		payload = {
			"call_from": int(call_from),
			"call_to": int(call_to),
			"call_types": ["Missed", "Rejected", "Incoming", "Outgoing"],
			"is_exclude_numbers": True
		}
		update_last_fetched_time(end_point_name)
		result = post_api(url, token, payload)
		# frappe.throw(str(result))
		handle_analysis_report(call_from, call_to, company, result)
		
	return {"status": "success", "message": "Analysis report fetched successfully"}


def handle_analysis_report(start_date, end_date, company, result):
	doc = frappe.new_doc("Callyzer Analysis")
	doc.start_date = start_date
	doc.end_date = end_date
	doc.company = company

	# Average Duration
	avg = result.get("average_duration", {})
	doc.total_duration = avg.get("total_duration")
	doc.avg_per_call = avg.get("per_call")
	doc.total_calls = avg.get("total_calls")
	doc.avg_per_day = avg.get("per_day")
	doc.total_days = avg.get("total_days")
	doc.avg_per_incoming = avg.get("per_incoming_call")
	doc.total_incoming_calls = avg.get("total_incoming_calls")
	doc.avg_per_outgoing = avg.get("per_outgoing_call")
	doc.total_outgoing_calls = avg.get("total_outgoing_calls")

	# Top Dialer
	dialer = result.get("top_dialer", {})
	doc.top_dialer_name = dialer.get("emp_name")
	doc.top_dialer_number = dialer.get("emp_number")
	doc.top_dialer_tags = ", ".join(dialer.get("emp_tags", []))
	doc.top_dialer_outgoing_calls = dialer.get("total_outgoing_calls")

	# Top Answered
	answered = result.get("top_answered", {})
	doc.top_answered_name = answered.get("emp_name")
	doc.top_answered_number = answered.get("emp_number")
	doc.top_answered_tags = ", ".join(answered.get("emp_tags", []))
	doc.top_answered_incoming_calls = answered.get("total_incoming_calls")

	# Top Caller
	caller = result.get("top_caller", {})
	doc.top_caller_name = caller.get("emp_name")
	doc.top_caller_number = caller.get("emp_number")
	doc.top_caller_tags = ", ".join(caller.get("emp_tags", []))
	doc.top_caller_total_calls = caller.get("total_calls")

	# Longest Duration
	long_dur = result.get("longest_duration", {})
	doc.longest_duration_name = long_dur.get("emp_name")
	doc.longest_duration_number = long_dur.get("emp_number")
	doc.longest_duration_tags = ", ".join(long_dur.get("emp_tags", []))
	doc.longest_call_duration = long_dur.get("duration")

	# Highest Duration
	high_dur = result.get("highest_total_duration", {})
	doc.highest_duration_name = high_dur.get("emp_name")
	doc.highest_duration_number = high_dur.get("emp_number")
	doc.highest_duration_tags = ", ".join(high_dur.get("emp_tags", []))
	doc.highest_total_duration = high_dur.get("total_duration")

	doc.insert(ignore_permissions=True)
	return {"status": "success", "message": "Analysis data inserted"}

		
#Fetch Never Attended Report
@frappe.whitelist()
def fetch_never_attended_calls():
	end_point_name = "Never Attended"
	endpoint, call_from, call_to = get_endpoint(end_point_name)

	employee_ids = get_employees()
	settings = get_callyzer_settings()

	for setting in settings:
		company = setting["company"]
		url = setting['domain_api'].rstrip('/') + endpoint
		token = setting["api_key"]

		payload = {
			"call_from": int(call_from),
			"call_to": int(call_to),
			"emp_numbers": employee_ids,
			"emp_tags": [],
			"is_exclude_numbers": True,
			"page_no": 1,
			"page_size": 100
		}
		update_last_fetched_time(end_point_name)
		result = post_api(url, token, payload)
		handle_never_attended_calls(result, company)

	# return {"status": "success", "message": "Analysis data inserted"}

def handle_never_attended_calls(response, company):
	for emp in response:
		emp_number = emp.get("emp_number")

		if not frappe.db.exists("Callyzer Employee", {"employee_no": emp_number}):
			process_employee(emp)

		for log in emp.get("call_logs", []):
			external_id = log.get("id")

			# Try to find an existing Call History Log for linking
			call_log = frappe.db.get_value(
				"Call History Log",
				{"external_id": external_id},
				"name"
			)

			# Skip Callyzer Attendance Call creation only if already exists
			if call_log and frappe.db.exists("Callyzer Attendance Call", {"call_log": call_log}):
				continue
			if not call_log and frappe.db.exists("Callyzer Attendance Call", {"external_id": external_id}):
				continue

			call_date = log.get("call_date")
			doc = frappe.new_doc("Callyzer Attendance Call")
			doc.employee = emp_number
			doc.emp_code = emp.get("emp_code")
			doc.emp_name = emp.get("emp_name")
			doc.emp_number = emp_number
			doc.call_status = "Unattended Incoming"
			doc.client_name = log.get("client_name") or emp.get("client_name")
			doc.client_number = log.get("client_number") or emp.get("client_number")
			doc.external_id = external_id
			if call_log:
				doc.call_log = call_log
			doc.duration = log.get("duration")
			doc.call_type = log.get("call_type")
			doc.call_date = getdate(call_date)
			doc.call_time = log.get("call_time")
			doc.note = log.get("note")
			doc.call_recording_url = log.get("call_recording_url")
			doc.synced_at = log.get("synced_at")
			doc.modified_at = log.get("modified_at")
			doc.company = company
			doc.insert(ignore_permissions=True)


#Fetch Not Pickup By Client.
@frappe.whitelist()
def fetch_not_pickup_by_client_calls():
	settings = get_callyzer_settings()
	employee_ids = get_employees()
	end_point_name = "Not Pickup By Client"
	endpoint, call_from, call_to = get_endpoint(end_point_name)

	for setting in settings:
		company = setting["company"]
		token = setting["api_key"]
		url = setting['domain_api'].rstrip('/') + endpoint

		payload = {
			"call_from": int(call_from),
			"call_to": int(call_to),
			"call_types": ["Missed", "Rejected", "Incoming", "Outgoing"],
			"emp_numbers": employee_ids,
			"emp_tags": [],
			"is_exclude_numbers": True,
			"page_no": 1,
			"page_size": 100
		}

		update_last_fetched_time(end_point_name)
		result = post_api(url, token, payload)
		handle_not_pickup_by_client_calls(result, company)

	return {"status": "success", "message": "Analysis data inserted"}


def handle_not_pickup_by_client_calls(response, company):
	for emp in response:
		emp_number = emp.get("emp_number")
		if not emp_number:
			continue

		if not frappe.db.exists("Callyzer Employee", {"employee_no": emp_number}):
			process_employee(emp)

		for log in emp.get("call_logs", []):
			external_id = log.get("id")

			# Try to find an existing Call History Log for linking
			call_log = frappe.db.get_value(
				"Call History Log",
				{"external_id": external_id},
				"name"
			)

			# Skip only if Callyzer Attendance Call already created
			if call_log and frappe.db.exists("Callyzer Attendance Call", {"call_log": call_log}):
				continue
			if not call_log and frappe.db.exists("Callyzer Attendance Call", {"external_id": external_id}):
				continue

			call_date = log.get("call_date")
			doc = frappe.new_doc("Callyzer Attendance Call")
			doc.employee = emp_number
			doc.emp_code = emp.get("emp_code")
			doc.emp_name = emp.get("emp_name")
			doc.emp_number = emp_number
			doc.call_status = "Unattended Outgoing"
			doc.client_name = log.get("client_name") or emp.get("client_name")
			doc.client_number = log.get("client_number") or emp.get("client_number")
			doc.external_id = external_id
			if call_log:
				doc.call_log = call_log
			doc.duration = log.get("duration")
			doc.call_type = log.get("call_type")
			doc.call_date = getdate(call_date)
			doc.call_time = log.get("call_time")
			doc.note = log.get("note")
			doc.call_recording_url = log.get("call_recording_url")
			doc.synced_at = log.get("synced_at")
			doc.modified_at = log.get("modified_at")
			doc.company = company
			doc.insert(ignore_permissions=True)


# Fetch Unique Clients Report => Tested working fine
@frappe.whitelist()
def fetch_unique_clients_report():
	settings = get_callyzer_settings()
	employee_ids = get_employees()

	end_point_name = "Unique Clients"
	endpoint, call_from, call_to = get_endpoint(end_point_name)

	for setting in settings:
		company = setting["company"]
		token = setting["api_key"]
		url = setting['domain_api'] + endpoint
 
		payload = {
			"call_from": int(call_from),
			"call_to": int(call_to),
			"call_types": ["Incoming", "Outgoing"],
			"emp_numbers": employee_ids,
			"emp_tags": ["api"],
			"is_exclude_numbers": True,
			"page_no": 1,
			"page_size": 100
		}

		result = post_api(url, token, payload)
		update_last_fetched_time(end_point_name)
		process_unique_clients_response(result, company)

	return {"status": "success", "message": "Unique clients report fetched successfully"}

def process_unique_clients_response(result, company):
	clients = result
	inserted = 0

	for client in clients:
		if not (client.get("client_number") and client.get("client_country_code")):
			continue

		exists = frappe.db.exists("Callyzer Unique Client", {
			"client_number": client["client_number"],
			"client_country_code": client["client_country_code"],
			"company": company
		})
		if exists:
			continue

		doc = frappe.new_doc("Callyzer Unique Client")
		doc.client_name = client.get("client_name")
		doc.client_number = client.get("client_number")
		doc.client_country_code = client.get("client_country_code")
		doc.total_calls = client.get("total_calls")
		doc.total_incoming_calls = client.get("total_incoming_calls")
		doc.total_outgoing_calls = client.get("total_outgoing_calls")
		doc.total_incoming_duration = client.get("total_incoming_duration")
		doc.total_outgoing_duration = client.get("total_outgoing_duration")
		doc.total_missed_calls = client.get("total_missed_calls")
		doc.total_rejected_calls = client.get("total_rejected_calls")
		doc.total_connected_calls = client.get("total_connected_calls")
		doc.total_never_attended = client.get("total_never_attended")
		doc.total_not_picked_by_client = client.get("total_not_picked_by_client")
		doc.last_call_details = json.dumps(client.get("last_call_log"))
		doc.company = company

		last_call_log = client.get("last_call_log", {})
		if last_call_log:
			last_call_date = last_call_log.get("call_date")
			doc.last_call_date = getdate(last_call_date)
			doc.last_call_time = last_call_log.get("call_time")
			doc.last_call_type = last_call_log.get("call_type")

		doc.insert(ignore_permissions=True)
		inserted += 1

	return {"status": "success", "inserted": inserted}


# Fetch Hourly Analytics Report
@frappe.whitelist()
def fetch_hourly_analytics_report():
	end_point_name = "Hourly Analytics"
	endpoint, call_from, call_to = get_endpoint(end_point_name)

	settings = get_callyzer_settings()
	for setting in settings:
		company = setting["company"]
		token = setting["api_key"]

		url = setting['domain_api'] + endpoint

		payload = {
			"call_from": int(call_from),
			"call_to": int(call_to),
			"call_types": ["Missed", "Rejected", "Incoming", "Outgoing"],
			"working_hour_from": "10:00",
			"working_hour_to": "11:00",
			"is_exclude_numbers": True
		}
		update_last_fetched_time(end_point_name)
		result =  post_api(url, token, payload)
		process_hourly_analytics_response(result, company)

	return {"status": "success", "message": "Hourly analytics report fetched successfully"}
 

def process_hourly_analytics_response(result, company):
	result = result
	if not result:
		return {"status": "error", "message": "No result found in response"}

	total_calls = result.get("total_calls", 0)
	total_connected_calls = result.get("total_connected_calls", 0)
	total_duration = result.get("total_duration", 0)
	time_slots = result.get("time_slots", [])

	inserted = 0
	for slot in time_slots:
		doc = frappe.new_doc("Hourly Analytics")
		doc.company = company
		doc.hour = slot.get("hour")
		doc.call_count = slot.get("call_count", 0)
		doc.connected_call_count = slot.get("connected_call_count", 0)
		doc.duration = slot.get("duration", 0)
		doc.total_calls = total_calls
		doc.total_connected_calls = total_connected_calls
		doc.total_duration = total_duration
		doc.insert(ignore_permissions=True)
		inserted += 1

	return {
		"status": "success",
		"inserted": inserted,
		"total_slots": len(time_slots),
		"total_calls": total_calls,
		"total_connected_calls": total_connected_calls
	}


#Fetch Day-wise Analytics Report
@frappe.whitelist()
def fetch_day_wise_analytics_report(call_from=None, call_to=None):
	import time

	end_point_name = "Day-wise Analytics"

	# Accept dates from direct kwargs (bg job) or from HTTP form_dict (web request)
	call_from = call_from or frappe.form_dict.get("call_from")
	call_to = call_to or frappe.form_dict.get("call_to")

	if call_from and call_to:
		# Convert date strings to UTC Unix timestamps.
		# calendar.timegm() treats naive datetimes as UTC (unlike time.mktime which uses local tz)
		call_from = calendar.timegm(frappe.utils.getdate(call_from).timetuple())
		call_to = calendar.timegm(frappe.utils.getdate(call_to).timetuple())
		endpoint = get_endpoint(end_point_name)[0]  # only get the endpoint string
	else:
		# Use default logic if dates are not provided
		endpoint, call_from, call_to = get_endpoint(end_point_name)

	employee_ids = get_employees()
	settings = get_callyzer_settings()

	for setting in settings:
		company = setting["company"]
		token = setting["api_key"]
		url = setting['domain_api'] + endpoint

		payload = {
			"call_from": int(call_from),
			"call_to": int(call_to),
			"emp_numbers": employee_ids,
			"working_hour_from": "00:00",
			"working_hour_to": "20:59",
			"is_exclude_numbers": True
		}

		result = post_api(url, token, payload)
		update_last_fetched_time(end_point_name)
		process_daywise_analytics_response(result, company)

	return {
		"status": "success",
		"message": "Day-wise analytics report fetched successfully"
	}


def process_daywise_analytics_response(response_json, company):
	result = response_json or {}

	if not result:
		return {"status": "error", "message": "No day-wise analytics found in response"}

	time_slots = result.get("time_slots", [])

	for slot in time_slots:
		slot_name = slot.get("slot")
		existing_doc = frappe.get_all("Daywise Analyicts", filters={"company": company, "slot": slot_name}, fields=["name"])

		if existing_doc:
			doc = frappe.get_doc("Daywise Analyicts", existing_doc[0]["name"])
		else:
			doc = frappe.new_doc("Daywise Analyicts")
			doc.company = company
			doc.slot = slot_name
			doc.total_calls = slot.get("total_calls", 0)
			doc.total_connected_calls = slot.get("total_connected_calls", 0)
			doc.total_duration = slot.get("total_duration", 0)
			doc.total_call_perc = slot.get("total_call_perc", 0.0)
			doc.total_connected_calls_perc = slot.get("total_connected_calls_perc", 0.0)
			doc.total_duration_perc = slot.get("total_duration_perc", 0.0)

		existing_keys = {(child.date, child.day) for child in doc.daywise_calls}

		day_wise_entries = slot.get("day_wise", [])
		for entry in day_wise_entries:
			key = (entry.get("date"), entry.get("day"))
			if key in existing_keys:
				continue  

			doc.append("daywise_calls", {
				"date": entry.get("date"),
				"day": entry.get("day"),
				"total_calls": entry.get("total_calls", 0),
				"total_connected_calls": entry.get("total_connected_calls", 0),
				"total_duration": entry.get("total_duration", 0)
			})

		doc.save(ignore_permissions=True)

	return {"status": "success", "message": "Daywise analytics processed successfully"}


##Fetch Call History Report #Tested working
@frappe.whitelist()
def fetch_call_history_report(call_from=None, call_to=None):
	end_point_name = "Call History"

	# Accept dates from direct kwargs (bg job) or from HTTP form_dict (web request)
	call_from = call_from or frappe.form_dict.get("call_from")
	call_to = call_to or frappe.form_dict.get("call_to")

	if call_from and call_to:
		# Convert date strings to UTC Unix timestamps.
		# calendar.timegm() treats naive datetimes as UTC (unlike time.mktime which uses local tz)
		# call_from = start of the from_date (00:00:00 UTC)
		# call_to   = end of the to_date (23:59:59 UTC) so the full last day is included
		from datetime import datetime as _dt, time as _time
		call_from = calendar.timegm(frappe.utils.getdate(call_from).timetuple())
		call_to_date = frappe.utils.getdate(call_to)
		call_to = calendar.timegm(_dt.combine(call_to_date, _time(23, 59, 59)).timetuple())
		endpoint = get_endpoint(end_point_name)[0]  # only get the endpoint string
	else:
		# Use default logic if dates are not provided
		endpoint, call_from, call_to = get_endpoint(end_point_name)

	employee_ids = get_employees()
	settings = get_callyzer_settings()
	update_last_fetched_time(end_point_name)
	for setting in settings:
		company = setting["company"]
		token = setting["api_key"]

		# Strip trailing slash from domain_api to avoid double-slash URLs
		url = setting['domain_api'].rstrip('/') + endpoint
		page_size = 100
		page_no = 1

		while True:
			payload = {
				"call_from": int(call_from),
				"call_to": int(call_to),
				"call_types": [],
				"emp_numbers": employee_ids,
				"is_exclude_numbers": True,
				"page_no": page_no,
				"page_size": page_size
			}

			result = post_api(url, token, payload)
			
			if not result:
				break

			process_call_history_response(result, company)

			# Go to the next page
			page_no += 1

		
	return {"status": "success", "message": "Call history report fetched successfully"}
	   

def process_call_history_response(result, company):
	call_logs = result
	if not call_logs:
		return {"status": "error", "message": "No call history data found in response"}

	inserted = 0
	for call in call_logs:
		if not (call.get("id") and call.get("client_number")):
			continue

		exists = frappe.db.exists("Call History Log", {
			"external_id": call["id"],
			"client_number": call["client_number"],
			"company": company
		})
		if exists:
			continue
		if not frappe.db.exists("Callyzer Employee", {"employee_no": call.get("emp_number")}):
				process_employee(call)

		doc = frappe.new_doc("Call History Log")
		doc.external_id = call.get("id")
		doc.employee = call.get("emp_number")
		doc.employee_name = call.get("emp_name")
		doc.employee_code = call.get("emp_code")
		doc.employee_number = call.get("emp_number")
		doc.employee_country_code = call.get("emp_country_code")
		doc.employee_tags = ", ".join(call.get("emp_tags") or [])
		doc.client_name = call.get("client_name")
		doc.client_number = call.get("client_number")
		doc.client_country_code = call.get("client_country_code")
		doc.duration = call.get("duration")
		doc.call_type = call.get("call_type")
		call_date = call.get("call_date")
		doc.call_date = getdate(call_date)
		doc.call_time = call.get("call_time")
		doc.note = call.get("note")
		doc.call_recording_url = call.get("call_recording_url")
		doc.crm_status = call.get("crm_status")
		doc.reminder_date = call.get("reminder_date")
		doc.reminder_time = call.get("reminder_time")
		doc.synced_at = call.get("synced_at")
		doc.modified_at = call.get("modified_at")
		doc.lead_id = call.get("lead_id")
		doc.company = company

		doc.insert(ignore_permissions=True)
		inserted += 1

	return {
		"status": "success",
		"inserted": inserted,
		"records_fetched": len(call_logs)
	}

#Fetch Call History By Ids
@frappe.whitelist()
def fetch_call_history_by_ids():
	end_point_name = "Call History By Ids"
	unique_ids = frappe.form_dict.get("unique_ids")
	company = frappe.form_dict.get("company")
	endpoint, call_from, call_to = get_endpoint(end_point_name)
	api_key = frappe.form_dict.get("api_key")
	domain_api = frappe.form_dict.get("domain_api")
	# if not unique_ids or not isinstance(unique_ids, list):
	#     frappe.throw(_("Please provide a valid list of Unique IDs"))
	# frappe.throw(str(api_key))
	url = domain_api + endpoint
	
	payload = {
		"unique_ids": unique_ids
	}
	result = post_api(url, api_key, payload)
	update_last_fetched_time(end_point_name)
	process_call_history_response(result, company)

	return {"status": "success", "message": "Call history fetched successfully"}
  
  
#Remove Call Recording
@frappe.whitelist()
def remove_call_recording(unique_ids: list[str], company: str = None):
	end_point_name = "Remove Call Recording"
	if not unique_ids:
		frappe.throw(_("Unique IDs are required"))

	settings = frappe.get_doc("Callyzer Settings", company)
	base_url = settings.api_url.rstrip("/")
	api_key = settings.api_key

	try:
		res = requests.delete(
			f"{base_url}/call-log/call-recording/remove",
			headers={"api-key": api_key},
			json={"unique_ids": unique_ids},
			timeout=30
		)
		res.raise_for_status()
		return {"status": "success", "message": res.json()}
	except requests.RequestException as e:
		frappe.log_error(f"Failed to remove call recording: {e}", "Callyzer Remove Call Recording")
		return {"status": "error", "message": str(e)}

#Tested working
@frappe.whitelist(allow_guest=True)
def callyzer_call_log_webhook():
	"""Webhook endpoint for receiving and processing Callyzer employee & call log data."""
	try:
		if frappe.request.method != "POST":
			frappe.throw(_("Webhook only accepts POST requests"), frappe.ValidationError)

		payload = frappe.request.get_json()
		if not payload:
			frappe.throw(_("Invalid or empty JSON payload"))

		data = normalize_payload(payload)

		total_created = 0
		total_logs = 0

		for item in data:
			employee_name, is_new = process_employee(item)
			if is_new:
				total_created += 1

			logs_created = process_call_logs(employee_name, item.get("call_logs", []))
			total_logs += logs_created

		return {
			"status": "success",
			"employees_created": total_created,
			"call_logs_created": total_logs
		}

	except Exception:
		frappe.log_error("Webhook: Failed to process Callyzer data", frappe.get_traceback())
		return {"status": "error", "message": "Processing failed"}

#Tested working
def post_api(url, api_key, payload):
	# Normalise any double-slash that arises when domain_api ends with / and endpoint starts with /
	url = url.replace('https://', '__SCHEME__').replace('//', '/').replace('__SCHEME__', 'https://')
	headers = build_callyzer_headers(api_key)
	try:
		try:
			response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
		except requests.exceptions.ReadTimeout:
			# First attempt timed out — retry once with a longer timeout before giving up
			frappe.log_error(_("Callyzer API timed out (20s). Retrying with 60s timeout."), _("Callyzer Timeout Retry"))
			response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)

		if response.status_code == 429:
			time.sleep(5)
			response = requests.post(url, json=payload, headers=headers, timeout=60)

		if response.status_code != 200:
			frappe.throw(_(f"Callyzer API request failed with status {response.status_code}: {response.text}"))

		return response.json().get("result", {})
		
	except requests.exceptions.ReadTimeout:
		frappe.log_error(_("Callyzer API Timeout"), frappe.get_traceback())
		frappe.throw(_("Callyzer API timed out after retry. The server is taking too long to respond."))
	except requests.exceptions.RequestException as e:
		frappe.log_error(_("Callyzer API Error"), frappe.get_traceback())
		frappe.throw(_("Error communicating with Callyzer API: ") + str(e))

def get_api(url, api_key, payload):
	url = url.replace('https://', '__SCHEME__').replace('//', '/').replace('__SCHEME__', 'https://')
	headers = build_callyzer_headers(api_key)
	try:
		try:
			response = requests.get(url, headers=headers, data=json.dumps(payload), timeout=20)
		except requests.exceptions.ReadTimeout:
			# Retry once with a longer timeout
			frappe.log_error(_("Callyzer GET API timed out (20s). Retrying with 60s timeout."), _("Callyzer Timeout Retry"))
			response = requests.get(url, headers=headers, data=json.dumps(payload), timeout=60)

		if response.status_code != 200:
			frappe.throw(_(f"Callyzer API request failed with status {response.status_code}: {response.text}"))

		return response.json().get("result", {})
		
	except requests.exceptions.ReadTimeout:
		frappe.log_error(_("Callyzer API Timeout"),frappe.get_traceback())
		frappe.throw(_("Callyzer API timed out after retry. The server is taking too long to respond."))
	except requests.exceptions.RequestException as e:
		frappe.log_error(_("Callyzer API Error"), frappe.get_traceback())
		frappe.throw(_("Error communicating with Callyzer API: ") + str(e))

def get_valid_callyzer_settings(company):
	settings = get_callyzer_settings(company)
	if not settings:
		frappe.throw(_("Callyzer settings not found for the company"))
	return settings

def build_callyzer_headers(api_key):
	return {
		"Authorization": f"Bearer {api_key}",
		"Content-Type": "application/json"
	}


@frappe.whitelist()
def bg_fetch_summary_report():
	frappe.enqueue(
		"callyzer.api.call_log.fetch_summary_report",
		queue='default',  
		timeout=600,  
		now=False
	)
	return _("Summary report job has been queued. You will be notified once it's complete.")

@frappe.whitelist()
def bg_fetch_employee_summary_report():
	frappe.enqueue(
		"callyzer.api.call_log.fetch_employee_summary_report",
		queue='default',  
		timeout=600,  
		now=False
	)
	return _("Employee summary report job has been queued. You will be notified once it's complete.")

@frappe.whitelist()
def bg_fetch_analysis_report():
	frappe.enqueue(
		"callyzer.api.call_log.fetch_analysis_report",
		queue='default',  
		timeout=600,  
		now=False
	)
	return _("Analysis report job has been queued. You will be notified once it's complete.")

@frappe.whitelist()
def bg_fetch_never_attended_calls():
	frappe.enqueue(
		"callyzer.api.call_log.fetch_never_attended_calls",
		queue='default',  
		timeout=600,  
		now=False
	)
	return _("Never attended calls job has been queued. You will be notified once it's complete.")

@frappe.whitelist()
def bg_fetch_not_pickup_by_client_calls():
	frappe.enqueue(
		"callyzer.api.call_log.fetch_not_pickup_by_client_calls",
		queue='default',  
		timeout=600,  
		now=False
	)
	return _("Not pickup by client calls job has been queued. You will be notified once it's complete.")

@frappe.whitelist()
def bg_fetch_unique_clients_report():
	frappe.enqueue(
		"callyzer.api.call_log.fetch_unique_clients_report",
		queue='default',  
		timeout=600,  
		now=False
	)
	return _("Unique clients report job has been queued. You will be notified once it's complete.")

@frappe.whitelist()
def bg_fetch_hourly_analytics_report():
	frappe.enqueue(
		"callyzer.api.call_log.fetch_hourly_analytics_report",
		queue='default',  
		timeout=600,  
		now=False
	)
	return _("Hourly analytics report job has been queued. You will be notified once it's complete.")

@frappe.whitelist()
def bg_fetch_day_wise_analytics_report(call_from=None, call_to=None):
	frappe.enqueue(
		"callyzer.api.call_log.fetch_day_wise_analytics_report",
		queue='default',
		timeout=600,
		now=False,
		call_from=call_from,
		call_to=call_to
	)
	return _("Day-wise analytics report job has been queued. You will be notified once it's complete.")

@frappe.whitelist()
def bg_fetch_call_history_report(call_from=None, call_to=None):
	frappe.enqueue(
		"callyzer.api.call_log.fetch_call_history_report",
		queue='default',
		timeout=600,
		now=False,
		call_from=call_from,
		call_to=call_to
	)
	return _("Call history report job has been queued. You will be notified once it's complete.")


@frappe.whitelist()
def fetch_call_history_report_daily():
	end_point_name = "Call History"
	
	# Define today's start and end timestamps
	today_date = getdate()
	call_from_dt = datetime.combine(today_date, time.min)  # 12:00 AM
	call_to_dt = datetime.combine(today_date, time.max)    # 11:59:59 PM

	# calendar.timegm() ensures UTC is used regardless of server local timezone
	call_from = calendar.timegm(call_from_dt.timetuple())
	call_to = calendar.timegm(call_to_dt.timetuple())

	endpoint = get_endpoint(end_point_name)[0]  # Only get the endpoint string

	employee_ids = get_employees()
	settings = get_callyzer_settings()

	for setting in settings:
		company = setting["company"]
		token = setting["api_key"]
		url = setting["domain_api"] + endpoint
		page_size = 100
		page_no = 1

		while True:
			payload = {
				"call_from": call_from,
				"call_to": call_to,
				"call_types": [],
				"emp_numbers": employee_ids,
				"is_exclude_numbers": True,
				"page_no": page_no,
				"page_size": page_size
			}

			result = post_api(url, token, payload)

			if not result:
				break

			process_call_history_response(result, company)
			page_no += 1

	return {"status": "success", "message": "Call history report fetched successfully"}