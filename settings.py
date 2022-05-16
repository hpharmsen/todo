import datetime
from pathlib import Path
from configparser import ConfigParser

scriptpath = Path(__file__).resolve().parent
inifile = ConfigParser()
try:
    inifile.read(scriptpath / "localtodo.ini")  # Versie die niet in HG is ingecheckt
except:
    inifile.read(scriptpath / "todo.ini")

datafolder = Path(inifile.get("general", "datafolder"))
if inifile.has_section("todoist"):
    todoist_api_key = inifile.get("todoist", "api_key")
    todoist_user_id = int(inifile.get("todoist", "user_id"))
else:
    todoist_api_key = todoist_user_id = None

subdomain = inifile.get("simplicate", "subdomain")
api_key = inifile.get("simplicate", "api_key")
api_secret = inifile.get("simplicate", "api_secret")
employee_name = inifile.get("simplicate", "employee_name")

priorities = ["!", "-", "~", "O", "X"]


def get_employee_id():
    try:
        return inifile.get("simplicate", "employee_id")
    except:
        return ""


def set_employee_id(id):
    inifile["simplicate"]["employee_id"] = id


def getNextDay(date):
    date += datetime.timedelta(days=1)
    if date.weekday() == 5:
        date += datetime.timedelta(days=2)
    elif date.weekday() == 6:
        date += datetime.timedelta(days=1)
    return date


def getPrevDay(date):
    date += datetime.timedelta(days=-1)
    if date.weekday() == 5:
        date += datetime.timedelta(days=-1)
    elif date.weekday() == 6:
        date += datetime.timedelta(days=-2)
    return date
