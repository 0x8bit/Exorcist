from utils import *

files = []
visited = set()
properties = {}
slines = {}
unsafe_func = ['memcpy', 'strcpy', 'realloc', 'free', 'system', 'malloc']         #not exhaustive list, just for test
root_dir = ""

args = {"-v":[get_args('-v', lone=True), "verbose"], "-s":[get_args('-s'), "Search"], 
        "-f":[get_args('-f'), "File"], "-o":[get_args('-o'), "Log file"],  
        "-d":[get_args('-d'), "Directory"], "--sfile":[get_args('--sfile', opFile=True), "Take search queries from file"], 
        "-l":[get_args('-l'), "Lines to scan only"], "--exact":[get_args('--exact', lone=True), "Exact match"], 
        "-i":[get_args('-i', lone=True), "Case sensitive"], "--func-attr":[get_args('--func-attr'), "Get function attributes. Parameters must be supplied this way\n" "\t\t\"funtion name,return type,source file\""],
        "-h | --help":[get_args('-h' if ('-h' in sys.argv) else '--help', lone=True), "Show help"] }

        
vlevel = 0

def getlines(dir):
    """
    Take a dir/file. If it's a directory, operate only on files that endswith (.c, .cc, .cpp) 
    then parse all lines to a dictionary whose key is the full filepath. Same goes for a specific file 
    input except that there are no extension restrictions.
    """
    global slines, visited
    if os.path.isdir(dir):     # walk directories
        root_dir = dir
        for (head, subdir, files) in os.walk(dir):
            for sfiles in files:
                if sfiles.endswith(('.c', '.cc', '.cpp')):
                    fullpath = os.path.join(os.path.normpath(head), sfiles)
                    if fullpath in visited:
                        continue
                    visited.add(fullpath)
        
                    try:
                        with open(fullpath, 'r') as sfile:
                            slines[fullpath] = list(map(discard_cmmnts, sfile.readlines()))
                    except:
                        with open(fullpath, 'r', encoding='utf-8') as sfile:
                            slines[fullpath] = list(map(discard_cmmnts, sfile.readlines()))

    elif os.path.isfile(dir):   # scan a specific file
        fullpath = os.path.abspath(dir)
        visited.add(fullpath)

        try:
            with open(fullpath, 'r') as sfile:
                slines[fullpath] = list(map(discard_cmmnts, sfile.readlines()))
        except:
            with open(fullpath, 'r', encoding='utf-8') as sfile:
                slines[fullpath] = list(map(discard_cmmnts, sfile.readlines()))

    else:
        print("Input is not a file nor a directory")
        os._exit(5)
                    
def parselines(lines=slines, unsafe_func=unsafe_func):
    ddir = args['-s'][0]
    log_file = args['-o'][0]
    unsafe_file = args['--sfile'][0]  # open file descriptor
    exact_name = args['--exact'][0]

    if (ddir):
        if ',' in ddir:
            unsafe_func = ddir.split(',')
        else:
            unsafe_func = [ddir]
        if log_file:
            log("Accepting a specific unsafe function [%s]\n" % ddir, log_file)
    
    if(unsafe_file):
        unsafe_func = []
        with unsafe_file as ufile:
            for line in ufile:
                unsafe_func.append(line.rstrip())
        if log_file:
            log("Accepting unsafe functions [%s] from file\n" % (', '.join(unsafe_func)), log_file)
    
    for key in visited:
        for line in slines[key]:
            indexSearch = [i for i in unsafe_func if exactmatch(i, line, lastChar='[(]')] if exact_name \
                          else [i for i in unsafe_func if i in line]
            #print(indexSearch)
            if (indexSearch):
                print(Fore.CYAN + key + "::" + Fore.RED + str(slines[key].index(line)+1), end="  ")
                print(Fore.GREEN + line.strip())
                if log_file:
                    log("%s::%s  %s\n" % (key, slines[key].index(line)+1, line.strip()), log_file)
                continue

