import os, shutil, re, sys
from pathlib import Path

package_name = os.environ.get("PKG_NAME")
is_container = os.environ.get("IS_CONTAINER") == "true"
image_name = os.environ.get("IMG_NAME", "")
base_path = Path("target") / package_name

# Inject pre-built thrift binary to avoid download issues.
# IMPORTANT: centos-7 uses glibc 2.17; binaries built on rocky-8/9 (glibc 2.28+) will not
# execute on centos-7. Always prefer the centos-7 binary — it runs everywhere.
is_centos7 = 'centos-7' in image_name

if is_centos7:
    possible_thrift_sources = [
        f'artifacts/aurora-centos-7/rpmbuild/BUILD/{package_name}/build-support/thrift/thrift',
    ]
else:
    possible_thrift_sources = [
        f'artifacts/aurora-centos-7/rpmbuild/BUILD/{package_name}/build-support/thrift/thrift',
        f'artifacts/aurora-rocky-8/rpmbuild/BUILD/{package_name}/build-support/thrift/thrift',
    ]

target_thrift = base_path / 'build-support/thrift/thrift'

# Always remove stale binary so the correct platform binary is re-evaluated each build.
if target_thrift.exists():
    target_thrift.unlink()

for src in possible_thrift_sources:
    src_path = Path(src)
    if src_path.exists():
        print(f'Injecting pre-built thrift from {src}')
        target_thrift.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, target_thrift)
        os.chmod(target_thrift, 0o755)
        break


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
    
    # 1. Force version to 0.22
    text = text.replace('expected_version = "0.22.0"', 'expected_version = "0.22"')
    
    # 2. Force RELATIVE search paths (relative to pants.toml) with <PATH> fallback
    thrift_rel_dir = "build-support/thrift"
    thrift_section = f"\n[apache-thrift]\nthrift_search_paths = [\"{thrift_rel_dir}\", \"<PATH>\"]\nexpected_version = \"0.22\"\n"
    
    if "[apache-thrift]" in text:
        text = re.sub(r"\[apache-thrift\].*?(\n\n|\Z)", thrift_section, text, flags=re.DOTALL)
    else:
        text += thrift_section
        
    pants_toml.write_text(text)
    print(f"--- DEBUG: VERIFYING pants.toml at {pants_toml} ---")
    print(pants_toml.read_text())
    print("--- DEBUG: END VERIFYING ---")
