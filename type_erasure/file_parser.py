import clang
import util
from clang.cindex import TranslationUnit


Break = 0
Continue = 1
Recurse = 2


class GenericFileParser(object):
    def __init__(self, processor, data):
        self.processor = processor
        self.data = data

    def parse(self):
        all_clang_args = [self.data.file]
        all_clang_args.extend(self.data.clang_args)

        index = clang.cindex.Index.create()
        self.data.tu = index.parse(None, all_clang_args, options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        self.data.filename = self.data.tu.spelling

        self.visit(self.data.tu.cursor)

        if self.data.current_struct != clang.cindex.conf.lib.clang_getNullCursor():
            self.processor.process_close_class()

        util.close_namespaces(self.processor, self.data)

    def visit(self, cursor):
        for child in cursor.get_children():
            result = self.visit_impl(child, cursor)
            if result == Recurse:
                if self.visit(child) == Break:
                    return Break
            elif result == Break:
                return Break
            elif result == Continue:
                continue

    def visit_impl(self, cursor, parent):
        try:
            kind = cursor.kind
        except:
            return Break

        self.parse_closing_namespaces(parent)
        self.parse_closing_class(parent)

        if util.is_namespace(cursor.kind):
            return self.parse_opening_namespace(cursor)
        elif util.is_class(cursor.kind):
            return self.parse_opening_class(cursor)
        self.parse_function(cursor)

        return Continue

    def parse_closing_namespaces(self,enclosing_namespace):
        while enclosing_namespace != self.data.tu.cursor and not util.is_namespace(enclosing_namespace.kind):
            enclosing_namespace = enclosing_namespace.semantic_parent

        if enclosing_namespace != self.data.tu.cursor and util.is_namespace(enclosing_namespace.kind):
            while len(self.data.current_namespaces) and \
                            enclosing_namespace != self.data.current_namespaces[-1]:
                self.data.current_namespaces.pop()
                self.processor.process_close_namespace()

    def parse_closing_class(self,enclosing_struct):
        while enclosing_struct and \
                        enclosing_struct != self.data.tu.cursor and \
                not util.is_class(enclosing_struct.kind):
            enclosing_struct = enclosing_struct.semantic_parent

        if enclosing_struct and \
                        self.data.current_struct != clang.cindex.conf.lib.clang_getNullCursor() and \
                        enclosing_struct != self.data.current_struct:
            self.processor.process_close_class()
            self.data.current_struct = clang.cindex.conf.lib.clang_getNullCursor()
            self.data.member_functions = []

    def parse_function(self,cursor):
        if util.is_function(cursor.kind):
            self.processor.process_function(self.data, cursor)

    def parse_opening_namespace(self,cursor):
        if clang.cindex.conf.lib.clang_Location_isFromMainFile(cursor.location):
            self.processor.process_open_namespace(cursor.spelling)
            self.data.current_namespaces.append(cursor)
            return Recurse
        else:
            return Continue

    def parse_opening_class(self,cursor):
        if self.data.current_struct == clang.cindex.conf.lib.clang_getNullCursor():
            self.data.current_struct = cursor
            self.data.current_struct_prefix = util.class_prefix(self.data.tu, cursor)
            self.processor.process_open_class(self.data)
            return Recurse
        return Continue


class FileProcessor(object):
    def __init__(self):
        pass

    def process_open_include_guard(self, filename):
        pass

    def process_close_include_guard(self):
        pass

    def process_headers(self, headers):
        pass

    def process_open_namespace(self, namespace_name):
        pass

    def process_close_namespace(self):
        pass

    def process_open_class(self, data):
        pass

    def process_close_class(self):
        pass

    def process_function(self, data, cursor):
        pass

    def write_to_file(self):
        pass