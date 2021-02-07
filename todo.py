import sys, re
import subprocess

# TODO:
# - assign to specific person
# - Do not sync items from shared todoist projects that are not assigned to me nor assigned by me

from dayclass import Day, datafolder, priorityActions
from ist import Ist  # todoist
from settings import panic, getNextDay, getPrevDay
from item import Item
from simplicate import book, hours_booked_status, hours_booked, approve_hours


def isInt(s):
    try:
        int(s)
        return 1
    except:
        return 0


def getIntParam():
    try:
        return int(sys.argv[2])
    except:
        panic('Provide integer as 2nd parameter')


def extractDuration(s):
    match = re.match('(\d*\.?\d+)([hm])', s)
    if not match:
        return
    number = float(match.groups()[0])
    if match.groups()[1] == 'h':
        return number
    else:
        return 1.0 * number / 60


def getTextParam(paramnum=2):
    if not sys.argv[paramnum:]:
        panic('Provide text as parameter ' + str(paramnum))
    args = sys.argv[paramnum:]
    res = ''
    for i in range(len(args)):
        if extractDuration(args[i]):
            return res
        if res:
            res += ' '
        res += args[i]
    return res


def getDurationParam(paramnum=2):
    if not sys.argv[paramnum:]:
        panic('Provide text as parameter ' + str(paramnum))
    args = sys.argv[paramnum:]
    for i in range(len(args)):
        duration = extractDuration(args[i])
        if duration:
            return duration, ' '.join(args[i + 1 :])


def data_files():
    return [filepath for filepath in datafolder.iterdir() if filepath.is_file() and filepath.suffix == '.txt']


def findText(needle):
    needle = needle.lower()
    for filepath in data_files():
        lines = open(filepath).readlines()
        for line in lines:
            if line.lower().count(needle):
                print(filepath.name[:-4] + ' ' + line.strip())


def findMeeting(needle):
    title = ''
    needle = needle.lower()
    for filepath in data_files():
        with open(filepath) as f:
            lines = f.readlines()
        status = ''
        contents = []
        for line in lines:
            if status == 'collecting':
                if line.startswith('---') or line.startswith('———'):
                    status = ''
                    contents = contents[:-2]
                else:
                    contents += [line]
            elif status == 'found':
                if line.startswith('---'):
                    status = 'collecting'
                else:
                    status = ''
            elif line.lower().count(needle):
                status = 'found'
                title = line.strip()
        if contents:
            print(f"\n=============\n{filepath.name[:-4]} {title}\n---")
            print("".join(contents).strip())


def push_all(day, ist):
    for item in day.items:
        if item.id and item.prio < 4:  # 4 is done
            try:
                ist.push_forward(item.id)
            except:
                pass  # Er is dan wel iets raars aan de hand
    day.pushAllForward()


def printHoursBooked():
    lines = ['{booked:0.2f} {project}, {task} - {note}'.format(**line) for line in hours_booked()]
    print('\n'.join(sorted(lines)))


def printPriorities():
    pass


def printHelp():
    print('todo                        - lists todays items')
    print('todo last                   - lists last working day')
    print('todo next                   - lists next working day')
    print('todo add thingie            - adds thingie to todays list')
    print('todo del 9                  - removes item 9')
    print('todo edit 9 blah            - changes text of item to blah')
    print('todo dup 9                  - duplicates item 9')
    print('todo high 9                 - sets item to high priority')
    print('toto normal 9               - sets item to normal priority')
    print('todo low 9                  - sets item to low priority')
    print('todo low thingie            - adds thingie and marks it as low priority')
    print('todo done 9                 - marks item as done')
    print('todo done thingie           - adds thingie and marks it as done')
    print('todo undone 9               - marks item as undone')
    print('todo push [9]               - moves item or all undone to the next day')
    print('todo pull [9]               - moves item or all undone from previous day to current')
    print('todo pushback [9]           - moves item or all undone from previous day to current')
    print('todo schedule d/m/[y] 9     - moves item 9 to the specfied day')
    print('todo schedule d/m[/y] thing - adds thing to the specfied day')
    print('todo today                  - prints the day' 's file in full')
    print('todo find text              - finds any line with text')
    print('todo meeting text           - finds meetings with text in the name')
    print('todo booked                 - list hours booked today')
    print('todo note                   - opens editor with the current day')
    print('todo ready                  - closes day in timesheet and pushes all open items to next day')
    print("todo ids                    - shows the list with todoist id's")
    print('todo help                   - this message\n')


