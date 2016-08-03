%struct_prefix%
{
    using Buffer = std::array<unsigned char, 100>;
    template <class T>
    using StackAllocatedHandle = Handle<T,Buffer,false>;
    template <class T>
    using HeapAllocatedHandle = Handle<T,Buffer,true>;
public:
    // Contructors
    %struct_name% () = default;

    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name% (T&& value)
    {
        handle_ = type_erasure_detail::clone_impl< HandleBase<Buffer>, StackAllocatedHandle<T>, HeapAllocatedHandle<T> >( std::forward<T>(value), buffer_ );
    }

    %struct_name% (const %struct_name%& rhs)
    {
        if (rhs.handle_)
            handle_ = rhs.handle_->clone_into(buffer_);
    }

    %struct_name% (%struct_name%&& rhs) noexcept
    {
        swap(rhs.handle_, rhs.buffer_);
    }

    // Assignment
    template <typename T,
              typename std::enable_if<
                  !std::is_same< %struct_name%, typename std::decay<T>::type >::value
                  >::type* = nullptr>
    %struct_name%& operator= (T&& value)
    {
        reset();
        handle_ = type_erasure_detail::clone_impl< HandleBase<Buffer>, StackAllocatedHandle<T>, HeapAllocatedHandle<T> >(std::forward<T>(value), buffer_);
        return *this;
    }

    %struct_name%& operator= (const %struct_name%& rhs)
    {
        %struct_name% temp(rhs);
        swap(temp.handle_, temp.buffer_);
        return *this;
    }

    %struct_name%& operator= (%struct_name%&& rhs) noexcept
    {
        %struct_name% temp(std::move(rhs));
        swap(temp.handle_, temp.buffer_);
        return *this;
    }

    ~%struct_name% ()
    {
        reset();
    }

    /**
     * @brief Checks if the type-erased interface holds an implementation.
     * @return true if an implementation is stored, else false
     */
    explicit operator bool() const
    {
        return handle_ != nullptr;
    }

    /**
     * @brief Conversion of the stored implementation to @code T*@endcode.
     * @return pointer to stored object if conversion to @code T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    T* target()
    {
        void* buffer_ptr = type_erasure_detail::get_buffer_ptr<typename std::decay<T>::type>(const_cast<Buffer&>(buffer_));
        if(buffer_ptr)
            return type_erasure_detail::cast< T, StackAllocatedHandle<T> >( handle_ );
        return type_erasure_detail::cast< T, HeapAllocatedHandle<T> >( handle_ );
    }

    /**
     * @brief Conversion of the stored implementation to @code const T*@endcode.
     * @return pointer to stored object if conversion to @code const T*@endcode
     *         was successful, else nullptr
     */
    template <typename T>
    const T* target() const
    {
        void* buffer_ptr = type_erasure_detail::get_buffer_ptr<typename std::decay<T>::type>(const_cast<Buffer&>(buffer_));
        if(buffer_ptr)
            return type_erasure_detail::cast< const T, const StackAllocatedHandle<T> >( handle_ );
        return type_erasure_detail::cast< const T, const HeapAllocatedHandle<T> >( handle_ );
    }

    %nonvirtual_members%

private:
    void swap (HandleBase<Buffer>*& rhs_handle, Buffer& rhs_buffer)
    {
        using namespace type_erasure_detail;
        const bool this_heap_allocated =
                !handle_ || handle_->heap_allocated();
        const bool rhs_heap_allocated =
                !rhs_handle || rhs_handle->heap_allocated();

        if (this_heap_allocated && rhs_heap_allocated) {
            std::swap(handle_, rhs_handle);
        } else if (this_heap_allocated) {
            const std::ptrdiff_t offset = handle_offset(rhs_handle, rhs_buffer);
            rhs_handle = handle_;
            buffer_ = rhs_buffer;
            handle_ = handle_ptr< HandleBase<Buffer> >(char_ptr(&buffer_) + offset);
        } else if (rhs_heap_allocated) {
            const std::ptrdiff_t offset = handle_offset(handle_, buffer_);
            handle_ = rhs_handle;
            rhs_buffer = buffer_;
            rhs_handle = handle_ptr< HandleBase<Buffer> >(char_ptr(&rhs_buffer) + offset);
        } else {
            const std::ptrdiff_t this_offset = handle_offset(handle_, buffer_);
            const std::ptrdiff_t rhs_offset = handle_offset(rhs_handle, rhs_buffer);
            std::swap(buffer_, rhs_buffer);
            handle_ = handle_ptr< HandleBase<Buffer> >(char_ptr(&buffer_) + this_offset);
            rhs_handle = handle_ptr< HandleBase<Buffer> >(char_ptr(&rhs_buffer) + rhs_offset);
        }
    }

    void reset ()
    {
        if (handle_)
            handle_->destroy();
    }

    HandleBase<Buffer>* handle_ = nullptr;
    Buffer buffer_;
};
