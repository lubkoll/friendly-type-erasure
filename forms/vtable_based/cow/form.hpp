%struct_prefix%
{
public:
    %type_aliases%
    // Contructors
    %struct_name%( );

    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name% ( T&& value ) :
        vtable_ ({
            &type_erasure_vtable_detail::clone_into_impl< typename std::decay<T>::type >,
	    %member_function_vtable_initialization%
        }),
        impl_ ( std::make_shared<typename std::decay<T>::type>( std::forward<T>(value) ) )
    { }

    // Assignment
    template <typename T,
              typename std::enable_if< !std::is_same<%struct_name%, typename std::decay<T>::type>::value >::type* = nullptr>
    %struct_name%& operator= ( T&& value )
    {
        return *this = %struct_name%( std::forward<T>(value) );
    }

    /**
     * @brief Conversion of the stored implementation to @code T*@endcode.
     * @return pointer to stored object if conversion to @code T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    T* target( ) noexcept
    {
        return type_erasure_vtable_detail::cast_impl<T>( read( ) );
    }
    
    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target( ) const noexcept
    {
        return type_erasure_vtable_detail::cast_impl<T>( read( ) );
    }

    %member_functions%

private:
    void* read( ) const noexcept;

    void* write( );

    %namespace_prefix%::vtable vtable_;
    std::shared_ptr<void> impl_;
};
