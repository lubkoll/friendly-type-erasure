%struct_prefix%
{
    using Buffer = std::array<char, %buffer_size%>;
    template <class T>
    using StackAllocatedHandle = Handle<T, Buffer, false>;
    template <class T>
    using HeapAllocatedHandle = Handle<T, Buffer, true>;

public:
    %struct_name% ( ) noexcept = default;

    // Constructors
    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name% (T&& impl)
    {
        using PlainT = typename std::decay<T>::type;
        handle_ = type_erasure_detail::clone_impl< HandleBase<Buffer>, StackAllocatedHandle<PlainT>, HeapAllocatedHandle<PlainT> >( std::forward<T>(impl), buffer_ );
    }

    %struct_name% ( const %struct_name%& other );

    %struct_name% ( %struct_name%&& other ) noexcept;

    // Assignments
    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name%& operator= ( T&& impl )
    {
        reset( );
        using PlainT = typename std::decay<T>::type;
        handle_ = type_erasure_detail::clone_impl< HandleBase<Buffer>, StackAllocatedHandle<PlainT>, HeapAllocatedHandle<PlainT> >( std::forward<T>(impl), buffer_ );
        return *this;
    }

    %struct_name%& operator= ( const %struct_name%& other );

    %struct_name%& operator= ( %struct_name%&& other ) noexcept;

    ~%struct_name% ();

    /**
     * @brief Checks if the type-erased interface holds an implementation.
     * @return true if an implementation is stored, else false
     */
    explicit operator bool( ) const noexcept;

    /**
     * @brief Conversion of the stored implementation to @code T*@endcode.
     * @return pointer to stored object if conversion to @code T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    T* target( ) noexcept
    {
        assert( handle_ );
        if( type_erasure_detail::is_heap_allocated( handle_, buffer_ ) )
        {
            auto handle = dynamic_cast<HeapAllocatedHandle<T>*>( handle_ );
            if( handle )
                return &handle->value_;
        }
        else
        {
            auto handle = dynamic_cast<StackAllocatedHandle<T>*>( handle_ );
            if( handle )
                return &handle->value_;
        }

        return nullptr;
    }

    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target() const noexcept
    {
        assert( handle_ );
        if( type_erasure_detail::is_heap_allocated( handle_, buffer_ ) )
        {
            auto handle = dynamic_cast<const HeapAllocatedHandle<T>*>(handle_);
            if( handle )
                return &handle->value_;
        }
        else
        {
            auto handle = dynamic_cast<const StackAllocatedHandle<T>*>(handle_);
            if( handle )
                return &handle->value_;
        }

        return nullptr;
    }

    %nonvirtual_members%

private:
    void swap ( HandleBase<Buffer>*& other_handle, Buffer& other_buffer ) noexcept;

    void reset ( ) noexcept;

    const HandleBase<Buffer>& read ( ) const noexcept;

    HandleBase<Buffer> & write ( );

    HandleBase<Buffer>* handle_ = nullptr;
    Buffer buffer_;
};
