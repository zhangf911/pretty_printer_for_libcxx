import gdb
import itertools
import re

class CxxStringPrinter:
    "Print a std::__1::basic_string"
    def __init__(self, typename, val):
        self.val = val

    def to_string(self):
        self.is_short = self.val['__r_']['__first_']['__s']['__size_'] & 1
        if self.is_short == 0 :
            self.ptr = self.val['__r_']['__first_']['__s']['__data_']
            self.length = self.val['__r_']['__first_']['__s']['__size_'] / 2 % 256
        else:
            self.ptr = self.val['__r_']['__first_']['__l']['__data_']
            self.length = self.val['__r_']['__first_']['__l']['__size_'] + 1
        return ('"%s"' % (self.ptr.string (length = self.length)))

    def display_hint (self):
        return "std::string"

class CxxVectorPrinter:
    "std::__1::vector"

    class _iterator:
        def __init__(self, begin, end):
            self.begin = begin
            self.end = end
            self.count = 0

        def __iter__(self):
            return self
        
        def next(self):
            count = self.count
            self.count = self.count + 1
            if self.begin == self.end:
                raise StopIteration
            value = self.begin.dereference()
            self.begin = self.begin + 1
            return ('[%d]' % count, value)

    def __init__(self, typename, val):
        self.val = val
        self.typename = typename

    def children(self):
        return self._iterator(self.val['__begin_'],
                              self.val['__end_'])

    def to_string(self):
        begin = self.val['__begin_']
        end = self.val['__end_'] 
        size = end - begin
        return ('%s of length %d' % (self.typename, int(end - begin)))

    def display_hint(self):
        return 'std::vector'

class CxxListPrinter:
    "std::__1::list"

    class _iterator:
        def __init__(self, begin, size):
            self.begin = begin
            self.count = 0
            self.size = size

        def __iter__(self):
            return self
        
        def next(self):
            count = self.count
            self.count = self.count + 1
            if count == self.size:
                raise StopIteration
            value = self.begin.dereference()['__value_']
            self.begin = self.begin['__next_']
            return ('[%d]' % count, value)

    def __init__(self, typename, val):
        self.val = val
        self.typename = typename

    def children(self):
        return self._iterator(self.val['__end_']['__next_'],
                              self.val['__size_alloc_']['__first_'])

    def to_string(self):
        size = self.val['__size_alloc_']['__first_']
        return ('%s of length %d' % (self.typename, size))

    def display_hint(self):
        return 'std::list'

class CxxDequePrinter:
    "std::__1::deque"

    class _iterator:
        def __init__(self, begin, offset, block, size):
            self.begin = begin
            self.count = 0
            self.size = size
            self.offset = offset
            self.block = block

        def __iter__(self):
            return self
        
        def next(self):
            count = self.count
            self.count = self.count + 1
            if count == self.size:
                raise StopIteration
            index = count + self.offset
            i,j = index / self.block, index % self.block
            value = ((self.begin + i).dereference() + j).dereference()
            return ('[%d]' % count, value)

    def __init__(self, typename, val):
        self.val = val
        self.typename = typename

    def children(self):
        begin = self.val['__map_']['__first_']
        block = self.val['__block_size']
        offset = self.val['__start_']
        size  = self.val['__size_']['__first_']

        return self._iterator(begin, offset, block, size)
                              

    def to_string(self):
        size = self.val['__size_']['__first_']
        return ('%s of length %d' % (self.typename, size))

    def display_hint(self):
        return 'std::deque'

class CxxStackPrinter:
    "std::__1::stack or std::__1::queue"

    def __init__ (self, typename, val):
        self.typename = typename
        self.visualizer = gdb.default_visualizer(val['c'])

    def children (self):
        return self.visualizer.children()

    def to_string (self):
        return '%s wrapping: %s' % (self.typename,
                self.visualizer.to_string())

    def display_hint (self):
        if hasattr (self.visualizer, 'display_hint'):
            return self.visualizer.display_hint ()
        return None

_type_parse_map = []

def reg_function(regex, parse):
    global _type_parse_map

    p = re.compile(regex)

    _type_parse_map.append((p,parse))

def lookup_type (val):
    global _type_parse_map
    typename = str(val.type)
    for (regex, Printer) in _type_parse_map:
        m = regex.match(typename)
        if m is not None:
            return Printer(typename, val)
    #print("Not Fount Type %s" % (typename))
    return None

def register_libcxx_printers(obj):
    global _type_parse_map
    if len(_type_parse_map) < 1:
        reg_function('^std::__1::basic_string<char.*>$', CxxStringPrinter)
        reg_function('^std::__1::string$', CxxStringPrinter)
        reg_function('^std::__1::vector<.*>$', CxxVectorPrinter)
        reg_function('^std::__1::list<.*>$', CxxListPrinter)
        reg_function('^std::__1::deque<.*>$', CxxDequePrinter)
        reg_function('^std::__1::stack<.*>$', CxxStackPrinter)
    
    if obj is None:
        obj = gdb
    obj.pretty_printers.append(lookup_type)

