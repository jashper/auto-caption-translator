#!/usr/bin/env python3
"""
版本一致性檢查工具

檢查實際安裝的包版本是否與 requirements-locked.txt 一致。
用於防止意外的自動升級導致兼容性問題。

使用方式：
    python check_versions.py

返回值：
    0 - 所有版本一致
    1 - 發現版本不一致
"""

import subprocess
import sys
from pathlib import Path


def parse_requirements(file_path):
    """解析 requirements 文件，返回 {package: version} 字典"""
    requirements = {}
    
    if not Path(file_path).exists():
        print(f"❌ 文件不存在: {file_path}")
        return requirements
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # 跳過註釋和空行
            if not line or line.startswith('#'):
                continue
            
            # 處理 package==version 格式
            if '==' in line:
                # 移除 [extras] 部分（如 uvicorn[standard]）
                if '[' in line:
                    line = line.split('[')[0] + line.split(']')[1]
                
                pkg, ver = line.split('==', 1)
                pkg = pkg.strip().lower()
                ver = ver.strip()
                
                # 移除註釋
                if '#' in ver:
                    ver = ver.split('#')[0].strip()
                
                requirements[pkg] = ver
    
    return requirements


def get_installed_packages():
    """獲取實際安裝的包版本，返回 {package: version} 字典"""
    installed = {}
    
    try:
        # 使用當前 Python 解釋器的 pip（確保使用正確的環境）
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'freeze'],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            if '==' in line and not line.startswith('-e'):
                # 移除 @ file:// 等路徑信息
                if ' @' in line:
                    line = line.split(' @')[0]
                
                pkg, ver = line.split('==', 1)
                installed[pkg.lower()] = ver
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 執行 pip freeze 失敗: {e}")
        sys.exit(1)
    
    return installed


def normalize_version(version):
    """
    標準化版本號，處理特殊情況
    
    例如：
    - 2.8.0+cpu -> 2.8.0
    - 2.9.0.post0 -> 2.9.0
    """
    # 移除 +cpu, +cu118 等後綴
    if '+' in version:
        version = version.split('+')[0]
    
    # 移除 .post0 等後綴
    if '.post' in version:
        version = version.split('.post')[0]
    
    return version


def check_versions():
    """檢查版本一致性"""
    print("🔍 檢查版本一致性...\n")
    
    # 解析 requirements-locked.txt
    requirements_file = 'requirements-locked.txt'
    expected = parse_requirements(requirements_file)
    
    if not expected:
        print(f"❌ 無法讀取 {requirements_file}")
        return False
    
    print(f"📋 從 {requirements_file} 讀取了 {len(expected)} 個依賴\n")
    
    # 獲取實際安裝版本
    installed = get_installed_packages()
    
    if not installed:
        print("❌ 無法獲取已安裝的包列表")
        return False
    
    # 比較版本
    mismatches = []
    missing = []
    
    for pkg, expected_ver in expected.items():
        actual_ver = installed.get(pkg)
        
        if not actual_ver:
            missing.append(pkg)
            continue
        
        # 標準化版本號進行比較
        expected_normalized = normalize_version(expected_ver)
        actual_normalized = normalize_version(actual_ver)
        
        if expected_normalized != actual_normalized:
            mismatches.append({
                'package': pkg,
                'expected': expected_ver,
                'actual': actual_ver,
                'expected_normalized': expected_normalized,
                'actual_normalized': actual_normalized
            })
    
    # 輸出結果
    all_ok = True
    
    if missing:
        print("❌ 缺少以下依賴：")
        for pkg in missing:
            print(f"  - {pkg}")
        print()
        all_ok = False
    
    if mismatches:
        print("⚠️  版本不一致：")
        for m in mismatches:
            print(f"  - {m['package']}:")
            print(f"    期望: {m['expected']} (標準化: {m['expected_normalized']})")
            print(f"    實際: {m['actual']} (標準化: {m['actual_normalized']})")
        print()
        all_ok = False
    
    if all_ok:
        print("✅ 所有版本一致！")
        print(f"\n已檢查 {len(expected)} 個核心依賴，全部匹配。")
        return True
    else:
        print("\n💡 建議操作：")
        if missing:
            print("  1. 安裝缺少的依賴：")
            print(f"     pip install -r {requirements_file}")
        if mismatches:
            print("  2. 重新安裝以匹配鎖定版本：")
            print(f"     pip install -r {requirements_file} --force-reinstall")
        print("\n  3. 或者更新鎖定文件以匹配當前環境：")
        print("     pip freeze > requirements-frozen.txt")
        return False


def main():
    """主函數"""
    try:
        success = check_versions()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  檢查被中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
