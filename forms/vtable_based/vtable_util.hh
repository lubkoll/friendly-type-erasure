#pragma once

namespace type_erasure_vtable_detail
{
    template <typename ValueType>
    inline void* clone_impl ( void* value )
    {
        return new ValueType( *static_cast<ValueType*>( value ) );
    }

    template <typename ValueType>
    inline void clone_into_impl ( void* value, std::shared_ptr<void>& ptr )
    {
        ptr = std::make_shared<ValueType>( *static_cast<ValueType*>( value ) );
    }

    template <typename ValueType>
    inline void delete_impl ( void* value )
    {
        delete static_cast<ValueType*>( value );
    }

    template <typename ValueType>
    inline ValueType* cast_impl( void* value )
    {
        if( value )
            return static_cast<ValueType*>( value );
        return nullptr;
    };

    template <typename ValueType>
    inline const ValueType* cast_impl( const void* value )
    {
        if( value )
            return static_cast<const ValueType*>( value );
        return nullptr;
    };
}
