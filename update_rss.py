import os
import re
import logging
from datetime import datetime
import xml.etree.ElementTree as ET
from feedgen.feed import FeedGenerator
import html

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('update_rss')

class RSSUpdater:
    """RSS更新器，用于从Markdown文件生成RSS条目并更新feed.xml"""
    
    def __init__(self, feed_path='feed.xml', articles_dir='latepost_articles'):
        """初始化RSS更新器"""
        self.feed_path = feed_path
        self.articles_dir = articles_dir
        self.base_url = 'https://www.latepost.com'
    
    def _parse_markdown(self, file_path):
        """解析Markdown文件，提取文章信息"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取标题
            title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
            title = title_match.group(1) if title_match else "未知标题"
            
            # 提取发布日期
            date_match = re.search(r'\*\*发布日期\*\*: (.+)', content)
            date_str = date_match.group(1) if date_match else "未知日期"
            
            # 提取作者
            author_match = re.search(r'\*\*作者\*\*: (.+)', content)
            author = author_match.group(1) if author_match else "未知作者"
            
            # 提取原文链接
            link_match = re.search(r'\*\*原文链接\*\*: (.+)', content)
            link = link_match.group(1) if link_match else ""
            
            # 提取文章ID
            article_id = None
            if link:
                id_match = re.search(r'id=(\d+)', link)
                article_id = id_match.group(1) if id_match else None
            
            # 提取正文内容（分隔线后的所有内容）
            content_match = re.split(r'---\s*\n', content, 1)
            article_content = content_match[1] if len(content_match) > 1 else ""
            
            return {
                'title': title,
                'date': date_str,
                'author': author,
                'link': link,
                'id': article_id,
                'content': article_content
            }
        
        except Exception as e:
            logger.error(f"解析Markdown文件出错: {file_path}, 错误: {str(e)}")
            return None
    
    def _convert_date_to_rfc822(self, date_str):
        """将日期字符串转换为RFC822格式"""
        try:
            # 处理常见的日期格式，如：03月08日 21:03
            match = re.search(r'(\d{2})月(\d{2})日\s+(\d{2}):(\d{2})', date_str)
            if match:
                month, day, hour, minute = match.groups()
                # 假设年份是当前年份
                year = datetime.now().year
                # 创建datetime对象
                dt = datetime(year, int(month), int(day), int(hour), int(minute))
                # 转换为RFC822格式
                return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
            else:
                # 尝试解析其他可能的日期格式
                try:
                    # 尝试直接解析RFC822格式
                    dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                    return date_str  # 已经是正确格式，直接返回
                except ValueError:
                    # 如果无法解析，返回当前时间
                    logger.warning(f"无法解析日期格式: {date_str}，使用当前时间")
                    return datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        except Exception as e:
            logger.error(f"日期转换出错: {date_str}, 错误: {str(e)}")
            return datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
    
    def _markdown_to_html(self, markdown_content):
        """将Markdown内容转换为HTML"""
        # 这里使用简单的转换规则，实际项目中可以使用专门的Markdown解析库
        # 检查输入是否为字典类型，如果是，则提取content字段
        if isinstance(markdown_content, dict):
            content = markdown_content.get('content', '')
        else:
            content = markdown_content
            
        html_content = content
        
        # 转换段落
        html_content = re.sub(r'^([^\n#>!].+)$', r'<p>\1</p>', html_content, flags=re.MULTILINE)
        
        # 转换标题
        html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
        
        # 转换引用
        html_content = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html_content, flags=re.MULTILINE)
        
        # 转换图片
        html_content = re.sub(r'!\[(.*)\]\((.+)\)', r'<img src="\2" alt="\1">', html_content)
        
        # 转换链接
        html_content = re.sub(r'\[(.+)\]\((.+)\)', r'<a href="\2">\1</a>', html_content)
        
        # 转换粗体
        html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)
        
        # 转换斜体
        html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)
        
        # 添加样式
        styled_html = f"""
                <style>
                    .article-container {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; max-width: 800px; margin: 0 auto; line-height: 1.8; padding: 20px; background: #fff; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border-radius: 8px; }}
                    .article-meta {{ color: #666; font-size: 14px; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 1px solid #eee; display: flex; flex-wrap: wrap; gap: 16px; }}
                    .article-meta span {{ display: inline-flex; align-items: center; }}
                    .article-meta span::before {{ content: ''; display: inline-block; width: 4px; height: 4px; background: #666; border-radius: 50%; margin-right: 8px; }}
                    .article-content {{ font-size: 16px; color: #2c3e50; }}
                    .article-content p {{ margin-bottom: 20px; line-height: 1.8; }}
                    .article-content img {{ max-width: 100%; height: auto; margin: 24px 0; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
                    .article-content blockquote {{ background: #f8f9fa; border-left: 4px solid #4a90e2; margin: 20px 0; padding: 20px; font-style: italic; border-radius: 0 8px 8px 0; }}
                    .article-content h1 {{ font-size: 24px; margin: 32px 0 16px; color: #2c3e50; }}
                    .article-content h2 {{ font-size: 20px; margin: 28px 0 14px; color: #2c3e50; }}
                </style>
                <div class='article-container'>
                    <div class='article-meta'>
                        <span>作者：{html.escape(markdown_content.get('author', '未知作者'))}</span>
                        <span>发布日期：{html.escape(markdown_content.get('date', '未知日期'))}</span>
                    </div>
                    <div class='article-content'>
                {html_content}
                    </div>
                </div>
        """
        
        return styled_html
    
    def get_latest_article_id(self):
        """从feed.xml中获取最新文章的ID"""
        try:
            if not os.path.exists(self.feed_path):
                logger.warning(f"feed.xml不存在: {self.feed_path}")
                return None
            
            # 解析XML
            tree = ET.parse(self.feed_path)
            root = tree.getroot()
            
            # 查找所有item元素
            items = root.findall('./channel/item')
            if not items:
                logger.warning("feed.xml中没有找到item元素")
                return None
            
            # 存储所有文章ID
            article_ids = []
            
            # 遍历所有item，提取ID
            for item in items:
                link_elem = item.find('link')
                if link_elem is not None and link_elem.text:
                    link = link_elem.text
                    id_match = re.search(r'id=(\d+)', link)
                    if id_match:
                        article_ids.append(int(id_match.group(1)))
            
            if not article_ids:
                logger.warning("未找到有效的文章ID")
                return None
            
            # 获取最大的ID作为最新文章ID
            latest_id = str(max(article_ids))
            logger.info(f"最新文章ID: {latest_id}")
            return latest_id
        
        except Exception as e:
            logger.error(f"获取最新文章ID出错: {str(e)}")
            return None
    
    def update_feed(self, new_article_ids):
        """更新feed.xml，添加新文章，并保留最新的50篇文章"""
        try:
            # 存储所有文章条目（新文章和现有文章）
            all_entries = []
            existing_article_ids = set()
            
            # 如果feed.xml已存在，先读取现有条目
            if os.path.exists(self.feed_path):
                try:
                    tree = ET.parse(self.feed_path)
                    root = tree.getroot()
                    
                    for item in root.findall('./channel/item'):
                        title_elem = item.find('title')
                        link_elem = item.find('link')
                        desc_elem = item.find('description')
                        pubdate_elem = item.find('pubDate')
                        
                        if all([title_elem, link_elem, desc_elem, pubdate_elem]):
                            # 提取文章ID
                            link = link_elem.text
                            id_match = re.search(r'id=(\d+)', link)
                            article_id = id_match.group(1) if id_match else None
                            
                            # 保存所有现有条目，无论是否在新文章列表中
                            if article_id:  # 确保文章ID有效
                                existing_article_ids.add(article_id)
                                try:
                                    date_obj = datetime.strptime(pubdate_elem.text, '%a, %d %b %Y %H:%M:%S %z') if pubdate_elem.text else datetime.now()
                                    all_entries.append({
                                        'title': title_elem.text,
                                        'link': link_elem.text,
                                        'description': desc_elem.text,
                                        'pubDate': pubdate_elem.text,
                                        'id': article_id,
                                        'date_obj': date_obj
                                    })
                                    logger.info(f"从现有feed.xml中读取文章: ID={article_id}, 标题={title_elem.text}")
                                except Exception as date_error:
                                    logger.warning(f"解析文章日期出错: {str(date_error)}，使用当前时间")
                                    # 使用当前时间作为备选
                                    current_time = datetime.now()
                                    rfc822_time = current_time.strftime('%a, %d %b %Y %H:%M:%S +0000')
                                    all_entries.append({
                                        'title': title_elem.text,
                                        'link': link_elem.text,
                                        'description': desc_elem.text,
                                        'pubDate': rfc822_time,
                                        'id': article_id,
                                        'date_obj': current_time
                                    })
                                    logger.info(f"从现有feed.xml中读取文章(使用当前时间): ID={article_id}, 标题={title_elem.text}")
                    
                    logger.info(f"从现有feed.xml中读取了{len(all_entries)}篇文章")
                except Exception as e:
                    logger.error(f"解析现有feed.xml出错: {str(e)}，将创建新的feed.xml")
                    # 即使解析出错，也不要放弃之前的文章，尝试读取文章文件夹中的文章
            
            # 添加新文章
            new_added_count = 0
            for article_id in new_article_ids:
                # 检查是否已存在该文章（避免重复添加）
                if article_id in existing_article_ids:
                    logger.info(f"文章ID={article_id}已存在，跳过添加")
                    continue
                    
                article_file = os.path.join(self.articles_dir, f"latepost_article_{article_id}.md")
                if not os.path.exists(article_file):
                    logger.warning(f"文章文件不存在: {article_file}")
                    continue
                
                # 解析文章
                article_data = self._parse_markdown(article_file)
                if not article_data:
                    logger.warning(f"无法解析文章: {article_file}")
                    continue
                
                # 转换日期字符串为RFC822格式
                pub_date = self._convert_date_to_rfc822(article_data['date'])
                
                # 转换Markdown为HTML
                html_content = self._markdown_to_html(article_data)
                
                # 添加到所有条目列表
                all_entries.append({
                    'title': article_data['title'],
                    'link': article_data['link'],
                    'description': html_content,
                    'pubDate': pub_date,
                    'id': article_id,
                    'date_obj': datetime.strptime(pub_date, '%a, %d %b %Y %H:%M:%S %z') if pub_date else datetime.now()
                })
                new_added_count += 1
                logger.info(f"添加新文章: ID={article_id}, 标题={article_data['title']}")
            
            # 按发布日期排序（最新的在前）
            all_entries.sort(key=lambda x: x['date_obj'], reverse=True)
            
            # 只保留最新的50篇文章
            latest_entries = all_entries[:50]
            
            # 创建新的FeedGenerator
            fg = FeedGenerator()
            fg.title('晚点LatePost')
            fg.link(href=self.base_url)
            fg.description('晚点LatePost的文章更新')
            fg.language('zh-CN')
            
            # 设置lastBuildDate为当前时间
            current_time = datetime.now()
            fg.lastBuildDate(current_time)
            
            # 将排序后的条目添加到feed
            for entry in latest_entries:
                fe = fg.add_entry()
                fe.title(entry['title'])
                fe.link(href=entry['link'])
                fe.description(entry['description'])
                fe.pubDate(entry['pubDate'])
            
            # 生成feed.xml
            fg.rss_file(self.feed_path, pretty=True)
            logger.info(f"feed.xml已更新，共包含{len(latest_entries)}篇文章，其中新增{new_added_count}篇")
            return True
        
        except Exception as e:
            logger.error(f"更新feed.xml出错: {str(e)}")
            return False