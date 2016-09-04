import code
import copy
import os
import re

import file_parser
import cpp_file_parser
import parser_addition
import to_string
import util


def replace_entry_in_tokens(old_name, new_name, tokens):
    for i in range(len(tokens)):
        if tokens[i].spelling == old_name:
            tokens[i].spelling = new_name
    return tokens


def replace_type_in_arguments(old_name, new_name, arguments):
    for arg in arguments:
        arg.tokens = replace_entry_in_tokens(old_name, new_name, arg.tokens)
    return arguments


def replace_classname_impl(old_name, new_name, scope_class):
    scope_class.name = old_name + '::' + new_name
    for i in range(len(scope_class.content)):
        type = scope_class.content[i].type
        if type in ['destructor', 'constructor', 'function']:
            scope_class.content[i].tokens = replace_entry_in_tokens(old_name, new_name, scope_class.content[i].tokens)
            if type == 'destructor':
                scope_class.content[i].name = '~' + new_name
            if type == 'constructor':
                scope_class.content[i].name = new_name


def replace_classname(old_name, new_name, scope):
    for i in range(len(scope.content)):
        entry = scope.content[i]
        if util.same_class(entry, old_name):
            replace_classname_impl(old_name, new_name, entry)
        elif entry.type in ['class','namespace']:
            replace_classname(old_name, new_name, entry)
        elif cpp_file_parser.is_function(entry):
            replace_entry_in_tokens(old_name, new_name, entry.tokens)


def remove_outside_class(classname, scope):
    for i in range(len(scope.content)):
        if util.same_class(scope.content[i], classname):
            scope.content = [ scope.content[i] ]
            return
        elif cpp_file_parser.is_namespace(scope.content[i]):
            remove_outside_class(classname, scope.content[i])


def remove_from_class(types_to_remove, classname, scope, do_remove=False):
    content = []
    for entry in scope.content:
        if util.same_class(entry, classname):
            remove_from_class(types_to_remove, classname, entry, True)
            content.append(entry)
        if cpp_file_parser.is_namespace(entry):
            remove_from_class(types_to_remove, classname, entry)
            content.append(entry)
        if do_remove:
            if entry.type not in types_to_remove:
                content.append(entry)
    scope.content = content


def replace_inclusion_directive(old_header, new_header, scope):
    for entry in scope.content:
        if entry.type == 'include' and old_header in entry.value:
            entry.value = entry.value.replace(old_header,new_header)


def remove_private_members_impl(class_scope):
    in_private_section = False
    content = []
    for entry in class_scope.content:
        if cpp_file_parser.is_access_specifier(entry):
            if entry.value == cpp_file_parser.PRIVATE:
                in_private_section = True
            else:
                in_private_section = False
                content.append(entry)
        else:
            if not in_private_section:
                content.append(entry)
    class_scope.content = content


def remove_private_members(classname, scope):
    for entry in scope.content:
        if util.same_class(entry, classname):
            remove_private_members_impl(entry)
        if cpp_file_parser.is_namespace(entry):
            remove_private_members(classname, entry)


def add_pimpl_section(classname, pimpl_classname, scope):
    for entry in scope.content:
        if util.same_class(entry,classname):
            entry.content.append( cpp_file_parser.AccessSpecifier(cpp_file_parser.PRIVATE) )
            entry.content.append( cpp_file_parser.ForwardDeclaration('class ' + pimpl_classname + ';' ) )
            entry.content.append( cpp_file_parser.Variable('std::unique_ptr<' + pimpl_classname + '> pimpl_;' ) )
        if cpp_file_parser.is_namespace(entry):
            add_pimpl_section(classname, pimpl_classname, entry)


def pimpl_function(function):
    arguments = cpp_file_parser.get_function_arguments(function.name, function.tokens)
    new_tokens = function.tokens[:cpp_file_parser.get_declaration_end_index(function.name,function.tokens)]
    function_call = function.return_str + 'pimpl_->' + function.name + '( '
    for arg in arguments:
        function_call += arg.name()
        if arg is not arguments[-1]:
            function_call += ', '
    function_call += ' );\n'
    new_body = [ cpp_file_parser.SimpleToken('{\n'),
                 cpp_file_parser.SimpleToken('assert(pimpl_);\n'),
                 cpp_file_parser.SimpleToken(function_call),
                 cpp_file_parser.SimpleToken('}\n')]
    new_tokens.extend(new_body)
    function.tokens = new_tokens