if __name__ == '__main__':
    ist = Ist()
    day = Day()
    day.pullAll()
    ist.sync(day)

    action = ''
    DayAction = True
    show_ids = False

    if len(sys.argv) > 1:
        action = sys.argv[1].lower()
        params = sys.argv[2:]

        if action == 'undone':
            action = 'normal'

        if action == 'add':
            todo_item = day.add(Item(getTextParam()))
            todo_item.id = ist.add_item(todo_item)

        elif action == 'del':
            id = day.delete(getIntParam())
            if id:
                ist.delete_item(id)

        elif action == 'dup':
            item = day.duplicate(getIntParam())
            item.id = ist.add_item(item)

        elif action in priorityActions:
            prio = priorityActions.index(action)
            if isInt(sys.argv[2]):
                # syntax: todo high 3
                item = day.setPriority(getIntParam(), prio)
                if item.id:
                    try:
                        ist.set_priority(item.id, item.ist_prio())
                    except Exception as e:
                        if item.ist_prio() == 4:
                            pass
                        else:
                            raise e

            else:
                # syntax: todo low read a boook
                if getTextParam(2):
                    item = day.add(Item(getTextParam(2), prio))
                    item.id = ist.add_item(item)
                else:
                    # syntax: todo done 3h overleg
                    item = Item('')  # Special case, only book hours if specified. No todo item.

            if action == 'done':
                if item.id:
                    try:
                        ist.complete_item(item.id)
                    except:
                        pass  # Is toch done dus who cares
                durationtuple = getDurationParam()
                if durationtuple:
                    # syntax: todo done [4|task description] 3h overleg
                    duration, project = durationtuple
                    if not project:
                        panic('Specify project/task. Syntax: todo done 1 3h Sales')

                    if not book(project, duration, item.desc):
                        sys.exit()
        elif action == 'push':
            if len(sys.argv) == 3:
                id = day.pushForward(getIntParam())
                if id:
                    ist.push_forward(id)
            else:
                push_all(day, ist)

        elif action == 'pull':
            if len(sys.argv) == 3:
                day.pullFromLast(getIntParam())
            else:
                day.pullAll()

        elif action == 'pushback':
            id = day.pushBack(getIntParam())
            if id:
                ist.push_back(id)

        elif action == 'schedule':
            date_str = sys.argv[2]
            if isInt(sys.argv[3]):
                # syntax: todo schedule d/m[/y] 9
                id, date = day.reschedule(int(sys.argv[3]), date_str)
                if id:
                    ist.reschedule(id, date)
            else:
                # syntax: todo schedule d/m[/y] thingie
                item, date = day.schedule(getTextParam(3), date_str)
                item.id = ist.add_item(item)
                ist.reschedule(item.id, date)

        elif action == 'next':
            day = Day(getNextDay(day.date))

        elif action == 'last':
            day = Day(getPrevDay(day.date))

        elif action == 'edit':
            num = getIntParam()
            new_text = getTextParam(3)
            item = day.edit(num, new_text)
            ist.edit_item(item.id, new_text)

        elif action == 'today':
            print(day.asText())
            DayAction = False

        elif action == 'find':
            findText(getTextParam())
            DayAction = False

        elif action == 'meeting':
            findMeeting(getTextParam())

        elif action == 'booked':
            printHoursBooked()
            print(hours_booked_status())
            DayAction = False

        elif action == 'note':
            subprocess.run(['open', day.path], check=True)

        elif action == 'ready':
            approve_hours()
            push_all(day, ist)

        elif action == 'ids':
            # Show the todo list with todoist id's
            show_ids = True

        elif action == 'help':
            printHelp()
            DayAction = False

        elif action == 'log':
            # syntax: todo log Offerte maken 3h Sales
            durationtuple = getDurationParam()
            if not durationtuple:
                panic('specify duration like 30m or 1h')
            duration, project = durationtuple
            if not project:
                panic('Specify project/task. Syntax: todo log Offerte maken 3h Sales')

            comment = getTextParam()
            if not book(project, duration, comment):
                sys.exit()
            DayAction = 0

        else:
            panic('Unknown action: ' + action)

    if DayAction:
        printPriorities()
        day.reorder()
        day.show(show_ids)
        if day.originaltext != day.asText():
            day.write()

        print(hours_booked_status())
