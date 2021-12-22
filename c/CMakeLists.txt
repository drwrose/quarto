cmake_minimum_required(VERSION 2.8)
project(quarto)

# Scan for dependencies
set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

# Tell CMake we need to use C++ 11.
if (CMAKE_VERSION VERSION_LESS "3.1")
  if (CMAKE_CXX_COMPILER_ID STREQUAL "GNU")
    set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=gnu++11")
  endif ()
else ()
  set (CMAKE_CXX_STANDARD 11)
endif ()

# Options

find_package(Threads)

set(BUILD_MQUARTO TRUE CACHE BOOL "Build mquarto command-line tool")
set(BUILD_LIBQUARTO FALSE CACHE BOOL "Build libquarto shared library")

set(QUARTO_SOURCES Quarto.h Quarto.cpp GameState.h GameState.cpp Board.h Board.cpp Piece.h Piece.cpp Player.h Player.cpp SearchResult.h SearchResult.cpp)

if (BUILD_LIBQUARTO)
  # Build libquarto
  add_library(quarto SHARED ${QUARTO_SOURCES})
  set_target_properties(quarto PROPERTIES COMPILE_DEFINITIONS "EXPORT_LIBQUARTO=1;${GLOBAL_DEFINES}" CXX_STANDARD 11)
  target_link_libraries(quarto ${WS2_LIBRARY} ${CMAKE_THREAD_LIBS_INIT})
endif (BUILD_LIBQUARTO)

if (BUILD_MQUARTO)
  # Build mquarto
  add_executable(mquarto mquarto_main.cpp pgetopt.c pgetopt.h ${QUARTO_SOURCES})
  target_link_libraries(mquarto ${WS2_LIBRARY} ${CMAKE_THREAD_LIBS_INIT})
  set_target_properties(mquarto PROPERTIES COMPILE_DEFINITIONS "${GLOBAL_DEFINES}" CXX_STANDARD 11)
endif (BUILD_MQUARTO)
