import os
import requests
from bs4 import BeautifulSoup
from typing import TypedDict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# 加载环境变量
load_dotenv()

# 定义单个书签分类的状态
class BookmarkState(TypedDict):
    url: str
    content: str
    current_category: List[str]
    new_category: List[str]
    error: str

class AICategorizer:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")
        model_name = os.getenv("OPENAI_MODEL_NAME") or "gpt-3.5-turbo"
        
        if not api_key:
            print("警告: 未设置 OPENAI_API_KEY。AI 分类将被跳过。")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model_name,
                temperature=0
            )

        self.workflow = self._build_workflow()
        
        # 加载 prompt 模板
        try:
            with open(os.path.join("prompt", "categorize.txt"), "r", encoding="utf-8") as f:
                self.prompt_template = f.read()
        except Exception as e:
            print(f"加载Prompt模板失败: {e}")
            self.prompt_template = ""
        
    def _fetch_content(self, state: BookmarkState) -> BookmarkState:
        """从 URL 获取标题和元描述。"""
        url = state['url']
        try:
            # 使用合适的 User-Agent
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; BookmarkUnifier/1.0)'}
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding
            
            if response.status_code >= 400:
                return {**state, "content": "", "error": f"HTTP {response.status_code}"}
                
            soup = BeautifulSoup(response.text, 'lxml')
            title = soup.title.string.strip() if soup.title else ""
            
            # 获取元描述
            desc = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc:
                desc = meta_desc.get('content', '').strip()
            
            # 简单的内容摘要
            content_summary = f"Title: {title}\nDescription: {desc}"
            return {**state, "content": content_summary}
            
        except Exception as e:
             return {**state, "content": "", "error": str(e)}

    def _classify(self, state: BookmarkState) -> BookmarkState:
        """要求 LLM 根据内容对书签进行分类。"""
        if not self.llm or not state['content']:
            return state # 如果没有 LLM 或内容则跳过
            
        current_path = " > ".join(state['current_category'])
        
        if not self.prompt_template:
            return state
            
        prompt = self.prompt_template.format(
            current_path=current_path,
            url=state['url'],
            content=state['content']
        )

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            result = response.content.strip()
            
            if result == "KEEP":
                 # 无变化
                 return state
            
            # 解析新分类
            new_path = [p.strip() for p in result.split(">")]
            return {**state, "new_category": new_path}
            
        except Exception as e:
            return {**state, "error": f"LLM 错误: {str(e)}"}

    def _build_workflow(self):
        """构建 LangGraph 工作流。"""
        workflow = StateGraph(BookmarkState)
        
        workflow.add_node("fetch_content", self._fetch_content)
        workflow.add_node("classify", self._classify)
        
        workflow.set_entry_point("fetch_content")
        workflow.add_edge("fetch_content", "classify")
        workflow.add_edge("classify", END)
        
        return workflow.compile()

    def categorize(self, bookmark):
        """对单个书签运行工作流。"""
        if not self.llm:
            return bookmark['path']
            
        initial_state = {
            "url": bookmark['url'],
            "current_category": bookmark['path'],
            "content": "",
            "new_category": [], # 空表示保持当前
            "error": ""
        }
        
        print(f"AI 正在分析: {bookmark['url']}")
        result = self.workflow.invoke(initial_state)
        
        if result.get('new_category'):
            print(f"  -> 建议: {result['new_category']}")
            return result['new_category']
        elif result.get('error'):
             print(f"  -> 错误: {result['error']}")
             
        return bookmark['path']
