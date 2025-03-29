#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import tempfile
import argparse
from datetime import datetime

def extract_files_from_readme(readme_path):
    """从README.md文件中提取文件链接"""
    try:
        # 检查文件是否存在
        if not os.path.exists(readme_path):
            print(f"错误: 文件不存在 {readme_path}")
            return None, []
        
        print(f"正在从 {readme_path} 提取文件链接...")
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题
        title_match = re.search(r'^#\s+(.+?)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else os.path.basename(os.path.dirname(readme_path))
        
        print(f"提取到的标题: {title}")
        
        # 使用正则表达式提取所有文件链接
        links = re.findall(r'\[.*?\]\((.*?\.md)\)', content)
        
        print(f"找到 {len(links)} 个链接: {links}")
        
        return title, links
    except Exception as e:
        print(f"提取文件链接时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return None, []

def create_title_page(title, version="1.0", author=""):
    """创建封面页"""
    try:
        title_content = f"""---
title: {title}
author: {author}
date: {datetime.now().strftime('%Y年%m月%d日')}
---

# {title}

**版本: {version}**

© {datetime.now().year} {author if author else "版权所有"}, 保留所有权利

---

"""
        
        # 创建临时文件
        fd, path = tempfile.mkstemp(suffix='.md')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(title_content)
        
        print(f"封面页创建成功: {path}")
        return path
    except Exception as e:
        print(f"创建封面页时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        # 返回一个简单的备用封面页
        fd, path = tempfile.mkstemp(suffix='.md')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n")
        return path

def fix_image_paths(file_list, repo_root=None):
    """创建临时文件，修复图片路径
    Args:
        file_list: 待处理的文件列表
        repo_root: 仓库根目录绝对路径（GitHub Actions环境下需要）
    """
    temp_files = []
    
    try:
        for file_path in file_list:
            if not os.path.exists(file_path):
                print(f"警告: 文件不存在 {file_path}")
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 获取文件所在目录（兼容相对路径和绝对路径）
            file_dir = os.path.dirname(os.path.abspath(file_path))
            
            # 修复图片路径 ![alt](path) -> ![alt](absolute_path)
            def replace_path(match):
                alt_text = match.group(1)
                img_path = match.group(2)
                
                # 跳过网络图片
                if img_path.startswith(('http://', 'https://')):
                    return match.group(0)
                
                # 处理绝对路径（在GitHub Actions中需要基于仓库根目录）
                if os.path.isabs(img_path) and repo_root:
                    abs_path = os.path.join(repo_root, img_path.lstrip('/'))
                else:
                    abs_path = os.path.normpath(os.path.join(file_dir, img_path))
                
                # 验证路径是否存在（尝试多种可能位置）
                possible_paths = [
                    abs_path,
                    os.path.join(repo_root, img_path) if repo_root else None,
                    os.path.join(file_dir, img_path)
                ]
                
                for test_path in filter(None, possible_paths):
                    if os.path.exists(test_path):
                        return f'![{alt_text}]({test_path})'
                
                print(f"警告: 图片不存在 {img_path}，尝试的路径: {possible_paths}")
                return match.group(0)
            
            fixed_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_path, content)
            
            # 创建临时文件
            fd, temp_path = tempfile.mkstemp(suffix='.md')
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(fixed_content)
            
            temp_files.append(temp_path)
        
        return temp_files
    except Exception as e:
        print(f"修复图片路径时出错: {str(e)}")
        traceback.print_exc()
        for temp_file in temp_files:
            try: os.remove(temp_file)
            except: pass
        return []


def generate_pdf_with_pandoc(file_list, output_pdf, title, css_file=None, author=""):
    """使用Pandoc生成PDF"""
    try:
        # 检查文件列表是否为空
        if not file_list:
            print("错误: 没有要处理的文件")
            return False
        
        # 检查是否所有文件都存在
        missing_files = [f for f in file_list if not os.path.exists(f)]
        if missing_files:
            print(f"警告: 以下文件不存在: {missing_files}")
            # 过滤掉不存在的文件
            file_list = [f for f in file_list if os.path.exists(f)]
            if not file_list:
                print("错误: 没有有效的文件可处理")
                return False
        
        # 基本Pandoc命令
        cmd = ['pandoc', '-o', output_pdf, '--pdf-engine=weasyprint']
        
        # 添加CSS样式
        if css_file:
            if os.path.exists(css_file):
                cmd.extend(['--css', css_file])
            else:
                print(f"警告: CSS文件不存在 {css_file}")
        
        # 添加目录
        cmd.extend(['--toc', '--toc-depth=3'])
        
        # 添加更多自定义选项
        cmd.extend([
            '--number-sections',           # 章节自动编号
            '--highlight-style=tango',     # 代码高亮样式
            '--metadata', f'title={title}',
            '--metadata', 'lang=zh-CN',
            '--variable', 'papersize=a4',  # 纸张大小
            '--variable', 'margin-top=25mm',
            '--variable', 'margin-right=25mm',
            '--variable', 'margin-bottom=25mm',
            '--variable', 'margin-left=25mm'
        ])
        
        if author:
            cmd.extend(['--metadata', f'author={author}'])
        
        # 添加所有文件
        cmd.extend(file_list)
        
        print("执行命令:", ' '.join(cmd))
        
        # 执行命令
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        # 检查是否有错误
        if process.returncode != 0:
            print(f"错误: PDF生成失败")
            print(f"错误信息: {process.stderr}")
            return False
        
        print(f"PDF生成成功: {output_pdf}")
        return True
    except Exception as e:
        print(f"生成PDF时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def find_readme_files(start_dir, pattern='README.md'):
    """递归查找指定目录下的README文件"""
    try:
        readme_files = []
        
        for root, dirs, files in os.walk(start_dir):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            if pattern in files:
                readme_files.append(os.path.join(root, pattern))
        
        return readme_files
    except Exception as e:
        print(f"查找README文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def process_single_manual(readme_path, css_file, output_dir=None, author="", version="1.0", pdf_name=None):
    """处理单个手册"""
    try:
        manual_dir = os.path.dirname(readme_path)
        
        print(f"\n处理手册: {manual_dir}")
        print(f"从 {readme_path} 提取文件列表...")
        
        # 提取文件列表和标题
        title, file_list = extract_files_from_readme(readme_path)
        
        if not title or not file_list:
            print(f"错误: 无法从 {readme_path} 提取有效内容")
            return False
        
        print(f"标题: {title}")
        print(f"发现 {len(file_list)} 个链接的Markdown文件")
        
        # 将相对路径转换为绝对路径
        file_list = [os.path.join(manual_dir, f) if not os.path.isabs(f) else f for f in file_list]
        
        # 检查每个文件是否存在
        missing_files = [f for f in file_list if not os.path.exists(f)]
        if missing_files:
            print(f"警告: 以下文件不存在: {missing_files}")
        
        # 创建封面页
        title_page = create_title_page(title, version, author)
        
        # 所有处理的文件
        all_files = [title_page] + file_list
        
        print("修复图片路径...")
        
        # 修复图片路径
        temp_files = fix_image_paths(all_files)
        
        if not temp_files:
            print("错误: 图片路径修复失败或没有有效的文件")
            # 清理封面页
            try:
                os.remove(title_page)
            except:
                pass
            return False
        
        # 设置输出PDF路径
        if pdf_name:
            output_pdf = pdf_name
        else:
            # 使用目录名作为PDF名
            dir_name = os.path.basename(manual_dir)
            output_pdf = f"{dir_name}.pdf"
        
        if output_dir:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            output_pdf = os.path.join(output_dir, output_pdf)
        
        print(f"使用Pandoc生成PDF: {output_pdf}")
        
        # 生成PDF
        success = generate_pdf_with_pandoc(temp_files, output_pdf, title, css_file, author)
        
        print("清理临时文件...")
        
        # 清理临时文件
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass
        
        # 删除封面页
        try:
            os.remove(title_page)
        except:
            pass
        
        if success:
            print(f"PDF已成功生成: {output_pdf}")
            return True
        else:
            print("PDF生成失败")
            return False
    except Exception as e:
        print(f"处理手册时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    try:
        # 创建命令行参数解析器
        parser = argparse.ArgumentParser(description='将Markdown文件转换为PDF')
        
        parser.add_argument('--dir', '-d', help='包含README.md的目录路径', default='.')
        parser.add_argument('--recursive', '-r', action='store_true', help='递归处理子目录')
        parser.add_argument('--output', '-o', help='输出PDF的目录')
        parser.add_argument('--css', '-c', help='CSS样式文件路径')
        parser.add_argument('--author', '-a', help='文档作者', default='')
        parser.add_argument('--version', '-v', help='文档版本', default='1.0')
        parser.add_argument('--name', '-n', help='输出PDF文件名')
        parser.add_argument('--verbose', action='store_true', help='显示详细的调试信息')
        
        args = parser.parse_args()
        
        # 检查目录是否存在
        if not os.path.exists(args.dir):
            print(f"错误: 目录不存在 {args.dir}")
            return 1
        
        # 检查CSS文件是否存在
        if args.css and not os.path.exists(args.css):
            print(f"警告: CSS文件 {args.css} 不存在")
        
        if args.recursive:
            # 递归处理多个手册
            readme_files = find_readme_files(args.dir)
            print(f"找到 {len(readme_files)} 个README文件")
            
            if not readme_files:
                print(f"错误: 在 {args.dir} 目录下未找到README.md文件")
                return 1
            
            success_count = 0
            failed_count = 0
            
            for readme in readme_files:
                success = process_single_manual(
                    readme, args.css, args.output, args.author, args.version
                )
                if success:
                    success_count += 1
                else:
                    failed_count += 1
            
            print(f"\n处理完成: 成功 {success_count}, 失败 {failed_count}")
            
            # 如果有任何失败，返回非零退出码
            return 0 if failed_count == 0 else 1
        else:
            # 处理单个手册
            readme_path = os.path.join(args.dir, 'README.md')
            if not os.path.exists(readme_path):
                print(f"错误: 文件 {readme_path} 不存在")
                return 1
            
            success = process_single_manual(
                readme_path, args.css, args.output, args.author, args.version, args.name
            )
            
            return 0 if success else 1
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"程序执行出错: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
