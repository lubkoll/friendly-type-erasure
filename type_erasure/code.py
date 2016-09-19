import cpp_file_parser
import parser_addition
import util


def get_decayed(type_):
    return 'typename std :: decay < ' + type_ + ' > :: type'


def get_handle_return_type(data, classname):
    if data.copy_on_write:
        if data.small_buffer_optimization:
            return 'std :: shared_ptr < HandleBase < ' + data.interface_type + ' , Buffer > > '
        else:
            return 'std :: shared_ptr < HandleBase < ' + data.interface_type + ' > > '
    else:
        return classname + ' * '


def get_generator(data, classname):
    if data.copy_on_write:
        return 'std :: make_shared < typename std :: decay < ' + classname + ' > :: type >'
    else:
        return 'new typename std :: decay < ' + classname + ' > :: type'


static_reference_check = 'typename std :: enable_if < std :: is_same < typename std :: remove_const < T > :: type , ' + \
                         get_decayed('U') + ' & > :: value > :: type * = nullptr '


def get_static_value_check(first_type, second_type):
    return 'typename std :: enable_if < std :: is_same < ' + first_type + ' , ' + get_decayed(second_type) + \
           ' > :: value > :: type * = nullptr'

def enable_if_not_same(first_type, second_type):
    return 'typename std :: enable_if < ! std :: is_same < ' + first_type + ' , ' + get_decayed(second_type) + \
           ' > :: value > :: type * = nullptr'

noexcept_if_nothrow_constructible = 'noexcept ( type_erasure_detail :: is_nothrow_constructible < U > ( ) )'


def get_default_default_constructor(classname, noexcept='', constexpr=''):
    return (constexpr and constexpr + ' ' or '') + classname + ' ( ) ' + (noexcept and noexcept + ' ' or '')  + '= default ;'


def get_constructor_from_value_declaration(classname):
    return 'template < typename T , ' + enable_if_not_same(classname, 'T') + ' > ' + classname + ' ( T && value ) '


def get_handle_constructor_body_for_small_buffer_optimization(data, clone_into):
    return '' + data.impl_member + ' = type_erasure_detail :: ' + clone_into + ' < HandleBase , StackAllocatedHandle < ' + get_decayed('T') + \
           ' > , HeapAllocatedHandle < ' + get_decayed('T') + ' > > ( std :: forward < T > ( value ) , buffer_ ) ; '


def get_handle_constructor(data, classname, handle_namespace):
    constructor = get_constructor_from_value_declaration(classname)
    if data.small_buffer_optimization:
        clone_into = 'clone_into_shared_ptr' if data.copy_on_write else 'clone_into'
        constructor += '{ ' + get_handle_constructor_body_for_small_buffer_optimization(data, clone_into) + '}'
    else:
        constructor += ': ' + data.impl_member + ' ( ' + \
                       get_generator(data, handle_namespace + ' :: Handle < ' + get_decayed('T') + ' , ' + classname + ' > ') + ' '
        constructor += '( std :: forward < T > ( value ) ) ) { }'
    return constructor


def get_assignment_from_value(data, classname, handle_namespace):
    code = 'template < typename T , ' + enable_if_not_same(classname, 'T') + ' > '
    code += classname + ' &  operator= ( T && value ) { '

    if data.table:
        return code + 'return * this = ' + classname + ' ( std :: forward < T > ( value ) ) ; }'

    if data.small_buffer_optimization:
        clone_into = 'clone_into_shared_ptr' if data.copy_on_write else 'clone_into'
        if not data.copy_on_write:
            code += 'reset ( ) ; '
        code += get_handle_constructor_body_for_small_buffer_optimization(data, clone_into)
    else:
        if data.copy_on_write:
            code += data.impl_member + ' = '
        else:
            code += '' + data.impl_member + ' . reset ( '
        code += get_generator(data, handle_namespace + ' :: Handle < ' + get_decayed('T') + ' , ' + classname + ' >  ')
        code += ' ( std :: forward < T > ( value ) ) '
        if not data.copy_on_write:
            code += ') '
        code += '; '
    return code + 'return * this ; }'


