import datetime
import settings
from settings import panic

db = None # Used for logging to TimeSheet. Initialized only when needed.

def getDB():
    global db
    if db:  # Singleton
        return db

    from hplib.dbclass import dbClass

    try:
        return dbClass.from_inifile(settings.scriptpath / 'localtodo.ini')
    except:
        print('No database connection')
        return None


def findTasks( needle ):
    db = getDB()
    user = settings.timesheetuser

    # Eerste subquery is uurbasisprojecten.
    # Tweede is fixed price. Er moet daarvoor wel een hoursestimate zijn ingevuld. Tenzij het een Oberonproject is.
    sql = f'''SELECT DISTINCT p.id as projectid, -2 as taskid, CONCAT( c.name, " ", title ) AS taskname 
                     FROM project p 
                     JOIN customer c ON c.id = p.customerId
                     JOIN project_user pu on p.id=pu.projectId and pu.user="{user}" 
                     WHERE timesheet=1 and phase <90  and hourlyBasis=1
                     AND CONCAT( c.name, " ", title ) LIKE "%{needle}%"

            UNION

            SELECT DISTINCT p.id as projectid, t.id as taskid, CONCAT( c.name, " ", title,  " ", t.name ) AS taskname 
                 FROM project p 
                 JOIN customer c ON c.id = p.customerId
                 JOIN task_project tp on p.id=tp.projectId and tp.user="{user}" 
                 JOIN task t ON t.id=tp.taskId 
                 WHERE timesheet=1 and phase <90 and (c.Id=4 or hoursestimate>0) and hourlyBasis=0
              AND CONCAT( c.name, " ", title,  " ", t.name ) LIKE "%{needle}%" '''
    return db.execute( sql )


def saveToTimesheet( project, duration, comment='' ):

    tasks = findTasks( project )
    if len(tasks )==0:
        panic( 'No task found' )
    if len(tasks) >1:
        print( 'Multiple tasks found' )
        for t in tasks:
            print( t['taskid'], t['taskname'] )
        panic('')

    task = tasks[0]
    if task['taskid']=='':
        panic( 'Task Id is empty')

    db = getDB()
    if not db:
        return
    user = settings.timesheetuser
    today = datetime.datetime.now().strftime('%Y/%m/%d')
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    wheredict = {'user':user, 'day':today, 'projectId':task['projectid'], 'taskId':task['taskid'] }

    alreadybooked = db.select( 'timesheet', wheredict )
    if not alreadybooked:
        valuedict = {'hours': duration, 'comment':comment, 'lastchange':now }
        insertdict = wheredict.copy()
        insertdict.update(valuedict)
        db.insert( 'timesheet', insertdict )
    else:
        if not alreadybooked[0]['comment']:
            alreadybooked[0]['comment'] = ''
        valuedict = {'hours': alreadybooked[0]['hours'] + duration,
                     'comment':alreadybooked[0]['comment'] + ' / ' + comment,
                     'lastchange':now }
        db.update( 'timesheet', wheredict, valuedict )
    db.commit()
    print( 'Booked ', duration, 'hours on task', task['taskname'] )



def getHoursBooked():
    user = settings.timesheetuser
    db = getDB()
    return db.execute(f"""SELECT p.title as project, t.name as task, sum(ts.hours) as booked from timesheet ts, project p, task t 
                         where ts.projectId=p.id and ts.taskId=t.Id and user='{user}' and day=curdate() 
                         group by ts.projectId, ts.taskId""")


def closeDayInTimesheet():
    db = getDB()
    user = settings.timesheetuser
    today = datetime.date.today().strftime( '%Y-%m-%d' )
    try:
        db.insert( 'timesheetcompleted', {'user':user, 'day':today} )
        db.commit()
    except:
        pass