from simple_scraper import SimpleLatePostScraper
from main import LatePostRSSGenerator
import os
from persistence import initialize_persistence, save_after_update

def update_rss_with_simple_scraper():
    # 初始化持久化存储
    persistence = initialize_persistence()
    
    # 获取当前已有的最新文章ID
    articles_dir = "./latepost_articles"
    
    # 确保文章目录存在
    if not os.path.exists(articles_dir):
        print(f"创建文章目录: {articles_dir}")
        os.makedirs(articles_dir)
    
    # 获取最新文章ID，优先从持久化存储获取
    last_id = None
    if persistence:
        last_id = persistence.get_latest_article_id()
    
    # 如果无法从持久化存储获取，尝试从文件名获取
    if last_id is None:
        existing_articles = [f for f in os.listdir(articles_dir) 
                            if f.endswith('.md') and f.startswith('latepost_article_')]
        
        if existing_articles:
            article_ids = []
            for article_file in existing_articles:
                try:
                    article_id = int(article_file.replace('latepost_article_', '').replace('.md', ''))
                    article_ids.append(article_id)
                except ValueError:
                    continue
            
            if article_ids:
                last_id = max(article_ids)
                print(f"从文件名中获取到最新文章ID: {last_id}")
    
    # 如果仍然无法获取最新ID，但需要确保feed.xml不为空
    if last_id is None:
        if persistence:
            print("未找到现有文章，但需要确保feed.xml不为空")
            persistence._ensure_feed_not_empty()
        return False
    
    # 创建爬虫实例
    scraper = SimpleLatePostScraper(output_dir=articles_dir)
    
    # 尝试爬取下一篇文章
    next_id = last_id + 1
    print(f"尝试爬取ID为 {next_id} 的文章...")
    
    article_data = scraper.scrape_article(next_id)
    
    if article_data:
        # 转换为markdown并保存
        markdown_content = scraper.convert_to_markdown(article_data)
        if scraper.save_markdown(next_id, markdown_content):
            print(f"成功爬取新文章，ID: {next_id}")
            
            # 更新RSS
            print("正在更新RSS文件...")
            rss_generator = LatePostRSSGenerator(articles_dir=articles_dir, last_id=next_id)
            rss_generator.generate_rss()
            print("RSS文件更新完成")
            
            # 将更改保存到Git仓库
            if persistence:
                print("正在将更改保存到Git仓库...")
                save_after_update(persistence, next_id)
                print("Git仓库更新完成")
            
            return True
    
    print(f"未发现新文章，ID: {next_id}")
    return False

def update_rss():
    """提供一个简单的接口用于重新生成RSS"""
    # 初始化持久化存储
    persistence = initialize_persistence()
    
    # 获取最新文章ID
    articles_dir = "./latepost_articles"
    last_id = None
    
    # 首先检查文章目录是否存在
    if not os.path.exists(articles_dir):
        print(f"创建文章目录: {articles_dir}")
        os.makedirs(articles_dir)
    
    # 优先从持久化存储获取最新ID
    if persistence:
        last_id = persistence.get_latest_article_id()
    
    # 如果从持久化存储获取失败，尝试从文件名获取
    if last_id is None:
        existing_articles = [f for f in os.listdir(articles_dir) 
                            if f.endswith('.md') and f.startswith('latepost_article_')]
        
        if existing_articles:
            article_ids = []
            for article_file in existing_articles:
                try:
                    article_id = int(article_file.replace('latepost_article_', '').replace('.md', ''))
                    article_ids.append(article_id)
                except ValueError:
                    continue
            
            if article_ids:
                last_id = max(article_ids)
                print(f"从文件名中获取到最新文章ID: {last_id}")
    
    # 如果有文章，生成RSS
    if last_id:
        print(f"使用最新文章ID {last_id} 生成RSS")
        rss_generator = LatePostRSSGenerator(articles_dir=articles_dir, last_id=last_id)
        rss_generator.generate_rss()
        print("RSS文件更新完成")
        return True
    else:
        # 如果没有文章但已有feed.xml，保持现有内容
        if os.path.exists('feed.xml'):
            print("未找到文章，但已存在feed.xml，保持现有内容")
            return True
        # 如果没有文章且没有feed.xml，创建基本结构
        elif persistence:
            print("未找到文章，创建基本的RSS结构")
            persistence._ensure_feed_not_empty()
            return True
        return False

if __name__ == "__main__":
    print("开始检查并更新RSS...")
    result = update_rss_with_simple_scraper()
    print(f"更新结果: {'成功' if result else '未发现新文章'}")