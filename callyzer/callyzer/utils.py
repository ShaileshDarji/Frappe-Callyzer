import frappe
from datetime import datetime, timedelta
from frappe import _

MAX_DATE_RANGE_DAYS = 179

def get_callyzer_settings(company=None):
    filters = {"is_active": 1}
    if company:
        filters["company"] = company

    settings = frappe.get_all(
        "Callyzer Settings",
        filters=filters,
        fields=["name", "domain_api", "api_key", "company"]
    )
    return settings if settings else None


def normalize_payload(payload):
    """Normalize input payload to a list of data dictionaries."""
    if isinstance(payload, list):
        return payload
    elif isinstance(payload, dict):
        return payload.get("result", []) or [payload]
    else:
        frappe.throw(_("Unexpected payload format"))

def get_employees():
    employees_id = []
    all_callyzer_employee = frappe.get_all("Callyzer Employee", fields=["name"])
    for employee in all_callyzer_employee:
        employees_id.append(employee.name)
    return employees_id


def format_time_timestamp_(date):
    if isinstance(date, str):
        # Try parsing the common Frappe datetime format
        try:
            date = frappe.utils.get_datetime(date)
        except Exception:
            # Fallback if parsing fails
            date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
    
    return int(date.timestamp())


def get_endpoint_settings():
    settings = frappe.get_single("Callyzer Endpoint Settings")
    endpoints = []

    for endpoint_item in settings.endpoints:
        endpoints.append({
            "endpoint_name": endpoint_item.endpoint_name,
            "endpoint": endpoint_item.endpoint,
            "last_fetched": endpoint_item.last_fetch,
        })
    
    return endpoints

def get_endpoint(endpoint_name):
    call_from = None
    call_to = format_time_timestamp_(frappe.utils.now())
    for endpoint in get_endpoint_settings():
        if endpoint["endpoint_name"] == endpoint_name:
            endpoint_url = endpoint["endpoint"]
            call_from = format_time_timestamp_(endpoint["last_fetched"])
            break

    # Callyzer API enforces a 180-day maximum date range.
    # Cap call_from so it is never more than MAX_DATE_RANGE_DAYS before call_to.
    max_call_from = call_to - (MAX_DATE_RANGE_DAYS * 24 * 60 * 60)
    if call_from is None or call_from < max_call_from:
        call_from = max_call_from

    return endpoint_url, call_from, call_to

def update_last_fetched_time(endpoint_name):
    # found = False
    settings = frappe.get_single("Callyzer Endpoint Settings")

    for row in settings.endpoints:
        if row.endpoint_name == endpoint_name:
            last_fetch = frappe.utils.now()
            frappe.db.set_value("Endpoint Call", row.name, "last_fetch", last_fetch)
            # frappe.db.commit()
            # settings.save(ignore_permissions=True)
            break
    else:
        frappe.throw(f"{endpoint_name} not found in settings")
    