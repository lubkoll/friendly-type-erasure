%struct_name%::%struct_name% ( ) noexcept :
    impl_ ( nullptr )
{ }

%struct_name%::%struct_name% ( const %struct_name%& other ) :
    vtable_ ( other.vtable_ ),
    impl_ ( other.clone( ) )
{ }

%struct_name%::%struct_name% ( %struct_name%&& other ) noexcept :
    vtable_ ( other.vtable_ ),
    impl_ ( other.impl_ )
{
    other.impl_ = nullptr;
}

%struct_name%& %struct_name%::operator= ( const %struct_name%& other )
{
    %struct_name% temp( other );
    std::swap( temp, *this );
    return *this;
}

%struct_name%& %struct_name%::operator= ( %struct_name%&& other ) noexcept
{
    using std::swap;
    %struct_name% temp( std::move( other ) );
    swap( temp.vtable_, vtable_ );
    swap( temp.impl_, impl_ );
    other.impl_ = nullptr;
    return *this;
}

%struct_name%::~%struct_name% ( )
{
    if( impl_ )
        vtable_.del( impl_ );
}

%struct_name%::operator bool( ) const noexcept
{
    return impl_ != nullptr;
}

void* %struct_name%::clone ( ) const
{
    if( impl_ )
        return vtable_.clone( impl_ );
    return nullptr;
}

%member_functions%
