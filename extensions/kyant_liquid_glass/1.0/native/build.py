"""Build the catalog payload with JDK 17+, ECJ 3.39.0 and D8 8.10.21.

Pass the Android SDK 35 android.jar, Xposed API 82 jar and the classes.jar
from AndroidX DynamicAnimation 1.1.0. They are compile-time dependencies.
"""
import argparse
import base64
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZipFile
import zlib

parser = argparse.ArgumentParser(description=__doc__)
for flag in ("ecj", "d8", "android", "xposed", "dynamicanimation"):
    parser.add_argument(f"--{flag}", required=True, type=Path)
args = parser.parse_args()
here = Path(__file__).resolve().parent

with tempfile.TemporaryDirectory() as directory:
    work = Path(directory)
    android_api = work / "android-api.jar"
    classes = work / "classes"
    classes.mkdir()

    # ECJ uses the JDK for java.* and the Android SDK for platform classes.
    with ZipFile(args.android) as source, ZipFile(android_api, "w") as output:
        for entry in source.infolist():
            if entry.filename.startswith(("android/", "dalvik/")):
                output.writestr(entry, source.read(entry))

    subprocess.run([
        "java", "-jar", str(args.ecj), "-17", "-proc:none", "-encoding", "UTF-8",
        "-classpath", os.pathsep.join(map(str, [android_api, args.xposed, args.dynamicanimation])),
        "-d", str(classes), *map(str, sorted(here.glob("*.java"))),
    ], check=True)
    subprocess.run([
        "java", "-cp", str(args.d8), "com.android.tools.r8.D8", "--release",
        "--min-api", "33", "--lib", str(args.android), "--classpath", str(args.xposed),
        "--classpath", str(args.dynamicanimation), "--output", str(work),
        *map(str, sorted(classes.rglob("*.class"))),
    ], check=True)
    raw = (work / "classes.dex").read_bytes()

assert raw.startswith(b"dex\n") and len(raw) <= 512 * 1024
packed = base64.b64encode(zlib.compress(raw, level=9))
assert len(packed) <= 384 * 1024
(here.parent / "payload" / "module.b64").write_bytes(packed + b"\n")
print("DEX size", len(raw))
print("DEX SHA-256", hashlib.sha256(raw).hexdigest())
