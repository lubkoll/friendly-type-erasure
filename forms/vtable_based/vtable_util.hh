#pragma once

namespace type_erasure_vtable_detail
{
    template <class T, class Buffer>
    inline void* get_buffer_ptr ( Buffer& buffer ) noexcept
    {
        void* buffer_ptr = &buffer;
        auto buffer_size = sizeof(buffer);
        return std::align( alignof(T),
                           sizeof(T),
                           buffer_ptr,
                           buffer_size);

    }

    template < class T >
    inline void* clone_impl ( void* impl )
    {
        assert(impl);
        return new T( *static_cast<T*>( impl ) );
    }

    template < class T >
    inline void clone_into_impl ( void* impl, std::shared_ptr<void>& ptr )
    {
        assert(impl);
        ptr = std::make_shared<T>( *static_cast<T*>( impl ) );
    }

    template< class T, class Buffer >
    inline void* clone_into_buffer( void* impl, Buffer& buffer ) noexcept
    {
        assert(impl);
        auto buffer_ptr = get_buffer_ptr<T>( buffer );
        new (buffer_ptr) T( *static_cast<T*>( impl ) );
        return buffer_ptr;
    }

    template < class T >
    inline void delete_impl ( void* impl ) noexcept
    {
        assert(impl);
        delete static_cast<T*>( impl );
    }

    template < class T >
    inline T* cast_impl( void* impl )
    {
        assert(impl);
        if( impl )
            return static_cast<T*>( impl );
        return nullptr;
    };

    template < class T >
    inline const T* cast_impl( const void* impl )
    {
        assert(impl);
        if( impl )
            return static_cast<const T*>( impl );
        return nullptr;
    };



    inline char* char_ptr ( void* ptr ) noexcept
    {
        assert(ptr);
        return static_cast<char*>( ptr );
    }

    inline const char* char_ptr( const void* ptr ) noexcept
    {
        assert(ptr);
        return static_cast<const char*>( ptr );
    }

    template < class Buffer >
    inline std::ptrdiff_t impl_offset ( void* impl, Buffer& buffer ) noexcept
    {
        assert(impl);
        return char_ptr(impl) - char_ptr( static_cast<void*>(&buffer) );
    }

    template < class Buffer >
    inline bool heap_allocated ( void* impl, const Buffer& buffer ) noexcept
    {
        assert(impl);
        return impl < static_cast<const void*>(&buffer) ||
               static_cast<const void*>( char_ptr(&buffer) + sizeof(buffer) ) <= impl;
    }
}
