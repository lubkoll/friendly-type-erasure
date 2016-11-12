import clang_util
import cpp
import file_parser
import re
import util
import parser_addition
from clang.cindex import TypeKind


def sequence_from_text(text):
    return [cpp.SimpleToken(entry) for entry in text.split(' ')]


def get_alias_from_text(name, text):
    return cpp.Alias(name, [cpp.SimpleToken(spelling) for spelling in text.split(' ')])


def get_function_from_text(classname, functionname, return_str, text, function_type='function'):
    return cpp.Function(classname, functionname, return_str, [cpp.SimpleToken(spelling) for spelling in text.split(' ')], function_type)


def returns_this(function):
    remaining_tokens = function.tokens[cpp.get_declaration_end_index(function.name, function.tokens):]
    return cpp.contains_sequence(remaining_tokens, sequence_from_text('return * this ;'))


def get_table_return_type(function):
    index, offset = cpp.find_function_name(function.name, function.tokens)
    return_type = util.concat(function.tokens[:index], ' ')
    if return_type in ['const ' + function.classname + ' & ',
                       function.classname + ' & ']:
        return 'void '
    if return_type == function.classname + ' ':
        return

    if returns_this(function):
        return 'void '

    return util.concat(function.tokens[:index], ' ')


def replace_in_tokens(old_spelling, new_spelling, tokens):
    for token in tokens:
        if token.spelling == old_spelling:
            token.spelling = new_spelling


def const_specifier(function):
    return 'const ' if cpp.is_const(function) else ''


def same_tokens(tokens, other_tokens):
    if len(tokens) != len(other_tokens):
        return False
    for i in range(len(tokens)):
        if tokens[i].spelling != other_tokens[i].spelling:
            return False
    return True


def contains(name, tokens):
    for token in tokens:
        if token.spelling == name:
            return True
    return False


def get_function_name_for_tokens(name):
    if 'operator' in name:
        return 'operator ' + name[8:]
    return name


def get_function_name_for_type_erasure(function):
    arg_extension = ''
    args = cpp.get_function_arguments(function)
    for arg in args:
        arg_extension += '_' + arg.type()
    arg_extension = arg_extension.replace('&', '_ref').replace('*', '_ptr')
    arg_extension = re.sub(' |::|\(|\)', '_', arg_extension)
    arg_extension = re.sub(r'<|>|\[|\]\(|\)\{\}', '', arg_extension)
    arg_extension = re.sub('_+', '_', arg_extension)
    arg_extension = arg_extension[:-1] if arg_extension.endswith('_') else arg_extension
    if function.name == 'operator()':
        return 'call' + arg_extension
    elif function.name == 'operator=':
        return 'assignment' + arg_extension
    elif function.name == 'operator+=':
        return 'add' + arg_extension
    elif function.name == 'operator*=':
        return 'multiply' + arg_extension
    elif function.name == 'operator-=':
        return 'subtract' + arg_extension
    elif function.name == 'operator-':
        return 'negate' + arg_extension
    elif function.name == 'operator/=':
        return 'divide' + arg_extension
    elif function.name == 'operator==':
        return 'compare' + arg_extension
    return function.name + arg_extension


class CppFileParser(file_parser.FileProcessor):
    def __init__(self):
        self.scope = cpp.Namespace('global')

    def process_inclusion_directive(self, data, cursor):
        self.scope.add(cpp.InclusionDirective(clang_util.parse_inclusion_directive(data, cursor).replace('#include ', '').replace('\n', '')))

    def process_open_include_guard(self, filename):
        self.scope.add(cpp.ScopeEntry('include_guard', parser_addition.extract_include_guard(filename)))

    def process_headers(self, headers):
        self.scope.add(cpp.ScopeEntry('headers', headers))

    def process_open_namespace(self, data, cursor):
        self.scope.add(cpp.Namespace(cursor.spelling, clang_util.get_tokens(data.tu, cursor)))

    def process_close_namespace(self):
        self.scope.close()

    def process_open_class(self, data, cursor):
        if clang_util.get_tokens(data.tu, cursor)[2].spelling == clang_util.semicolon:
            self.scope.add(cpp.Class(data.current_struct.spelling, clang_util.get_tokens(data.tu, cursor)[:3]))
