namespace %namespace_prefix%
{
    struct vtable {
        using clone_function_type = void(*)(void*, std::shared_ptr<void>&);
        %member_function_signatures%

        clone_function_type clone_into;
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
