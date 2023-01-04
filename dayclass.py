from item import Item
from settings import datafolder, priorities
from base import bcolors
from justdays import Day, Period

class TodoDay:
    items = []  # List of Item
    notedata = ""
    date = Day()
    originaltext = ""

    ######### Construction, read and write ############

    def __init__(self, date=Day()):
        self.date = date
        self.items = []
        self.notedata = ""
        self.originaltext = ""
        self._dailyNotesBook = None

        self.path = datafolder / f'{self.date}.txt'

        self.read()

    def read(self):
        if not self.path.is_file():
            return

        with open(self.path) as f:
            self.originaltext = f.read()

        data = self.originaltext.split("\n\n", 1)
        tododata = data[0]
        if len(data) > 1:
            self.notedata = data[1]
        else:
            self.notedata = ""

        for line in tododata.split("\n"):
            if not line:
                continue
            try:
                num = int(line.split(". ")[0].strip())
            except:
                num = 0
            if num:
                line = line.split(". ", 1)[1]
            if line[:3] == "X. ":
                num = 1
                line = line[3:]
                prio = 3
            elif line[0] in priorities:
                prio = priorities.index(line[0])
                line = line[2:]
            else:
                prio = 1

            if line.count(" :: "):
                line, id = line.split(" :: ")
                id = int(id)
            else:
                id = 0

            self.add(Item(line, prio, id))

    def reorder(self):
        self.items.sort(key=lambda a: a.prio)

    def write(self):
        with open(self.path, "w") as f:
            f.write(self.asText())

    def by_id(self):
        # returns a dict of items that have an id != 0. Key of the dict is the id
        return {item.id: item for item in self.items if item.id}

    ######### Display ############

    def show(self, show_ids=False):
        print(f"\nTo do's for {weekdays[self.date.day_of_week()]} {self.date.d} {monthnames[self.date.m-1]}\n")
        print(self.asStrings(display="screen", show_ids=show_ids))

    def asStrings(self, display="file", show_ids=False):
        res = ""
        for i, item in enumerate(self.items, 1):
            if display == "screen":
                # Empty line between before the done items
                if i > 1 and self.items[i - 2].prio != 4 and item.prio == 4:
                    res += "\n"
                if item.prio in (2, 4):
                    res += bcolors.GRAY
            id = f" :: {item.id}" if (display == "file" or show_ids) and item.id else ""
            res += f"{i:2}. {item}{id}"
            if display == "screen" and item.prio in (2, 4):
                res += bcolors.ENDC
            res += "\n"
        return res

    def asText(self):
        res = self.asStrings()
        if self.notedata:
            res += "\n" + self.notedata
        return res

    ######### Operations ############

    def add(self, item):
        if item.prio == -1:
            if item.desc[0] in priorities and item.desc[1] == " ":
                # priority added with the description
                item.prio = priorities.index(item.desc[0])
                item.desc = item.desc[2:]
            else:
                item.prio = 1  # normal
        self.items += [item]
        return item

    def delete(self, num):
        id = self.items[num - 1].id
        del [self.items[num - 1]]
        return id

    def edit(self, num, newtext):
        item = self.items[num - 1]
        item.desc = newtext
        return item

    def setPriority(self, num, prio):
        item = self.items[num - 1]
        item.prio = prio
        return item

    def pushForward(self, num):
        item = self.items[num - 1]
        id = item.id
        tomorrow = TodoDay(self.date.next_weekday())
        tomorrow.add(item.dup())
        tomorrow.write()
        self.delete(num)
        return id

    def pushBack(self, num):
        item = self.items[num - 1]
        id = item.id
        new_item = Item(item.desc, 4)  # 4 is done
        yesterday = TodoDay(self.date.previous_weekday())
        yesterday.add(new_item)
        yesterday.write()
        self.delete(num)
        return id

    def pushAllForward(self):
        tomorrow = TodoDay(self.date.next_weekday())
        for item in reversed(self.items):
            if item.prio < 4:
                tomorrow.add(item.dup())
                self.items.remove(item)
        tomorrow.write()

    def pullFromLast(self, num):
        lastday = TodoDay(self.date.previous_weekday())
        self.add(lastday.items[num - 1].dup())
        lastday.delete(num)
        lastday.write()

    def pullAll(self):
        for date in Period(self.date.plus_days(-1), self.date):
            self.pullFromDay(date)

    def pullFromDay(self, date):
        lastday = TodoDay(date)
        changed = 0
        for item in reversed(lastday.items):
            if item.prio < 4:
                self.add(item.dup())
                lastday.items.remove(item)
                changed = 1
        if changed:
            lastday.write()
        return changed

    def schedule(self, desc, date):
        day = TodoDay(date)
        item = day.add(desc)
        day.write()
        return item, date

    def reschedule(self, num, date):
        item = self.items[num - 1]
        id = item.id
        day = TodoDay(date)
        day.add(item.dup())
        day.write()
        self.delete(num)
        return id, date

    def duplicate(self, num):
        item = self.items[num - 1].dup()
        item.id = 0
        self.items += [item]
        return item


weekdays = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"]
monthnames = [
    "jan",
    "feb",
    "maart",
    "apr",
    "mei",
    "jun",
    "jul",
    "aug",
    "sept",
    "okt",
    "nov",
    "dec",
]
priorityActions = ["high", "normal", "low", "other", "done"]
