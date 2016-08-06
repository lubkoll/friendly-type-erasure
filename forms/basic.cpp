%struct_name%::%struct_name%( const %struct_name% & rhs )
    : handle_ ( rhs.handle_ ? rhs.handle_->clone( ) : nullptr )
{}

%struct_name%::%struct_name%( %struct_name%&& rhs ) noexcept
    : handle_ ( std::move( rhs.handle_ ) )
{}

%struct_name%& %struct_name%::operator=( const %struct_name%& rhs )
{
    %struct_name% temp( rhs );
    std::swap( temp, *this );
    return *this;
}

%struct_name%& %struct_name%::operator=( %struct_name%&& rhs ) noexcept
{
    handle_ = std::move( rhs.handle_ );
    return *this;
}

%struct_name%::operator bool( ) const noexcept
{
    return handle_ != nullptr;
}

%nonvirtual_members%
