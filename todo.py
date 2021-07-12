import sys
import subprocess
from collections import namedtuple

# TODO:
# - assign to specific person
# - Do not sync items from shared todoist projects that are not assigned to me nor assigned by me

from dayclass import Day, datafolder, priorityActions
from settings import getNextDay, getPrevDay, todoist_api_key
from base import panic, extractDuration, isDate

if todoist_api_key:
    from ist import Ist  # todoist
from item import Item
from simplicate import (
    book,
    hours_booked_status,
    approve_hours,
    printHoursBooked,
    DATE_FORMAT,
)

Command = namedtuple("Command", "action itemnumber text timespent task date")


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
        panic("Provide integer as 2nd parameter")


def getTextParam(paramnum=2):
    if not sys.argv[paramnum:]:
        panic("Provide text as parameter " + str(paramnum))
    args = sys.argv[paramnum:]
    res = ""
    for i in range(len(args)):
        if extractDuration(args[i]):
            return res
        if res:
            res += " "
        res += args[i]
    return res


def getDurationParam(paramnum=2):
    if not sys.argv[paramnum:]:
        panic("Provide text as parameter " + str(paramnum))
    args = sys.argv[paramnum:]
    for i in range(len(args)):
        duration = extractDuration(args[i])
        if duration:
            return duration, " ".join(args[i + 1 :])


def data_files():
    return [
        filepath
        for filepath in datafolder.iterdir()
        if filepath.is_file() and filepath.suffix == ".txt"
    ]


def findText(needle):
    needle = needle.lower()
    for filepath in data_files():
        lines = open(filepath).readlines()
        for line in lines:
            if line.lower().count(needle):
                print(filepath.name[:-4] + " " + line.strip())


def findMeeting(needle):
    title = ""
    needle = needle.lower()
    for filepath in data_files():
        with open(filepath) as f:
            lines = f.readlines()
        status = ""
        contents = []
        for line in lines:
            if status == "collecting":
                if line.startswith("---") or line.startswith("———"):
                    status = ""
                    contents = contents[:-2]
                else:
                    contents += [line]
            elif status == "found":
                if line.startswith("---"):
                    status = "collecting"
                else:
                    status = ""
            elif line.lower().count(needle):
                status = "found"
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


def printPriorities():
    pass


def parse_commandline():
    def append(oldtext, newtext):
        if oldtext:
            return oldtext + " " + newtext
        return newtext

    action = ""
    itemnumber = None
    text = ""
    timespent = 0
    task = ""
    date = None

    if len(sys.argv) > 1:
        action = sys.argv[1].lower()  # first param is almost always the action
        if isDate(action):
            params = sys.argv[1:]  # Unless it's a date
            action = ""
        else:
            params = sys.argv[2:]
        try:
            itemnumber = int(params[0])
            params = params[1:]
        except:
            pass

        # Fill command.text with the rest of the command line params
        # unless something special (duration, date) happens
        collecting_task = False
        for param in params:
            duration = extractDuration(param)
            if duration:  # Duration found
                timespent = duration
                collecting_task = True
                param = ""
            if date := isDate(param):  # Date found
                break
            # Param is just text, add it to command.text or command.task depending on where we are
            if collecting_task:
                task = append(task, param)
            else:
                text = append(text, param)
    return Command(action, itemnumber, text, timespent, task, date)


def get_todoist(day):
    ist = None
    if todoist_api_key:
        ist = Ist()
        ist.sync(day)
    return ist


def printHelp():
    print("todo                        - lists todays items")
    print("todo last                   - lists last working day")
    print("todo next                   - lists next working day")
    print("todo add thingie            - adds thingie to todays list")
    print("todo del 9                  - removes item 9")
    print("todo edit 9 blah            - changes text of item to blah")
    print("todo dup 9                  - duplicates item 9")
    print("todo high 9                 - sets item to high priority")
    print("toto normal 9               - sets item to normal priority")
    print("todo low 9                  - sets item to low priority")
    print("todo low thingie            - adds thingie and marks it as low priority")
    print("todo done 9                 - marks item as done")
    print("todo done thingie           - adds thingie and marks it as done")
    print("todo undone 9               - marks item as undone")
    print("todo push [9]               - moves item or all undone to the next day")
    print(
        "todo pull [9]               - moves item or all undone from previous day to current"
    )
    print(
        "todo pushback [9]           - moves item or all undone from previous day to current"
    )
    print("todo schedule 9 d/m/[y]      - moves item 9 to the specfied day")
    print("todo schedule thing d/m[/y] - adds thing to the specfied day")
    print("todo today                  - prints the day" "s file in full")
    print("todo find text              - finds any line with text")
    print("todo meeting text           - finds meetings with text in the name")
    print("todo booked                 - list hours booked today")
    print("todo note                   - opens editor with the current day")
    print(
        "todo ready                  - closes day in timesheet and pushes all open items to next day"
    )
    print("todo ids                    - shows the list with todoist id's")
    print("todo help                   - this message\n")


