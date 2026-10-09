#!/usr/bin/env python3
"""Fetch the pinned MIT-licensed upstream and optionally install its package."""
import argparse
from pathlib import Path
import subprocess

COMMIT = 'd5c8329422e0a0b834a15874545cb6a74b4f9b26'
ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--upstream', type=Path, default=ROOT / 'outputs/hipporag_upstream')
    parser.add_argument('--python', help='Python >=3.10 virtualenv executable; install upstream if supplied')
    args = parser.parse_args()
    target = args.upstream.resolve()
    if target.exists():
        current = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
        changed = subprocess.check_output(['git', '-C', str(target), 'status', '--porcelain', '--untracked-files=no'], text=True).strip()
        if current != COMMIT or changed:
            raise ValueError('existing upstream differs; use a new empty path')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(['git', 'clone', 'https://github.com/OSU-NLP-Group/HippoRAG.git', str(target)], check=True)
        subprocess.run(['git', '-C', str(target), 'checkout', '--detach', COMMIT], check=True)
    if args.python:
        subprocess.run([args.python, '-m', 'pip', 'install', '-e', str(target)], check=True)
    print(f'pinned upstream: {target} @ {COMMIT}')


if __name__ == '__main__':
    main()
