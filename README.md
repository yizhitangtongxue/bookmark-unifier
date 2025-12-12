# 书签合并优化工具 (Bookmark Unifier)

这是一个功能强大的浏览器书签整理工具，支持去重、死链检测、智能代理访问以及 **AI 自动分类**。

## 主要功能

1.  **自动合并**：将 `input` 文件夹下的所有 HTML 书签文件合并为一个。
2.  **智能去重**：自动检测并删除重复的网址。
3.  **死链分离**：
    *   **result.html**: 包含所有有效书签。
    *   **broken.html**: 包含所有访问失败的书签，方便后续人工排查。
4.  **智能网络访问**：
    *   **GeoIP 识别**: 自动识别 IP 归属地。
    *   **智能代理**: 国内网站直连，国外/被墙网站自动走代理，大幅提高验证成功率。
5.  **AI 智能分类** (New!): 集成 LangGraph + OpenAI，分析网页内容并将书签自动归类到最合适的文件夹。

## 目录结构
```
bookmark-unifier/
├── input/       # [输入] 放置导出的书签文件 (.html)
├── out/         # [输出] result.html (有效) 和 broken.html (失效)
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

## 运行程序

1.  将浏览器导出的书签 (`.html`) 放入 `input/` 文件夹。
2.  运行：
    ```bash
    uv run main.py
    ```
3.  程序将自动合并、去重并验证链接。
4.  验证完成后，程序会询问是否进行 **AI 智能分类**，输入 `y` 确认即可。

## 输出结果
*   `out/result.html`: 最终的干净书签文件，可直接导入浏览器。
*   `out/broken.html`: 失效链接列表。

## 技术栈
*   **Python 3.12+**
*   **LangGraph**: AI 工作流编排
*   **BeautifulSoup & lxml**: 高性能 HTML 解析
*   **Requests & PySocks**: 网络请求与代理支持
*   **GeoIP2**: IP 地理位置识别