def get_handle_copy_assignment_for_small_buffer_optimization(data):
    return data.impl_member + ' = other . ' + data.impl_member + ' ? other . ' + data.impl_member + ' -> clone_into ( buffer_ ) : nullptr ; '


def get_cast_to_handle_base(buffer):
    return 'static_cast < HandleBase * >( static_cast < void * > ( ' + buffer + ' ) )'


def get_handle_move_assignment_for_small_buffer_optimization(data, escape_sequence):
    return escape_sequence + 'if ( type_erasure_detail :: is_heap_allocated ( other . ' + data.impl_member + ' , other . buffer_ ) ) ' + \
           data.impl_member + ' = other . ' + data.impl_member + ' ; else { buffer_ = other.buffer_ ; ' + \
           data.impl_member + ' = ' + get_cast_to_handle_base('& buffer_') + ' ; } '


def get_copy_constructor_for_table(data, classname):
    declaration = classname + ' ( const ' + classname + ' & other ) : ' + data.function_table_member + ' ( other . '
    declaration += data.function_table_member + ' ) '
    if data.small_buffer_optimization:
        if data.copy_on_write:
            return declaration + ', ' + data.impl_member + ' ( other . ' + data.impl_member + ' ) { }'
        else:
            return declaration + '{ ' + data.impl_member + ' = other . clone_into ( buffer_ ) ; }'
    else:
        declaration += ' , ' + data.impl_member + ' ( other . ' + data.impl_member + ' ? other . ' + \
                       data.function_table_member + ' . clone ( other . ' + data.impl_member + ' ) '
        return declaration + ': nullptr ) { }'


def get_copy_constructor_for_handle(data, classname):
    declaration = classname + ' ( const ' + classname + ' & other ) '
    if data.small_buffer_optimization:
        return declaration + '{ ' + get_handle_copy_assignment_for_small_buffer_optimization(data) + '}'
    return declaration + ': ' + data.impl_member + ' ( other . ' + data.impl_member + ' ? other . ' + data.impl_member + ' -> clone ( ) : nullptr ) { }'


def get_pimpl_copy_constructor(data, classname, private_classname, member):
    declaration = classname + ' ( const ' + classname + ' & other ) '
    if data.small_buffer_optimization:
        return declaration + '{ ' + get_handle_copy_assignment_for_small_buffer_optimization(data) + '}'
    return declaration + ': ' + member + ' ( other . ' + member + ' ? new ' + private_classname + ' ( * other . pimpl_ ) : ' \
                                                                                                  'nullptr ) { }'


def get_pimpl_move_constructor(data, classname, member):
    declaration = classname + ' ( ' + classname + ' && other ) '
    if data.small_buffer_optimization:
        return declaration + '{ ' + get_handle_copy_assignment_for_small_buffer_optimization(data) + '}'
    return declaration + ': ' + member + ' ( std::move( other ) . ' + member + ' ) { }'


def get_pimpl_copy_assignment(data, classname, private_classname, member):
    declaration = classname + ' & ' + 'operator = ( const ' + classname + ' & other ) { '
    if data.small_buffer_optimization:
        declaration += get_handle_copy_assignment_for_small_buffer_optimization(data)
    declaration += 'if ( other . ' + member + ' ) '
    return declaration + member + ' . reset ( new ' + private_classname + '( * other . pimpl_ ) ) ; ' \
                                                                          'else pimpl_ = nullptr ; return * this ; }'


def get_pimpl_move_assignment(data, classname, member):
    declaration = classname + ' & ' + 'operator = ( ' + classname + ' && other ) { '
    if data.small_buffer_optimization:
        declaration += get_handle_copy_assignment_for_small_buffer_optimization(data)
    return declaration + member + ' = std::move( other ) . ' + member + ' ; return * this ; }'


def get_copy_constructor(data, classname):
    return get_copy_constructor_for_table(data, classname) if data.table \
            else get_copy_constructor_for_handle(data, classname)


