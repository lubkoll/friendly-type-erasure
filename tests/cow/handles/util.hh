#pragma once

#include <cassert>
#include <cstddef>
#include <memory>

namespace type_erasure_detail
{    
    template <class T, class Derived, class Base>
    T* cast(Base* base) noexcept
    {
        assert(base);
        auto derived = dynamic_cast<Derived*>(base);
        if(derived)
            return &derived->value_;
        return nullptr;
    }

    template <class BufferHandle, class Buffer>
    void* get_buffer_ptr(Buffer& buffer)
    {
        void* buffer_ptr = &buffer;
        auto buffer_size = sizeof(buffer);
        return std::align( alignof(BufferHandle),
                           sizeof(BufferHandle),
                           buffer_ptr,
                           buffer_size);

    }

    template <typename T>
    inline unsigned char* char_ptr (T* ptr) noexcept
    {
        return static_cast<unsigned char*>(static_cast<void*>(ptr));
    }

    template <class HandleBase>
    inline HandleBase* handle_ptr (unsigned char* ptr) noexcept
    {
        return static_cast<HandleBase*>(static_cast<void*>(ptr));
    }

    template <class HandleBase, class Buffer>
    inline std::ptrdiff_t handle_offset (HandleBase* handle, Buffer& buffer) noexcept
    {
        assert(handle);
        return char_ptr(handle) - char_ptr(&buffer);
    }
}