class PimplFunctions(cpp_file_parser.RecursionVisitor):
    def __init__(self, classname, private_classname):
        self.classname = classname
        self.private_classname = private_classname
        self.in_pimpl = False

    def visit_class(self,class_):
        self.in_pimpl = class_.get_name() == self.classname
        for entry in class_.content:
            entry.visit(self)

    def visit_function(self,function):
        if not self.in_pimpl or cpp_file_parser.is_special_member_function(function):
            return

        new_function = function.get_declaration()
        if function.type == cpp_file_parser.CONSTRUCTOR:
            new_function += ' : pimpl_ ( new ' + self.private_classname
            new_function += ' ( ' + cpp_file_parser.get_function_arguments_in_single_call(function) + ' ) ) { }'
        else:
            new_function += ' { assert ( pimpl_ ) ; '
            new_function += function.return_str + 'pimpl_ -> ' + code.get_single_function_call(function) + ' ;'
            new_function += '}'
        function.tokens = [cpp_file_parser.SimpleToken(spelling) for spelling in new_function.split(' ')]


class RemoveConstructors(cpp_file_parser.RecursionVisitor):
    def __init__(self, classname):
        self.classname = classname
        self.new_content = []

    def visit(self, visited):
        self.new_content.append(visited)

    def visit_function(self,function):
        if not cpp_file_parser.is_special_member_function(function):
            self.new_content.append(function)

    def visit_class(self,class_object):
        if class_object.get_name() != self.classname:
            return

        self.new_content = []
        for entry in class_object.content:
            entry.visit(self)
        class_object.content = self.new_content


class AddConstructorsAndAssignments(cpp_file_parser.RecursionVisitor):
    def __init__(self, data):
        self.data = data

    def visit_class(self,class_object):
        if class_object.get_name() != self.data.classname:
            return

        class_object.content.append(cpp_file_parser.AccessSpecifier(cpp_file_parser.PUBLIC))

        default_constructor = self.data.classname + ' ( ) '
        if self.data.implicit_default_constructor:
            default_constructor += ': pimpl_( new ' + self.data.private_classname + ' ( ) ) { }'
        else:
            default_constructor += '{ }'
        class_object.content.append(cpp_file_parser.get_function_from_text(self.data.classname, self.data.classname,
                                                                           '', default_constructor,
                                                                           cpp_file_parser.CONSTRUCTOR))
        destructor = '~ ' + self.data.classname + ' ( ) { } '
        class_object.content.append(cpp_file_parser.get_function_from_text(self.data.classname,
                                                                           '~' + self.data.classname,
                                                                           '', destructor,
                                                                           cpp_file_parser.DESTRUCTOR))

        if not self.data.non_copyable:
            copy_assignment = code.get_pimpl_copy_assignment(self.data, self.data.classname,
                                                             self.data.private_classname, 'pimpl_')
            class_object.content.append(cpp_file_parser.get_function_from_text(self.data.classname, 'operator=',
                                                                               '', copy_assignment,
                                                                               cpp_file_parser.ASSIGNMENT_OPERATOR))
            copy_constructor = code.get_pimpl_copy_constructor(self.data, self.data.classname,
                                                               self.data.private_classname, 'pimpl_')
            class_object.content.append(cpp_file_parser.get_function_from_text(self.data.classname, self.data.classname,
                                                                               '', copy_constructor,
                                                                               cpp_file_parser.CONSTRUCTOR))

        if not self.data.non_moveable:
            move_assignment = code.get_pimpl_move_assignment(self.data, self.data.classname, 'pimpl_')
            class_object.content.append(cpp_file_parser.get_function_from_text(self.data.classname, 'operator=',
                                                                               '', move_assignment,
                                                                               cpp_file_parser.ASSIGNMENT_OPERATOR))
            move_constructor = code.get_pimpl_move_constructor(self.data, self.data.classname, 'pimpl_')
            class_object.content.append(cpp_file_parser.get_function_from_text(self.data.classname, self.data.classname,
                                                                               '', move_constructor,
                                                                               cpp_file_parser.CONSTRUCTOR))

###


