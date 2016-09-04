import re
from clang.cindex import CursorKind
from util import trim


semicolon = ';'
open_paren = '('
close_paren = ')'
const_token = 'const'
open_brace = '{'
close_brace = '}'
open_bracket = '<'
close_bracket = '>'
comma = ','
brackets = [open_paren, close_paren, open_brace, close_brace]


def get_tokens(tu, cursor):
    return [x for x in tu.get_tokens(extent=cursor.extent)]


def get_class_prefix(translation_unit, class_cursor):
    retval = ''
    tokens = get_tokens(translation_unit, class_cursor)

    open_brackets = 0
    for i in range(len(tokens)):
        spelling = tokens[i].spelling
        if spelling == open_brace or spelling == semicolon:
            break
        elif spelling == close_bracket:
            open_brackets -= 1
            if open_brackets == 0:
                retval += spelling + '\n'
                continue
        elif i and not i+1 == len(tokens) and \
                not retval[-1] == open_bracket and \
                not retval[-1] == close_bracket and \
                not retval[-1] == '\n':
            if spelling == open_bracket:
                open_brackets += 1
            retval += ' '
        retval += spelling

    return retval


def without_spaces(spelling):
    return spelling == '::' or spelling == '<' or spelling == '>' or spelling == ','


def get_type_alias(translation_unit, cursor):
    tokens = get_tokens(translation_unit, cursor)
    type_alias = ''
    for token in tokens:
        spelling = token.spelling
        if token == tokens[-1]:
            type_alias += spelling + '\n'
        elif without_spaces(spelling):
            alias_start = (len(type_alias) > 0 and type_alias[:-1] or '')
            type_alias = alias_start + spelling
        elif token == tokens[-2]:
            type_alias += spelling
        else:
            type_alias += spelling + ' '
    return type_alias


def get_typedef(translation_unit, cursor):
    tokens = get_tokens(translation_unit, cursor)
    typedef = ''
    for token in tokens:
        spelling = token.spelling
        if token == tokens[-1]:
            typedef += spelling + '\n'
        elif without_spaces(spelling):
            typedef_start = (len(typedef) > 0 and typedef[:-1] or '')
            typedef = typedef_start + spelling
        elif token == tokens[-2]:
            typedef += spelling
        else:
            typedef += spelling + ' '
    return typedef


def get_type_alias_or_typedef(translation_unit, cursor):
    if is_type_alias(cursor.kind):
        return get_type_alias(translation_unit, cursor)
    if is_typedef(cursor.kind):
        return get_typedef(translation_unit, cursor)


def get_variable_declaration(translation_unit, cursor):
    tokens = get_tokens(translation_unit, cursor)
    variable_declaration = ''
    for token in tokens:
        spelling = token.spelling
        if token == tokens[-1]:
            variable_declaration += spelling + '\n'
        elif token == tokens[-2]:
            variable_declaration += spelling
        else:
            variable_declaration += spelling + ' '
    return variable_declaration


def get_enum_definition(translation_unit, cursor):
    tokens = get_tokens(translation_unit, cursor)
    enum_definition = ''
    for token in tokens:
        enum_definition += token.spelling
        if token == tokens[-1]:
            enum_definition += '\n'
        elif token != tokens[-2]:
            enum_definition += ' '

    return enum_definition


def format_enum_definition(enum_indent, base_indent, enum_definition):
    formatted_definition = ''
    enum_prefix = trim(enum_definition.split(open_brace)[0])
    formatted_definition += enum_indent + enum_prefix + '\n'
    formatted_definition += enum_indent + open_brace

    enum_definition = trim(trim(trim(enum_definition)[len(enum_prefix):])[1:])
    enum_definition = enum_definition.replace('};','')
    entries = enum_definition.split(comma)
    for entry in entries:
        if entry != entries[0]:
            formatted_definition += comma
        formatted_definition += '\n' + enum_indent + base_indent + trim(entry)
    formatted_definition += '\n' + enum_indent + '};\n'
    return formatted_definition


