# Additional clean files
cmake_minimum_required(VERSION 3.16)

if("${CONFIG}" STREQUAL "" OR "${CONFIG}" STREQUAL "")
  file(REMOVE_RECURSE
  "CMakeFiles/loseme_gui_autogen.dir/AutogenUsed.txt"
  "CMakeFiles/loseme_gui_autogen.dir/ParseCache.txt"
  "loseme_gui_autogen"
  )
endif()
