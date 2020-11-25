import datetime
from settings import datafolder, priorities, getNextDay, getPrevDay, panic


class Day:
    items = []
    notedata = ''
    date = datetime.date.today()
    originaltext = ''

    ######### Construction, read and write ############

    def __init__( self, date=datetime.date.today() ):
        self.date = date
        self.items = []
        self.notedata = ''
        self.originaltext = ''
        self._dailyNotesBook = None

        #self.path = datafolder /  self.date.strftime( '%Y-%m-%d' ) + '.txt'
        self.path = datafolder /  f'{self.date}.txt'

        self.read()

    def read( self ):
        if not self.path.is_file():
            return

        #filetime = time.localtime( os.stat(self.filename())[8] )

        #note = None
        #if note and time.localtime( note.updated/1000 ) > filetime:
        #    self.originaltext = parseNote( note ).replace('<br/>',"\n")
        #else:
        with open( self.path ) as f:
            self.originaltext = f.read()

        data = self.originaltext.split( '\n\n',1 )
        tododata = data[0]
        if len(data)>1:
            self.notedata = data[1]
        else:
            self.notedata = ''

        for line in tododata.split( '\n' ):
            if not line: continue
            try:
                num = int(line.split( '. ')[0].strip())
            except:
                num = 0
            if num:
                line = line.split( '. ',1)[1]
            if line[:3] == 'X. ':
                num = 1
                line = line[3:]
                prio = 3
            elif line[0] in priorities:
                prio = priorities.index(line[0])
                line = line[2:]
            else:
                prio = 1

            if line.count(' :: '):
                line, id = line.split(' :: ')
                id = int(id)
            else:
                id = 0

            self.add( line, prio, id )

    def reorder( self ):
        self.items.sort( key=lambda a: a['prio'] )

    def write( self ):
        with open( self.path, 'w' ) as f:
            f.write( self.asText() )

    def by_id(self):
        # returns a dict of items that have an id != 0. Key of the dict is the id
        return {item['id']:item for item in self.items if item.get('id')}

    ######### Display ############

    def show( self, show_ids=False ):
        print( f"\nTo do's for {weekdays[self.date.weekday()]} {self.date.day} {monthnames[self.date.month-1]}\n")
        print( self.asStrings(display='screen', show_ids=show_ids) )

    def asStrings( self, display='file', show_ids=False ):
        res = ''
        #for i in range(len(self.items)):
        for i, item in enumerate( self.items, 1 ):
            if display=='screen':
                if i>1 and self.items[i-2]['prio']!=4 and item['prio']==4:
                    res += '\n'
            id = f" :: {item['id']}" if (display=='file' or show_ids) and item.get('id') else ""
            res += f"{i:2}. {priorities[item['prio']]} {item['desc']}{id}\n"
        return res

    def asText( self ):
        res = self.asStrings()
        if self.notedata:
            res += '\n'+ self.notedata
        return res

    ######### Operations ############

    def add( self, desc, prio=-1, id=0 ):
        if prio==-1:
            if desc[0] in priorities and desc[1]== ' ':
                # priority added with the description
                prio = priorities.index(desc[0])
                desc = desc[2:]
            else:
                prio = 1 # normal
        newitem = {'desc':desc, 'prio':prio, 'id':id}
        self.items += [newitem]
        return newitem

    def delete( self, num ):
        id = self.items[num-1].get('id')
        del[self.items[num-1]]
        return id

    def edit( self, num, newtext ):
        item = self.items[num-1]
        item['desc'] = newtext
        return item

    def setPriority( self, num, prio ):
        item = self.items[num-1]
        item['prio'] = prio
        return item

    def pushForward( self, num ):
        tomorrow = Day(getNextDay(self.date))
        id = self.items[num - 1].get('id')
        tomorrow.add( self.items[num-1]['desc'], self.items[num-1]['prio'], id )
        tomorrow.write()
        self.delete( num )
        return id

    def pushBack( self, num ):
        item = self.items[num-1]
        id = item.get('id')
        yesterday = Day(getPrevDay(self.date))
        yesterday.add( item['desc'], 4 ) # 4 is done
        yesterday.write()
        self.delete( num )
        return id

    def pushAllForward( self ):
        tomorrow = Day(getNextDay(self.date))
        for item in reversed(self.items):
            if item['prio'] < 4:
                tomorrow.add( item['desc'], item['prio'] )
                self.items.remove( item )
        tomorrow.write()

    def pullFromLast( self, num ):
        lastday = Day(getPrevDay(self.date))
        self.add( lastday.items[num-1]['desc'], lastday.items[num-1]['prio'] )
        lastday.delete( num )
        lastday.write()

    def pullAll( self ):
        lastday = Day( self.date )
        changed = False
        date = self.date
        for days in range( 10 ):
            date = getPrevDay(date)
            changed = self.pullFromDay( date ) or changed

    def pullFromDay( self, date ):
        lastday = Day( date )
        changed = 0
        for item in reversed(lastday.items):
            if priorities[item['prio']] < 'X':
                self.add( item['desc'], item['prio'] )
                lastday.items.remove( item )
                changed = 1
        if changed:
            lastday.write()
        return changed

    def schedule(self, desc, date_str):
        date = dmy2ymd(date_str)
        day = Day( date )
        item = day.add(desc)
        day.write()
        return item, date

    def reschedule(self, num, date_str):
        item = self.items[num - 1]
        id = item.get('id')
        date = dmy2ymd(date_str)
        day = Day(date)
        day.add(item['desc'], item['prio'], item.get('id'))
        day.write()
        self.delete(num)
        return id, date

    def duplicate( self, num ):
        item = self.items[num-1]
        self.items += [item]
        return item

def dmy2ymd(date_str):
    y = datetime.datetime.today().strftime('%Y')
    try:
        d, m, y = date_str.split('/')
    except:
        try:
            d, m = date_str.split('/')
        except:
            panic(f'Invalid date {date_str}. Specify in d/m or d/m/y format')
    #return datetime.datetime.strptime(f'{y}-{m}-{d}', '%Y-%m-%d')
    return f'{y}-{m}-{d}'

weekdays = ['Ma','Di','Wo','Do','Vr','Za','Zo']
monthnames = ['jan','feb','maart','apr','mei','jun','jul','aug','sept','okt','nov','dec']
priorityActions = ['high','normal','low','miek','done']
