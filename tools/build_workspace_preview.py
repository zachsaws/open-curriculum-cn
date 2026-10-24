#!/usr/bin/env python3
"""Package the existing static web tree for local review; never deploy."""
import argparse
import shutil
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True,help='A new directory; never overwritten')
    args=parser.parse_args()
    output=args.output.resolve()
    if output.exists():
        raise SystemExit('Output already exists; choose a new directory to preserve earlier builds')
    subprocess.run(['python3',str(ROOT/'tools/build_learning_relations.py'),'--check'],check=True)
    subprocess.run(['node','--check',str(ROOT/'web/learning-core.mjs')],check=True)
    subprocess.run(['node','--check',str(ROOT/'web/learning-workspace.mjs')],check=True)
    subprocess.run(['node','--check',str(ROOT/'web/consumer.mjs')],check=True)
    for script in sorted((ROOT/'web'/'v2').glob('*.mjs')):
        subprocess.run(['node','--check',str(script)],check=True)
    for script in sorted((ROOT/'web'/'planet').glob('*.mjs')):
        subprocess.run(['node','--check',str(script)],check=True)
    subprocess.run(['node','--check',str(ROOT/'tools'/'serve_planet.mjs')],check=True)
    shutil.copytree(ROOT/'web',output,ignore=shutil.ignore_patterns('.DS_Store'))
    (output/'.nojekyll').touch()
    print(f'Packaged static preview in {output}; source and old pages preserved')

if __name__=='__main__': main()
