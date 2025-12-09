import concurrent.futures
import requests
from bookmark_manager import BookmarkManager

from tqdm import tqdm

class Processor:
    """
    处理类
    负责书签的去重、链接有效性验证和合并。
    """
    def __init__(self):
        self.seen_urls = set()

    def deduplicate(self, bookmarks):
        """
        去除重复的书签。
        保留第一次出现的书签。
        """
        unique_bookmarks = []
        for b in bookmarks:
            if b['url'] not in self.seen_urls:
                self.seen_urls.add(b['url'])
                unique_bookmarks.append(b)
        return unique_bookmarks

    def validate_links(self, bookmarks, max_workers=10):
        """
        验证链接是否可访问。
        将不可访问的链接移动到 "Broken Bookmarks" (失效书签) 文件夹。
        使用线程池进行并行检查。
        """
        # 我们只检查唯一的 URL 以节省时间
        # 为了显示书签名称，我们需要构建一个 url -> title 的映射 (取第一个遇到的标题)
        url_map = {b['url']: b['title'] for b in bookmarks}
        urls_to_check = list(url_map.keys())
        
        valid_urls = set()
        broken_urls = set()

        print(f"正在验证 {len(urls_to_check)} 个唯一链接...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self._check_url, url): url for url in urls_to_check}
            
            # 使用 tqdm 显示进度条
            # unit="link" 表示单位
            # dynamic_ncols=True 自动调整宽度
            with tqdm(total=len(urls_to_check), unit="link", dynamic_ncols=True) as pbar:
                for future in concurrent.futures.as_completed(future_to_url):
                    url = future_to_url[future]
                    title = url_map.get(url, "Unknown")
                    
                    # 更新进度条描述，显示当前正在处理(完成)的书签标题
                    # 截断过长的标题以保持界面整洁
                    display_title = (title[:20] + '..') if len(title) > 20 else title
                    pbar.set_description(f"处理: {display_title}")
                    
                    try:
                        is_valid = future.result()
                    except Exception as e:
                        is_valid = False
                    
                    if is_valid:
                        valid_urls.add(url)
                    else:
                        broken_urls.add(url)
                        # 这里可以使用 pbar.write 来输出，避免打乱进度条
                        # pbar.write(f"失效链接: {title} ({url})")

                    pbar.update(1)

        print(f"\n验证完成。发现 {len(broken_urls)} 个失效链接。")

        # 更新书签
        processed_bookmarks = []
        for b in bookmarks:
            if b['url'] in broken_urls:
                # 移动到 'Broken Bookmarks' 文件夹
                # 我们将其作为顶级文件夹 'Broken Bookmarks' 添加到路径前缀，
                # 或者保留原有层级结构
                b['path'] = ['Broken Bookmarks'] + b['path']
            processed_bookmarks.append(b)
            
        return processed_bookmarks

    def _check_url(self, url):
        """
        检查单个 URL 的连通性。
        先尝试 HEAD 请求，如果失败则尝试 GET 请求。
        """
        try:
            # 先尝试 HEAD 请求 (更轻量)
            response = requests.head(url, timeout=5, allow_redirects=True)
            if response.status_code < 400:
                return True
            # 有些服务器认为 HEAD 请求是恶意的或不支持，尝试 GET 请求
            response = requests.get(url, timeout=5, stream=True)
            if response.status_code < 400:
                response.close() # 只需要状态码，不需要内容，立即关闭
                return True
            return False
        except:
            return False

    def merge_bookmarks(self, file_paths):
        """
        合并多个文件的书签。
        """
        manager = BookmarkManager()
        all_bookmarks = []
        
        for fp in file_paths:
            print(f"正在处理 {fp}...")
            bookmarks = manager.parse_file(fp)
            print(f"  -> 包含 {len(bookmarks)} 个书签")
            all_bookmarks.extend(bookmarks)
            
        return all_bookmarks
