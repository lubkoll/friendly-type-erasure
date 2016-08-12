// Contructors
%struct_name%::%struct_name% ( ) :
    impl_ ( nullptr )
{ }

%member_functions%

void* %struct_name%::read( ) const noexcept
{
    return impl_.get( );
}

void* %struct_name%::write( )
{
    if( !impl_.unique( ) )
        vtable_.clone_into( read( ), impl_ );
    return impl_.get( );
}