def get_move_constructor_for_table(data, classname):
    declaration = classname + ' ( ' + classname + ' && other ) noexcept : '
    declaration += data.function_table_member + ' ( other . ' + data.function_table_member + ' ) '
    if not data.no_rtti:
        declaration += ', type_id_ ( other . type_id_ ) '
    if data.small_buffer_optimization:
        if data.copy_on_write:
            declaration += '{ if ( type_erasure_table_detail :: is_heap_allocated ( other . ' + data.impl_member + ' . get ( ) , '
            declaration += 'other . buffer_ ) ) ' + data.impl_member + ' = std :: move ( other . ' + data.impl_member + ' ) ;'
            declaration += 'else other . ' + data.function_table_member + ' . clone_into ( other . ' + data.impl_member + ' . get ( ) , '
            return declaration + ' buffer_ , ' + data.impl_member + ' ) ; other . ' + data.impl_member + ' = nullptr ; }'
        else:
            declaration += '{ if ( ! other . ' + data.impl_member + ' ) { reset ( ) ; ' + data.impl_member + ' = nullptr ; return ; } '
            declaration += 'if ( type_erasure_table_detail :: is_heap_allocated ( other . ' + data.impl_member + ' , other . buffer_ ) ) '
            declaration += data.impl_member + ' = other . ' + data.impl_member + ' ; '
            declaration += 'else { buffer_ = std :: move ( other . buffer_ ) ; ' + data.impl_member + ' = & buffer_ ; } '
            return declaration + 'other . ' + data.impl_member + ' = nullptr ; }'
    else:
        declaration += ' , ' + data.impl_member + ' ( other . ' + data.impl_member + ' ) '
        return declaration + '{ other . ' + data.impl_member + ' = nullptr ; }'


def get_move_constructor_for_handle(data, classname):
    declaration = classname + ' ( ' + classname + ' && other ) noexcept '
    if data.small_buffer_optimization:
        escape_sequence = 'if ( ! other . ' + data.impl_member + ' ) return ; '
        declaration += '{ ' + get_handle_move_assignment_for_small_buffer_optimization(data, escape_sequence)
    else:
        declaration += ': ' + data.impl_member + ' ( std :: move ( other.' + data.impl_member + ' ) ) { '
    return declaration + 'other . ' + data.impl_member + ' = nullptr ; }'


def get_move_constructor(data, classname):
    return get_move_constructor_for_table(data, classname) if data.table \
            else get_move_constructor_for_handle(data, classname)


def get_copy_operator_for_handle(data, classname):
    declaration = classname + ' & operator = ( const ' + classname + ' & other ) '
    if data.small_buffer_optimization:
        declaration += '{ ' + get_handle_copy_assignment_for_small_buffer_optimization(data)
    else:
        declaration += '{ ' + data.impl_member + ' . reset ( other . ' + data.impl_member + ' ? other . ' + data.impl_member + ' -> clone ( ) : nullptr ) ; '
    return declaration + 'return * this ; }'


def get_copy_operator_for_table(data, classname):
    declaration = classname + ' & operator = ( const ' + classname + ' & other ) { '
    declaration += data.function_table_member + ' = other . ' + data.function_table_member + ' ; '
    if not data.no_rtti:
        declaration += 'type_id_ = other . type_id_ ; '
    if data.small_buffer_optimization:
        if data.copy_on_write:
            declaration += data.impl_member + ' = other . ' + data.impl_member + ' ; '
        else:
            declaration += data.impl_member + ' = other . clone_into ( buffer_ ) ; '
    else:
        declaration += data.impl_member + ' = other . ' + data.impl_member + ' ? other . ' + data.function_table_member + ' . clone ( other . ' + data.impl_member + ' ) '
        declaration += ': nullptr ; '
    return declaration + 'return * this ; }'


def get_copy_operator(data, classname):
    return get_copy_operator_for_table(data, classname) if data.table \
        else get_copy_operator_for_handle(data, classname)


