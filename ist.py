import datetime
from collections import defaultdict

import requests
import todoist
import settings
from item import Item

TODAY = datetime.datetime.now().strftime('%Y-%m-%d')

# Hoe het werkt met prioriteiten
# In todo: ['!','-','~','M','X']
# 0 = high, 1 = normal, 2 = low, 3 = miek, 4 = done
#
# In todoist
# 1 = low, 2 = miek, 3 = normal, 4 = high


def ist2todoprio(prio, date_completed):
    # 1 -> 2 low
    # 2 -> 3 miek
    # 3 -> 1 normal
    # 4 -> 0 high
    if date_completed:
        return 4  # done
    else:
        return {0: 1, 1: 2, 2: 3, 3: 1, 4: 0}[prio]


class Ist:
    def __init__(self):
        self.api = todoist.TodoistAPI(settings.todoist_api_key)
        try:
            self.api.sync()
        except requests.exceptions.ConnectionError:
            return None  # Network
        self.projects = self.get_projects()

    def items(self, project=None, scheduled=False, deleted=False, completed_today=True):
        items = []
        for item in self.api['items']:

            # Filter out completed items
            if item['date_completed']:
                if item['date_completed'].split('T')[0] < TODAY:
                    continue
                if item['date_completed'].split('T')[0] == TODAY and not completed_today:
                    continue

            # Filter out items assigned to someone else, unless assigned by me
            if item['responsible_uid'] and item['responsible_uid'] != settings.todoist_user_id:
                by = item['assigned_by_uid']
                u = settings.todoist_user_id
                if item['assigned_by_uid'] == settings.todoist_user_id:
                    item['priority'] = 2  # Blauw
                else:
                    continue

            # Filter out items from shared projects that are not assigned to nor assigned by me

            own_projects = [p['id'] for p in self.projects if not p['shared']]
            if (
                not item['project_id'] in own_projects
                and item['responsible_uid'] != settings.todoist_user_id
                and item['assigned_by_uid'] != settings.todoist_user_id
            ):
                continue

            # If specified filter out all items not belonging to the project.
            if project and item['project_id'] != project.id:
                continue

            # Filter out deleted items
            if not deleted and item['is_deleted']:
                continue

            # Filter out items scheduled for a later time
            if not scheduled and item['due'] and item['due']['date'] > TODAY:
                continue

            items += [item]

        return items

    def get_projects(self):
        return self.api.state['projects']

    def project_by_name(self, project_name):
        for project in self.projects:
            if project['name'] == project_name:
                return project

    def project_by_id(self, project_id):
        for project in self.projects:
            if project.id == project_id:
                return project

    def sync(self, day):
        day_dict = day.by_id()
        todoist_items = self.items(deleted=True, scheduled=False, completed_today=True)
        todoist_ids = set()
        for todoist_item in todoist_items:
            title = todoist_item.data['content']
            prio = ist2todoprio(
                todoist_item.data['priority'],
                todoist_item.data['date_completed'],
            )
            id = todoist_item.data['id']
            if id == 4369327690:
                continue  # Ghost id that cannot be found or deleted in todoist
            todoist_ids.add(id)
            day_item = day_dict.get(id)
            if not day_item:
                # todoist item not found in day. Add it
                day_item = day.add(Item(title, prio, id))
            # Update if Todoist item appears to have changed
            if day_item.prio != prio:
                day_item.prio = prio
            if day_item.desc != title:
                day_item.desc = title

        for day_item in day.items:
            if day_item.id:
                if not day_item.id in todoist_ids:
                    # Item has an id so used to be in todoist but isn't there anymore. Delete it.
                    day.items.remove(day_item)
            else:
                # No id, must be a new item. Add it to todoist
                item = self.api.add_item(day_item.desc)
                self.api.items.update(item.id, priority=day_item.ist_prio())
                self.api.commit()
                day_item.id = item.id

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
            project_name = self.project_by_id(project_id)['name']
            projects[project_name].append(string)
        res = ''
        for project, items in projects.items():
            res += project + '\n'
            for item in items:
                res += '   ' + item + '\n'
        return res

    ### ACTIONS ###

    def add_item(self, item):
        i = item.ist_prio()
        new = self.api.add_item(item.desc, priority=item.ist_prio())
        self.api.commit()
        return new['id']

    def complete_item(self, id):
        date_completed = datetime.datetime.today().strftime('%Y-%m-%d')

        self.api.items.complete(id, date_completed=date_completed)
        self.api.items.archive(id)
        self.api.commit()

    def delete_item(self, id):
        self.api.items.delete(id)
        self.api.commit()

    def edit_item(self, id, new_text):
        self.api.items.update(id, content=new_text)
        self.api.commit()

    def set_priority(self, id, priority):
        self.api.items.update(id, priority=priority)
        self.api.commit()

    def push_forward(self, id):
        due = {"string": "tomorrow"}
        self.api.items.update(id, due=due)
        self.api.commit()

    def push_back(self, id):
        prev_day = settings.getPrevDay(datetime.datetime.today()).strftime('%Y-%m-%d')
        self.api.items.complete(id, date_completed=prev_day)
        self.api.commit()

    def reschedule(self, id, date):
        due = {"string": date}
        self.api.items.update(id, due=due)
        self.api.commit()


if __name__ == '__main__':
    ist = Ist()
    inbox_project = ist.project_by_name('Inbox')
    inbox_items = ist.items(inbox_project)
    for item in inbox_items:
        print(item)
