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
    formatter_file = os.path.join(os.path.dirname(__file__), 'formatting.txt')
    line = trim(open(formatter_file, 'r').readline().replace('filename', filename))
    call(line.split(' '))


def same_class(entry, classname):
    return entry.type == 'class' and entry.name == classname


def get_comment(comments, name):
    if comments is not None:
        for comment in comments:
            if same_signature(name,comment.name):
                return comment
    return ''


def contains_include_for_forward_declaration(comment):
    return re.match(r'//\s*%\s*([<>"._\\\-a-zA-Z0-9]*)\s*%',comment.comment[0])


def get_inclusion_directives_for_forward_declarations(data, comments):
    inclusion_directives_for_forward_decl = []
    for comment in comments:
        match = contains_include_for_forward_declaration(comment)
        if match:
            inclusion_directives_for_forward_decl.append(match.group(1))
    return inclusion_directives_for_forward_decl