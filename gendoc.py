#!/usr/bin/env python3

from datetime import date
from os import system, environ
from packaging.version import Version
from subprocess import run, CalledProcessError

def check_gen_sidoc_version(version):
    try:
        p = run(["python3", "-m", "libdoc", "--version"], capture_output=True)
        return p.returncode == 0 and Version(p.stdout.decode()) >= Version(version)
    except CalledProcessError:
        return False

def main():
    hostname = 'pdup4'
    docdate = str(date.today())
    libdoc_version = "0.1.16"
    if not check_gen_sidoc_version(environ.get("LIBDOC_VERSION", libdoc_version)):
        cmd = f"python3 -m pip install -U git+https://github.com/spaceinventor/libdoc.git@{libdoc_version}"
        print(cmd)
        system(cmd)
    cmd = f"python3 -m libdoc --elf build-0/lib/c21/compile/pdup4-0.elf -d {docdate} -t MAN -n 001 {hostname} -o build-doc/{hostname}_MAN.pdf doc/index_man.rst"
    print(cmd)
    system(cmd)
    cmd = f"python3 -m libdoc --elf build-0/lib/c21/compile/pdup4-0.elf -d {docdate} -t SWICD -n 001 {hostname} -o build-doc/{hostname}_SWICD.pdf doc/index_sw.rst"
    print(cmd)
    system(cmd)

main()
