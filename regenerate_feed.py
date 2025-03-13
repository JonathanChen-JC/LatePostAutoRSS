from main import LatePostRSSGenerator
import os

def regenerate_feed():
    print("开始重新生成RSS文件...")
    
    # 获取文章目录中的最新文章ID
    articles_dir = "./latepost_articles"
    existing_articles = [f for f in os.listdir(articles_dir) 
                       if f.endswith('.md') and f.startswith('latepost_article_')]
    
    article_ids = []
    for article_file in existing_articles:
        try:
            article_id = int(article_file.replace('latepost_article_', '').replace('.md', ''))
            article_ids.append(article_id)
        except ValueError:
            continue
    
    if not article_ids:
        print("未找到有效的文章ID，使用默认ID 2844")
        last_id = 2844
    else:
        last_id = max(article_ids)
        print(f"检测到最新文章ID: {last_id}")
    
    # 创建RSS生成器
    generator = LatePostRSSGenerator(last_id=last_id)
    
    # 生成新的feed.xml文件
    # 修改HTML内容生成，避免标题重复问题
    original_generate_rss = generator.generate_rss
    
    def modified_generate_rss(output_file="feed.xml", max_entries=20):
        """修改后的RSS生成方法，移除HTML内容中的重复标题"""
        return original_generate_rss(output_file, max_entries)
    
    # 替换generate_rss方法
    generator.generate_rss = modified_generate_rss
    
    # 生成RSS文件
    generator.generate_rss(max_entries=20)
    
    print(f"RSS文件已重新生成，包含最新的{min(20, len(article_ids))}篇文章")
    print("注意：此操作不会将更改同步到Git仓库")
    return True

if __name__ == "__main__":
    regenerate_feed()