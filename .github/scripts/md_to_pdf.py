#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版PDF生成器 - 专为GitHub Actions设计
"""

import os
import re
import sys
import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description='生成PDF文档')
    parser.add_argument('--root', required=True, help='仓库根目录')
    parser.add_argument('--readme', required=True, help='README.md路径')
    parser.add_argument('--output', required=True, help='输出PDF路径')
    parser.add_argument('--css', help='CSS样式表路径')
    parser.add_argument('--title', default='产品文档', help='文档标题')
    parser.add_argument('--author', help='文档作者')
    parser.add_argument('--verbose', action='store_true', help='详细模式')
    return parser.parse_args()

def find_all_markdown_files(readme_path, root_dir):
    """递归查找所有关联的Markdown文件"""
    with open(readme_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 匹配两种格式：
    # 1. [text](path.md)
    # 2. ➢ 1-directory
    pattern = r'(?:\[.*?\]\((.*?\.md)\)|➢\s*(\d+-[\w\-]+)'
    matches = re.finditer(pattern, content)
    
    files = {os.path.normpath(readme_path)}
    readme_dir = os.path.dirname(readme_path)

    for match in matches:
        # 处理[text](path.md)格式
        if match.group(1):
            abs_path = os.path.normpath(os.path.join(readme_dir, match.group(1)))
            if abs_path.endswith('.md') and os.path.exists(abs_path):
                files.add(abs_path)
        
        # 处理➢ directory格式
        elif match.group(2):
            dir_path = os.path.join(readme_dir, match.group(2))
            if os.path.isdir(dir_path):
                for root, _, filenames in os.walk(dir_path):
                    for fname in filenames:
                        if fname.endswith('.md'):
                            files.add(os.path.normpath(os.path.join(root, fname)))

    return sorted(files)

def generate_pdf(files, output_path, css_path=None, title="", author=""):
    """使用pandoc生成PDF"""
    cmd = [
        'pandoc',
        '-o', output_path,
        '--pdf-engine=weasyprint',
        '--toc',
        '--toc-depth=3',
        '-V', 'CJKmainfont=Noto Sans CJK SC',
        '--metadata', f'title={title}',
    ]

    if css_path:
        cmd.extend(['--css', css_path])
    if author:
        cmd.extend(['--metadata', f'author={author}'])

    cmd.extend(files)

    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"PDF生成失败: {e}", file=sys.stderr)
        return False

def main():
    args = parse_args()
    
    if args.verbose:
        print(f"仓库根目录: {args.root}")
        print(f"README路径: {args.readme}")

    # 查找所有Markdown文件
    md_files = find_all_markdown_files(args.readme, args.root)
    
    if args.verbose:
        print("将合并的文件:")
        for f in md_files:
            print(f" - {f}")

    # 确保输出目录存在
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # 生成PDF
    success = generate_pdf(
        md_files,
        args.output,
        args.css,
        args.title,
        args.author
    )

    if not success:
        sys.exit(1)

if __name__ == '__main__':
    main()
