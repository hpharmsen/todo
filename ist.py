import datetime
from collections import defaultdict

import requests
import todoist
import settings

TODAY = datetime.datetime.now().strftime( '%Y-%m-%d')

# Hoe het werkt met prioriteiten
# In todo: ['!','-','~','M','X']
# 0 = high, 1 = normal, 2 = low, 3 = miek, 4 = done
#
# In todoist
# 1 = low, 2 = miek, 3 = normal, 4 = high

def todo2istprio( prio ):
    # 0 -> 4
    # 1 -> 3
    # 2 -> 1
    # 3 -> 2 and Assign to someone else
    # 4 -> Set to done
    #if prio==3:
    #    self.api.items.update(id)
    #    self.api.commit()
    return {0:4, 1:3, 2:1, 3:2, 4:4}[prio]

def ist2todoprio( prio, date_completed ):
    # 1 -> 2 low
    # 2 -> 3 miek
    # 3 -> 1 normal
    # 4 -> 0 high
    if date_completed:
        return 4 # done
    else:
        return {0:1, 1:2, 2:3, 3:1, 4:0}[prio]

class Ist():
    def __init__(self):
        self.api = todoist.TodoistAPI(settings.todoist_api_key)
        try:
            self.api.sync()
        except requests.exceptions.ConnectionError:
            return None # Network

    def items(self, project=None, scheduled=False, deleted=False, completed_today=True):
        items = [item for item in self.api['items'] if not item['date_completed'] or completed_today and item['date_completed'].split('T')[0] == TODAY]
        if project:
            items = [item for item in items if item['project_id'] == project['id']]

        if not deleted:
            items = [item for item in items if item['is_deleted'] ==0]

        if not scheduled:
            items = [item for item in items if not item['due'] or item['due']['date'] <= TODAY]
        return items

    def projects(self):
        return self.api.state['projects']

    def project_by_name(self, project_name):
        for project in self.projects():
            if project['name'] == project_name:
                return project

    def project_by_id(self, project_id):
        for project in self.projects():
            if project['id'] == project_id:
                return project

    def sync(self, day):
        day_dict = day.by_id()
        todoist_items = self.items(deleted=True, scheduled=False, completed_today=True)
        for todoist_item in todoist_items:
            title = todoist_item.data['content']
            prio = ist2todoprio(todoist_item.data['priority'],todoist_item.data['date_completed'],)
            id = todoist_item.data['id']
            day_item = day_dict.get(id)
            if not day_item:
                # todoist item not found in day. Add it
                day_item = day.add( title, prio, id )
            # Update if Todoist item appears to have changed
            if day_item['prio'] != prio:
                day_item['prio'] = prio
            if day_item['desc'] != title:
                day_item['dec'] = title

        for day_item in day.items:
            if not day_item.get('id'):
                # No id, must be a new item. Add it to todoist
                item = self.api.add_item( day_item['desc'])
                self.api.items.update(item['id'], priority=day_item['prio'])
                self.api.commit()
                day_item['id'] = item['id']

    def __str__(self):
        projects = defaultdict(list)
        for item in self.items(completed_today=False):
            marker = 'X' if item['date_completed'] else settings.priorities[item['priority']]
            content = item['content']
            due = ' @ ' + item['due']['date'] if item['due'] else ''
            completed = ' √ ' + item['date_completed'] if item['date_completed'] else ''
            deleted = ' DELETED' if item['is_deleted'] else ''
            string = marker + ' ' + content + due + completed + deleted

            project_id = item.data['project_id']
            project_name =  self.project_by_id(project_id)['name']
            projects[project_name].append( string )
        res = ''
        for project, items in projects.items():
            res += project + '\n'
            for item in items:
                res += '   ' + item + '\n'
        return res

    ### ACTIONS ###

    def add_item(self, content, prio):
        converted_prio = todo2istprio(prio)
        new = self.api.add_item(content, priority=converted_prio)
        self.api.commit()
        return new['id']

    def delete_item(self, id):
        self.api.items.delete(id)
        self.api.commit()

    def complete_item(self, id):
        date_completed = {"string":  "today"}
        date_completed = datetime.datetime.today().strftime('%Y-%m-%d')

        self.api.items.complete(id, date_completed=date_completed)
        self.api.items.archive(id)
        self.api.commit()

    def set_priority(self, id, prio):
        prio = todo2istprio(prio)
        self.api.items.update(id, priority=prio)
        self.api.commit()

    def push_forward(self, id):
        due = {"string":  "tomorrow"}
        self.api.items.update(id, due=due)
        self.api.commit()

    def push_back(self, id):
        prev_day = settings.getPrevDay(datetime.datetime.today()).strftime('%Y-%m-%d')
        self.api.items.complete(id, date_completed=prev_day)
        self.api.commit()

    def reschedule(self, id, date):
        due = {"string":  date}
        self.api.items.update(id, due=due)
        self.api.commit()

if __name__=='__main__':
    ist = Ist()
    inbox_project = ist.project_by_name('Inbox')
    inbox_items = ist.items( inbox_project )
    for item in inbox_items:
        print( item )
    #sync(api)