python_sources(
  name = "zookeeper",
  sources = ["**/*.py"],
  dependencies = [
    "src/main/python/twitter:twitter_pkg",
    "src/main/python/twitter/common:common_pkg",
    "3rdparty/python#kazoo",
    "src/main/python/twitter/common:common_sources",
  ],
)

python_distribution(
  name = "zookeeper_dist",
  dependencies = [
    ":zookeeper",
  ],
  provides = python_artifact(
    name = "twitter-common-zookeeper",
    version = "0.3.9+aurora",
  ),
)
