%struct_name%::operator bool() const
{
    return handle_ != nullptr;
}

%nonvirtual_members%

const HandleBase& %struct_name%::read( ) const
{
    return *handle_;
}

HandleBase& %struct_name%::write( )
{
    if( !handle_.unique( ) )
        handle_ = handle_->clone( );
    return *handle_;
}
