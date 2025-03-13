from simple_scraper import SimpleLatePostScraper
from main import LatePostRSSGenerator
import os
from persistence import initialize_persistence, save_after_update

def update_rss_with_simple_scraper():
    # 初始化持久化存储
    persistence = initialize_persistence()
    
    # 获取当前已有的最新文章ID
    articles_dir = "./latepost_articles"
    
    # 如果使用持久化存储，直接从持久化存储获取最新ID
    if persistence:
        last_id = persistence.get_latest_article_id()
        if last_id is None:
            return False
    else:
        # 如果没有持久化存储，使用原来的方法获取最新ID
        existing_articles = [f for f in os.listdir(articles_dir) 
                            if f.endswith('.md') and f.startswith('latepost_article_')]
        
        if not existing_articles:
            print("未找到现有文章，无法确定最新ID")
            return False
        
        # 提取文章ID并找出最大值
        article_ids = []
        for article_file in existing_articles:
            try:
                article_id = int(article_file.replace('latepost_article_', '').replace('.md', ''))
                article_ids.append(article_id)
            except ValueError:
                continue
        
        if not article_ids:
            print("无法从文件名中提取有效的文章ID")
            return False
        
        last_id = max(article_ids)
        print(f"当前最新文章ID: {last_id}")
    
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

if __name__ == "__main__":
    print("开始检查并更新RSS...")
    result = update_rss_with_simple_scraper()
    print(f"更新结果: {'成功' if result else '未发现新文章'}")