# Friendly type-erasure
Some scripts for the generation of type-erased interfaces in C++11 (motivated by https://github.com/tzlaine/type_erasure).

## Requirements
- python2
- libclang with python-bindings

## Usage 
python2 type_erase.py --handle-file implementation_details.hh --interface-file type_erased_interface.hh given_interface.hh

Most relevant parameters:
 - '--vtable' for vtable-based type erasure
 - '--sbo' to enable small buffer optimization
 - '--buffer' to specify the buffer size when using small buffer optimization
 - '--cow' to enable copy-on-write

## Unit tests for generated interfaces 
[![Build Status](https://travis-ci.org/lubkoll/friendly-type-erasure.svg?branch=master)](https://travis-ci.org/lubkoll/friendly-type-erasure)
