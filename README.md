# 书签合并优化工具 (Bookmark Unifier)

这是一个功能强大的 **Chromium 系列浏览器书签管理与优化工具**（适用于 Chrome, Edge, Brave, Arc 等），旨在帮助您从混乱的书签中解脱出来。它支持多设备书签的**自动合并**、**深度优化**、**智能去重**以及基于 AI 的**自动分类**。

## 主要功能

1.  **多来源自动合并**：
    *   支持将来自 Chrome、Edge 等不同浏览器的书签文件 (`.html`) 放入 `input` 文件夹，程序将自动把它们合并为一个完整的书签树。
2.  **结构深度优化**：
    *   自动清理空文件夹、扁平化冗余层级，优化书签树结构。
3.  **智能精准去重**：
    *   不仅比较 URL，还能处理相似链接，自动检测并删除重复的书签，保留最新或层级最合理的版本。
4.  **死链检测与分离**：
    *   **result.html**: 包含所有经过验证的有效书签。
    *   **broken.html**: 自动分离无法访问或 404 的死链，方便后续人工确认或清理。
5.  **智能网络访问**：
    *   **GeoIP 识别**: 自动识别目标网站 IP 归属地。
    *   **内网地址跳过**: 自动检测并跳过 IPv4 局域网/保留地址（如 192.168.x.x, 10.x.x.x, 127.0.0.1 等）的连通性检查，直接视为有效，避免因无法访问内网而误判为死链。
    *   **智能代理与重试**: 
        *   国内网站优先直连。
        *   国外/被墙网站自动走代理。
        *   **三级重试机制**: Direct HEAD -> Proxy HEAD -> Proxy GET，大幅提高死链检测的准确率，最大程度减少误判。
6.  **高性能处理**:
    *   **多线程并发**: 默认开启 10 线程并发验证，极速处理大量书签。
    *   **健壮解析**: 基于 `BeautifulSoup` + `lxml`，完美兼容 Netscape 书签格式的各类怪异嵌套和非标准标签。
7.  **AI 智能分类** (New!): 
    *   集成 LangGraph + OpenAI (LLM)，深度分析网页内容。
    *   将散乱的书签自动归类到逻辑清晰的文件夹结构中，实现真正的自动化整理。

## 目录结构
```
bookmark-unifier/
├── input/       # [输入] 放置导出的书签文件 (.html)
├── output/      # [输出] result.html (有效) 和 broken.html (失效)
├── .env         # [配置] API Key 和 代理配置
├── GeoLite2-Country.mmdb # [数据] GeoIP 数据库 (需手动下载)
├── main.py      # 主程序
└── ...
```

## 安装与配置

### 1. 环境准备
推荐使用 `uv` 进行依赖管理。

```bash
# 初始化环境并安装依赖
uv sync
```

### 2. 配置 GeoIP (必须)
为了区分国内外流量，您需要下载 MaxMind 的 GeoIP 数据库。

1.  **下载地址**: [https://github.com/P3TERX/GeoLite.mmdb/releases](https://github.com/P3TERX/GeoLite.mmdb/releases)
2.  **下载文件**: `GeoLite2-Country.mmdb`
3.  **放置位置**: 将文件放入项目根目录下的 `data/` 文件夹中（如果没有请创建）。
    > `data/GeoLite2-Country.mmdb`

### 3. 配置 .env (AI 功能必须)
复制配置文件模板并修改：

```bash
cp .env.example .env
```

在 `.env` 文件中填入您的配置：
```ini
# OpenAI 配置 (AI 分类功能需要)
OPENAI_API_KEY=sk-xxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o

# 代理配置 (可选，用于访问国外网站)
HTTP_PROXY=http://127.0.0.1:7890
HTTPS_PROXY=http://127.0.0.1:7890
```

### 4. 注意事项 (重要)
> [!IMPORTANT]
> **本脚本不支持 FakeIP 或 Tun 模式**
> 
> *   **FakeIP**: 会导致域名解析为虚拟 IP (如 198.18.x.x)，使 **GeoIP 无法正确识别** 目标网站地理位置，导致代理策略失效。
> *   **Tun 模式**: 可能导致 Python 网络请求库无法正确走代理或连接被重置。
> 
> 请务必使用 **系统代理 (System Proxy)** 模式，或直接在 `.env` 中配置 HTTP 端口代理。

## 运行程序

1.  将浏览器导出的书签 (`.html`) 放入 `input/` 文件夹。
2.  运行：
    ```bash
    uv run main.py
    ```
3.  程序将自动合并、去重并验证链接。
4.  验证完成后，程序会询问是否进行 **AI 智能分类**，输入 `y` 确认即可。

## 输出结果
*   `output/result.html`: 最终的干净书签文件，可直接导入浏览器。
*   `output/broken.html`: 失效链接列表。

## 技术栈
*   **Python 3.12+**
*   **LangGraph**: AI 工作流编排
*   **BeautifulSoup & lxml**: 高性能 HTML 解析
*   **Requests & PySocks**: 网络请求与代理支持
*   **GeoIP2**: IP 地理位置识别