#            self.scope.add(ForwardDeclaration(util.concat(clang_util.get_tokens(data.tu, cursor)[:3], ' ')))
        else:
            self.scope.add(cpp.Class(data.current_struct.spelling, clang_util.get_tokens(data.tu, cursor)))

    def process_open_struct(self, data, cursor):
        if clang_util.get_tokens(data.tu, cursor)[2].spelling == clang_util.semicolon:
            self.scope.add(cpp.Struct(data.current_struct.spelling, clang_util.get_tokens(data.tu, cursor)[:3]))
#            self.scope.add(ForwardDeclaration(util.concat(clang_util.get_tokens(data.tu, cursor)[:3], ' ')))
        else:
            self.scope.add(cpp.Struct(data.current_struct.spelling, clang_util.get_tokens(data.tu, cursor)))

    def process_close_class(self):
        if self.scope.get_open_scope().get_type() == cpp.NAMESPACE:
            return
        self.scope.close()

    def process_function(self, data, cursor):
        classname = ''
        if data.current_struct.spelling:
            classname = data.current_struct.spelling
        current_scope = self.scope.get_open_scope()

        tokens = clang_util.get_tokens(data.tu, cursor)
        tokens = tokens[:cpp.get_body_end_index(cursor.spelling, tokens)]
        if current_scope.get_tokens() and not tokens[-1].spelling == clang_util.semicolon:
            tokens = clang_util.get_all_tokens(tokens, current_scope.get_tokens())

        function_type = cpp.FUNCTION
        if clang_util.is_function_template(cursor.kind):
            function_type = cpp.FUNCTION_TEMPLATE
        self.scope.add(cpp.Function(classname, cursor.spelling, cursor.result_type.kind != TypeKind.VOID and 'return ' or '', tokens, function_type))

    def process_function_template(self, data, cursor):
        self.process_function(data, cursor)

    def process_constructor(self, data, cursor):
        classname = ''
        if data.current_struct.spelling:
            classname = data.current_struct.spelling
        current_scope = self.scope.get_open_scope()
        tokens = clang_util.get_tokens(data.tu, cursor)
        tokens = tokens[:cpp.get_body_end_index(cursor.spelling, tokens)]
        if current_scope.get_tokens() and not tokens[-1].spelling == clang_util.semicolon:
            tokens = clang_util.get_all_tokens(tokens, current_scope.get_tokens())
        self.scope.add(cpp.Function(classname, cursor.spelling, cursor.result_type.kind != TypeKind.VOID and 'return ' or '', tokens, cpp.CONSTRUCTOR))

    def process_destructor(self, data, cursor):
        self.process_function(data, cursor)

    def process_type_alias(self,data,cursor):
        self.scope.add(cpp.Alias(cursor.spelling, clang_util.get_tokens(data.tu, cursor)))

    def process_variable_declaration(self,data,cursor):
        tokens = clang_util.get_tokens(data.tu, cursor)
        if tokens[-1].spelling != clang_util.semicolon and self.scope.get_open_scope().get_tokens():
            tokens = clang_util.get_all_variable_tokens(tokens, self.scope.get_open_scope().get_tokens())

        variable_declaration = util.concat(tokens, ' ')
        # in case that an underlying type is specified,
        # clang interprets enums at variables.
        # filter out these cases:
        if 'enum ' in variable_declaration:
            #TODO try to find a workaround for this
            return
        if clang_util.get_tokens(data.tu, cursor)[0].spelling == 'static':
            self.scope.add(cpp.StaticVariable(variable_declaration))
        else:
            self.scope.add(cpp.Variable(variable_declaration))

    def process_member_variable_declaration(self,data,cursor):
        self.process_variable_declaration(data, cursor)

    def process_forward_declaration(self,data,cursor):
        pass

    def process_enum(self,data,cursor):
        self.scope.add(cpp.ScopeEntry('enum', clang_util.get_enum_definition(data.tu, cursor)))

    def process_access_specifier(self, data, cursor):
        self.scope.add(cpp.AccessSpecifier(clang_util.get_tokens(data.tu, cursor)[0].spelling))


