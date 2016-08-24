import argparse
import copy
import re
from subprocess import call

import clang_util
import file_parser
import cpp_file_parser
import file_writer
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
    scope_class.name = new_name
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
        elif util.is_function(entry):
            replace_entry_in_tokens(old_name, new_name, entry.tokens)


def remove_outside_class(classname, scope):
    for i in range(len(scope.content)):
        if util.same_class(scope.content[i], classname):
            scope.content = [ scope.content[i] ]
            return
        elif util.is_namespace(scope.content[i]):
            remove_outside_class(classname, scope.content[i])


def remove_from_class(types_to_remove, classname, scope, do_remove=False):
    content = []
    for entry in scope.content:
        if util.same_class(entry, classname):
            remove_from_class(types_to_remove, classname, entry, True)
            content.append(entry)
        if util.is_namespace(entry):
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
        if entry.type == 'access specifier':
            if entry.value == 'private:':
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
        if util.is_namespace(entry):
            remove_private_members(classname, entry)


def add_pimpl_section(classname, pimpl_classname, scope):
    for entry in scope.content:
        if util.same_class(entry,classname):
            entry.content.append( cpp_file_parser.ScopeEntry('access specifier', 'private:' ) )
            entry.content.append( cpp_file_parser.ScopeEntry('forward declaration', 'class ' + pimpl_classname + ';' ) )
            entry.content.append( cpp_file_parser.ScopeEntry('variable', 'std::unique_ptr<' + pimpl_classname + '> pimpl_;' ) )
        if util.is_namespace(entry):
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


def pimpl_functions(classname, scope):
    for entry in scope.content:
        if util.is_namespace(entry):
            pimpl_functions(classname, entry)
        if util.is_function(entry) and entry.classname == classname:
            pimpl_function(entry)


def add_inclusion_directive_at_end(filename, scope):
    i = 0
    while scope.content[i].type == cpp_file_parser.include_directive:
        i += 1
    scope.content.insert(i, cpp_file_parser.InclusionDirective( '#include "' + filename + '"'))


def add_inclusion_directive_at_start_if_not_present(inclusion_directive, scope):
    present = False
    for entry in scope.content:
        if entry.type == 'include' and entry.value == inclusion_directive:
            present = True
            break

    if not present:
        scope.content.insert(0, cpp_file_parser.InclusionDirective(inclusion_directive))


def remove_inclusion_directives(scope):
    content = []
    for entry in scope.content:
        if entry.type != cpp_file_parser.include_directive:
            content.append(entry)
    scope.content = content

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
    content = copy.deepcopy(processor.content)
    remove_outside_class(data.classname, content)
    remove_from_class(['alias', 'enum', 'static variable'], data.classname, content)
    replace_classname(data.classname, data.classname + data.impl, content)

    to_string.write_scope(content, private_filename)
    util.clang_format(private_filename)

    # write public header file
    content = copy.deepcopy(processor.content)
    remove_private_members(data.classname, content)
    add_pimpl_section(data.classname, data.classname + data.impl, content)
    add_inclusion_directive_at_start_if_not_present('#include <memory>', content)

    comments = parser_addition.extract_comments(data.file)
    visitor = to_string.VisitorForHeaderFile(comments)
    to_string.write_scope(content, data.interface_header_file, visitor)
    util.clang_format(data.interface_header_file)


def process_private_source_file(data, content, header_file, private_filename):
    replace_inclusion_directive('#include "' + header_file + '"',
                                '#include "' + get_private_name(data.interface_header_file, data.impl) + '"', content)

    replace_classname(data.classname, data.classname + data.impl, content)

    to_string.write_scope(content, private_filename)
    util.clang_format(private_filename)


def process_public_source_file(data, content):
    pimpl_functions(data.classname, content)
    remove_inclusion_directives(content)
    add_inclusion_directive_at_end(data.interface_header_file, content)
    add_inclusion_directive_at_end(get_private_name(data.interface_header_file,data.impl), content)
    to_string.write_scope(content, data.interface_source_file, to_string.VisitorForSourceFile())
    util.clang_format(data.interface_source_file)


def process_source_file(data):
    header_file = data.file
    data.file = data.cpp_file

    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()

    content = copy.deepcopy(processor.content)
    private_filename = get_private_name(data.interface_source_file, data.impl)
    process_private_source_file(data, content, header_file, private_filename)

    content = copy.deepcopy(processor.content)
    process_public_source_file(data, content)


def pimpl_class(data):
#    comments = parser_addition.extract_comments(data.file)

    process_header_file(data)
    process_source_file(data)
