import datetime
import settings
from pysimplicate import Simplicate

APRROVED_ID = "approvalstatus:9a4660a21af7234e"
DATE_FORMAT = '%Y-%m-%d'

_sim = None
def simplicate():
    global _sim
    if not _sim:
        _sim = Simplicate(settings.subdomain, settings.api_key, settings.api_secret)
    return _sim


def find_bookable( zoek):
    zoek = zoek.lower()

    projects = {p['id']: p['name'] for p in simplicate().project({'active': True})}
    services = [s for s in simplicate().service({'status': 'open', 'track_hours':True})
                if s.get('name') and s['project_id'] in projects.keys()]

    res = []
    found_services = []
    for s in services:
        for h in s.get('hour_types',[]):
            full_name = projects[s['project_id']] + ' ' + s['name'] + ' ' + h['hourstype']['label']
            full_name = full_name.replace( ' Internal ', ' ')
            if not full_name.lower().count(zoek):
                continue
            found_services += [full_name]
            res += [( s['project_id'], s['id'], h['hourstype']['id'] )]
    if len(res) == 1:
        return res[0]
    if len(res) == 0:
        print( 'No service found')
    else:
        print( 'Multiple services found')
        for f in found_services:
            print(f)
    return None, None, None


def book( search, amount, note='', date=None ):
    if not date:
        date = datetime.datetime.now().strftime(DATE_FORMAT)
    project_id, service_id, hourstype_id = find_bookable( search)
    if project_id:
        postdata = {
          "employee_id": settings.employee_id,
          "project_id": project_id,
          "projectservice_id": service_id,
          "type_id": hourstype_id,
          "amount": amount,
          "start_date": date,
          "note": note
        }
        print( 'posting')
        res = simplicate().book_hours(postdata)
        return res
    else:
        print( 'nope')

def hours_booked_status():
    now = datetime.datetime.now()
    booked = simplicate().hours_count({'employee_name':settings.employee_name, 'day':now.strftime(DATE_FORMAT)})

    weekday = now.weekday()
    if weekday >= 5: # zo za
        return ''
    elif weekday == 2: # wo
        start_hour = 8
    else:
        start_hour = 9
    lunch = now.hour>=12 and 30*60 or 0
    start_time = datetime.datetime( now.year, now.month, now.day, start_hour, 30 )
    s =  '{:0.2f} booked'.format( booked )
    if now>start_time:
        time_passed = now - start_time
        missing = (((time_passed.seconds-lunch) * 4)  / 3600 - 4* booked) / 4.0
        if missing>=0.5:
            s += ', {:0.2f} hours missing'.format( missing )
    return s

def hours_booked():
    now = datetime.datetime.now()
    booked = simplicate().hours_simple({'employee_name':settings.employee_name, 'day':now.strftime(DATE_FORMAT)})
    return [{'project':b['project_name'],
            'task':b['service'] + ' ' + b['type'],
            'booked':b['hours'],
            'note':b['note']} for b in booked]

def approve_hours():
    today = datetime.datetime.today().strftime(DATE_FORMAT)
    res = simplicate().hours_approval({'employee_id':settings.employee_id, 'approvalstatus_id':APRROVED_ID, 'date':today})
    return res

if __name__== '__main__':
    print(hours_booked_status())