def get_move_operator_for_table(data, classname):
    declaration = classname + ' & operator = ( ' + classname + ' && other ) noexcept { '
    if data.small_buffer_optimization:
        if data.copy_on_write:
            declaration += data.function_table_member + ' = other . ' + data.function_table_member + ' ; '
            declaration += 'if ( type_erasure_table_detail :: is_heap_allocated ( other . ' + data.impl_member + ' .  get ( ) , '
            declaration += 'other . buffer_ ) ) ' + data.impl_member + ' = std :: move ( other . ' + data.impl_member + ' ) ; '
            declaration +='else other . ' + data.function_table_member + ' . clone_into ( other . ' + data.impl_member + ' . get ( ) , '
            declaration += 'buffer_ , ' + data.impl_member + ' ) ;'
        else:
            declaration += 'if ( ! other . ' + data.impl_member + ' ) { reset ( ) ; ' + data.impl_member + ' = nullptr ; return * this ; } '
            declaration += data.function_table_member + ' = other . ' + data.function_table_member + ' ; '
            declaration += 'if ( type_erasure_table_detail :: is_heap_allocated ( other . ' + data.impl_member + ' , other . buffer_ ) ) '
            declaration += data.impl_member + ' = other . ' + data.impl_member + ' ; '
            declaration += 'else { buffer_ = std :: move ( other . buffer_ ) ; ' + data.impl_member + ' = & buffer_ ; } '
    else:
        declaration += data.function_table_member + ' = other . ' + data.function_table_member + ' ; '
        declaration += data.impl_member + ' = other . ' + data.impl_member + ' ; '
    declaration += 'other . ' + data.impl_member + ' = nullptr ; '
    return declaration + 'return * this ; }'


def get_move_operator_for_handle(data, classname):
    declaration = classname + ' & operator = ( ' + classname + ' && other ) noexcept '
    if data.small_buffer_optimization:
        escape_sequence = 'if ( ! other . ' + data.impl_member + ' ) { ' + data.impl_member + ' = nullptr ; return * this ; }'
        declaration += '{ reset ( ) ; ' + get_handle_move_assignment_for_small_buffer_optimization(data, escape_sequence)
    else:
        declaration += '{ ' + data.impl_member + ' = std :: move ( other . ' + data.impl_member + ' ) ; '
    return declaration + 'other . ' + data.impl_member + ' = nullptr ; return * this ; }'


def get_move_operator(data, classname):
    return get_move_operator_for_table(data, classname) if data.table \
        else get_move_operator_for_handle(data, classname)


def get_operator_bool_for_member_ptr(member):
    return 'explicit operator bool ( ) const noexcept { return ' + member + ' != nullptr ; }'


def get_operator_bool_comment(declaration):
    comment = ['/**\n',
               ' * @brief Checks if the type-erased interface holds an implementation.\n',
               ' * @return true if an implementation is stored, else false\n',
               ' */\n']
    return parser_addition.Comment(comment, declaration)


def get_cast(data, classname, handle_namespace, const=''):
    const = const and const + ' ' or ''
    declaration = 'template < class T > ' + const + 'T * target ( ) ' + const + 'noexcept '

    if data.table:
        if data.no_rtti:
            declaration += '{ return type_erasure_table_detail :: cast_impl < T > ( '
            declaration += 'read ( )' if data.copy_on_write else data.impl_raw_member
            return declaration + ' ) ; }'
        else:
            declaration += '{ return type_erasure_table_detail :: dynamic_cast_impl < T > ( type_id_ , '
            declaration += 'read ( )' if data.copy_on_write else data.impl_raw_member
            return declaration + ' ) ; }'
    else:
        if data.small_buffer_optimization:
            return declaration + '{ if ( type_erasure_detail :: is_heap_allocated ( ' + data.impl_raw_member + ' , buffer_ ) ) ' \
                                 'return type_erasure_detail :: cast < ' + const + 'T , ' + \
                                 const + 'HeapAllocatedHandle < T > > ( ' + data.impl_raw_member + ' ) ; ' \
                                'return type_erasure_detail :: cast < ' + const + 'T , ' + \
                                 const + 'StackAllocatedHandle < T > > ( ' + data.impl_raw_member + ' ) ; }'
    return declaration + '{ return type_erasure_detail :: cast < ' + const + 'T , ' + \
           const + handle_namespace + ' :: Handle < T , ' + classname + ' > > ( ' + data.impl_raw_member + ' ) ; }'


