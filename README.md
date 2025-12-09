# 书签合并优化工具 (Bookmark Unifier)
这是一个用于整理和优化浏览器书签的 Python 工具。

## 主要功能
该工具处理从浏览器导出的书签（HTML格式），并执行以下操作：
1. **自动合并**：将 `input` 文件夹下的所有 HTML 书签文件合并为一个。
2. **智能去重**：自动检测并删除重复的网址（保留第一次出现的）。
3. **死链检测**：自动验证每个书签的连通性。无法访问的书签会被移动到 **"Broken Bookmarks"** 文件夹中，而不是直接强制删除，防止误删。
4. **空文件夹清理**：优化输出结构，去除无用的空文件夹。

## 目录结构
```
bookmark-unifier/
├── input/       # [输入] 放置导出的书签文件 (.html)
├── out/         # [输出] 生成和清理后的书签文件
├── main.py      # 主程序入口
├── bookmark_manager.py  # 书签解析与写入模块
├── processor.py         # 核心处理逻辑 (去重、验证)
└── README.md    # 说明文档
```

## 安装与使用
本项目建议使用 `uv` 进行依赖管理，也可以使用 `pip`。

### 1. 环境准备

#### 使用 uv (推荐)
```bash
# 初始化项目 (如果尚未初始化)
uv init

# 添加依赖
uv add beautifulsoup4 lxml requests tqdm
```

#### 使用 pip
```bash
pip install beautifulsoup4 lxml requests
```

### 2. 运行程序
1. 将浏览器导出的书签文件 (例如 `bookmarks_10_9_23.html`) 放入 **`input`** 文件夹中。
2. 运行主程序：

```bash
# 使用 uv 运行
uv run main.py

# 或者直接 python 运行
python main.py
```

### 3. 查看结果
程序运行完成后，清理后的书签将生成在 **`out/result.html`**。
您可以直接将此文件导入回浏览器。

## 技术细节
- **HTML 解析**: 使用 `BeautifulSoup` 和 `lxml` 引擎，健壮地处理 Netscape 书签格式的各种怪癖（如嵌套不规范、标签未闭合等）。
- **并行验证**: 使用线程池 (`concurrent.futures`) 并发检测链接有效性，显著提高处理速度。
- **安全策略**: 对于网络超时或暂时无法访问的链接，采取“隔离”而非“删除”策略，确保数据安全。

## 开源协议
MIT License
