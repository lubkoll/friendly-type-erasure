%struct_prefix%
{    
    using Buffer = std::array<char, %buffer_size%>;

public:
    %type_aliases%
    // Contructors
    %struct_name%( ) noexcept :
        impl_ ( nullptr )
    { }

    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name% ( T&& value ) :
        vtable_ { 
            &type_erasure_vtable_detail::clone_into_impl< typename std::decay<T>::type >,
            &type_erasure_vtable_detail::clone_into_buffer< typename std::decay<T>::type, Buffer >,
	    %member_function_vtable_initialization%
        },
        impl_ ( nullptr )
    {
        using Decayed = typename std::decay<T>::type;
        if( sizeof( Decayed ) <= sizeof( Buffer ) )
        {
            new (&buffer_) Decayed( std::forward<T>(value) );
            impl_ = std::shared_ptr<Decayed>( std::shared_ptr<Decayed>( nullptr ), static_cast<Decayed*>( static_cast<void*>(&buffer_) ) );
        }
        else            
            impl_ = std::make_shared<Decayed>( std::forward<T>(value) );
    }

    %struct_name% ( const %struct_name%& other ) :
        vtable_( other.vtable_ ),
        impl_( other.impl_ )
    {}

    %struct_name% ( %struct_name%&& other ) noexcept :
        vtable_( other.vtable_ )
    {
        if( type_erasure_vtable_detail::is_heap_allocated( other.impl_.get( ), other.buffer_ ) )
            impl_ = std::move( other.impl_ );
        else
            other.vtable_.clone_into( other.impl_.get( ), buffer_, impl_ );

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
        impl_ = other.impl_;
        return *this;
    }

    %struct_name%& operator= ( %struct_name%&& other ) noexcept
    {
        vtable_ = other.vtable_;
        if( type_erasure_vtable_detail::is_heap_allocated( other.impl_.get( ), other.buffer_ ) )
            impl_ = std::move( other.impl_ );
        else
            other.vtable_.clone_into( other.impl_.get( ), buffer_, impl_ );

        other.impl_ = nullptr;

        return *this;
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
        return type_erasure_vtable_detail::cast_impl<T>( impl_.get( ) );
    }
    
    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target( ) const noexcept
    {
        return type_erasure_vtable_detail::cast_impl<T>( impl_.get( ) );
    }

    %member_functions%

private:
    void* read( ) const noexcept
    {
        return impl_.get( );
    }

    void* write( )
    {
        if( !impl_.unique( ) )
        {
            if( type_erasure_vtable_detail::is_heap_allocated( impl_.get( ), buffer_) )
                vtable_.clone( impl_.get( ), impl_ );
            else
                vtable_.clone_into( impl_.get( ), buffer_, impl_ );
        }
        return impl_.get( );
    }

    %namespace_prefix%::vtable<Buffer> vtable_;
    Buffer buffer_;
    std::shared_ptr<void> impl_;
};