def get_handle_cast_comment(declaration, const=''):
    comment = ['/**\n',
               '* @brief Conversion of the stored implementation to @code ' + const + ' T* @endcode.\n',
               '* @return pointer to the stored object if conversion was successful, else nullptr\n',
               '*/\n']
    return parser_addition.Comment(comment,declaration)


def get_handle_interface_function(data, function):
    code = util.concat(function.tokens[:cpp_file_parser.get_declaration_end_index(function.name,function.tokens)],' ')
    code += ' { assert ( ' + data.impl_member + ' ) ; ' + function.return_str + ' ' + data.impl_member + ' -> ' + function.name + ' ( '
    arguments = cpp_file_parser.get_function_arguments(function)
    for arg in arguments:
        code += arg.in_single_function_call()
        if arg is not arguments[-1]:
            code += ' , '
    return code + ' ) ; }'


def get_handle_specialization(data):
    if data.small_buffer_optimization:
        return 'template < class T , class Interface , class Buffer , bool HeapAllocated > ' \
               'struct Handle < std :: reference_wrapper < T > , Interface , Buffer , HeapAllocated > : ' \
               'Handle < T & , Interface , Buffer , HeapAllocated > { ' \
               'Handle ( std :: reference_wrapper < T > ref ) noexcept : ' \
               'Handle < T & , Interface , Buffer , HeapAllocated > ( ref . get ( ) ) { } ' \
               '};'
    return 'template < class T , class Interface > struct Handle < std :: reference_wrapper < T > , Interface > : Handle < T & , Interface > { ' \
           'Handle ( std :: reference_wrapper < T > ref ) noexcept : Handle < T & , Interface > ( ref . get ( ) ) { } } ;'


def get_read_function_for_handle(return_type, member):
    return return_type + ' read ( ) const noexcept { assert ( ' + member + ' ) ; ' \
                                         'return * ' + member + ' ; }'


def get_read_function_for_table(data, return_type):
    return return_type + ' read ( ) const noexcept { assert ( ' + data.impl_member + ' ) ; return ' + data.impl_raw_member + ' ; }'


def get_read_function(data, return_type, member):
    return get_read_function_for_table(data, return_type) if data.table \
        else get_read_function_for_handle(return_type, member)


def get_write_function_for_handle(data, return_type, member):
    code = return_type + ' write ( ) { assert ( ' + member + ' ) ; if ( ! ' + member + ' . unique ( ) ) '
    if data.small_buffer_optimization:
        code += member + ' = ' + member + ' -> clone_into ( buffer_ ) ; '
    else:
        code += member + ' = ' + member + ' -> clone ( ) ; '
    return code + 'return * ' + member + ' ; }'


def get_write_function_for_table(data, return_type, member):
    code = return_type + ' write ( ) { if ( ! ' + member + ' . unique ( ) ) '
    if data.small_buffer_optimization:
        code += '{ if ( type_erasure_table_detail :: is_heap_allocated ( ' + member + ' . get ( ) , buffer_ ) ) '
        code += data.function_table_member + ' . clone( ' + member + ' . get ( ) , ' + member + ' ) ; '
        code += 'else ' + data.function_table_member + ' . clone_into ( ' + member + ' . get ( ) , buffer_ , ' + member + ' ) ; }'
    else:
        code += data.function_table_member + ' . clone ( read ( ) , ' + member + ' ) ; '
    return code + 'return ' + member + ' . get ( ) ; }'


def get_write_function(data, return_type, member):
    return get_write_function_for_table(data, return_type, member) if data.table \
        else get_write_function_for_handle(data, return_type, member)


def get_single_function_call(function):
    return function.name + ' ( ' + cpp_file_parser.get_function_arguments_in_single_call(function) + ' ) '
