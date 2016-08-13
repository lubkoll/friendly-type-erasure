import argparse
import clang
import os
import re

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
    function = re.sub('\s*\&\s*', '& ',function)
    function = re.sub('\s*\<\s*', '\<',function)
    function = re.sub('\s*\>\s*', '\>',function)
    function = re.sub('\s*\*\s*', '* ',function)
    function = re.sub('\s*\(\s*', '(',function)
    function = re.sub('\s*]\)\s*', ') ',function)
    function = re.sub('class\s+','',function)
    function = re.sub('struct\s+','',function)
    function = re.sub(';','',function)
    function = re.sub('{','',function)
    function = re.sub('\n','',function)
    return trim(function)


def same_signature(function, other_function):
    return unify_signature(function) == unify_signature(other_function)


def close_namespaces(file_writer, data):
    while len(data.current_namespaces):
        data.current_namespaces.pop()
        file_writer.process_close_namespace()


def indent_lines(lines, data, indent):
    regex = re.compile(r'\n')
    return regex.sub('\n' + indent, indent + lines)


def get_comment(findent, comments, name):
    if comments is not None:
        for comment in comments:
            if same_signature(name,comment.name):
                out = ''
                for line in comment.comment:
                    if line.startswith('*'):
                        out += ' '
                    out += findent + line
                return out
    return ''


def add_default_arguments(parser):
    parser.add_argument('--non-copyable', type=str, required=False,
                        help='set to true to generate a non-copyable interface')
    parser.add_argument('--indent', nargs='?', type=int,
                        const=4, default=4,
                        help='number of spaces for indentation')
    parser.add_argument('--handle-extension', nargs='?', type=str,
                        default='Handles',
                        help='ending for namespace containing the handle implementation (not considered if --handle-namespace is specified)')
    parser.add_argument('--clang-path', type=str, required=False,
                        default='/usr/lib/llvm-3.8/lib',
                        help='path to libclang library')
    parser.add_argument('clang_args', metavar='Clang-arg', type=str, nargs=argparse.REMAINDER,
                        default='-std=c++14',
                        help='additional args to pass to Clang')
    parser.add_argument('file', type=str, help='the input file containing archetypes')
    parser.add_argument('--handle-namespace', nargs='?', type=str, required=False,
                        default='',
                        help='namespace containing the handle implementations')
    parser.add_argument('--vtable', action='store_true',
                        help='use vtable-based type erasure')

def parse_default_args(args, data):
    data.non_copyable = args.non_copyable
    data.indent = args.indent
    data.handle_extension = args.handle_extension
    data.handle_namespace = args.handle_namespace
    data.file = args.file
    data.vtable = args.vtable
    data.clang_args = args.clang_args
    return data

    return data