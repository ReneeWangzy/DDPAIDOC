#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def main():
    # 获取参数
    readme_path = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else 'output.pdf'
    
    # 自动查找所有Markdown文件（包括README和章节文件）
    md_files = []
    with open(readme_path, 'r') as f:
        content = f.read()
    
    # 匹配所有.md文件链接和章节标记
    for line in content.split('\n'):
        if '➢' in line:  # 处理章节标记
            dir_name = line.split('➢')[-1].strip()
            dir_path = os.path.join(os.path.dirname(readme_path), dir_name)
            if os.path.isdir(dir_path):
                for fname in os.listdir(dir_path):
                    if fname.endswith('.md'):
                        md_files.append(os.path.join(dir_path, fname))
        elif '.md)' in line:  # 处理普通链接
            start = line.find('(') + 1
            end = line.find(')')
            md_path = line[start:end]
            if md_path.endswith('.md'):
                abs_path = os.path.join(os.path.dirname(readme_path), md_path)
                if os.path.exists(abs_path):
                    md_files.append(abs_path)
    
    # 去重并确保README排第一
    md_files = [readme_path] + list(set(md_files) - {readme_path})
    
    # 生成PDF（图片路径完全依赖Markdown文件中的原始路径）
    subprocess.run([
        'pandoc',
        '-o', output_pdf,
        '--pdf-engine=weasyprint',
        '--toc',
        '-V', 'CJKmainfont=Noto Sans CJK SC'
    ] + md_files)

if __name__ == '__main__':
    main()
