#!/usr/bin/env python

import to_string
import util
import file_parser
import cpp
import cpp_file_parser
import parser_addition
import os
import handle_detail
import table_detail


def add_details(data, scope, class_scope):
    if data.table:
        table_detail.add_table(data, scope, class_scope)
        table_detail.add_execution_wrapper(data, scope, class_scope)
    else:
        handle_detail.add_handle_base(data, scope, class_scope)
        handle_detail.add_handle(data, scope, class_scope)


def get_detail_file_impl(data, scope, interface_scope):
    for entry in interface_scope.content:
        if cpp.is_namespace(entry):
            scope.add( cpp.Namespace(entry.name) )
            get_detail_file_impl(data,scope,entry)
            scope.close()
        elif cpp.is_class(entry) or cpp.is_struct(entry):
            scope.add(cpp.Namespace(entry.name + data.detail_extension))
            add_details(data, scope, entry)
            scope.close()


def get_detail_file(data, interface_scope):
    main_scope = cpp.Namespace('global')
    main_scope.add(cpp.ScopeEntry(cpp.INCLUDE_GUARD, '#pragma once\n'))
    for entry in interface_scope.content:
        if cpp.is_inclusion_directive(entry):
            main_scope.add(entry)
    main_scope.add( cpp.InclusionDirective('<functional>') )
    if data.copy_on_write:
        main_scope.add(cpp.InclusionDirective('<memory>'))
    if not data.table:
        main_scope.add( cpp.InclusionDirective('<type_traits>') )
        main_scope.add( cpp.InclusionDirective('<utility>') )
        main_scope.add( cpp.InclusionDirective('<' + os.path.join(data.util_include_path,'util.hh') + '>') )
    else:
        main_scope.add( cpp.InclusionDirective('<' + os.path.join(data.util_include_path,'table_util.hh') + '>') )

    comments = parser_addition.extract_comments(data.file)
    inclusion_directives_for_forward_decl = util.get_inclusion_directives_for_forward_declarations(data, comments)
    for inclusion_directive in inclusion_directives_for_forward_decl:
        main_scope.add(cpp.InclusionDirective(inclusion_directive))

    get_detail_file_impl(data, main_scope, interface_scope)
    return main_scope


def write_file(data):
    processor = cpp_file_parser.CppFileParser()
    parser = file_parser.GenericFileParser(processor, data)
    parser.parse()
    scope = get_detail_file(data, processor.scope)
    cpp_file_parser.remove_duplicate_inclusion_directives(scope)
    if data.table:
        scope.visit(table_detail.SortTable())
    to_string.write_scope(scope, os.path.join(data.detail_folder,data.detail_file), to_string.Visitor(short_entries=[cpp.ALIAS]), not data.no_warning_header, True)