class func_attr:
    def __init__(self, func_name, return_type, source, sline=slines):
        self.func_name = func_name     
        self.return_type = return_type
        source_path = find_file(sline, source)

        self.start, self.end = 0, 0
        self.ll = 0
        self.total_lines = 0
        self.blocks = {}
        self.arguments = []
        self.get_lines = [i.rstrip() for i in sline[source_path]]
        
        self.find_blocks()

    def find_blocks(self):
        try:
            self.start, self.end = self.func_begin_n_end()
            self.total_lines = self.end - self.start
        except TypeError:
            raise TypeError("Something went wrong, maybe the given function name is incorrect?")
        
        inserted = 0
        b_counter = 1
        nested_block = 0
        idx = 0
        hold = []
        block_end = 0
        lines = self.get_lines[self.start:self.end-1]

        for line in lines:
            if line.find('{') >= 0:
                block_begin = lines.index(line)
                self.blocks['Block ' + str(b_counter)] = {'begin':block_begin+self.start+1, 'end':0}
                lines[block_begin] = random_string(10)

                #lines_ = lines[block_begin+1:]
                for end in lines[block_begin+1:]:
                    if res := re.findall('{', end):    # code patterns like "{ blah blah; {" on a single line
                        nested_block += len(res)
                        #inserted = 0 if inserted > 0 else inserted
                        
                    if res := re.findall('}', end):
                        if (nested_block > 0):
                            idx, value = lines.index(end), end
                            hold.append((idx,value))
                            lines[idx] = random_string(10)      # poisoned to avoid repetition
                            nested_block -= len(res)
                        else:
                            block_end = lines.index(end)
                            self.blocks['Block ' + str(b_counter)]['end'] = block_end+self.start+1
                            if end.find('{') > 0:
                                lines.insert(idx+1, '{')
                                inserted += 1
                            lines[block_end] = random_string(10)       
                            if ((block_end, end)) in hold:       # never restored, this denote that a full block has been found and also       
                                hold.remove((block_end, end))    #... poisoned so we don't find it anymore on next iteration
                            break

                b_counter += 1
                for (i, j) in hold:    
                    lines[i] = j        # restore the poisoned strings

    def func_begin_n_end(self):
        start = self.func_definition()
        nests = 0
        func_end = 0
        
        if (start >= 0):
            copy = self.get_lines[:]
            for i in copy[start-1:]:
                if i.find('{') >= 0:
                    func_begin = copy[start-1:].index(i)+start  # bcus the file has been copied and cut, we need to add the line start...
                    break                                       #...index to get the accurate line number

            copy_ = copy[func_begin:]
            for _ in copy_:
                if res := re.findall('{', _):
                    nests += len(res)

                # fall through cos of scenario such as this " } else {" on the same line
                # and initially there have been a "{" 
                if (res := re.findall('}', _)) and nests > 0:
                    idx = copy_.index(_)
                    copy_[idx] = random_string(10)  # poisoned to avoid repetition
                    nests -= len(res)
                    continue

                if nests == 0 and _.find('}') >= 0:
                    func_end = copy_.index('}')+1
                    break
            
            return func_begin, (func_end+func_begin)
        else:
            return -1

    def func_definition(self):
        #get_lines = [i.strip() for i in sline[r'os.path.norm(source)']]

        func_name = self.func_name
        return_type = self.return_type

        for line in self.get_lines:
            if not line.endswith((';', ',')):
                line_index = self.get_lines.index(line)+1
                search = exactmatch(func_name, line, lastChar='[(]')
                if not search:
                    continue
                start, end = search.span()
                chars_before = line[:start]
                self.ll = line_index

                #Some function definition has calling convention and inlining before function name,
                #this check if string before function name has the return type
                if (chars_before):
                    if exactmatch(return_type, chars_before):
                        #self.return_type = chars_before
                        self.parameters(line, end)  # we've found the function, now get the parameters
                        return line_index

                #look for return type above line
                if line_index != 0:
                    line_before = self.get_lines[line_index-2]
                    if (not line_before.endswith(';')) and (not line_before.startswith('}') and (not line_before.startswith('#'))):
                        ret_type = exactmatch(return_type, line_before)
                        if ret_type:
                            #self.return_type = line_before
                            self.parameters(line, end)
                            return line_index
                        else:
                            continue

        if line == self.get_lines[-1]:
            return -1    

    def parameters(self, line, end):
        incr = 0
        l_index = self.ll-1
        while True:
            if (incr == 8):
                break
            arg = self.get_lines[l_index+incr]
            if not arg[-1].endswith(')'):  
                self.arguments.append(arg)
                print(arg)
            else:
                h = arg[:-1]
                self.arguments.append(h)
                break
            incr +=1
                
def f_attribute(attr):
    if attr:
        l_param = attr.split(',')
        funcattr = func_attr(*l_param)

        func_name = funcattr.func_name
        func_total_lines = funcattr.total_lines
        func_start, func_end = funcattr.start, funcattr.end
        func_args = funcattr.arguments
        func_return = funcattr.return_type

        print(Fore.LIGHTGREEN_EX + "FUNCTION NAME: ", func_name)
        print(Fore.LIGHTGREEN_EX + "\tARGUMENTS: ", func_args)
        print(Fore.LIGHTGREEN_EX + "\tRETURN TYPE: ", func_return)
        print(Fore.LIGHTGREEN_EX + "\tSTART = ", func_start, Fore.LIGHTGREEN_EX +  "END = ", func_end)
        print(Fore.LIGHTGREEN_EX + "\tTOTAL NUMBER OF LINES: ", func_total_lines)
        print(Fore.LIGHTGREEN_EX + "\tBLOCKS:")
        for i,j in funcattr.blocks.items():
            print("\t\t%s == %s" % (i,j))

        print_function(funcattr.get_lines, funcattr.start, funcattr.end)

    return 0

if __name__ == "__main__":
    time = Timer()
    time.start()
    init(autoreset=True)
    if len(sys.argv ) < 2:
        print(Fore.BLUE + "python main.py --help", "for usage")
        os._exit(1)

    args["-h | --help"][0] and printHelp(args)
    getlines(args['-d'][0] or args['-f'][0])
    (args['-s'][0] or args['--sfile'][0]) and parselines()
    function_attribute = args['--func-attr'][0]
    function_attribute and f_attribute(function_attribute)
    time.stop()
    



                

