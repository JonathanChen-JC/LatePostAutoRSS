import os
import time
import schedule
from datetime import datetime
from flask import Flask, send_file
from latepost_scraper import LatePostScraper
from feedgen.feed import FeedGenerator
from persistence import initialize_persistence, save_after_update
from health_check import setup_health_check

app = Flask(__name__)

@app.route('/')
def home():
    return '晚点LatePost RSS Feed 服务正在运行'

@app.route('/feed.xml')
def feed():
    return send_file('feed.xml', mimetype='application/rss+xml')

class LatePostRSSGenerator:
    def __init__(self, articles_dir="./latepost_articles", last_id=2844):
        """初始化RSS生成器"""
        self.articles_dir = articles_dir
        self.last_id = last_id
        self.scraper = LatePostScraper(output_dir=articles_dir)
        
    def generate_rss(self, output_file="feed.xml", max_entries=20):
        """生成RSS文件
        
        Args:
            output_file: 输出的RSS文件名
            max_entries: RSS中包含的最大文章数量，默认为20
        """
        fg = FeedGenerator()
        fg.title('晚点LatePost')
        fg.description('晚点LatePost的文章更新')
        fg.link(href='https://www.latepost.com')
        fg.language('zh-CN')
        
        # 获取所有markdown文件
        markdown_files = [f for f in os.listdir(self.articles_dir) 
                        if f.endswith('.md') and f.startswith('latepost_article_')]
        
        # 按照文章ID排序并限制数量
        sorted_files = sorted(markdown_files, reverse=True)
        # 只处理最新的max_entries篇文章
        for md_file in sorted_files[:max_entries]:
            try:
                with open(os.path.join(self.articles_dir, md_file), 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析markdown内容
                lines = content.split('\n')
                title = lines[0].replace('# ', '')
                
                # 提取元信息
                meta_info = {}
                for line in lines[2:5]:
                    if line.startswith('- **'):
                        key, value = line.replace('- **', '').split('**: ')
                        meta_info[key] = value
                
                # 创建RSS条目
                fe = fg.add_entry()
                fe.title(title)
                fe.link(href=meta_info.get('原文链接', ''))
                # 将Markdown内容转换为美观的HTML
                html_content = f"""
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
                        <span>作者：{meta_info.get('作者', '未知作者')}</span>
                        <span>发布日期：{meta_info.get('发布日期', '未知日期')}</span>
                    </div>
                    <div class='article-content'>
                """

                # 处理文章内容
                for line in lines[5:]:  # 跳过标题和元信息
                    if line.startswith('# '):
                        html_content += f"<h1>{line[2:]}</h1>\n"
                    elif line.startswith('## '):
                        html_content += f"<h2>{line[3:]}</h2>\n"
                    elif line.startswith('> '):
                        html_content += f"<blockquote>{line[2:]}</blockquote>\n"
                    elif line.startswith('!['):
                        # 处理图片
                        img_parts = line.split('](')  # 分割Markdown图片语法
                        if len(img_parts) == 2:
                            img_url = img_parts[1].rstrip(')')
                            html_content += f"<img src=\"{img_url}\" alt=\"图片\"/>\n"
                    elif line.strip():
                        html_content += f"<p>{line}</p>\n"

                html_content += "</div></div>"
                fe.description(html_content)
                # 添加完整的HTML内容
                # fe.content.content(html_content, type="html") # 这行有问题，注释掉
                if '发布日期' in meta_info:
                    try:
                        # 解析中文日期格式
                        date_str = meta_info['发布日期']
                        try:
                            # 导入需要的模块
                            from datetime import timezone, timedelta
                            
                            # 处理相对日期格式
                            from datetime import timezone, timedelta
                            current_date = datetime.now()
                            
                            # 处理"今天"和"昨天"格式
                            if date_str.startswith('今天'):
                                time_part = date_str.replace('今天', '').strip()
                                hour, minute = map(int, time_part.split(':'))
                                date_obj = current_date.replace(hour=hour, minute=minute)
                            elif date_str.startswith('昨天'):
                                time_part = date_str.replace('昨天', '').strip()
                                hour, minute = map(int, time_part.split(':'))
                                date_obj = (current_date - timedelta(days=1)).replace(hour=hour, minute=minute)
                            else:
                                # 原有的月日格式处理
                                date_obj = datetime.strptime(date_str, '%m月%d日 %H:%M')
                                # 添加当前年份
                                date_obj = date_obj.replace(year=current_date.year)
                            
                            # 添加UTC时区
                            date_with_timezone = date_obj.replace(tzinfo=timezone.utc)
                            fe.published(date_with_timezone)
                        except Exception as e:
                            print(f"日期解析错误: {date_str}, {str(e)}")
                            fe.published(datetime.now().replace(tzinfo=timezone.utc))
                    except:
                        fe.published(datetime.now())
                if '作者' in meta_info:
                    fe.author({'name': meta_info['作者']})
            except Exception as e:
                print(f"处理文件 {md_file} 时出错: {str(e)}")
        
        # 生成RSS文件
        fg.rss_file(output_file, pretty=True)
        print(f"RSS文件已生成: {output_file}")
    
    def check_new_articles(self):
        """检查并爬取新文章"""
        try:
            print(f"\n开始检查新文章，当前最新ID: {self.last_id}")
            
            # 尝试获取下一篇文章
            next_id = self.last_id + 1
            self.scraper.start_driver()
            
            # 爬取文章
            article_data = self.scraper.scrape_article(next_id)
            
            if article_data:
                # 转换为markdown并保存
                markdown_content = self.scraper.convert_to_markdown(article_data)
                if self.scraper.save_markdown(next_id, markdown_content):
                    print(f"成功爬取新文章，ID: {next_id}")
                    self.last_id = next_id
                    
                    # 更新RSS
                    self.generate_rss()
                    return True
            
            print(f"未发现新文章，ID: {next_id}")
            return False
            
        except Exception as e:
            print(f"检查新文章时出错: {str(e)}")
            return False
        finally:
            self.scraper.close_driver()

def job():
    """定时任务"""
    # 使用update_rss.py中的函数，它使用SimpleLatePostScraper
    from update_rss import update_rss_with_simple_scraper
    update_rss_with_simple_scraper()

def main():
    # 初始化持久化存储
    print("正在初始化持久化存储...")
    persistence = initialize_persistence()
    
    # 设置定时任务
    schedule.every(1).hours.do(job)
    
    # 初始化RSS生成器并生成初始RSS
    if persistence:
        last_id = persistence.get_latest_article_id()
        if last_id:
            rss_generator = LatePostRSSGenerator(last_id=last_id)
        else:
            rss_generator = LatePostRSSGenerator()
    else:
        rss_generator = LatePostRSSGenerator()
    
    rss_generator.generate_rss()
    
    print("服务已启动，将每1小时检查一次更新...")
    
    # 启动Flask应用和定时任务
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # 设置健康检查
    service_url = os.environ.get('SERVICE_URL')
    if service_url:
        print(f"设置健康检查，服务URL: {service_url}")
        setup_health_check(app, check_interval=300)
    else:
        print("未设置SERVICE_URL环境变量，健康检查将使用本地URL")
        setup_health_check(app, check_interval=300)
    
    # 启动Flask应用
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

def run_scheduler():
    """运行定时任务"""
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()