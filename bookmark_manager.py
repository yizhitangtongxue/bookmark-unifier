from bs4 import BeautifulSoup
import sys

class BookmarkManager:
    """
    书签管理器类
    负责解析 Netscape 格式的书签文件及生成新的书签文件。
    """
    def parse_file(self, file_path):
        """
        解析 Netscape 书签格式的 HTML 文件。
        返回一个字典列表，每个字典包含: {'url', 'title', 'add_date', 'icon', 'path'}
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # 如果 UTF-8 失败，尝试忽略错误读取
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

        # 使用 lxml 解析器以获得更好的健壮性 (html.parser 可能会有嵌套问题)
        soup = BeautifulSoup(content, 'lxml')
        bookmarks = []
        
        # 开始遍历
        # Netscape 文件通常包含一个根 DL 标签
        root_dl = soup.find('dl')
        if not root_dl:
            print(f"[{file_path}] 未找到根 DL 标签。")
            return []

        # print(f"[{file_path}] HTML 解析成功。找到根 DL 标签。")
        self._traverse(root_dl, [], bookmarks)
        return bookmarks

    def _traverse(self, element, current_path, bookmarks):
        """
        递归遍历 DOM 树以提取书签。
        处理 Netscape 格式的怪癖，如未闭合的标签和嵌套结构。
        """
        # 获取所有子节点用于遍历
        nodes_to_visit = list(element.children)
        
        while nodes_to_visit:
            node = nodes_to_visit.pop(0)
            
            if not node.name:
                continue
                
            if node.name == 'p':
                # 解包 P 标签：Netscape 格式中有时会将列表包含在 P 标签中
                # 将 P 标签的子节点加回到遍历队列的前端
                p_children = list(node.children)
                nodes_to_visit = p_children + nodes_to_visit
                continue

            if node.name == 'dt':
                # 检查是否为文件夹 (包含 H3)
                # 使用 recursive=False 防止找到嵌套 DT 中的 H3
                h3 = node.find('h3', recursive=False)
                if h3:
                    folder_name = h3.get_text(strip=True)
                    new_path = current_path + [folder_name]
                    # print(f"Found Folder: {folder_name}")
                    
                    # 查找文件夹内容的 DL 标签
                    # 1. 尝试直接子节点
                    next_dl = node.find('dl', recursive=False)
                    # 2. 尝试兄弟节点
                    if not next_dl:
                        next_dl = node.find_next_sibling('dl')
                    
                    # 3. 处理嵌套 DT 情况 (例如 OuterDT -> A -> InnerDT -> H3)
                    # 这种情况下，DL 往往是 OuterDT 的兄弟节点，而不是 InnerDT 的兄弟。
                    if not next_dl:
                        parent = node.parent
                        while parent and parent.name == 'dt':
                            # 检查父级 DT 的兄弟 DL
                            sibling_dl = parent.find_next_sibling('dl')
                            if sibling_dl:
                                next_dl = sibling_dl
                                break
                            parent = parent.parent

                    if next_dl:
                        self._traverse(next_dl, new_path, bookmarks)
                    # else:
                    #     # Empty folder, no DL tag found. This is common for empty folders.
                    #     pass
                else:
                    # 检查是否为书签链接 (包含 A 标签)
                    # 使用 recursive=False 避免找到后续嵌套结构中的 A 标签 (尽管 parse 逻辑应该处理了)
                    a = node.find('a', recursive=False)
                    if a:
                        url = a.get('href')
                        title = a.get_text(strip=True)
                        add_date = a.get('add_date')
                        icon = a.get('icon')
                        
                        # print(f"Found Bookmark: {title} ({url})")
                        if url:
                            bookmarks.append({
                                'url': url,
                                'title': title,
                                'add_date': add_date,
                                'icon': icon,
                                'path': current_path
                            })

                # 关键修复：lxml 经常将未闭合的 DT 标签解析为嵌套结构
                # 而不是兄弟节点。我们需要处理当前 DT 的子节点，
                # 以便找到那些本应是兄弟节点的内容。
                dt_children = list(node.children)
                nodes_to_visit = dt_children + nodes_to_visit

    def write_file(self, bookmarks, file_path):
        """
        将书签列表写入 Netscape 格式的 HTML 文件。
        bookmarks: 书签字典列表
        """
        # 构建树状结构：
        # node = {'name': 'root', 'children': { '文件夹名': node }, 'items': [bookmarks]}
        root = {'name': 'root', 'children': {}, 'items': []}

        for b in bookmarks:
            current = root
            for folder in b['path']:
                if folder not in current['children']:
                    current['children'][folder] = {'name': folder, 'children': {}, 'items': []}
                current = current['children'][folder]
            current['items'].append(b)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('<!DOCTYPE NETSCAPE-Bookmark-file-1>\n')
            f.write('<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">\n')
            f.write('<TITLE>Bookmarks</TITLE>\n')
            f.write('<H1>Bookmarks</H1>\n')
            f.write('<DL><p>\n')
            self._write_node(f, root, 0)
            f.write('</DL><p>\n')

    def _write_node(self, f, node, level):
        indent = '    ' * level
        # 写入书签项
        for item in node['items']:
            f.write(f'{indent}<DT><A HREF="{item["url"]}" ADD_DATE="{item["add_date"]}" ICON="{item["icon"]}">{item["title"]}</A>\n')
        
        # 写入文件夹
        for folder_name, folder_node in node['children'].items():
            f.write(f'{indent}<DT><H3>{folder_name}</H3>\n')
            f.write(f'{indent}<DL><p>\n')
            self._write_node(f, folder_node, level + 1)
            f.write(f'{indent}</DL><p>\n')
