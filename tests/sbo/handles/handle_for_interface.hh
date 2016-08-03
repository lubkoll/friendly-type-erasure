#pragma once

#include <functional>
#include <memory>
#include <type_traits>
#include <utility>
#include "util.hh"

namespace SBO
{    
    namespace Fooable_impl
    {
        template <typename Buffer>
        struct HandleBase
        {
            virtual ~HandleBase () {}
            virtual HandleBase* clone_into (Buffer& buffer) const = 0;
            virtual bool heap_allocated () const = 0;
            virtual void destroy () = 0;
    
            virtual int foo ( ) const = 0;
            virtual void set_value ( int value ) = 0;
        };
    
        template <typename T, typename Buffer, bool HeapAllocated>
        struct Handle : HandleBase<Buffer>
        {
            template <typename U,
                      typename std::enable_if<
                          !std::is_same< T, typename std::decay<U>::type >::value
                                               >::type* = nullptr>
            explicit Handle(U&& value) noexcept :
                value_( value )
            {}
    
            template <typename U,
                      typename std::enable_if<
                          std::is_same< T, typename std::decay<U>::type >::value
                                               >::type* = nullptr>
            explicit Handle(U&& value) noexcept ( std::is_rvalue_reference<U>::value &&
                                                  std::is_nothrow_move_constructible<typename std::decay<U>::type>::value ) :
                value_( std::forward<U>(value) )
            {}
    
            virtual HandleBase<Buffer>* clone_into (Buffer& buffer) const
            {
                return type_erasure_detail::clone_impl< HandleBase<Buffer>, Handle<T,Buffer,false>, Handle<T,Buffer,true> >(value_, buffer);
            }
    
            virtual bool heap_allocated () const
            {
                return HeapAllocated;
            }
    
            virtual void destroy ()
            {
                if (HeapAllocated)
                    delete this;
                else
                    this->~Handle();
            }
    
            virtual int foo ( ) const override
            {
                return value_.foo( );
            }

            virtual void set_value ( int value ) override
            {
                value_.set_value(value );
            }
    
            T value_;
        };
    
        template <typename T, typename Buffer, bool HeapAllocated>
        struct Handle<std::reference_wrapper<T>, Buffer, HeapAllocated> : Handle<T&, Buffer, HeapAllocated>
        {
            Handle (std::reference_wrapper<T> ref) :
                Handle<T&, Buffer, HeapAllocated> (ref.get())
            {}
        };
    }
    
}

