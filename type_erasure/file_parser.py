import clang
import clang_util
from clang.cindex import TranslationUnit
import util


Break = 0
Continue = 1
Recurse = 2


class GenericFileParser(object):
    def __init__(self, processor, data):
        self.processor = processor
        self.data = data
        self.opened = []

    def parse(self):
        all_clang_args = self.data.clang_args

        index = clang.cindex.Index.create()
        self.data.tu = index.parse(None, all_clang_args, options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        self.data.filename = self.data.tu.spelling

        self.visit(self.data.tu.cursor)

        if self.data.current_struct != clang.cindex.conf.lib.clang_getNullCursor():
            self.processor.process_close_class()

        while len(self.data.current_namespaces):
            self.data.current_namespaces.pop()
            self.processor.process_close_namespace()

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
        if not clang.cindex.conf.lib.clang_Location_isFromMainFile(cursor.location):
            return Continue
        try:
            kind = cursor.kind
        except:
            return Break

        # close open namespaces and classes
        # when another non-nested namespace or class is opened
        if len(self.opened) > 0:
            if self.opened[-1] == 'namespace':
                self.parse_closing_namespaces(parent)
            if self.opened[-1] in ['class','struct']:
                self.parse_closing_class(parent)

#        print '\nCursor'
#        print cursor.kind
#        print cursor.spelling
#        print util.concat(clang_util.get_tokens(self.data.tu, cursor),' ')
#         print self.data.current_struct.spelling
#         tokens = clang_util.get_tokens(self.data.tu, cursor)
#         for token in tokens:
#             print token.spelling

        if clang_util.is_inclusion_directive(cursor.kind):
            self.processor.process_inclusion_directive(self.data,cursor)
        elif clang_util.is_access_specifier(cursor.kind):
            self.processor.process_access_specifier(self.data,cursor)
        elif clang_util.is_constructor(cursor.kind):
            self.processor.process_constructor(self.data,cursor)
        elif clang_util.is_destructor(cursor.kind):
            self.processor.process_destructor(self.data,cursor)
        elif clang_util.is_static_or_global_variable(cursor.kind):
            self.processor.process_variable_declaration(self.data,cursor)
        elif clang_util.is_member_variable(cursor.kind):
            self.processor.process_member_variable_declaration(self.data,cursor)
        elif clang_util.is_enum(cursor.kind):
            self.processor.process_enum(self.data,cursor)
        elif clang_util.is_forward_declaration(self.data.tu, cursor):
            self.processor.process_forward_declaration(self.data,cursor)
        elif clang_util.is_namespace(cursor.kind):
            self.opened.append('namespace')
            return self.parse_opening_namespace(cursor)
        elif clang_util.is_class(cursor.kind):
            self.opened.append('class')
            return self.parse_opening_class(cursor)
        elif clang_util.is_struct(cursor.kind):
            self.opened.append('struct')
            return self.parse_opening_class(cursor)
        elif clang_util.is_function(cursor.kind):
            return self.parse_function(cursor)
        elif clang_util.is_type_alias(kind) or clang_util.is_typedef(kind):
            self.processor.process_type_alias(self.data,cursor)

        return Continue

    def parse_closing_namespaces(self,enclosing_namespace):
        while enclosing_namespace != self.data.tu.cursor and not clang_util.is_namespace(enclosing_namespace.kind):
            enclosing_namespace = enclosing_namespace.semantic_parent

        if enclosing_namespace != self.data.tu.cursor and clang_util.is_namespace(enclosing_namespace.kind):
            while len(self.data.current_namespaces) and \
                            enclosing_namespace != self.data.current_namespaces[-1]:
                self.data.current_namespaces.pop()
                self.opened.pop()
                self.processor.process_close_namespace()

    def parse_closing_class(self,enclosing_struct):
        while enclosing_struct and \
                        enclosing_struct != self.data.tu.cursor and \
                not clang_util.is_class(enclosing_struct.kind) and not clang_util.is_struct(enclosing_struct.kind):
            enclosing_struct = enclosing_struct.semantic_parent

        if enclosing_struct and \
                        self.data.current_struct != clang.cindex.conf.lib.clang_getNullCursor() and \
                        enclosing_struct != self.data.current_struct:
            self.processor.process_close_class()
            self.opened.pop()
            self.data.current_struct = clang.cindex.conf.lib.clang_getNullCursor()
            self.data.member_functions = []

    def parse_function(self,cursor):
        if clang_util.is_function(cursor.kind):
            self.processor.process_function(self.data, cursor)
        return Continue

    def parse_opening_namespace(self,cursor):
        if clang.cindex.conf.lib.clang_Location_isFromMainFile(cursor.location):
            self.processor.process_open_namespace(self.data, cursor)
            self.data.current_namespaces.append(cursor)
            return Recurse
        return Continue

    def parse_opening_class(self,cursor):
        if self.data.current_struct == clang.cindex.conf.lib.clang_getNullCursor():
            self.data.current_struct = cursor
            self.data.current_struct_prefix = clang_util.get_class_prefix(self.data.tu, cursor)
            if clang_util.is_class(cursor.kind):
                self.processor.process_open_class(self.data, cursor)
            else:
                self.processor.process_open_struct(self.data, cursor)
            return Recurse
        return Continue


class FileProcessor(object):
    def __init__(self):
        pass

    def process_inclusion_directive(self, data, cursor):
        pass

    def process_open_include_guard(self, filename):
        pass

    def process_close_include_guard(self):
        pass

    def process_headers(self, headers):
        pass

    def process_open_namespace(self, data, cursor):
        pass

    def process_close_namespace(self):
        pass

    def process_open_class(self, data, cursor):
        pass

    def process_open_struct(self, data, cursor):
        pass

    def process_close_class(self):
        pass

    def process_function(self, data, cursor):
        pass

    def process_forward_declaration(self, data, cursor):
        pass

    def process_variable_declaration(self, data, cursor):
        pass

    def process_member_variable_declaration(self, data, cursor):
        pass

    def process_constructor(self, data, cursor):
        pass

    def process_destructor(self, data, cursor):
        pass

    def process_type_alias(self, data, cursor):
        pass

    def process_enum(self, data, cursor):
        pass

    def process_access_specifier(self, data, cursor):
        pass
