"""
測試 VTT 格式
檢查生成的 VTT 文件是否正確
"""
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.subtitle_generator import SubtitleGenerator
from src.models.subtitle import SubtitleSegment

def test_vtt_generation():
    """測試 VTT 生成"""
    print("=" * 50)
    print("測試 VTT 格式生成")
    print("=" * 50)
    
    # 創建測試數據
    segments = [
        SubtitleSegment(
            index=1,
            start_time=0.0,
            end_time=2.5,
            text="Hello, this is a test.",
            language="en"
        ),
        SubtitleSegment(
            index=2,
            start_time=2.5,
            end_time=5.0,
            text="Testing VTT format.",
            language="en"
        )
    ]
    
    # 生成 VTT
    generator = SubtitleGenerator()
    output_path = project_root / "tools" / "test_output.vtt"
    
    print(f"\n生成 VTT 文件到: {output_path}")
    generator.generate_vtt(segments, str(output_path), "en")
    
    # 讀取並顯示內容
    print("\n生成的 VTT 內容:")
    print("-" * 50)
    with open(output_path, 'r', encoding='utf-8') as f:
        content = f.read()
        print(content)
    print("-" * 50)
    
    # 驗證格式
    print("\n驗證:")
    if content.startswith("WEBVTT"):
        print("✅ 有 WEBVTT 標頭")
    else:
        print("❌ 缺少 WEBVTT 標頭")
    
    if "00:00:00.000 --> 00:00:02.500" in content:
        print("✅ 時間戳格式正確")
    else:
        print("❌ 時間戳格式錯誤")
    
    if "Hello, this is a test." in content:
        print("✅ 文字內容正確")
    else:
        print("❌ 文字內容錯誤")
    
    # 清理測試文件
    output_path.unlink()
    print("\n測試完成！")

if __name__ == "__main__":
    test_vtt_generation()
