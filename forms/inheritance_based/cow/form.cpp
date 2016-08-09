%struct_name%::operator bool() const noexcept
{
    return handle_ != nullptr;
}

%nonvirtual_members%

const HandleBase& %struct_name%::read( ) const noexcept
{
    assert(handle_);
    return *handle_;
}

HandleBase& %struct_name%::write( )
{
    assert(handle_);
    if( !handle_.unique( ) )
        handle_ = handle_->clone( );
    return *handle_;
}
