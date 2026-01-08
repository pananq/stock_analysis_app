#!/usr/bin/env python3
"""
项目代码行数统计工具
统计指定目录下的代码行数和文档行数
"""

import os
import sys
from pathlib import Path

def count_lines_in_file(file_path):
    """统计单个文件的行数"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return len(f.readlines())
    except Exception as e:
        print(f"警告: 无法读取文件 {file_path}: {e}")
        return 0

def is_code_file(file_path):
    """判断是否为代码文件"""
    code_extensions = {
        '.py',    # Python
        '.js',    # JavaScript
        '.html',  # HTML
        '.css',   # CSS
        '.sh',    # Shell脚本
        '.yaml',  # YAML配置
        '.yml',   # YAML配置
        '.sql',   # SQL脚本
        '.java',  # Java
        '.cpp',   # C++
        '.c',     # C
        '.h',     # C头文件
        '.php',   # PHP
        '.rb',    # Ruby
        '.go',    # Go
        '.rs',    # Rust
        '.ts',    # TypeScript
        '.vue',   # Vue.js
        '.jsx',   # React JSX
        '.tsx',   # React TSX
    }
    return file_path.suffix.lower() in code_extensions

def is_doc_file(file_path):
    """判断是否为文档文件"""
    return file_path.suffix.lower() == '.md'

def should_ignore_directory(dir_name):
    """判断是否应该忽略的目录"""
    ignore_dirs = {
        '.git', '.svn', '.hg', '.idea', '.vscode',
        '__pycache__', 'node_modules', 'venv', 'env',
        '.codebuddy', 'logs', 'data'
    }
    return dir_name in ignore_dirs

def analyze_project(directory_path):
    """分析项目代码行数和文档行数"""
    directory = Path(directory_path)
    
    if not directory.exists():
        print(f"错误: 目录 {directory_path} 不存在")
        return None
    
    code_stats = {}
    doc_stats = {}
    total_code_lines = 0
    total_doc_lines = 0
    
    print(f"正在分析项目: {directory_path}")
    print("-" * 60)
    
    for root, dirs, files in os.walk(directory):
        # 过滤需要忽略的目录
        dirs[:] = [d for d in dirs if not should_ignore_directory(d)]
        
        for file in files:
            file_path = Path(root) / file
            
            if is_code_file(file_path):
                lines = count_lines_in_file(file_path)
                ext = file_path.suffix.lower()
                code_stats[ext] = code_stats.get(ext, 0) + lines
                total_code_lines += lines
                
            elif is_doc_file(file_path):
                lines = count_lines_in_file(file_path)
                doc_stats[file_path.relative_to(directory)] = lines
                total_doc_lines += lines
    
    return {
        'code_stats': code_stats,
        'doc_stats': doc_stats,
        'total_code_lines': total_code_lines,
        'total_doc_lines': total_doc_lines
    }

def print_statistics(results):
    """打印统计结果"""
    if not results:
        return
    
    print("\n📊 代码文件统计:")
    print("-" * 40)
    for ext, lines in sorted(results['code_stats'].items()):
        print(f"{ext:8} : {lines:>6} 行")
    
    print(f"\n📈 代码文件总计: {results['total_code_lines']} 行")
    
    print("\n📄 文档文件统计:")
    print("-" * 40)
    for file_path, lines in sorted(results['doc_stats'].items()):
        print(f"{str(file_path):40} : {lines:>6} 行")
    
    print(f"\n📚 文档文件总计: {results['total_doc_lines']} 行")
    
    print(f"\n🎯 项目总计: {results['total_code_lines'] + results['total_doc_lines']} 行")
    print(f"    - 代码文件: {results['total_code_lines']} 行 ({results['total_code_lines']/(results['total_code_lines'] + results['total_doc_lines'])*100:.1f}%)")
    print(f"    - 文档文件: {results['total_doc_lines']} 行 ({results['total_doc_lines']/(results['total_code_lines'] + results['total_doc_lines'])*100:.1f}%)")

def main():
    """主函数"""
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = os.getcwd()
    
    print("项目代码行数统计工具")
    print("=" * 60)
    
    results = analyze_project(directory)
    
    if results:
        print_statistics(results)
    
    print("\n✅ 统计完成!")

if __name__ == "__main__":
    main()