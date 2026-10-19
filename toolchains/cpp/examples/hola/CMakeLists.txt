cmake_minimum_required(VERSION 3.28)
project(gordus_hola_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_executable(hola main.cpp)
target_compile_options(hola PRIVATE -Wall -Wextra -Wpedantic -Werror)
