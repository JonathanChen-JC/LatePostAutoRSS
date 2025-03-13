import requests
from bs4 import BeautifulSoup
import os
import time
import random
from datetime import datetime

class SimpleLatePostScraper:
    def __init__(self, output_dir="./latepost_articles"):
        """初始化爬虫类"""
        self.output_dir = output_dir
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 设置更真实的用户代理
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
    
    def get_headers(self):
        """获取随机请求头"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    def scrape_article(self, article_id):
        """爬取单篇文章"""
        url = f"https://www.latepost.com/news/dj_detail?id={article_id}"
        
        try:
            print(f"正在爬取文章 ID: {article_id}")
            
            # 添加随机延迟，模拟人类行为
            time.sleep(random.uniform(1, 3))
            
            # 发送请求
            response = requests.get(url, headers=self.get_headers(), timeout=15)
            
            # 检查响应状态
            if response.status_code != 200:
                print(f"请求失败，状态码: {response.status_code}，ID: {article_id}")
                return None
            
            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 提取文章标题
            title_element = soup.select_one('.article-header-title')
            if not title_element:
                print(f"警告: 无法找到文章标题，ID: {article_id}")
                return None
            
            title = title_element.text.strip()
            
            # 提取文章发布日期
            date_element = soup.select_one('.article-header-date')
            publish_date = date_element.text.strip() if date_element else "未知日期"
            
            # 提取作者信息
            author_elements = soup.select('.article-header-author .author-link .cursor')
            authors = [author.text.strip() for author in author_elements if author.text.strip()]
            author_info = "、".join(authors) if authors else "未知作者"
            
            # 提取文章正文
            article_body = soup.select_one('.article-body.ql-editor')
            if not article_body:
                print(f"警告: 无法找到文章正文，ID: {article_id}")
                return None
            
            # 提取所有段落和图片
            content_elements = []
            
            for element in article_body.find_all(['p', 'img', 'blockquote']):
                if element.name == 'p':
                    text = element.text.strip()
                    if text:  # 只添加非空段落
                        content_elements.append(('text', text))
                elif element.name == 'img':
                    img_src = element.get('src', '')
                    if img_src:
                        content_elements.append(('image', img_src))
                elif element.name == 'blockquote':
                    quote_text = element.text.strip()
                    if quote_text:
                        content_elements.append(('quote', quote_text))
            
            return {
                'id': article_id,
                'title': title,
                'date': publish_date,
                'author': author_info,
                'content_elements': content_elements,
                'url': url
            }
            
        except Exception as e:
            print(f"爬取文章出错，ID: {article_id}, 错误: {str(e)}")
            return None
    
    def convert_to_markdown(self, article_data):
        """将文章数据转换为Markdown格式"""
        if not article_data:
            return None
        
        markdown_content = []
        
        # 添加标题
        markdown_content.append(f"# {article_data['title']}\n")
        
        # 添加元信息
        markdown_content.append(f"- **发布日期**: {article_data['date']}")
        markdown_content.append(f"- **作者**: {article_data['author']}")
        markdown_content.append(f"- **原文链接**: {article_data['url']}\n")
        
        # 添加分隔线
        markdown_content.append("---\n")
        
        # 添加正文内容
        for element_type, content in article_data['content_elements']:
            if element_type == 'text':
                # 处理普通段落
                markdown_content.append(f"{content}\n")
            elif element_type == 'image':
                # 处理图片
                markdown_content.append(f"![图片]({content})\n")
            elif element_type == 'quote':
                # 处理引用
                markdown_content.append(f"> {content}\n")
        
        return "\n".join(markdown_content)
    
    def save_markdown(self, article_id, markdown_content):
        """保存Markdown内容到文件"""
        if not markdown_content:
            return False
        
        filename = os.path.join(self.output_dir, f"latepost_article_{article_id}.md")
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            print(f"文章已保存: {filename}")
            return True
        except Exception as e:
            print(f"保存文章出错，ID: {article_id}, 错误: {str(e)}")
            return False
    
    def scrape_articles_range(self, start_id, end_id):
        """爬取指定范围内的所有文章"""
        results = {
            'success': [],
            'failed': []
        }
        
        for article_id in range(start_id, end_id + 1):
            # 爬取文章
            article_data = self.scrape_article(article_id)
            
            if article_data:
                # 转换为markdown
                markdown_content = self.convert_to_markdown(article_data)
                
                # 保存文章
                if self.save_markdown(article_id, markdown_content):
                    results['success'].append(article_id)
                else:
                    results['failed'].append(article_id)
            else:
                results['failed'].append(article_id)
            
            # 添加随机延迟，避免被检测
            time.sleep(random.uniform(2, 5))
        
        return results

def main():
    # 创建爬虫实例
    scraper = SimpleLatePostScraper(output_dir="./latepost_articles")
    
    # 设置要爬取的文章ID范围
    start_id = 2845  # 从2844之后的文章开始爬取
    end_id = 2850    # 尝试爬取几篇最新文章
    
    print(f"开始爬取晚点LatePost文章，ID范围: {start_id} - {end_id}")
    
    # 爬取文章
    results = scraper.scrape_articles_range(start_id, end_id)
    
    # 打印结果
    print("\n爬取结果汇总:")
    print(f"成功爬取: {len(results['success'])} 篇文章")
    if results['success']:
        print(f"成功的文章ID: {', '.join(map(str, results['success']))}")
    
    print(f"爬取失败: {len(results['failed'])} 篇文章")
    if results['failed']:
        print(f"失败的文章ID: {', '.join(map(str, results['failed']))}")
    
    print(f"\n所有文章已保存到目录: {os.path.abspath(scraper.output_dir)}")

if __name__ == "__main__":
    main()