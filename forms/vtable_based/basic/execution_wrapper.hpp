namespace %namespace_prefix%
{
    struct vtable {
        using delete_function_type = void(*)(void*) noexcept;
        using clone_function_type = void*(*)(void*);
        %member_function_signatures%

        delete_function_type del;
        clone_function_type clone;
        %member_function_pointers%
    };

    template <class Impl>
    struct execution_wrapper
    {
        %member_functions%
    };


    template <class Impl>
    struct execution_wrapper< std::reference_wrapper<Impl> >
    {
        %reference_wrapped_member_functions%
    };
}
