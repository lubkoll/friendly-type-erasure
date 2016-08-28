import clang
import os
import re
from subprocess import call


def trim(string):
    return string.strip(' \n\r\t')


def rtrim(string):
    return string.rstrip(' \n\r\t')


def ltrim(string):
    return string.lstrip(' \t')


def print_diagnostic(diag):
    severities = ['ignored', 'note', 'warning', 'error', 'fatal error']
    file_ = diag.location.file
    line = diag.location.line
    column = diag.location.column
    severity = severities[diag.severity]
    spelling = diag.spelling
    os.write(2, '{file_}:{line}:{column} {severity}: {spelling}\n'.format(**locals()))


def unify_signature(function):
    function = re.sub(r'\s*(~|=|&|<|>|,|\*|\(|\)|\{|\}|\[|\]|)\s*', r'\1', function)
    function = re.sub(r'class\s+|struct\s+|;|\n', '', function)
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
    pass
#    call(["clang-format-3.8", '-i', filename])


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
            if same_signature(name,comment.name):
                return comment
    return ''


def get_return_type(data, classname):
    if data.copy_on_write:
        return 'std :: shared_ptr < HandleBase > '
    else:
        return classname + ' * '


def get_generator(data, classname):
    if data.copy_on_write:
        return 'std :: make_shared < typename std :: decay < ' + classname + ' > :: type >'
    else:
        return 'new typename std :: decay < ' + classname + ' > :: type'