def generate_private_file(classname, filename, impl):
    given_file = open(filename, 'r')
    ending = '.' + filename.split('.')[-1]
    file = open(filename.replace(ending,impl + ending), 'w')
    regex_ = r'([\s\(\{\[<&\*]*)(' + classname + ')([\s\)\]\}>&\*]*)'
    for line in given_file:
        line = re.sub(regex_, r'\1' + classname + impl + r'\3', line)
        file.write(line)
    given_file.close()
    file.close()


def generate_private_implementation(args):
    generate_private_file(args.classname, args.file, args.impl)
#    if args.source_file != '':
#        generate_private_file(args.classname, args.classname + args.impl, filename.replace('.hh','.cpp'))


def get_private_name(file, impl):
    ending = '.' + file.split('.')[-1]
    return file.replace(ending, impl + ending)


def process_header_file(data):
    private_filename = get_private_name(data.interface_header_file, data.impl)
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()

    # write private header file
    main_scope = copy.deepcopy(processor.scope)
    remove_outside_class(data.classname, main_scope)
    remove_from_class([cpp_file_parser.ALIAS, cpp_file_parser.ENUM, cpp_file_parser.STATIC_VARIABLE],
                      data.classname, main_scope)
    replace_classname(data.classname, data.classname + data.impl, main_scope)

    comments = parser_addition.extract_comments(data.file)
    inclusion_directives = [cpp_file_parser.InclusionDirective(inclusion_directive)
                            for inclusion_directive in
                            util.get_inclusion_directives_for_forward_declarations(data, comments)]
    cpp_file_parser.append_inclusion_directives(main_scope, inclusion_directives)

    main_scope.visit(cpp_file_parser.SortClass())
    to_string.write_scope(main_scope, private_filename)
    util.clang_format(private_filename)

    # write public header file
    main_scope = copy.deepcopy(processor.scope)
    remove_private_members(data.classname, main_scope)
    add_pimpl_section(data.classname, data.classname + data.impl, main_scope)
    main_scope.visit(RemoveConstructors(data.classname))
    main_scope.visit(AddConstructorsAndAssignments(data))
    cpp_file_parser.prepend_inclusion_directives(main_scope, [cpp_file_parser.InclusionDirective('<memory>')])

    visitor = to_string.VisitorForHeaderFile()
    main_scope.visit(cpp_file_parser.SortClass())
    comments = parser_addition.extract_comments(data.file)
    cpp_file_parser.add_comments(main_scope, comments)
    to_string.write_scope(main_scope, data.interface_header_file, visitor)
    util.clang_format(data.interface_header_file)
    return main_scope


def process_private_source_file(data, content, header_file, private_filename):
    replace_inclusion_directive('"' + header_file + '"',
                                '"' + get_private_name(data.interface_header_file, data.impl) + '"', content)

    replace_classname(data.classname, data.classname + data.impl, content)

    to_string.write_scope(content, private_filename)
    util.clang_format(private_filename)


def process_public_source_file(data, main_scope):
    main_scope.visit(PimplFunctions(data.classname, data.private_classname))
    cpp_file_parser.remove_inclusion_directives(main_scope)

    public_header_file = os.path.basename(data.interface_header_file)
    relative_include_files = [public_header_file, get_private_name(public_header_file,data.impl)]
    inclusion_directives = [cpp_file_parser.InclusionDirective('"' + include + '"') for include in relative_include_files]
    inclusion_directives.append(cpp_file_parser.InclusionDirective('<cassert>'))
    cpp_file_parser.prepend_inclusion_directives(main_scope, inclusion_directives)

    main_scope.visit(cpp_file_parser.SortClass())
    to_string.write_scope(main_scope, data.interface_source_file, to_string.VisitorForSourceFile())
    util.clang_format(data.interface_source_file)


def process_source_file(data, main_scope):
    if data.cpp_file:
        header_file = data.file
        data.file = data.cpp_file

        processor = cpp_file_parser.CppFileParser()
        parser = file_parser.GenericFileParser(processor, data)
        parser.parse()

        main_scope = copy.deepcopy(processor.scope)
        private_filename = get_private_name(data.interface_source_file, data.impl)
        process_private_source_file(data, main_scope, header_file, private_filename)
        main_scope = copy.deepcopy(processor.scope)

    process_public_source_file(data, main_scope)


def pimpl_class(data):
#    comments = parser_addition.extract_comments(data.file)

    main_scope = process_header_file(data)
    process_source_file(data, main_scope)
