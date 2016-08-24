import argparse
import clang
import os
import re
from subprocess import call
from parser_addition import extract_include_guard, trim


def trim(string):
    return string.strip(' \n\r\t')


def rtrim(string):
    return string.rstrip(' \n\r\t')


class client_data:
    def __init__(self):
        self.tu = None
        self.current_namespaces = []  # cursors
        self.current_struct = clang.cindex.conf.lib.clang_getNullCursor()
        # function signature, forwarding call arguments, optional return
        # keyword, function name, and "const"/"" for function constness
        self.member_functions = []  # each element [''] * 5
        self.given_interface = ''
        self.interface_file = ''
        self.handle_form = ''
        self.form_lines = []
        self.non_copyable = False
        self. indent = ''
        self.impl_ending = ''
        self.current_cursor = None


def prepare_form_impl (form):
    form = form.replace('{', '{{')
    form = form.replace('}', '}}')
    regex = re.compile(r'%(\w+)%')
    return regex.sub(r'{\1}', form)[:-1]


def prepare_form (form):
    if type(form) == str:
        return prepare_form_impl(form)
    else:
        for i in range(len(form)):
            form[i] = prepare_form_impl(form[i])
        return \
            form


def print_diagnostic(diag):
    severities = ['ignored', 'note', 'warning', 'error', 'fatal error']
    file_ = diag.location.file
    line = diag.location.line
    column = diag.location.column
    severity = severities[diag.severity]
    spelling = diag.spelling
    os.write(2, '{file_}:{line}:{column} {severity}: {spelling}\n'.format(**locals()))


def unify_signature(function):
    function = re.sub('\s*~\s*', '~',function)
    function = re.sub('\s*=\s*', '=',function)
    function = re.sub('\s*\&\s*', '& ',function)
    function = re.sub('\s*\<\s*', '\<',function)
    function = re.sub('\s*\>\s*', '\>',function)
    function = re.sub('\s*\*\s*', '* ',function)
    function = re.sub('\s*\(\s*', '(',function)
    function = re.sub('\s*\)\s*', ') ',function)
    function = re.sub('\s*\{\s*', '(',function)
    function = re.sub('\s*\}\s*', ') ',function)
    function = re.sub('class\s+','',function)
    function = re.sub('struct\s+','',function)
    function = re.sub(';','',function)
    function = re.sub('\s*,\s*',',',function)
    function = re.sub('\n','',function)
    return trim(function)


def same_signature(function, other_function):
    return unify_signature(function) == unify_signature(other_function)


def close_namespaces(file_writer, data):
    while len(data.current_namespaces):
        data.current_namespaces.pop()
        file_writer.process_close_namespace()


def concat(tokens,spacing=''):
    str = ''
    for token in tokens:
        str += token.spelling + spacing
    return str


def clang_format(filename):
    call(["clang-format-3.8", '-i', filename])


def indent_lines(lines, data, indent):
    regex = re.compile(r'\n')
    return regex.sub('\n' + indent, indent + lines)


def same_class(entry, classname):
    return entry.type == 'class' and entry.name == classname


def is_class(entry):
    return entry.type == 'class' or entry.type == 'struct'


def is_namespace(entry):
    return entry.type == 'namespace'


def is_function(entry):
    return entry.type == 'function'


def get_comment(comments, name):
    if comments is not None:
        for comment in comments:
            print "comparing " + name + " and " + comment.name
            if same_signature(name,comment.name):
                out = ''
                for line in comment.comment:
                    if line.startswith('*'):
                        out += ' '
                    out += line
                return out
    return ''


def add_default_arguments(parser):
    parser.add_argument('--non-copyable', type=str, required=False,
                        help='set to true to generate a non-copyable interface')
    parser.add_argument('--indent', nargs='?', type=int,
                        const=4, default=4,
                        help='number of spaces for indentation')
    parser.add_argument('--detail-extension', nargs='?', type=str,
                        default='Handles',
                        help='ending for namespace containing the handle or function pointer table implementation (not considered if --detail-namespace is specified)')
    parser.add_argument('--clang-path', type=str, required=False,
                        default='/usr/lib/llvm-3.8/lib',
                        help='path to libclang library')
    parser.add_argument('clang_args', metavar='Clang-arg', type=str, nargs=argparse.REMAINDER,
                        default='-std=c++14',
                        help='additional args to pass to Clang')
    parser.add_argument('file', type=str, help='the input file containing archetypes')
    parser.add_argument('--detail-namespace', nargs='?', type=str, required=False,
                        default='',
                        help='namespace containing implementations of handles, resp tables for the function pointers')
    parser.add_argument('--vtable', action='store_true',
                        help='use vtable-based type erasure')

def parse_default_args(args, data):
    data.non_copyable = args.non_copyable
    data.indent = args.indent
    data.detail_extension = args.detail_extension
    data.detail_namespace = args.detail_namespace
    data.file = args.file
    data.vtable = args.vtable
    data.clang_args = args.clang_args
    return data

    return data