def get_function(function_indent, base_indent, translation_unit, cursor, class_prefix=''):
    tokens = get_tokens(translation_unit, cursor)

    function = function_indent
    open_braces = 0
    indent = function_indent
    for i in range(len(tokens)):
        spelling = tokens[i].spelling

        if spelling == cursor.spelling:
            spelling = class_prefix + spelling
        if spelling == open_brace:
            function += '\n' + indent + spelling + '\n' + indent + base_indent
            open_braces += 1
            indent += base_indent
        elif spelling == close_brace:
            open_braces -= 1
            indent = function_indent + open_braces * base_indent
            function = function[:-len(base_indent)]
            function += spelling + '\n' + indent
            if open_braces == 0:
                break
        elif spelling == semicolon:
            function = function[:-1]
            function += spelling + '\n' + indent
        else:
            function += spelling + ' '

    if function.endswith(indent):
        function = function[:-len(indent)]
    if function_indent == '':
        function = function[1:]
    return function


def get_function_declaration(translation_unit, cursor, class_prefix=''):
    tokens = get_tokens(translation_unit, cursor)

    function_declaration = ''
    for token in tokens:
        spelling = token.spelling
        if spelling == cursor.spelling:
            spelling = class_prefix + spelling
        if spelling == open_brace or spelling == semicolon:
            break
        elif spelling == '*' or spelling == '&':
            function_declaration = function_declaration[:-1]
            function_declaration += spelling + ' '
        elif spelling == '::':
            function_declaration = function_declaration[:-1]
            function_declaration += spelling
        else:
            function_declaration += spelling + ' '
    return function_declaration[:-1] + ';\n'


def is_inclusion_directive(kind):
    return kind == CursorKind.INCLUSION_DIRECTIVE


def is_class(kind):
    return kind == CursorKind.CLASS_DECL or \
                    kind == CursorKind.CLASS_TEMPLATE or \
                    kind == CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION


def is_struct(kind):
    return kind == CursorKind.STRUCT_DECL


def is_forward_declaration(translation_unit, cursor):
    if not is_class(cursor.kind):
        return False
    return get_class_prefix(translation_unit, cursor)[-1] == ';'


def is_namespace(kind):
    return kind == CursorKind.NAMESPACE


def is_function(kind):
    return kind in [CursorKind.CXX_METHOD,
                    CursorKind.FUNCTION_DECL,
                    CursorKind.CONVERSION_FUNCTION]


def is_template(kind):
    return kind == CursorKind.CLASS_TEMPLATE or \
                    kind == CursorKind.CLASS_TEMPLATE_PARTIAL_SPECIALIZATION or \
                    kind == CursorKind.FUNCTION_TEMPLATE


def is_type_alias(kind):
    return kind == CursorKind.TYPE_ALIAS_DECL


def is_typedef(kind):
    return kind == CursorKind.TYPEDEF_DECL


def is_static_or_global_variable(kind):
    return kind == CursorKind.VAR_DECL


def is_enum(kind):
    return kind == CursorKind.ENUM_DECL


def is_access_specifier(kind):
    return kind == CursorKind.CXX_ACCESS_SPEC_DECL


def is_variable(kind):
    return kind == CursorKind.FIELD_DECL


def is_member_variable(kind):
    return is_variable(kind)


def is_constructor(kind):
    return kind == CursorKind.CONSTRUCTOR


def is_destructor(kind):
    return kind == CursorKind.DESTRUCTOR


class SpecifierParser(object):
    def __init__(self):
        self.last = ''

    def parse(self,function,spelling):
        if spelling == '=':
            self.last = '='
        elif spelling == 'default' and last == '=':
            function.is_default = True
            self.last = ''
        elif spelling == 'delete' and last == '=':
            function.is_deleted = True
            self.last = ''
        elif spelling == 'noexcept':
            function.is_noexcept = True
            self.last = ''
        return function


def make_type(spellings):
    function_type = ''
    for spelling in spellings:
        function_type += spelling
        if spelling == 'const' or spelling == 'typename':
            function_type += ' '
    return function_type


def parse_inclusion_directive(data,cursor):
    tokens = get_tokens(data.tu, cursor)

    directive = tokens[0].spelling + tokens[1].spelling + ' '

    spelling = tokens[2].spelling
    if (spelling.startswith('"') and spelling.endswith('"')) or (spelling.startswith('<') and spelling.endswith('>')):
        return directive + spelling

    closing = '"'
    if tokens[2].spelling == '<':
        closing = '>'
    for i in range(2,len(tokens)):
        spelling = tokens[i].spelling
        directive += spelling
        if spelling == closing:
            return directive + '\n'


