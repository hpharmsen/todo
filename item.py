from dataclasses import dataclass

from settings import priorities


@dataclass()
class Item:
    desc: str
    prio: int = 1
    id: int = 0

    def dup(self):
        return Item(self.desc, self.prio, self.id)

    def __repr__(self):
        desc = self.desc.replace('\n', ' ')
        return f"{priorities[self.prio]} {desc}"

    def ist_prio(self):
        # 0 -> 4
        # 1 -> 3
        # 2 -> 1
        # 3 -> 2 and Assign to someone else
        # 4 -> Set to done
        return {0: 4, 1: 3, 2: 1, 3: 2, 4: 4}[self.prio]
