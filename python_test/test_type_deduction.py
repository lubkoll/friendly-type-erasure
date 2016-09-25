import unittest
import type_erasure.parser_addition


ref_ = ' &'
ptr_ = ' *'
const_ = 'const '
int_only_type = 'int'
int_vector_only_type = 'std :: vector < int >'


def ref(type):
    return type + ref_


def const(type):
    return const_ + type


def const_ref(type):
    return const(type) + ref_


def ptr(type):
    return type + ptr_


def const_ptr(type):
    return ptr(const(type))


def const_ptr_const(type):
    return ptr(const(type)) + ' const'


# single_line_test_comments = ['/// comment',
#                              '//! comment',
#                              '// comment',
#                              '    \n\r\t/// comment']
# multi_line_test_comments = [['/** comment */'],
#                             ['/* comment */'],
#                             ['/* comment', '*/'],
#                             ['/**', '* comment', '*/']]
#
#
# class TestIsComment(unittest.TestCase):
#     def test_is_single_line_comment(self):
#         for comment in single_line_test_comments:
#             self.assertTrue(type_erasure.parser_addition.is_single_line_comment(comment))
#         for comment in multi_line_test_comments:
#             for line in comment:
#                 self.assertFalse(type_erasure.parser_addition.is_single_line_comment(line))
#
#     def test_is_multi_line_comment(self):
#         for comment in single_line_test_comments:
#             self.assertFalse(type_erasure.parser_addition.is_multi_line_comment(comment, in_multi_line_comment=False))
#             self.assertFalse(type_erasure.parser_addition.is_multi_line_comment(comment, in_multi_line_comment=True))
#         for comment in multi_line_test_comments:
#             for line in comment:
#                 if line is comment[0]:
#                     self.assertTrue(type_erasure.parser_addition.is_multi_line_comment(line, in_multi_line_comment=False))
#                     self.assertFalse(type_erasure.parser_addition.is_multi_line_comment(line, in_multi_line_comment=True))
#                 else:
#                     self.assertFalse(type_erasure.parser_addition.is_multi_line_comment(line, in_multi_line_comment=False))
#                     self.assertTrue(type_erasure.parser_addition.is_multi_line_comment(line, in_multi_line_comment=True))
#
#     def test_is_comment(self):
#         for comment in single_line_test_comments:
#             self.assertTrue(type_erasure.parser_addition.is_comment(comment, in_multi_line_comment=False))
#             self.assertTrue(type_erasure.parser_addition.is_comment(comment, in_multi_line_comment=True))
#         for comment in multi_line_test_comments:
#             for line in comment:
#                 if line is comment[0]:
#                     self.assertTrue(type_erasure.parser_addition.is_comment(line, in_multi_line_comment=False))
#                     self.assertFalse(type_erasure.parser_addition.is_comment(line, in_multi_line_comment=True))
#                 else:
#                     self.assertFalse(type_erasure.parser_addition.is_comment(line, in_multi_line_comment=False))
#                     self.assertTrue(type_erasure.parser_addition.is_comment(line, in_multi_line_comment=True))


if __name__ == '__main__':
    unittest.main()