if __name__ == "__main__":
    command = parse_commandline()
    if command.action == "undone":
        command.action = "normal"
    print(command)

    # Load the right day
    if command.date and command.action in (
        "",
        "add",
        "del",
        "dup",
        "low",
        "high",
        "normal",
        "miek",
        "edit",
        "today",
        "booked",
        "note",
        "log",
    ):
        day = Day(command.date)
        ist = None
    else:
        day = Day()
        day.pullAll()
        ist = get_todoist(day)

    # Go process the command
    DayAction = True
    show_ids = False
    action = command.action

    if not action:  # Just a listing
        if command.date:
            day = Day(command.date)
            ist = None

    elif action == "add":
        if not command.text:
            panic("Pass text to add command")
        todo_item = day.add(Item(command.text))
        if ist:
            todo_item.id = ist.add_item(todo_item)

    elif action == "del":
        if not command.itemnumber:
            panic("Pass an item number to del command")
        id = day.delete(command.itemnumber)
        if id and ist:
            ist.delete_item(id)

    elif action == "dup":
        if not command.itemnumber:
            panic("Pass an item number to dup command")
        item = day.duplicate(command.itemnumber)
        if ist:
            item.id = ist.add_item(item)

    elif action in priorityActions:
        if command.date:
            day = Day(command.date)
            ist = None
        prio = priorityActions.index(action)
        if command.itemnumber:
            # syntax: todo high 3
            oldprio = day.items[command.itemnumber - 1].prio
            item = day.setPriority(command.itemnumber, prio)
            if item.id and ist:
                try:
                    ist.set_priority(item.id, item.ist_prio())
                except Exception as e:
                    if item.ist_prio() == 4:
                        pass
                    else:
                        raise e

        else:
            # syntax: todo low read a boook
            if command.text:
                item = day.add(Item(command.text, prio))
                if ist:
                    item.id = ist.add_item(item)
            else:
                # syntax: todo done 3h overleg
                item = Item(
                    ""
                )  # Special case, only book hours if specified. No todo item.

        if action == "done":
            if item.id and ist:
                try:
                    ist.complete_item(item.id)
                except:
                    pass  # Is toch done dus who cares
            if command.timespent:
                # syntax: todo done [4|task description] 3h overleg
                if not command.task:
                    panic("Specify project/task. Syntax: todo done 1 3h Sales")

                if not book(
                    command.task,
                    command.timespent,
                    item.desc,
                    day.date.strftime(DATE_FORMAT),
                ):
                    # Set back the prio to what it was
                    if command.itemnumber == None:
                        # Remove (do not add) the item
                        # Should be refactored so item will not be added in the first place
                        id = day.delete(len(day.items))
                        if id and ist:
                            ist.delete_item(id)
                    else:
                        # Set prio back to the old prio
                        day.setPriority(command.itemnumber, oldprio)
                    day.write()
                    sys.exit()
    elif action == "push":
        if command.itemnumber:
            id = day.pushForward(command.itemnumber)
            if id and ist:
                ist.push_forward(id)
        elif command.text:
            panic("Pushing new items is not yet supported")
        else:
            push_all(day, ist)

    elif action == "pull":
        if command.itemnumber:
            day.pullFromLast(command.itemnumber)
        else:
            day.pullAll()

    elif action == "pushback":
        if not command.itemnumber:
            panic("Pass item number to pushback command")
        id = day.pushBack(command.itemnumber)
        if id and ist:
            ist.push_back(id)

    elif action == "schedule":
        if command.itemnumber:
            # syntax: todo schedule d/m[/y] 9
            id, date = day.reschedule(command.itemnumber, command.date)
            if id and ist:
                ist.reschedule(id, date)
        else:
            # syntax: todo schedule d/m[/y] thingie
            item, date = day.schedule(Item(command.text), command.date)
            if ist:
                item.id = ist.add_item(item)
                ist.reschedule(item.id, date)

    elif action == "next":
        day = Day(getNextDay(day.date))

    elif action == "last":
        day = Day(getPrevDay(day.date))

    elif action == "edit":
        if not command.itemnumber:
            panic("Pass item number to edit command")
        if not command.text:
            panic("Pass new text to edit command")
        item = day.edit(command.itemnumber, command.text)
        if ist:
            ist.edit_item(item.id, command.text)

    elif action == "today":
        print(day.asText())
        DayAction = False

    elif action == "find":
        findText(getTextParam())
        DayAction = False

    elif action == "meeting":
        findMeeting(command.text)

    elif action == "booked":
        printHoursBooked(day.date)
        print(hours_booked_status(day.date))
        DayAction = False

    elif action == "note":
        subprocess.run(["open", day.path], check=True)

    elif action == "ready":
        approve_hours()
        if ist:
            push_all(day, ist)

    elif action == "ids":
        # Show the todo list with todoist id's
        show_ids = True

    elif action == "help":
        printHelp()
        DayAction = False

    elif action == "log":
        # syntax: todo log Offerte maken 3h Sales
        if not command.timespent:
            panic("specify duration like 30m or 1h")
        if not command.task:
            panic("Specify project/task. Syntax: todo log Offerte maken 3h Sales")

        comment = getTextParam()
        if not book(
            command.task, command.timespent, comment, day.date.strftime(DATE_FORMAT)
        ):
            sys.exit()
        DayAction = 0

    else:
        panic("Unknown action: " + action)

    if DayAction:
        printPriorities()
        day.reorder()
        day.show(show_ids)
        if day.originaltext != day.asText():
            day.write()

        print(hours_booked_status(day.date))
