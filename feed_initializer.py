import os
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from persistence import GitRepository, compare_feed_dates

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('feed_initializer')

class FeedInitializer:
    """RSS初始化器，用于初始化feed.xml文件"""
    
    def __init__(self, feed_path='feed.xml'):
        """初始化RSS初始化器"""
        self.feed_path = feed_path
        self.git_repo = GitRepository()
    
    def initialize_feed(self):
        """初始化feed.xml文件，比较本地和远程仓库中的时间戳，选择较新的作为初始文件"""
        logger.info("开始初始化feed.xml文件")
        
        # 检查本地feed.xml是否存在
        if not os.path.exists(self.feed_path):
            logger.warning(f"本地feed.xml不存在: {self.feed_path}")
            # 尝试从远程仓库获取
            remote_feed_content = self.git_repo.get_remote_feed()
            if remote_feed_content:
                logger.info("从远程仓库获取feed.xml成功")
                with open(self.feed_path, 'w', encoding='utf-8') as f:
                    f.write(remote_feed_content)
                return True
            else:
                logger.error("无法获取feed.xml，初始化失败")
                return False
        
        # 从远程仓库获取feed.xml
        remote_feed_content = self.git_repo.get_remote_feed()
        if not remote_feed_content:
            logger.warning("无法从远程仓库获取feed.xml，使用本地版本")
            return True
        
        # 比较本地和远程feed.xml的lastBuildDate
        source, content = compare_feed_dates(self.feed_path, remote_feed_content)
        
        # 如果远程版本更新，则使用远程版本
        if source == 'remote' and content:
            logger.info("使用远程仓库中的feed.xml")
            with open(self.feed_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            logger.info("使用本地feed.xml")
        
        return True

def initialize_feed():
    """初始化feed.xml文件的便捷函数"""
    initializer = FeedInitializer()
    return initializer.initialize_feed()

if __name__ == "__main__":
    initialize_feed()