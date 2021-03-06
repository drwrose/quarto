cmake_minimum_required(VERSION 3.16)
project(quarto LANGUAGES CXX C)

# SWIG: use standard target name.
if(POLICY CMP0078)
  cmake_policy(SET CMP0078 NEW)
endif()

# Scan for dependencies
set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

# Tell CMake we need to use C++ 11.
set(CMAKE_CXX_STANDARD 11)

# Options

find_package(Threads)

set(BUILD_MQUARTO TRUE CACHE BOOL "Build mquarto command-line tool")
set(BUILD_PYQUARTO TRUE CACHE BOOL "Build pyquarto Python module")

set(QUARTO_SOURCES Quarto.h Quarto.cpp GameState.h GameState.cpp Board.h Board.cpp Piece.h Piece.cpp Player.h Player.cpp SearchAccumulator.h SearchAccumulator.cpp SearchResult.h SearchResult.cpp)
set(QUARTO_SWIG pyquarto.i)

if (BUILD_PYQUARTO)
  # Build pyquarto

  find_package(Python3 COMPONENTS Development REQUIRED)
  include_directories(${Python3_INCLUDE_DIRS})
  find_package(SWIG REQUIRED)
  include(${SWIG_USE_FILE})

  include_directories("${CMAKE_SOURCE_DIR}")
  link_directories(${Python3_LIBRARY_DIRS})

  SET(CMAKE_SWIG_FLAGS "-threads")

  set_property(SOURCE ${QUARTO_SWIG} PROPERTY CPLUSPLUS ON)
  swig_add_library(pyquarto TYPE SHARED LANGUAGE PYTHON SOURCES ${QUARTO_SWIG} ${QUARTO_SOURCES})
  #target_link_libraries(pyquarto ${PYTHON3_LIBRARIES} ${WS2_LIBRARY} ${CMAKE_THREAD_LIBS_INIT})

endif (BUILD_PYQUARTO)

if (BUILD_MQUARTO)
  # Build mquarto
  add_executable(mquarto mquarto_main.cpp pgetopt.c pgetopt.h ${QUARTO_SOURCES})
  target_link_libraries(mquarto ${WS2_LIBRARY} ${CMAKE_THREAD_LIBS_INIT})
  set_target_properties(mquarto PROPERTIES COMPILE_DEFINITIONS "${GLOBAL_DEFINES}" CXX_STANDARD 11)
endif (BUILD_MQUARTO)
