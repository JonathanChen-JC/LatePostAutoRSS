import os
import subprocess
import tempfile
import shutil
from datetime import datetime
import xml.etree.ElementTree as ET
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('persistence')

class GitRepository:
    """Git仓库操作类，用于克隆、拉取和推送RSS文件"""
    
    def __init__(self):
        """初始化Git仓库操作类"""
        self.repo_url = os.environ.get('GIT_REPO_URL')
        self.username = os.environ.get('GIT_USERNAME')
        self.email = os.environ.get('GIT_EMAIL')
        self.token = os.environ.get('GIT_TOKEN')
        
        if not all([self.repo_url, self.username, self.email, self.token]):
            logger.warning("Git环境变量未完全设置，可能无法进行Git操作")
        
        # 创建带认证的仓库URL
        if self.repo_url and self.token and self.username:
            # 替换https://协议为带token的URL
            if self.repo_url.startswith('https://'):
                self.auth_repo_url = self.repo_url.replace(
                    'https://', 
                    f'https://{self.username}:{self.token}@'
                )
            else:
                self.auth_repo_url = self.repo_url
        else:
            self.auth_repo_url = None
    
    def _run_git_command(self, command, cwd=None):
        """运行Git命令"""
        try:
            result = subprocess.run(
                command,
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            logger.error(f"Git命令执行失败: {e.stderr}")
            return None
    
    def clone_repository(self):
        """克隆仓库到临时目录"""
        if not self.auth_repo_url:
            logger.error("未配置有效的Git仓库URL")
            return None
        
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(prefix="git_repo_")
        logger.info(f"克隆仓库到临时目录: {temp_dir}")
        
        # 克隆仓库
        result = self._run_git_command(
            ['git', 'clone', self.auth_repo_url, temp_dir]
        )
        
        if result is None:
            logger.error("克隆仓库失败")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None
        
        # 设置Git用户信息
        self._run_git_command(['git', 'config', 'user.name', self.username], cwd=temp_dir)
        self._run_git_command(['git', 'config', 'user.email', self.email], cwd=temp_dir)
        
        return temp_dir
    
    def push_feed_to_repository(self, feed_path):
        """将更新后的feed.xml推送到Git仓库"""
        if not os.path.exists(feed_path):
            logger.error(f"feed文件不存在: {feed_path}")
            return False
        
        # 克隆仓库
        repo_dir = self.clone_repository()
        if not repo_dir:
            return False
        
        try:
            # 复制feed.xml到仓库
            repo_feed_path = os.path.join(repo_dir, 'feed.xml')
            shutil.copy2(feed_path, repo_feed_path)
            
            # 添加文件到Git
            self._run_git_command(['git', 'add', 'feed.xml'], cwd=repo_dir)
            
            # 提交更改
            commit_message = f"更新RSS feed - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            self._run_git_command(
                ['git', 'commit', '-m', commit_message],
                cwd=repo_dir
            )
            
            # 推送到远程仓库
            push_result = self._run_git_command(
                ['git', 'push', 'origin', 'main'],
                cwd=repo_dir
            )
            
            if push_result is None:
                # 尝试master分支
                push_result = self._run_git_command(
                    ['git', 'push', 'origin', 'master'],
                    cwd=repo_dir
                )
            
            success = push_result is not None
            if success:
                logger.info("成功推送feed.xml到Git仓库")
            else:
                logger.error("推送feed.xml到Git仓库失败")
            
            return success
        
        finally:
            # 清理临时目录
            shutil.rmtree(repo_dir, ignore_errors=True)
    
    def get_remote_feed(self):
        """从远程仓库获取feed.xml文件"""
        # 克隆仓库
        repo_dir = self.clone_repository()
        if not repo_dir:
            return None
        
        try:
            # 检查feed.xml是否存在
            repo_feed_path = os.path.join(repo_dir, 'feed.xml')
            if not os.path.exists(repo_feed_path):
                logger.warning("远程仓库中不存在feed.xml文件")
                return None
            
            # 返回feed.xml的内容
            with open(repo_feed_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content
        
        finally:
            # 清理临时目录
            shutil.rmtree(repo_dir, ignore_errors=True)

def compare_feed_dates(local_feed_path, remote_feed_content):
    """比较本地和远程feed.xml的lastBuildDate，返回较新的那个"""
    try:
        # 解析本地feed.xml
        local_tree = ET.parse(local_feed_path)
        local_root = local_tree.getroot()
        local_build_date = local_root.find('./channel/lastBuildDate').text
        local_datetime = datetime.strptime(local_build_date, '%a, %d %b %Y %H:%M:%S %z')
        
        # 解析远程feed.xml
        remote_root = ET.fromstring(remote_feed_content)
        remote_build_date = remote_root.find('./channel/lastBuildDate').text
        remote_datetime = datetime.strptime(remote_build_date, '%a, %d %b %Y %H:%M:%S %z')
        
        # 比较日期
        if remote_datetime > local_datetime:
            logger.info("远程feed.xml更新，使用远程版本")
            return 'remote', remote_feed_content
        else:
            logger.info("本地feed.xml更新，使用本地版本")
            return 'local', None
    
    except Exception as e:
        logger.error(f"比较feed日期时出错: {str(e)}")
        logger.info("出错时默认使用本地feed.xml")
        return 'local', None