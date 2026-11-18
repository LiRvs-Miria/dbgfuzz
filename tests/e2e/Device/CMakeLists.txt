# Device side of the E2E environment.
#
# CMake CAN drive the lldb-server spawn: the `spawn` custom target runs the
# script in the foreground (USES_TERMINAL), Ctrl+C stops it.
#   cmake -S . -B build && cmake --build build
#   cmake --build build --target spawn          # blocks; Ctrl+C to stop
# The spawn script also works standalone: ./run_lldbserver.sh build/helloworld
cmake_minimum_required(VERSION 3.20)
project(ptrfuzz_device_e2e CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(helloworld helloworld.cpp)
# -g: line breakpoints from the DAP probe need a line table (symbol
# breakpoints would work without, but line BPs are the DAP-native form)
target_compile_options(helloworld PRIVATE -g)

set(E2E_PORT "51317" CACHE STRING "gdb-remote port for the device side")

add_custom_target(spawn
    COMMAND "${CMAKE_CURRENT_SOURCE_DIR}/run_lldbserver.sh"
            "$<TARGET_FILE:helloworld>" "${E2E_PORT}"
    DEPENDS helloworld
    USES_TERMINAL
)
