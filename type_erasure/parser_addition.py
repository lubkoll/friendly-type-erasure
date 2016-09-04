import copy
import re
from type_erasure.util import trim, ltrim

class Comment:
    def __init__(self, comment=[], name=""):
        self.comment = copy.deepcopy(comment)
        self.name = copy.deepcopy(name)

    def __str__(self):
        result = "Name:\n"  + self.name + "\n"
        result += "Comment:\n"
        for line in self.comment:
            result += line
        return result


def is_single_line_comment(line):
    single_line_comments = ['///', '//!', '//']
    line = trim(line)
    for prefix in single_line_comments:
        if line.startswith(prefix):
            return True
    return False


def is_multi_line_comment(line,in_multi_line_comment):
    line = trim(line)
    if not in_multi_line_comment and line.startswith('/*'):
        return True
    if in_multi_line_comment and line.startswith('*'):
        return True

    return False


def is_comment(line, in_multi_line_comment):
    return is_single_line_comment(line) or is_multi_line_comment(line,in_multi_line_comment)


def is_template(line):
    line = trim(line)
    return line.startswith("template ") or line.startswith("template<");


def skip_empty_lines(file,line):
    while trim(line) == '':
        line = file.readline()
    return line


def extract_include_guard(filename):
    # detect classical include guard
    archetypes = open(filename).read()
    guard_regex = re.compile(r'#ifndef\s+([^\s]+)[^\n]*\n#define\s+\1')
    match = guard_regex.search(archetypes)
    if match and match.start() == archetypes.index('#'):
        return '''#ifndef {0}
#define {0}

'''.format(match.group(1))

    # detect pragma once include guard
    guard_regex = re.compile(r'#pragma\s+once\s+')
    match = guard_regex.search(archetypes)
    if match and match.start() == archetypes.index('#'):
        return '#pragma once\n'

    return None


def read_template_definition(file, line):
    if not is_template(line):
        return ""

    opening_angles = line.count('<')
    closing_angles = line.count('>')
    name = line
    while opening_angles > closing_angles:
        line = file.readline()
        name += line
        opening_angles += line.count('<')
        closing_angles += line.count('>')
    return name


def read_comment(file,line,comment):
    multi_line_comment = False
    while is_comment(line, multi_line_comment):
        if not multi_line_comment:
            multi_line_comment = is_multi_line_comment(line,multi_line_comment)
        line = ltrim(line)
        comment.append(line)
        line = file.readline()

    return line


def read_name(file, line):
    if is_template(line):
        name = read_template_definition(file, line)
        line = file.readline()
    else:
        name = ""

    opening_brackets = line.count('(')
    closing_brackets = line.count(')')
    name += line;
    while opening_brackets > closing_brackets:
        line = file.readline()
        opening_brackets += line.count('(')
        closing_brackets += line.count(')')
        name += line
        file.readline()

    name = trim(name)
    if name.endswith(';\n'):
        name = name[:-2] + '\n'
    if name.endswith(';'):
        name = name[:-1]
    return trim(name)


def read_comment_and_name(file, line):
    comment = Comment()
    while is_comment(line,False):
        line = read_comment(file, line, comment.comment)
        line = skip_empty_lines(file, line)
    comment.name = read_name(file, line)
    return comment


def extract_comments(filename):
    comments = []
    file = open(filename, 'r+')
    while True:
        line = file.readline()
        if not line: break
        if is_comment(line,False):
            comment = read_comment_and_name(file, line)
            comments.append(comment)
    file.close()

    return comments