class Visitor(object):
    def visit(self,visited):
        pass

    def visit_function(self,function):
        return self.visit(function)

    def visit_template_function(self,function):
        return self.visit_function(function)

    def visit_constructor(self,constructor):
        return self.visit_function(constructor)

    def visit_destructor(self,destructor):
        return self.visit_function(destructor)

    def visit_operator(self,operator):
        return self.visit_function(operator)

    def visit_class(self,class_):
        return self.visit(class_)

    def visit_forward_declaration(self,forward_declaration):
        return self.visit(forward_declaration)

    def visit_template_class(self,template_class):
        return self.visit(template_class)

    def visit_namespace(self,namespace):
        return self.visit(namespace)

    def visit_inclusion_directive(self,inclusion_directive):
        return self.visit(inclusion_directive)

    def visit_access_specifier(self,access_specifier):
        return self.visit(access_specifier)

    def visit_variable(self,variable):
        return self.visit(variable)

    def visit_static_variable(self,variable):
        return self.visit(variable)

    def visit_alias(self,alias):
        return self.visit(alias)

    def visit_comment(self,comment):
        return self.visit(comment)


class RecursionVisitor(Visitor):
    def visit_class(self,class_):
        for entry in class_.content:
            entry.visit(self)

    def visit_template_class(self,template_class):
        for entry in template_class.content:
            entry.visit(self)

    def visit_namespace(self,namespace):
        for entry in namespace.content:
            entry.visit(self)


class ExtractPublicProtectedPrivateSections(RecursionVisitor):
    def __init__(self):
        self.private_section = []
        self.protected_section = []
        self.public_section = []
        self.access_specifier = cpp.PRIVATE

    def visit_access_specifier(self,access_specifier):
        self.access_specifier = access_specifier.value

    def visit(self,entry):
        if self.access_specifier == cpp.PRIVATE:
            self.private_section.append(entry)
        elif self.access_specifier == cpp.PROTECTED:
            self.protected_section.append(entry)
        else:
            self.public_section.append(entry)


def append_comment(comment,group):
    if comment:
        group.append(comment)
    return None


class ExtractTypes(Visitor):
    def __init__(self):
        self.aliases = []
        self.static_variables = []
        self.constructors = []
        self.destructor = []
        self.operators = []
        self.functions = []
        self.forward_declarations = []
        self.variables = []
        self.comment = None

    def visit_comment(self,comment):
        self.comment = comment

    def visit_function(self,function):
        if function.type in [cpp.ASSIGNMENT_OPERATOR]:
            self.comment = append_comment(self.comment, self.operators)
            self.operators.append(function)
        if function.type in [cpp.FUNCTION, cpp.FUNCTION_TEMPLATE]:
            if function.name.startswith('operator'):
                self.comment = append_comment(self.comment, self.operators)
                self.operators.append(function)
            else:
                self.comment = append_comment(self.comment, self.functions)
                self.functions.append(function)
        elif function.type in [cpp.CONSTRUCTOR, cpp.CONSTRUCTOR_TEMPLATE]:
            self.comment = append_comment(self.comment, self.constructors)
            self.constructors.append(function)
        elif function.type == cpp.DESTRUCTOR:
            self.comment = append_comment(self.comment, self.destructor)
            self.destructor.append(function)

    def visit_variable(self,variable):
        self.comment = append_comment(self.comment,self.variables)
        self.variables.append(variable)

    def visit_static_variable(self,variable):
        self.comment = append_comment(self.comment,self.static_variables)
        self.static_variables.append(variable)

    def visit_alias(self,alias):
        self.comment = append_comment(self.comment,self.aliases)
        self.aliases.append(alias)

    def visit_forward_declaration(self,forward_declaration):
        self.forward_declarations.append(forward_declaration)


