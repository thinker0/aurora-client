import os, shutil, re, sys
from pathlib import Path

package_name = os.environ.get("PKG_NAME")
is_container = os.environ.get("IS_CONTAINER") == "true"
image_name = os.environ.get("IMG_NAME", "")
base_path = Path("target") / package_name

print(f"--- Python Patching Start for {package_name} (image: {image_name}) ---")

# Patch build.gradle for Python 3 and Node.js
gradle_path = base_path / "build.gradle"
if gradle_path.exists():
    text = gradle_path.read_text()
    
    # Python 3 compatibility
    text = text.replace("def python27Executable = ['python2.7', 'python'].find { python ->", "def python27Executable = ['python3', 'python2.7', 'python'].find { python ->")
    text = text.replace("sys.version_info >= (2,7) and sys.version_info < (3,)", "sys.version_info >= (3,0)")
    text = text.replace("Build requires Python 2.7.", "Build requires Python 3.")

    # Dynamic NodeJS version based on platform
    node_version = '20.18.1'
    if 'centos-7' in image_name or 'centos-7' in package_name:
        node_version = '16.20.2'
        print(f"Detected CentOS 7, using Node {node_version}")
        
        # Downgrade cheerio for CentOS 7
        pkg_json = base_path / 'ui/package.json'
        if pkg_json.exists():
            pkg_text = pkg_json.read_text()
            pkg_text = pkg_text.replace('"cheerio": "1.2.0"', '"cheerio": "1.0.0-rc.12"')
            pkg_json.write_text(pkg_text)
    
    # Replace any version = '...' inside node { }
    text = re.sub(r"version = '[^']*'", f"version = '{node_version}'", text)
    gradle_path.write_text(text)
    print(f"Applied Node version {node_version} to build.gradle")

# Force public registry and remove lock file
lock_file = base_path / "ui/package-lock.json"
if lock_file.exists():
    lock_file.unlink()

npmrc_file = base_path / "ui/.npmrc"
npmrc_file.write_text("registry=https://registry.npmjs.org/\nstrict-ssl=false\n")

# Patch thrift codegen
codegen_path = base_path / "src/main/python/apache/aurora/tools/java/thrift_wrapper_codegen.py"
if codegen_path.exists():
    codegen = codegen_path.read_text()
    codegen = codegen.replace("return map(parse_field, re.finditer(FIELD_RE, field_str))", "return list(map(parse_field, re.finditer(FIELD_RE, field_str)))")
    codegen_path.write_text(codegen)

# Patch pants.toml
pants_toml = base_path / "pants.toml"
if pants_toml.exists():
    text = pants_toml.read_text()
    text = text.replace('indexes = ["https://pypi.org/simple"]', 'indexes = []')
    if is_container:
        new_wheels_url = f"file:///dist/rpmbuild/BUILD/{package_name}/3rdparty/python/wheels"
    else:
        wheels_dir = (base_path / "3rdparty/python/wheels").resolve().as_posix()
        new_wheels_url = f"file://{wheels_dir}"
    text = re.sub(r'file:///.*/3rdparty/python/wheels', new_wheels_url, text)
    pants_toml.write_text(text)

# Replace symlinks
for rel_path in ["3rdparty/python/wheels", "build-support/thrift/thrift"]:
    path = base_path / rel_path
    if path.exists() and path.is_symlink():
        resolved = path.resolve()
        path.unlink()
        if resolved.is_dir():
            shutil.copytree(resolved, path, symlinks=False)
        elif resolved.is_file():
            shutil.copy2(resolved, path)

print("--- Python Patching Completed ---")
