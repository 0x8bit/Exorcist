from imports import *

vlevel = 0
more_cmmnts = 0

###############################################################################

class Timer():
    def start(self):
        self.time_s = time.perf_counter()
    def stop(self):
        self.time_e = time.perf_counter() - self.time_s
        print("Execution Time: %.3f seconds" % self.time_e) 


def verbose(level):
    global vlevel

    if(len(level) >= 1 or len(level) <= 2):
        vlevel = len(level)
    if((len(level) > 2 or len(level) <= 5)):
        vlevel = len(level)

def get_args(arg, *, lone=False, opFile=False, argv=sys.argv):
    """
    get arguments value from console
    """ 
    
    try:
        argument = argv.index(arg)
        if argument and lone:        #lone arguments
            return True

        value = argv[argument + 1]
        isFile = os.path.isfile(value)
        isFile_path = os.path.abspath(os.path.normpath(value)) if isFile else False

        if isFile and opFile:   #return an open file descriptor to be closed by the caller
            file = open(isFile_path, 'r')
            return file         
        if isFile:
            return isFile_path
        return value
    except:
        return 0

def log(string, logfile):
    """
    create or use an existing log file
    """

    logfile = os.path.abspath(os.path.normpath(logfile))
    exist = os.path.exists(logfile)
    if exist:
        with open(logfile, 'a') as log:
            log.writelines(string)
    else:
        with open(logfile, 'w') as log:
            log.writelines(string)

def exactmatch(substr, string, *, lastChar=False, index=False, ignoreCase=True):
    query = "\\b" + substr + (lastChar if lastChar else "\\b")
    flag = re.IGNORECASE if ignoreCase else 0 
    search = re.search(query, string, flag)

    if index and search:
        start, end = search.span()
        return (start, end)
    return (search)

#this routine is designed to be used with an iterator (e.g map())
def discard_cmmnts(line):
    global more_cmmnts

    if more_cmmnts > 0:
        if line.find('*/') >= 0:
            more_cmmnts = 0
            return ''
        else:
            return ''

    cmmnt_token = '/*'
    cmmnt = line.find(cmmnt_token)
    if cmmnt == 0:
        if line.find('*/') >= 0:
            new_line = ''
            return new_line
        else:
            more_cmmnts = 1
            return ''
    elif cmmnt > 0:
        for i in range(cmmnt).__reversed__():
            if line[i] in [';', '(', ')' '{', '}', '[', ']'  '\\']:
                if (end := line.find('*/')) >= 0:
                    new_line = line.replace(line[cmmnt:end+2], '')
                    return new_line
                else:
                    new_line = line.rstrip(line[cmmnt:])
                    more_cmmnts = 1
                    return new_line
            else:
                if line[i].isspace():
                    if (end := line.find('*/')) >= 0:
                        new_line = line.replace(line[cmmnt:end+2], '')
                        return new_line
                    else:
                        new_line = line.rstrip(line[cmmnt:])
                        more_cmmnts = 1
                        return new_line
                else:
                    continue
    else:
        pass

    cmmnt_token = '//'  
    cmmnt = line.find(cmmnt_token)
    if cmmnt == 0:
        new_line = ''
        return new_line
    elif cmmnt > 0:
        for i in range(cmmnt).__reversed__():   # Read backward
            if line[i] in [';', '(', ')' '{', '}', '[', ']'  '\\']:
                new_line = line.rstrip(line[cmmnt:])
                return new_line
            else:
                if line[i].isspace():
                    new_line = line.rstrip(line[cmmnt:])
                    return new_line
                else:
                    continue
    else:
        return line

def _exactmatch(query, string):     #SLOW                                #working but a little slow (probably *don't use*)
    """
    Find a substring exact match in a contiguos string line
    """
    str_len = len(string)
    for i in range(1, str_len+1):
        substr, index = readN(i, string)        #read i, return the string at offset i and next index
        found = substr.find(query)
        #print(substr, index)

        if found < 0:
            continue

        if found >= 0:
            char_before = substr[found-1]
            if i < str_len and index != str_len:
                char_after = string[index]
            if ((char_before != " ") or (char_after != " ")) and (index != str_len) and (found > 0):
                string = poison(string, found, query)    # poison the substring so that find() won't hit it again     
                string += string[index:]
                continue
            else:
                return found
        
    if index == str_len and found < 0:
        return -1

def random_string(N):
    ret = ''.join(random.choices(string.ascii_uppercase + \
                  string.ascii_lowercase + string.digits, k=N))
    return ret

def printHelp(args):
    print("")
    for i,j in args.items():
        print("%s %s" % (i.ljust(15), Fore.BLUE + j[1]))
    os._exit(1)

def print_function(text, start, end, numlines=1):
    lines = text[start-1:end]             # like split('\n') but no '' at end
    while lines:
        chunk = lines[:numlines]
        lines = lines[numlines:]
        for line in chunk: print(Back.GREEN + Fore.LIGHTWHITE_EX + line)
        if lines and input() in ['Q', 'q']: break

def find_file(sline, file):
    for i in sline.keys():
        if os.path.basename(i) == file:
            return i
    return 0
