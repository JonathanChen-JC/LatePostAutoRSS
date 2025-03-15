import os
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
import re
from persistence import GitRepository

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('update_rss')

class RSSUpdater:
    """RSS更新器，用于更新feed.xml文件"""
    
    def __init__(self, feed_path='feed.xml', articles_dir='latepost_articles'):
        """初始化RSS更新器"""
        self.feed_path = feed_path
        self.articles_dir = articles_dir
        self.max_items = 50  # 最大保留文章数量
    
    def get_latest_article_id(self):
        """从feed.xml中获取最新文章ID"""
        try:
            if not os.path.exists(self.feed_path):
                logger.error(f"feed.xml文件不存在: {self.feed_path}")
                return None
            
            # 解析XML文件
            tree = ET.parse(self.feed_path)
            root = tree.getroot()
            
            # 查找所有链接
            links = root.findall('.//item/link')
            
            if not links:
                logger.warning("feed.xml中没有找到任何文章链接")
                return None
            
            # 提取所有文章ID并找出最大值
            article_ids = []
            for link in links:
                url = link.text
                # 使用正则表达式提取ID
                match = re.search(r'id=(\d+)', url)
                if match:
                    article_ids.append(int(match.group(1)))
            
            if not article_ids:
                logger.warning("未能从feed.xml中提取到任何文章ID")
                return None
            
            # 返回最大ID
            max_id = max(article_ids)
            logger.info(f"从feed.xml中获取到的最大文章ID: {max_id}")
            return max_id
            
        except Exception as e:
            logger.error(f"获取最新文章ID时出错: {str(e)}")
            return None
    
    def count_items(self, root):
        """计算feed.xml中的文章数量"""
        items = root.findall('.//item')
        return len(items)
    
    def update_feed(self, new_article_ids):
        """更新feed.xml，添加新文章"""
        try:
            if not os.path.exists(self.feed_path):
                logger.error(f"feed.xml文件不存在: {self.feed_path}")
                return False
            
            # 解析XML文件
            tree = ET.parse(self.feed_path)
            root = tree.getroot()
            channel = root.find('channel')
            
            # 更新lastBuildDate
            last_build_date = channel.find('lastBuildDate')
            now = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
            last_build_date.text = now
            
            # 添加新文章
            articles_added = 0
            for article_id in new_article_ids:
                article_path = os.path.join(self.articles_dir, f"latepost_article_{article_id}.md")
                
                if not os.path.exists(article_path):
                    logger.warning(f"文章文件不存在: {article_path}")
                    continue
                
                # 读取文章内容
                with open(article_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取标题、日期和作者
                title_match = re.search(r'# (.+)', content)
                date_match = re.search(r'\*\*发布日期\*\*: (.+)', content)
                author_match = re.search(r'\*\*作者\*\*: (.+)', content)
                
                if not title_match:
                    logger.warning(f"无法从文章中提取标题: {article_path}")
                    continue
                
                title = title_match.group(1).strip()
                publish_date = date_match.group(1).strip() if date_match else "未知日期"
                author = author_match.group(1).strip() if author_match else "未知作者"
                
                # 创建新的item元素
                item = ET.SubElement(channel, 'item')
                
                # 添加标题
                title_elem = ET.SubElement(item, 'title')
                title_elem.text = title
                
                # 添加链接
                link_elem = ET.SubElement(item, 'link')
                link_elem.text = f"https://www.latepost.com/news/dj_detail?id={article_id}"
                
                # 添加描述（HTML格式）
                desc_elem = ET.SubElement(item, 'description')
                
                # 创建HTML格式的描述
                html_content = self._create_html_description(content, title, publish_date, author)
                desc_elem.text = html_content
                
                # 添加发布日期
                pubdate_elem = ET.SubElement(item, 'pubDate')
                try:
                    # 尝试解析中文日期格式并转换为RSS标准格式
                    date_parts = publish_date.split(' ')
                    if len(date_parts) >= 2:
                        date_str = date_parts[0].replace('月', '/').replace('日', '')
                        time_str = date_parts[1]
                        dt = datetime.strptime(f"{date_str} {time_str}", "%m/%d %H:%M")
                        # 使用当前年份
                        current_year = datetime.now().year
                        dt = dt.replace(year=current_year)
                        pubdate_elem.text = dt.strftime('%a, %d %b %Y %H:%M:%S +0000')
                    else:
                        pubdate_elem.text = now  # 使用当前时间作为后备
                except Exception as e:
                    logger.warning(f"日期解析失败: {str(e)}，使用当前时间")
                    pubdate_elem.text = now
                
                # 添加GUID
                guid_elem = ET.SubElement(item, 'guid')
                guid_elem.text = f"https://www.latepost.com/news/dj_detail?id={article_id}"
                
                articles_added += 1
                logger.info(f"已添加文章: {title} (ID: {article_id})")
            
            # 检查文章总数，如果超过最大数量，删除最旧的文章
            items = channel.findall('item')
            if len(items) > self.max_items:
                # 按发布日期排序
                items_with_dates = []
                for item in items:
                    pubdate = item.find('pubDate')
                    if pubdate is not None and pubdate.text:
                        try:
                            dt = datetime.strptime(pubdate.text, '%a, %d %b %Y %H:%M:%S +0000')
                            items_with_dates.append((dt, item))
                        except Exception:
                            # 如果日期解析失败，假设是最新的文章
                            items_with_dates.append((datetime.now(), item))
                    else:
                        # 如果没有日期，假设是最新的文章
                        items_with_dates.append((datetime.now(), item))
                
                # 按日期排序
                items_with_dates.sort(key=lambda x: x[0])
                
                # 删除最旧的文章
                items_to_remove = len(items) - self.max_items
                for _, item in items_with_dates[:items_to_remove]:
                    title_elem = item.find('title')
                    title_text = title_elem.text if title_elem is not None else "未知标题"
                    logger.info(f"删除旧文章: {title_text}")
                    channel.remove(item)
            
            # 保存更新后的feed.xml
            tree.write(self.feed_path, encoding='utf-8', xml_declaration=True)
            logger.info(f"成功更新feed.xml，添加了{articles_added}篇新文章")
            
            # 同步到Git仓库
            self._sync_to_git_repository()
            
            return True
            
        except Exception as e:
            logger.error(f"更新feed.xml时出错: {str(e)}")
            return False
    
    def _create_html_description(self, markdown_content, title, publish_date, author):
        """从Markdown内容创建HTML描述"""
        # 创建基本的HTML结构
        html = f"""
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
                        <span>作者：{author}</span>
                        <span>发布日期：{publish_date}</span>
                    </div>
                    <div class='article-content'>
                """
        
        # 提取正文内容（跳过标题和元信息）
        content_lines = markdown_content.split('\n')
        content_start = False
        processed_content = []
        
        for line in content_lines:
            if line.strip() == '---':
                content_start = True
                continue
            
            if content_start:
                # 处理Markdown格式转HTML
                # 处理标题
                if line.startswith('# '):
                    processed_line = f"<h1>{line[2:]}</h1>"
                elif line.startswith('## '):
                    processed_line = f"<h2>{line[3:]}</h2>"
                # 处理引用
                elif line.startswith('> '):
                    processed_line = f"<blockquote>{line[2:]}</blockquote>"
                # 处理图片
                elif line.startswith('!['):
                    img_parts = line.split('](', 1)
                    if len(img_parts) > 1:
                        img_url = img_parts[1].rstrip(')')
                        processed_line = f"<img src=\"{img_url}\" alt=\"图片\">"
                    else:
                        processed_line = f"<p>{line}</p>"
                # 处理普通段落
                elif line.strip():
                    processed_line = f"<p>{line}</p>"
                else:
                    processed_line = ""
                
                processed_content.append(processed_line)
        
        html += '\n'.join(processed_content)
        html += "\n                    </div>\n                </div>"
        
        return html
    
    def _sync_to_git_repository(self):
        """将更新后的feed.xml同步到Git仓库"""
        try:
            git_repo = GitRepository()
            if git_repo.push_feed_to_repository(self.feed_path):
                logger.info("成功将feed.xml同步到Git仓库")
                return True
            else:
                logger.error("同步feed.xml到Git仓库失败")
                return False
        except Exception as e:
            logger.error(f"同步到Git仓库时出错: {str(e)}")
            return False

# 如果直接运行此脚本
if __name__ == "__main__":
    # 创建RSS更新器
    updater = RSSUpdater()
    
    # 获取最新文章ID
    latest_id = updater.get_latest_article_id()
    if latest_id:
        print(f"当前feed.xml中的最新文章ID: {latest_id}")
    else:
        print("无法获取最新文章ID")