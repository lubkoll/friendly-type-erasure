#pragma once

#include <cassert>
#include <cstddef>
#include <memory>

namespace type_erasure_detail
{    
    template <class T, class Derived, class Base>
    inline T* cast ( Base* base ) noexcept
    {
        assert(base);
        auto derived = dynamic_cast<Derived*>(base);
        if(derived)
            return &derived->value_;
        return nullptr;
    }

    template <class HandleBase,
              class StackAllocatedHandle,
              class HeapAllocatedHandle,
              typename T, typename Buffer>
    inline HandleBase* clone_impl ( T&& value, Buffer& buffer )
    {
        using PlainType = typename std::decay<T>::type;

        if ( sizeof( StackAllocatedHandle ) <= sizeof( Buffer ) ) {
            new (&buffer) StackAllocatedHandle( std::forward<T>(value) );
            return static_cast<HandleBase*>( static_cast<void*>(&buffer) );
        }

        return new HeapAllocatedHandle( std::forward<T>(value) );
    }

    template <typename T>
    inline char* char_ptr ( T* ptr ) noexcept
    {
        return static_cast<char*>( static_cast<void*>( ptr ) );
    }

    template <typename T>
    inline const char* char_ptr( const T* ptr ) noexcept
    {
        return static_cast<const char*>( static_cast<const void*>( ptr ) );
    }

    template <class HandleBase>
    inline HandleBase* handle_ptr ( char* ptr ) noexcept
    {
        return static_cast<HandleBase*>(static_cast<void*>(ptr));
    }

    template <class HandleBase>
    inline const HandleBase* handle_ptr( const char* ptr ) noexcept
    {
        return static_cast<const HandleBase*>( static_cast<const void*>(ptr) );
    }

    template <class HandleBase, class Buffer>
    inline std::ptrdiff_t handle_offset ( HandleBase* handle, Buffer& buffer ) noexcept
    {
        assert(handle);
        return char_ptr(handle) - char_ptr(&buffer);
    }

    template <class HandleBase, class Buffer>
    inline bool is_heap_allocated ( const HandleBase* handle, const Buffer& buffer ) noexcept
    {
        return handle < handle_ptr<HandleBase>( char_ptr(&buffer) ) ||
               handle_ptr<HandleBase>( char_ptr(&buffer) + sizeof(buffer) ) <= handle;
    }
}
