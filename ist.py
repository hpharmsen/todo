import datetime
from collections import defaultdict
#from typing import List

from todoist_api_python.api import TodoistAPI
from todoist_api_python.models import Task

import settings
from dayclass import TodoDay
from item import Item, PRIORITY_MAP

TODAY = datetime.datetime.now().strftime("%Y-%m-%d")

# Hoe het werkt met prioriteiten
# In todo: ['!','-','~','M','X']
# 0 = high, 1 = normal, 2 = low, 3 = other, 4 = done
#
# In todoist
# p1 = low, p2 = other, p3 = normal, p4 = high

def ist2todoprio(prio: int, is_completed: bool):
    # p4 = 1 -> 1 normal
    # p3 = 2 -> 3 other
    # p2 = 3 -> 2 low
    # p1 = 4 -> 0 high

    if is_completed:
        return 4  # done
    else:
        return PRIORITY_MAP[prio]


class Ist:
    def __init__(self):
        self.api = TodoistAPI(settings.todoist_api_key)
        # try:
        #     self.api.sync()
        # except requests.exceptions.ConnectionError:
        #     return None  # Network
        self.projects = self.get_projects()


    def tasks(self, project: object = None, scheduled: object = False, deleted: object = False,
              completed_today: object = True) -> list[Task]:
        result = []
        for task in self.api.get_tasks():

            # Filter out completed items
            if task.is_completed:
                continue
            # if item["date_completed"]:
            #     if item["date_completed"].split("T")[0] < TODAY:
            #         continue
            #     if item["date_completed"].split("T")[0] == TODAY and not completed_today:
            #         continue

            # Filter out items assigned to someone else, unless assigned by me
            if task.assignee_id and task.assignee_id != settings.todoist_user_id:
                by = task.assigner_id
                u = settings.todoist_user_id
                if task.assigner_id == settings.todoist_user_id:
                    task.priority = 2  # Blauw
                else:
                    continue

            # Filter out items from shared projects that are not assigned to nor assigned by me

            own_projects = [p.id for p in self.projects if not p.is_shared]
            if (
                not task.project_id in own_projects
                and task.assignee_id != settings.todoist_user_id
                and task.assigner_id != settings.todoist_user_id
            ):
                continue

            # If specified filter out all items not belonging to the project.
            if project and task.project_id != project.id:
                continue

            # Filter out deleted items
            #if not deleted and item["is_deleted"]:
            #    continue

            # Filter out items scheduled for a later time
            if not scheduled and task.due and task.due.date > TODAY:
                continue

            result += [task]

        return result

    def get_projects(self):
        return self.api.get_projects()

    def project_by_name(self, project_name):
        for project in self.projects:
            if project.name == project_name:
                return project

    def project_by_id(self, project_id):
        for project in self.projects:
            if project.id == project_id:
                return project

    def sync(self, day: TodoDay):
        """ Sync runt na evt actie zoals het toevoegen of verwijderen van items.
        Sync doet twee dingen:
        1. Check of er items in day staan die niet in todoist staan, zo ja, verwijder ze uit day
        2. Loop de items in todoist door, update day waar nodig of voeg zelfs toe aan day
        """
        todoist_tasks = self.tasks(deleted=True, scheduled=False, completed_today=True)
        todoist_by_title = {task.content: task for task in todoist_tasks}
        for day_item in day.items:
            todoist_task = todoist_by_title.get(day_item.desc)
            if not todoist_task:
                # Item not found in todoist. Delete it.
                print("    ", day_item.desc, "not found in todoist. Deleting it.")
                day.items.remove(day_item)

        day_items_by_title = {item.desc: item for item in day.items}
        for todoist_task in todoist_tasks:
            prio = ist2todoprio(todoist_task.priority, todoist_task.is_completed)
            day_item = day_items_by_title.get(todoist_task.content)
            if day_item:
                if day_item.prio != prio:
                    # Todoist item appears to have changed: update
                    print("    ", todoist_task.content, "changed prio in todoist. Updating it.")
                    day_item.prio = prio
            else:
                # Todoist item not found in day. Add it
                day_item = day.add(Item(todoist_task.content, prio, todoist_task.id))
                print("    ", todoist_task.content, "not found in day. Adding it.")


    def __str__(self):
        projects = defaultdict(list)
        for task in self.tasks(completed_today=False):
            marker = "X" if task.is_completed else settings.priorities[task.priority]
            content = task.content
            due = " @ " + task.due.date if task.due else ""
            completed = " √ " if task.is_completed else ""
            string = marker + " " + content + due + completed

            project_id = task.project_id
            project_name = self.project_by_id(project_id).name
            projects[project_name].append(string)
        res = ""
        for project, items in projects.items():
            res += project + "\n"
            for task in items:
                res += "   " + task + "\n"
        return res

    ### ACTIONS ###

    def add_item(self, item):
        i = item.ist_prio()
        new = self.api.add_task(item.desc, priority=item.ist_prio())
        #self.api.commit()
        if new:
            if type(new) == str:
                print(new)
            else:
                return new.id

    def complete_item(self, id):
        self.api.close_task(id)

    def delete_item(self, id):
        self.api.delete_task(id)

    def edit_item(self, id, new_text):
        self.api.update_task(id, content=new_text)

    def set_priority(self, id, priority):
        self.api.update_task(id, priority=priority)

    def push_forward(self, id):
        self.api.update_task(id, due_string="tomorrow")

    def push_back(self, id):
        #prev_day = settings.getPrevDay(datetime.datetime.today()).strftime("%Y-%m-%d")
        self.api.close_task(id)

    def reschedule(self, id, date):
        self.api.update_task(id, due_date=date)


if __name__ == "__main__":
    ist = Ist()
    inbox_project = ist.project_by_name("Inbox")
    inbox_items = ist.tasks(inbox_project)
    for item in inbox_items:
        print(item)
