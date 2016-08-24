import cpp_file_parser
import util

def get_decayed(type_):
    return 'typename std :: decay < ' + type_ + ' > :: type'


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


def get_handle_constructor(classname, handle_namespace):
    constructor = 'template < typename T , ' + enable_if_not_same(classname, 'T') + ' > '
    constructor += classname + ' ( T && value ) : handle_ ( new ' + handle_namespace + ' :: Handle < ' + get_decayed('T') + ' > '
    return constructor + '( std :: forward < T > ( value ) ) ) { }'


def get_handle_assignment(classname, handle_namespace):
    code = 'template < typename T , ' + enable_if_not_same(classname, 'T') + ' > '
    code += classname + ' &  operator= ( T && value ) { '
    code += 'handle_ . reset ( new ' + handle_namespace + ' :: Handle < ' + get_decayed('T') + ' > ( std :: forward < T > ( value ) ) ) ; '
    return code + 'return * this ; }'


def get_handle_copy_constructor(classname):
    return classname + ' ( const ' + classname + ' & other ) : handle_ ( other . handle_ ? other . handle_ -> clone ( ) : nullptr ) { }'


def get_handle_move_constructor(classname):
    return classname + ' ( ' + classname + ' && other ) noexcept : handle_ ( std :: move ( other.handle_ ) ) { }'


def get_handle_copy_operator(classname):
    declaration = classname + ' & operator = ( const ' + classname + ' & other ) '
    return declaration + '{ handle_ . reset ( other . handle_ ? other . handle_ -> clone ( ) : nullptr ) ; return * this ; }'


def get_handle_move_operator(classname):
    declaration = classname + ' & operator = ( ' + classname + ' && other ) noexcept '
    return declaration + '{ handle_ = std :: move ( other . handle_ ) ; return * this ; }'


def get_operator_bool_for_member_ptr(member):
    return 'explicit operator bool ( ) const noexcept { return ' + member + ' != nullptr ; }'


def get_handle_cast(member, handle_namespace, const=''):
    const = const and const + ' ' or ''
    declaration = 'template < class T > ' + const + 'T * target ( ) ' + const + 'noexcept '
    return declaration + '{ return type_erasure_detail :: cast < ' + const + 'T , ' + \
           const + handle_namespace + ' :: Handle < T > > ( ' + member + ' . get ( ) ) ; }'


def get_handle_interface_function(function):
    code = util.concat(function.tokens[:cpp_file_parser.get_declaration_end_index(function.name,function.tokens)],' ')
    code += ' { assert ( handle_ ) ; ' + function.return_str + ' handle_ -> ' + function.name + ' ( '
    arguments = cpp_file_parser.get_function_arguments(function)
    for arg in arguments:
        code += arg.in_single_function_call()
        if arg is not arguments[-1]:
            code += ' , '
    return code + ' ) ; }'


def get_handle_specialization():
    return 'template < typename T > struct Handle < std :: reference_wrapper < T > > : Handle < T & > { ' \
           'Handle ( std :: reference_wrapper < T > ref ) noexcept : Handle < T & > ( ref . get ( ) ) { } } ;'
