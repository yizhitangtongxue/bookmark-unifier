import concurrent.futures
import requests
from bookmark_manager import BookmarkManager

from tqdm import tqdm
import socket
import ipaddress
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
        
        # 尝试查找不同的数据库文件名
        # 优先查找 data 目录
        possible_paths = [
            os.path.join('data', 'GeoLite2-Country.mmdb'),
            os.path.join('data', 'Country.mmdb'),
            os.path.join('data', 'country.mmdb'),
            'GeoLite2-Country.mmdb', 
            'Country.mmdb', 
            'country.mmdb'
        ]
        db_path = None
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if db_path:
            try:
                self.geoip_reader = geoip2.database.Reader(db_path)
                print(f"已加载 GeoIP 数据库: {db_path}")
            except Exception as e:
                print(f"加载 GeoIP 数据库失败: {e}")
        else:
            print(f"未找到 GeoIP 数据库 (尝试查找: {possible_db_names})，将无法区分国内外流量 (默认直连/失败重试)。")
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
                        is_valid, status_code, used_proxy = future.result()
                    except Exception as e:
                        is_valid = False
                        status_code = "ERR"
                        used_proxy = False
                    
                    if is_valid:
                        valid_urls.add(url)
                    else:
                        broken_urls.add(url)
                    
                    # 打印状态
                    proxy_str = "代理" if used_proxy else "直连"
                    # status_code 可能是 int 或 str ("ERR")
                    status_str = str(status_code)
                    
                    # 按要求记录输出
                    pbar.write(f"[{status_str:<3}] [{proxy_str:<2}] {display_title} -> {url}")

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
        返回: (is_valid, status_code, used_proxy)
        """
        proxies = {
            'http': PROXY_URL,
            'https': PROXY_URL
        }
        
        use_proxy = False
        
        # 1. 解析 IP 并检查本地地址 / GeoIP
        ip = None
        hostname = None
        try:
            hostname = url.split('/')[2]
            if ':' in hostname: # 移除端口
                hostname = hostname.split(':')[0]
            
            # 解析 IP
            ip = socket.gethostbyname(hostname)
            
            # 检查私有 / 环回 IP
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private or ip_obj.is_loopback:
                    # 跳过本地 IP，视为有效以避免超时
                    return True, "跳过", False
            except ValueError:
                pass
                
        except Exception:
            # DNS 解析失败
            # 稍后使用 requests 验证 (可能会使用代理)
            pass

        if self.geoip_reader and ip:
            try:
                response = self.geoip_reader.country(ip)
                iso_code = response.country.iso_code
                if iso_code != 'CN':
                    use_proxy = True
            except geoip2.errors.AddressNotFoundError:
                 # 私有 IP 或未找到
                 pass
            except Exception:
                 use_proxy = True
        
        # 2. 发起请求
        try:
            # 首次尝试
            req_proxies = proxies if use_proxy else None
            timeout = 10 if use_proxy else 5
            
            resp = requests.head(url, timeout=timeout, proxies=req_proxies)
            return True, resp.status_code, use_proxy
        except requests.RequestException:
            # 失败重试逻辑
            if not use_proxy:
                # 如果刚才没用代理失败了，尝试用代理再试一次 (兜底)
                try:
                    resp = requests.head(url, timeout=10, proxies=proxies)
                    return True, resp.status_code, True
                except requests.RequestException:
                    pass
            
            # 尝试 GET 方法兜底
            try:
                # 统一再试一次 GET (带代理，最大成功率)
                resp = requests.get(url, timeout=10, stream=True, proxies=proxies)
                resp.close()
                return True, resp.status_code, True # If GET succeeds, it used proxy
            except requests.RequestException as e:
                # 尽可能获取异常代码，或者仅返回 0
                return False, 0, use_proxy

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
