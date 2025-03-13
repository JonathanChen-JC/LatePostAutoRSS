import os
from main import LatePostRSSGenerator
from persistence import GitPersistence, initialize_persistence
from datetime import datetime

def regenerate_feed():
    """重新生成RSS Feed
    确保在任何情况下都能生成有效的非空RSS文件
    """
    print("开始重新生成RSS Feed...")
    
    # 先检查是否有项目自带的feed.xml
    project_feed_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'feed.xml')
    if os.path.exists(project_feed_path):
        with open(project_feed_path, 'r', encoding='utf-8') as f:
            project_feed_content = f.read().strip()
        if project_feed_content and '<?xml version=' in project_feed_content and '<rss' in project_feed_content and '</rss>' in project_feed_content:
            print(f"使用项目自带的feed.xml作为初始RSS结构")
            with open("feed.xml", 'w', encoding='utf-8') as f:
                f.write(project_feed_content)
    
    # 初始化持久化存储
    persistence = initialize_persistence()
    if not persistence:
        persistence = GitPersistence()
    
    # 获取当前目录下的所有文章
    articles_dir = "./latepost_articles"
    if not os.path.exists(articles_dir):
        print(f"文章目录 {articles_dir} 不存在，创建目录")
        os.makedirs(articles_dir)
        
    # 获取最新的文章ID
    existing_articles = [f for f in os.listdir(articles_dir) 
                        if f.endswith('.md') and f.startswith('latepost_article_')]
    
    if not existing_articles:
        print("未找到任何文章文件，将创建基本的非空RSS结构")
        # 如果项目自带的feed.xml不可用，则使用持久化存储的方法
        if persistence:
            persistence._ensure_feed_not_empty()
            return True
        else:
            # 如果没有持久化存储，创建基本结构
            try:
                timestamp = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
                basic_feed = f'''<?xml version='1.0' encoding='UTF-8'?>
<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
  <channel>
    <title>晚点LatePost</title>
    <link>https://www.latepost.com</link>
    <description>晚点LatePost的文章更新</description>
    <docs>http://www.rssboard.org/rss-specification</docs>
    <generator>python-feedgen</generator>
    <language>zh-CN</language>
    <lastBuildDate>{timestamp}</lastBuildDate>
  </channel>
</rss>'''
                with open("feed.xml", 'w', encoding='utf-8') as f:
                    f.write(basic_feed)
                print("已创建基本的非空RSS feed结构")
                return True
            except Exception as e:
                print(f"创建基本feed结构时出错: {str(e)}")
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
        print("无法从文件名中提取有效的文章ID，将创建基本的非空RSS结构")
        if persistence:
            persistence._ensure_feed_not_empty()
            return True
        else:
            # 如果没有持久化存储，手动创建基本结构
            try:
                timestamp = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
                basic_feed = f'''<?xml version='1.0' encoding='UTF-8'?>
<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
  <channel>
    <title>晚点LatePost</title>
    <link>https://www.latepost.com</link>
    <description>晚点LatePost的文章更新</description>
    <docs>http://www.rssboard.org/rss-specification</docs>
    <generator>python-feedgen</generator>
    <language>zh-CN</language>
    <lastBuildDate>{timestamp}</lastBuildDate>
  </channel>
</rss>'''
                with open("feed.xml", 'w', encoding='utf-8') as f:
                    f.write(basic_feed)
                print("已创建基本的非空RSS feed结构")
                return True
            except Exception as e:
                print(f"创建基本feed结构时出错: {str(e)}")
                return False
        
    last_id = max(article_ids)
    print(f"找到最新文章ID: {last_id}")
    
    # 初始化RSS生成器
    generator = LatePostRSSGenerator(articles_dir=articles_dir, last_id=last_id)
    
    try:
        # 生成新的RSS Feed
        generator.generate_rss(max_entries=20)
        print("RSS Feed生成成功")
        
        # 验证生成的feed.xml是否有效
        if os.path.exists("feed.xml"):
            with open("feed.xml", 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content and '<?xml version=' in content and '<rss' in content and '</rss>' in content:
                print("生成的feed.xml有效")
                return True
            else:
                print("生成的feed.xml无效，将创建基本的RSS结构")
                if persistence:
                    persistence._ensure_feed_not_empty()
                    return True
        
        # 如果验证失败或文件不存在，创建基本结构
        if persistence:
            persistence._ensure_feed_not_empty()
            return True
        else:
            # 如果没有持久化存储，手动创建基本结构
            timestamp = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
            basic_feed = f'''<?xml version='1.0' encoding='UTF-8'?>
<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
  <channel>
    <title>晚点LatePost</title>
    <link>https://www.latepost.com</link>
    <description>晚点LatePost的文章更新</description>
    <docs>http://www.rssboard.org/rss-specification</docs>
    <generator>python-feedgen</generator>
    <language>zh-CN</language>
    <lastBuildDate>{timestamp}</lastBuildDate>
  </channel>
</rss>'''
            with open("feed.xml", 'w', encoding='utf-8') as f:
                f.write(basic_feed)
            print("已创建基本的非空RSS feed结构")
            return True
    except Exception as e:
        print(f"生成RSS时发生错误: {e}")
        # 出错时确保feed.xml不为空
        if persistence:
            persistence._ensure_feed_not_empty()
            return True
        else:
            # 如果没有持久化存储，手动创建基本结构
            try:
                timestamp = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000")
                basic_feed = f'''<?xml version='1.0' encoding='UTF-8'?>
<rss xmlns:atom="http://www.w3.org/2005/Atom" xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">
  <channel>
    <title>晚点LatePost</title>
    <link>https://www.latepost.com</link>
    <description>晚点LatePost的文章更新</description>
    <docs>http://www.rssboard.org/rss-specification</docs>
    <generator>python-feedgen</generator>
    <language>zh-CN</language>
    <lastBuildDate>{timestamp}</lastBuildDate>
  </channel>
</rss>'''
                with open("feed.xml", 'w', encoding='utf-8') as f:
                    f.write(basic_feed)
                print("已创建基本的非空RSS feed结构")
                return True
            except Exception as e:
                print(f"创建基本feed结构时出错: {str(e)}")
                return False

if __name__ == "__main__":
    print("开始重新生成RSS Feed...")
    result = regenerate_feed()
    print(f"重新生成结果: {'成功' if result else '失败'}")
    return True

if __name__ == "__main__":
    regenerate_feed()