def extend_section(new_section, section_part, with_separator=True):
    if new_section and section_part and with_separator:
        new_section.append(cpp.Separator())
    new_section.extend(section_part)


def sort_section(section):
    type_extractor = ExtractTypes()
    for entry in section:
        entry.visit(type_extractor)

    new_section = []
    new_section.extend(type_extractor.aliases)
    extend_section(new_section, type_extractor.static_variables)
    extend_section(new_section, type_extractor.constructors)
    extend_section(new_section, type_extractor.destructor)
    extend_section(new_section, type_extractor.operators)
    extend_section(new_section, type_extractor.functions)
    extend_section(new_section, type_extractor.forward_declarations)
    extend_section(new_section, type_extractor.variables, with_separator=False)
    return new_section


class SortClass(RecursionVisitor):
    def visit_class(self,class_):
        section_extractor = ExtractPublicProtectedPrivateSections()
        class_.visit(section_extractor)
        section_extractor.public_section = sort_section(section_extractor.public_section)
        section_extractor.protected_section = sort_section(section_extractor.protected_section)
        section_extractor.private_section = sort_section(section_extractor.private_section)

        class_.content = []
        if section_extractor.public_section:
            class_.content.append(cpp.public_access)
            class_.content.extend(section_extractor.public_section)
        if section_extractor.protected_section:
            class_.content.append(cpp.protected_access)
            class_.content.extend(section_extractor.protected_section)
        if section_extractor.private_section:
            class_.content.append(cpp.private_access)
            class_.content.extend(section_extractor.private_section)


def remove_inclusion_directives(main_scope):
    new_scope = []
    for entry in main_scope.content:
        if not cpp.is_inclusion_directive(entry):
            new_scope.append(entry)
    main_scope.content = new_scope


def remove_duplicate_inclusion_directives(main_scope):
    new_scope = []
    for entry in main_scope.content:
        if cpp.is_inclusion_directive(entry):
            in_new_scope = False
            for new_entry in new_scope:
                if cpp.is_inclusion_directive(new_entry) and new_entry.value == entry.value:
                    in_new_scope = True
                    break
            if not in_new_scope:
                new_scope.append(entry)
        else:
            new_scope.append(entry)
    main_scope.content = new_scope


def prepend_inclusion_directives(main_scope, inclusion_directives):
    for inclusion_directive in reversed(inclusion_directives):
        main_scope.content.insert(0, inclusion_directive)


def append_inclusion_directive(main_scope, inclusion_directive):
    for i in range(len(main_scope.content)):
        if not cpp.is_inclusion_directive(main_scope.content[i]):
            main_scope.content.insert(i, inclusion_directive)
            return


def append_inclusion_directives(main_scope, inclusion_directives):
    for inclusion_directive in inclusion_directives:
        append_inclusion_directive(main_scope, inclusion_directive)


def add_comment(new_content, entry, comments):
    comment = util.get_comment(comments, entry)
    if comment:
        new_content.append(cpp.Comment(comment))


def add_comments(scope, comments):
    new_content = []
    for entry in scope.content:
        if cpp.is_namespace(entry):
            add_comment(new_content, 'namespace ' + entry.name, comments)
            add_comments(entry, comments)
        elif cpp.is_class(entry) or cpp.is_struct(entry):
            add_comment(new_content, entry.type + ' ' + entry.name, comments)
            add_comments(entry, comments)
        elif entry.type in [cpp.FUNCTION, cpp.CONSTRUCTOR, cpp.DESTRUCTOR, cpp.FUNCTION_TEMPLATE, cpp.ASSIGNMENT_OPERATOR]:
            add_comment(new_content, entry.get_declaration(), comments)
        elif entry.type == cpp.ALIAS:
            add_comment(new_content, util.concat(entry.tokens, ' '), comments)
        new_content.append(entry)
    scope.content = new_content
