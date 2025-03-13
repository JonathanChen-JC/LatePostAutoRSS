import time
import random
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

class LatePostScraper:
    def __init__(self, output_dir="./latepost_articles"):
        """初始化爬虫类"""
        self.output_dir = output_dir
        
        # 创建输出目录
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 设置Chrome选项
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')  # 无头模式
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        
        # 设置更真实的用户代理
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        self.chrome_options.add_argument(f'--user-agent={random.choice(user_agents)}')
        
        # 禁用webdriver检测
        self.chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 初始化WebDriver
        self.driver = None
    
    def start_driver(self):
        """启动WebDriver"""
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=self.chrome_options
        )
        
        # 设置窗口大小
        self.driver.set_window_size(1366, 768)
        
        # 添加额外的反检测措施
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    
    def close_driver(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def simulate_human_behavior(self):
        """模拟人类行为"""
        # 随机滚动页面
        for _ in range(random.randint(2, 4)):
            scroll_amount = random.randint(300, 700)
            self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            time.sleep(random.uniform(0.5, 1.5))
    
    def scrape_article(self, article_id):
        """爬取单篇文章"""
        url = f"https://www.latepost.com/news/dj_detail?id={article_id}"
        
        try:
            print(f"正在爬取文章 ID: {article_id}")
            
            # 访问页面
            self.driver.get(url)
            
            # 等待页面加载完成
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "article-body"))
            )
            
            # 模拟人类行为
            self.simulate_human_behavior()
            
            # 获取渲染后的HTML
            html = self.driver.page_source
            
            # 解析HTML
            soup = BeautifulSoup(html, 'html.parser')
            
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
            
            # 添加随机延迟，避免被检测
            time.sleep(random.uniform(2, 5))
            
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
        try:
            self.start_driver()
            
            results = {
                'success': [],
                'failed': []
            }
            
            for article_id in range(start_id, end_id + 1):
                # 爬取文章
                article_data = self.scrape_article(article_id)
                
                if article_data:
                    # 转换为Markdown
                    markdown_content = self.convert_to_markdown(article_data)
                    
                    # 保存Markdown文件
                    if self.save_markdown(article_id, markdown_content):
                        results['success'].append(article_id)
                    else:
                        results['failed'].append(article_id)
                else:
                    results['failed'].append(article_id)
            
            return results
            
        finally:
            self.close_driver()

def main():
    # 创建爬虫实例
    scraper = LatePostScraper(output_dir="./latepost_articles")
    
    # 设置要爬取的文章ID范围
    start_id = 2840
    end_id = 2844
    
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
