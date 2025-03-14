import os
import time
import logging
import threading
from datetime import datetime
from flask import Flask, send_from_directory
from simple_scraper import SimpleLatePostScraper
from update_rss import RSSUpdater
from feed_initializer import initialize_feed
from persistence import GitRepository
from health_check import setup_health_check

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('main')

# 创建Flask应用
app = Flask(__name__)

# 设置健康检查
health_checker = setup_health_check(app)

# 全局变量
RSS_UPDATE_INTERVAL = 3600  # 1小时更新一次
ARTICLES_DIR = 'latepost_articles'
FEED_PATH = 'feed.xml'

def check_and_update_rss():
    """检查并更新RSS"""
    try:
        # 初始化RSS更新器和爬虫
        rss_updater = RSSUpdater(feed_path=FEED_PATH, articles_dir=ARTICLES_DIR)
        scraper = SimpleLatePostScraper(output_dir=ARTICLES_DIR)
        git_repo = GitRepository()
        
        # 获取最新文章ID
        latest_id = rss_updater.get_latest_article_id()
        if not latest_id:
            logger.error("无法获取最新文章ID，跳过本次更新")
            return
        
        latest_id = int(latest_id)
        logger.info(f"当前最新文章ID: {latest_id}")
        
        # 尝试爬取新文章（最新ID后的10篇）
        start_id = latest_id + 1
        end_id = latest_id + 10
        
        logger.info(f"开始爬取新文章，ID范围: {start_id} - {end_id}")
        results = scraper.scrape_articles_range(start_id, end_id)
        
        # 如果有新文章，更新RSS
        if results['success']:
            logger.info(f"成功爬取{len(results['success'])}篇新文章")
            
            # 更新RSS
            if rss_updater.update_feed(results['success']):
                logger.info("RSS更新成功")
                
                # 推送到Git仓库
                if git_repo.push_feed_to_repository(FEED_PATH):
                    logger.info("成功推送RSS到Git仓库")
                else:
                    logger.error("推送RSS到Git仓库失败")
            else:
                logger.error("RSS更新失败")
        else:
            logger.info("没有发现新文章")
    
    except Exception as e:
        logger.error(f"RSS更新过程出错: {str(e)}")

def rss_update_worker():
    """RSS更新工作线程"""
    while True:
        try:
            logger.info("开始RSS更新检查")
            check_and_update_rss()
            logger.info(f"RSS更新检查完成，等待{RSS_UPDATE_INTERVAL}秒后再次检查")
        except Exception as e:
            logger.error(f"RSS更新工作线程出错: {str(e)}")
        
        # 等待下一次更新
        time.sleep(RSS_UPDATE_INTERVAL)

@app.route('/')
def index():
    """首页"""
    return f"<h1>晚点LatePost RSS自动更新服务</h1><p>最后更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"

@app.route('/feed.xml')
def serve_rss():
    """提供RSS feed文件"""
    return send_from_directory('.', 'feed.xml')

def main():
    """主函数"""
    try:
        # 初始化feed.xml
        logger.info("开始初始化feed.xml")
        if initialize_feed():
            logger.info("feed.xml初始化成功")
        else:
            logger.error("feed.xml初始化失败")
        
        # 启动RSS更新线程
        logger.info("启动RSS更新线程")
        rss_thread = threading.Thread(target=rss_update_worker)
        rss_thread.daemon = True
        rss_thread.start()
        
        # 启动Flask应用
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"启动Web服务，端口: {port}")
        app.run(host='0.0.0.0', port=port)
    
    except Exception as e:
        logger.error(f"主程序出错: {str(e)}")

if __name__ == "__main__":
    main()