python_sources(
  name = "common_pkg",
  sources = ["__init__.py"],
  dependencies = [
    "src/main/python/twitter:twitter_pkg",
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
  ],
)
