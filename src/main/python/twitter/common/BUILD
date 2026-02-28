python_sources(
  name = "common_pkg",
  sources = ["__init__.py"],
  dependencies = [
    "src/main/python/twitter:twitter_pkg",
    "src/main/python:process_handle_ps_shim",
  ],
)

python_sources(
  name = "common_sources",
  sources = [
    "**/*.py",
    "!zookeeper/**",
  ],
  dependencies = [
    "src/main/python/twitter:twitter_pkg",
    "src/main/python:process_handle_ps_shim",
  ],
)
