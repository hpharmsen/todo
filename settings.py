import datetime
import sys
from pathlib import Path
from configparser import ConfigParser

scriptpath = Path(__file__).resolve().parent
inifile = ConfigParser()
try:
    inifile.read(scriptpath / 'localtodo.ini') # Versie die niet in HG is ingecheckt
except:
    inifile.read(scriptpath / 'todo.ini')

datafolder = Path(inifile.get('general', 'datafolder'))
timesheetuser = inifile.get('timesheet', 'timesheetuser')
todoist_api_key = inifile.get('todoist', 'api_key')
todoist_user_id = int(inifile.get('todoist', 'user_id'))

def panic( s ):
    print( s )
    sys.exit( 1 )


priorities = ['!','-','~','M','X']


def getNextDay( date ):
    date += datetime.timedelta(days=1)
    if date.weekday()==5:
        date += datetime.timedelta(days=2)
    elif date.weekday()==6:
        date += datetime.timedelta(days=1)
    return date


def getPrevDay( date ):
    date += datetime.timedelta(days=-1)
    if date.weekday()==5:
        date += datetime.timedelta(days=-1)
    elif date.weekday()==6:
        date += datetime.timedelta(days=-2)
    return date