my_identifier_regex = re.compile(r'[_a-zA-Z][_a-zA-Z0-9]*')
regex_for_identifier = r'[_a-zA-Z][_a-zA-Z0-9]*'
regex_for_type = regex_for_identifier + r'\s'


def get_function_regex(name):
    return re.compile( r'constexpr*\s*virtual\s*(.*)' + name + r'\s*\( .*(=*[_a-zA-Z][_a-zA-Z0-9]*)*\)\s*(const|noexcept|override|final|\&|\&\&)*\s*' )


def read_function_specifiers(function,tokens,index):
    last_was_equals = False
    while True:
        spelling = tokens[index].spelling
        if spelling == 'noexcept':
            function.is_noexcept = True
        elif spelling == 'const':
            function.is_const = True
        elif spelling == 'override':
            function.overrides_virtual = True
        elif spelling == 'final':
            function.is_final == True
        elif spelling == open_brace or spelling == semicolon:
            return function, index
        elif spelling == '=':
            last_was_equals = True
        elif last_was_equals:
            if spelling == 'default':
                function.is_default = True
            elif spelling == 'delete':
                function.is_deleted = True
            last_was_equals = False
        index += 1


def same_tokens(tokens, other_tokens):
    if len(tokens) != len(other_tokens):
        return False
    for i in range(len(tokens)):
        if tokens[i].spelling != other_tokens[i].spelling:
            return False
    return True


class ScopeMonitor(object):
    def __init__(self, open_parens = 0, open_brackets = 0, open_braces = 0):
        self.initial_open_parens = open_parens
        self.open_parens = self.initial_open_parens
        self.initial_open_brackets = open_brackets
        self.open_brackets = self.initial_open_brackets
        self.initial_open_braces = open_braces
        self.open_braces = self.initial_open_braces
        self.opened_scope = False

    def process(self,spelling):
        if spelling == open_paren:
            self.opened_scope = True
            self.open_parens += 1
        if spelling == close_paren:
            self.open_parens -= 1
        if spelling == open_bracket:
            self.opened_scope = True
            self.open_brackets += 1
        if spelling == close_bracket:
            self.open_brackets -= 1
        if spelling == open_brace:
            self.opened_scope = True
            self.open_braces += 1
        if spelling == close_brace:
            self.open_braces -= 1

    def before_scope(self):
        return not self.opened_scope

    def all_closed(self):
        return self.open_parens == self.initial_open_parens and \
               self.open_brackets == self.initial_open_brackets and \
               self.open_braces == self.initial_open_braces


def get_end_of_member_initialization(index,tokens):
    while tokens[index].spelling in [':', ',']:
        index += 1
        while tokens[index].spelling not in [open_paren, open_brace]:
            index += 1
        counter = ScopeMonitor()
        counter.process(tokens[index].spelling)
        while not counter.all_closed():
            index += 1
            counter.process(tokens[index].spelling)
    return index


def get_all_variable_tokens(decl_tokens, tokens):
    if len(decl_tokens) >= len(tokens):
        return decl_tokens

    index = -1
    for i in range(len(tokens) - len(decl_tokens)):
        if same_tokens(decl_tokens, tokens[i:len(decl_tokens) + i]):
            index = i
            break
    if index == -1:
        return decl_tokens

    for i in range(index+len(decl_tokens),len(tokens)):
        decl_tokens.append(tokens[i])
        if tokens[i].spelling == semicolon:
            return decl_tokens


def get_all_tokens(decl_tokens, tokens):
    if len(decl_tokens) >= len(tokens) or decl_tokens[-1].spelling == close_brace:
        return decl_tokens

    index = -1
    for i in range(len(tokens) - len(decl_tokens)):
        if same_tokens(decl_tokens, tokens[i:len(decl_tokens)+i]):
            index = i
            break
    if index == -1:
        return decl_tokens

    end_index = get_end_of_member_initialization(index+len(decl_tokens), tokens)
    decl_tokens.extend(tokens[index+len(decl_tokens):end_index])

    index = end_index
    while tokens[index].spelling != open_brace:
        decl_tokens.append(tokens[index])
        index += 1

    monitor = ScopeMonitor()
    for i in range(index, len(tokens)):
        monitor.process(tokens[i].spelling)
        decl_tokens.append(tokens[i])
        if not monitor.before_scope() and monitor.all_closed():
            return decl_tokens
