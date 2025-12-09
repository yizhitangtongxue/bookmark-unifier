import os
import glob
from processor import Processor
from bookmark_manager import BookmarkManager

def main():
    """
    主程序入口点。
    执行流程:
    1. 查找 input 文件夹下的 HTML 文件
    2. 读取并合并所有书签
    3. 去重
    4. 验证链接有效性 (耗时较长)
    5. 输出结果到 out/result.html
    """
    input_dir = 'input'
    output_dir = 'out'
    output_file = os.path.join(output_dir, 'result.html')

    # 确保目录存在
    os.makedirs(input_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    # 1. 查找 HTML 文件
    html_files = glob.glob(os.path.join(input_dir, '*.html'))
    if not html_files:
        print(f"{input_dir} 文件夹中未找到 HTML 文件。请将您的 Netscape 书签文件放入该文件夹。")
        return

    print(f"找到 {len(html_files)} 个文件: {html_files}")

    processor = Processor()
    manager = BookmarkManager()

    # 2. 合并 (读取所有)
    print("正在读取并合并书签...")
    all_bookmarks = processor.merge_bookmarks(html_files)
    print(f"共找到书签: {len(all_bookmarks)}")

    # 3. 去重
    print("正在去重...")
    unique_bookmarks = processor.deduplicate(all_bookmarks)
    print(f"去重后书签数: {len(unique_bookmarks)}")

    # 4. 验证 (可选，但在本项目中作为核心步骤)
    # 这一步会去除无法访问的书签
    print("正在验证链接 (这可能需要一些时间)...")
    validated_bookmarks = processor.validate_links(unique_bookmarks)

    # 5. 写入输出
    print(f"正在写入结果到 {output_file}...")
    manager.write_file(validated_bookmarks, output_file)
    print("完成!")

if __name__ == "__main__":
    main()
