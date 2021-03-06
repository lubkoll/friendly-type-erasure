cmake_minimum_required(VERSION 2.8)
project(type_erasure_test)

add_definitions(-std=c++11)

if(${CMAKE_SYSTEM_NAME} MATCHES "Windows")
  include(conanbuildinfo.cmake)
  conan_basic_setup()
  set(GTEST_LIBS ${CONAN_LIBS})
else(${CMAKE_SYSTEM_NAME} MATCHES "Windows")
  find_package(GTest REQUIRED)
  include_directories(. ${GTEST_INCLUDE_DIRS})
  set(GTEST_LIBS ${GTEST_LIBRARIES})
endif(${CMAKE_SYSTEM_NAME} MATCHES "Windows")

aux_source_directory(. SRC_LIST)
# inheritance-based type erasure
aux_source_directory(gen/basic SRC_LIST)
aux_source_directory(gen/basic_header_only SRC_LIST)
aux_source_directory(gen/cow SRC_LIST)
aux_source_directory(gen/cow_header_only SRC_LIST)
aux_source_directory(gen/sbo SRC_LIST)
aux_source_directory(gen/sbo_header_only SRC_LIST)
aux_source_directory(gen/sbo_cow SRC_LIST)
aux_source_directory(gen/sbo_cow_header_only SRC_LIST)
# vtable-based type erasure
aux_source_directory(gen/vtable_basic SRC_LIST)
aux_source_directory(gen/vtable_basic_header_only SRC_LIST)
aux_source_directory(gen/vtable_cow SRC_LIST)
aux_source_directory(gen/vtable_cow_header_only SRC_LIST)
aux_source_directory(gen/vtable_sbo SRC_LIST)
aux_source_directory(gen/vtable_sbo_header_only SRC_LIST)
aux_source_directory(gen/vtable_sbo_cow SRC_LIST)
aux_source_directory(gen/vtable_sbo_cow_header_only SRC_LIST)

aux_source_directory(gen/test SRC_LIST)

add_executable(unit_tests ${SRC_LIST})
target_link_libraries(unit_tests ${GTEST_LIBS} pthread)

include(CTest)
enable_testing()
add_test(test ${PROJECT_BINARY_DIR}/Test/unit_tests)
add_custom_target(check COMMAND ${CMAKE_CTEST_COMMAND}
DEPENDS ${PROJECT_BINARY_DIR}/Test/unit_tests)
