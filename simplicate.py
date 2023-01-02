import datetime
import pickle
from pathlib import Path
from justdays import Day

from base import bcolors
from pysimplicate import Simplicate

APRROVED_ID = "approvalstatus:9a4660a21af7234e"

_sim = None


def simplicate():
    global _sim
    if not _sim:
        import settings

        _sim = Simplicate(settings.subdomain, settings.api_key, settings.api_secret)
    return _sim


def find_bookable(zoek):

    matching_services = find_matching_services(zoek)
    if len(matching_services) == 0:
        matching_services = find_matching_services(zoek, use_cache=False)
    if len(matching_services) == 1:
        return matching_services[0]
    if len(matching_services) == 0:
        print(f'{bcolors.WARNING}No service found with "{zoek}"{bcolors.ENDC}')
    else:
        print(f'{bcolors.WARNING}Multiple services found matching "{zoek}"{bcolors.ENDC}')
        for f in matching_services:
            print(f[3])
    return None, None, None, None


def find_matching_services(zoek, use_cache=True):
    zoek = zoek.lower()
    scriptpath = Path(__file__).resolve().parent
    cache_file = scriptpath / ".servicescache"

    if use_cache:
        if not cache_file.is_file():
            return []  # Just return [] to run function again with use_cache=True
        with open(cache_file, "rb") as f:
            projects, services = pickle.load(f)
    else:
        projects = {p["id"]: p["name"] for p in simplicate().project({"active": True})}
        services = [
            s
            for s in simplicate().service({"status": "open", "track_hours": True})
            if s.get("name") and s["project_id"] in projects.keys()
        ]
        with open(cache_file, "wb") as f:
            pickle.dump((projects, services), f)

    res = []
    matching_services = []
    for s in services:
        for h in s.get("hour_types", []):
            full_name = projects[s["project_id"]] + " " + s["name"] + " " + h["hourstype"]["label"]
            full_name = full_name.replace("Internal", "").strip()
            if not full_name.lower().count(zoek):
                continue
            matching_services += [full_name]
            res += [(s["project_id"], s["id"], h["hourstype"]["id"], full_name)]
    return res


def book(search, amount, note, date: str):
    if not date:
        date = str(Day())
    project_id, service_id, hourstype_id, full_name = find_bookable(search)
    if project_id:
        postdata = {
            "employee_id": get_employee_id(),
            "project_id": project_id,
            "projectservice_id": service_id,
            "type_id": hourstype_id,
            "hours": amount,
            "start_date": date,
            "note": note,
        }
        res = simplicate().book_hours(postdata)
        howmuch = f"{amount:.1f} hours" if amount >= 1 else f"{amount*60:.0f} minutes"

        print(f"{bcolors.GREEN}Booked {howmuch} on {full_name}.{bcolors.ENDC}")
        return res


def hours_booked_status(day: Day=Day()):
    booked = simplicate().hours_count({"employee_name": get_employee_name(), "day": str(day)})

    weekday = day.day_of_week()
    if weekday >= 5:  # zo za
        return ""
    start_time = datetime.datetime(day.y, day.m, day.d, 9, 30)
    s = "{:0.2f} booked".format(booked)
    # if type(day) == datetime.datetime and day > start_time:
    #     lunch = day.hour >= 12 and 30 * 60 or 0
    #     time_passed = day - start_time
    #     missing = (((time_passed.seconds - lunch) * 4) / 3600 - 4 * booked) / 4.0
    #     if missing >= 0.5:
    #         s += ", {:0.2f} hours missing".format(missing)
    return s


def hours_booked(day:Day=Day()):
    booked = simplicate().hours_simple({"employee_name": get_employee_name(), "day": str(day)})
    return [
        {
            "project": b["project_name"],
            "task": b["service"] + " " + b["type"],
            "booked": b["hours"],
            "note": b["note"],
        }
        for b in booked
    ]


def approve_hours(day:Day=None):
    if not day:
        day = Day()
    filter = {
        "employee_id": get_employee_id(),
        "approvalstatus_id": APRROVED_ID,
        "date": str(day),
    }
    res = simplicate().hours_approval(filter)
    return res


def printHoursBooked(day:Day):
    booked = {}
    for item in hours_booked(day):
        key = f"{item['project']}, {item['task']}"
        if booked.get(key):
            booked[key][0] += item["booked"]
            if booked[key][1]:
                booked[key][1] += " / " + item["note"]
        else:
            booked[key] = [item["booked"], item["note"]]
    for key, val in booked.items():
        text = key.replace("Internal, ", "").replace(" normal", "")
        if val[1]:
            text += " - " + val[1]
        print(f"{val[0]:.2f} {text}")


_employee_name = ""


def get_employee_name():
    global _employee_name
    if not _employee_name:
        import settings

        _employee_name = settings.employee_name
    return _employee_name


_employee_id = ""


def get_employee_id():
    global _employee_id
    if not _employee_id:
        import settings

        _employee_id = settings.get_employee_id()
        if not _employee_id:
            emp = simplicate().employee({"name": get_employee_name()})
            _employee_id = emp["id"]
    return _employee_id


if __name__ == "__main__":
    print(hours_booked_status())
