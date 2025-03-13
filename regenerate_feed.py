import os
from main import LatePostRSSGenerator

def regenerate_feed():
    """重新生成RSS Feed"""
    # 如果feed.xml不存在，直接返回
    if not os.path.exists('feed.xml'):
        print("feed.xml不存在，无法重新生成")
        return False
        
    # 获取当前目录下的所有文章
    articles_dir = "./latepost_articles"
    if not os.path.exists(articles_dir):
        print(f"文章目录 {articles_dir} 不存在")
        return False
        
    # 获取最新的文章ID
    existing_articles = [f for f in os.listdir(articles_dir) 
                        if f.endswith('.md') and f.startswith('latepost_article_')]
    
    if not existing_articles:
        print("未找到任何文章文件")
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
    
    # 初始化RSS生成器
    generator = LatePostRSSGenerator(articles_dir=articles_dir, last_id=last_id)
    
    # 备份原有的feed.xml
    if os.path.exists('feed.xml'):
        with open('feed.xml', 'r', encoding='utf-8') as f:
            original_content = f.read()
            
        # 如果生成失败，恢复原有内容
        try:
            generator.generate_rss(max_entries=20)
        except Exception as e:
            print(f"生成RSS时发生错误: {e}")
            with open('feed.xml', 'w', encoding='utf-8') as f:
                f.write(original_content)
            return False
    
    return True

if __name__ == "__main__":
    print("开始重新生成RSS Feed...")
    result = regenerate_feed()
    print(f"重新生成结果: {'成功' if result else '失败'}")
    return True

if __name__ == "__main__":
    regenerate_feed()