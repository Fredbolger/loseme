cmake_minimum_required(VERSION 3.16)
project(loseme_gui VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 REQUIRED COMPONENTS 
    Core 
    Gui 
    Widgets 
    Network 
    Concurrent
)

add_executable(loseme_gui
    src/main.cpp
    src/mainwindow.cpp
    src/mainwindow.h
    src/apiclient.cpp
    src/apiclient.h
    src/ingestdialog.cpp
    src/ingestdialog.h
    src/searchwidget.cpp
    src/searchwidget.h
    src/sourceswidget.cpp
    src/sourceswidget.h
    src/runscontroller.cpp
    src/runscontroller.h
    src/models/documentpart.h
    src/models/indexingscope.h
    src/models/runstatus.h
)

target_link_libraries(loseme_gui PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::Network
    Qt6::Concurrent
)

if(WIN32)
    set_property(TARGET loseme_gui PROPERTY WIN32_EXECUTABLE TRUE)
endif()
