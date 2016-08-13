%struct_prefix%
{
public:
    %type_aliases%
    // Contructors
    %struct_name%( ) noexcept :
        impl_ ( nullptr )
    { }

    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name% ( T&& value ) :
        vtable_ ({ 
            &type_erasure_vtable_detail::delete_impl< typename std::decay<T>::type >,
            &type_erasure_vtable_detail::clone_impl< typename std::decay<T>::type >,
	    %member_function_vtable_initialization%
        }),
        impl_ ( new typename std::decay<T>::type( std::forward<T>(value) ) )
    { }

    %struct_name% ( const %struct_name%& other ) :
        vtable_ ( other.vtable_ ),
        impl_ ( other.impl_ ? other.vtable_.clone( other.impl_) : nullptr )
    { }

    %struct_name% ( %struct_name%&& other ) noexcept :
        vtable_ ( other.vtable_ ),
        impl_ ( other.impl_ )
    {
        other.impl_ = nullptr;
    }

    // Assignment
    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name%& operator= ( T&& value )
    {
        return *this = %struct_name%( std::forward<T>(value) );
    }

    %struct_name%& operator= ( const %struct_name%& other )
    {
        vtable_ = other.vtable_;
        impl_ = other.impl_ ? other.vtable_.clone( other.impl_) : nullptr;
	return *this;
    }

    %struct_name%& operator= ( %struct_name%&& other ) noexcept
    {
        vtable_ = other.vtable_;
        impl_ = other.impl_;
        other.impl_ = nullptr;
        return *this;
    }

    ~%struct_name% ( )
    {
        if( impl_ ) 
            vtable_.del( impl_ );
    }

    /**
     * @brief Checks if the type-erased interface holds an implementation.
     * @return true if an implementation is stored, else false
     */
    explicit operator bool( ) const noexcept
    {
        return impl_ != nullptr;
    }

    /**
     * @brief Conversion of the stored implementation to @code T*@endcode.
     * @return pointer to stored object if conversion to @code T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    T* target( ) noexcept
    {
        return type_erasure_vtable_detail::cast_impl<T>( impl_ );
    }
    
    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target( ) const noexcept
    {
        return type_erasure_vtable_detail::cast_impl<T>( impl_ );
    }

    %member_functions%

private:
    %namespace_prefix%::vtable vtable_;
    void* impl_;
};
