#!/usr/bin/env python

import handle_interface_generator
import table_interface_generator


def get_source_filename(header_filename):
    for ending in ['.hh', '.h', '.hpp']:
        header_filename = header_filename.replace(ending,'.cpp')
    return header_filename


def write_file(data):
    if data.table:
        table_interface_generator.write_file(data)
    else:
        handle_interface_generator.write_file(data)
