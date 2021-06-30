import re
import sys


def panic(s):
    print(s)
    sys.exit(1)


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GREEN = '\x1b[1;32;40m' # https://stackoverflow.com/questions/287871/how-to-print-colored-text-to-the-terminal/293633#293633
    GRAY = '\x1b[1;30;40m'


def extractDuration(s):
    match = re.match('(\d*\.?\d+)([hm])', s)
    if not match:
        return
    number = float(match.groups()[0])
    if match.groups()[1] == 'h':
        return number
    else:
        return 1.0 * number / 60


