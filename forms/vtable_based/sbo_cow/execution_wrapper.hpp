namespace %namespace_prefix%
{
    template <class Buffer>
    struct vtable {
        using clone_function_type = void(*)(void*, std::shared_ptr<void>&);
        using clone_into_function_type = void(*)(void*, Buffer&, std::shared_ptr<void>&);
        %member_function_signatures%

        clone_function_type clone;
        clone_into_function_type clone_into;
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
