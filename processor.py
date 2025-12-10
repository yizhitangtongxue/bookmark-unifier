import concurrent.futures
import requests
from bookmark_manager import BookmarkManager

from tqdm import tqdm
import socket
import geoip2.database
import os

# 配置
GEOIP_DB_PATH = 'GeoLite2-Country.mmdb'
PROXY_URL = os.getenv('HTTP_PROXY') or "http://127.0.0.1:7890" # 默认代理地址，可修改

class Processor:
    """
    处理类
    负责书签的去重、链接有效性验证和合并。
    """
    def __init__(self):
        self.geoip_reader = None
        if os.path.exists(GEOIP_DB_PATH):
            try:
                self.geoip_reader = geoip2.database.Reader(GEOIP_DB_PATH)
                print(f"已加载 GeoIP 数据库: {GEOIP_DB_PATH}")
            except Exception as e:
                print(f"加载 GeoIP 数据库失败: {e}")
        else:
            print(f"未找到 GeoIP 数据库 ({GEOIP_DB_PATH})，将无法区分国内外流量 (默认直连/失败重试)。")
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

        # 分离有效和无效书签
        valid_bookmarks = [b for b in bookmarks if b['url'] in valid_urls]
        broken_bookmarks = []
        for b in bookmarks:
            if b['url'] in broken_urls:
                # 移动到 'Broken Bookmarks' 文件夹
                # 我们将其作为顶级文件夹 'Broken Bookmarks' 添加到路径前缀，
                # 或者保留原有层级结构
                b['path'] = ['Broken Bookmarks'] + b['path']
                broken_bookmarks.append(b)
            
        return valid_bookmarks, broken_bookmarks

    def _check_url(self, url):
        """
        检查单个 URL 的连通性。
        策略:
        1. 尝试解析域名 IP
        2. 若有 GeoIP DB:
           - IP 为 CN -> 直连
           - IP 非 CN -> 走代理
        3. 若无 GeoIP DB 或 解析失败:
           - 先尝试直连
           - 失败则尝试走代理
        """
        proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
        
        use_proxy = False
        
        # 1. GeoIP 判定
        if self.geoip_reader:
            try:
                hostname = url.split('/')[2]
                if ':' in hostname: # remove port
                    hostname = hostname.split(':')[0]
                
                ip = socket.gethostbyname(hostname)
                response = self.geoip_reader.country(ip)
                iso_code = response.country.iso_code
                
                if iso_code != 'CN':
                    use_proxy = True
                    # print(f"Foreign IP ({iso_code}): {url} -> Use Proxy")
            except Exception:
                # 解析失败，可能被墙，尝试走代理
                use_proxy = True
        
        # 2. 发起请求
        try:
            # 首次尝试
            req_proxies = proxies if use_proxy else None
            timeout = 10 if use_proxy else 5
            
            requests.head(url, timeout=timeout, proxies=req_proxies)
            return True
        except requests.RequestException:
            # 失败重试逻辑
            if not use_proxy:
                # 如果刚才没用代理失败了，尝试用代理再试一次 (兜底)
                try:
                    requests.head(url, timeout=10, proxies=proxies)
                    return True
                except requests.RequestException:
                    pass
            
            # 尝试 GET 方法兜底
            try:
                # 简单点：如果上面 HEAD 失败了，我们统一再试一次 GET (带代理，最大成功率)
                requests.get(url, timeout=10, stream=True, proxies=proxies)
                return True
            except requests.RequestException:
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
