import os
import requests
from bs4 import BeautifulSoup
from typing import TypedDict, List
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END

# Load environment variables
load_dotenv()

# Define the state for a single bookmark categorization
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
            print("Warning: OPENAI_API_KEY not set. AI categorization will be skipped.")
            self.llm = None
        else:
            self.llm = ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=model_name,
                temperature=0
            )

        self.workflow = self._build_workflow()
        
    def _fetch_content(self, state: BookmarkState) -> BookmarkState:
        """Fetch title and meta description from the URL."""
        url = state['url']
        try:
            # Use a proper User-Agent
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; BookmarkUnifier/1.0)'}
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding
            
            if response.status_code >= 400:
                return {**state, "content": "", "error": f"HTTP {response.status_code}"}
                
            soup = BeautifulSoup(response.text, 'lxml')
            title = soup.title.string.strip() if soup.title else ""
            
            # Get meta description
            desc = ""
            meta_desc = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if meta_desc:
                desc = meta_desc.get('content', '').strip()
            
            # Simple content summary
            content_summary = f"Title: {title}\nDescription: {desc}"
            return {**state, "content": content_summary}
            
        except Exception as e:
             return {**state, "content": "", "error": str(e)}

    def _classify(self, state: BookmarkState) -> BookmarkState:
        """Ask LLM to classify the bookmark based on content."""
        if not self.llm or not state['content']:
            return state # Skip if no LLM or no content
            
        current_path = " > ".join(state['current_category'])
        
        prompt = f"""You are a bookmark organizer.
Current Folder Path: {current_path}
URL: {state['url']}
Page Content:
{state['content']}

Task:
Determine the best folder category for this bookmark.
- If the current category is good, output "KEEP".
- If it belongs in a specific subfolder (e.g. "Programming > Python"), output the full path using " > " separator.
- If it's a general/root bookmark, output "ROOT".
- If broken/unknown, output "KEEP".

Output ONLY the category path string or "KEEP". Do not output markdown or explanations.
"""
        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])
            result = response.content.strip()
            
            if result == "KEEP":
                 # No change
                 return state
            
            # Parse new category
            new_path = [p.strip() for p in result.split(">")]
            return {**state, "new_category": new_path}
            
        except Exception as e:
            return {**state, "error": f"LLM Error: {str(e)}"}

    def _build_workflow(self):
        """Build the LangGraph workflow."""
        workflow = StateGraph(BookmarkState)
        
        workflow.add_node("fetch_content", self._fetch_content)
        workflow.add_node("classify", self._classify)
        
        workflow.set_entry_point("fetch_content")
        workflow.add_edge("fetch_content", "classify")
        workflow.add_edge("classify", END)
        
        return workflow.compile()

    def categorize(self, bookmark):
        """Run the workflow for a single bookmark."""
        if not self.llm:
            return bookmark['path']
            
        initial_state = {
            "url": bookmark['url'],
            "current_category": bookmark['path'],
            "content": "",
            "new_category": [], # Empty means keep current
            "error": ""
        }
        
        print(f"AI Analyzing: {bookmark['url']}")
        result = self.workflow.invoke(initial_state)
        
        if result.get('new_category'):
            print(f"  -> Suggestion: {result['new_category']}")
            return result['new_category']
        elif result.get('error'):
             print(f"  -> Error: {result['error']}")
             
        return bookmark['path']
