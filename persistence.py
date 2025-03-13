import os
import subprocess
import time
from datetime import datetime

class GitPersistence:
    """
    使用Git仓库作为持久化存储，确保Render服务重启后能恢复数据
    """
    def __init__(self, repo_url=None, articles_dir="./latepost_articles", feed_file="feed.xml"):
        self.articles_dir = articles_dir
        self.feed_file = feed_file
        self.repo_url = repo_url or os.environ.get('GIT_REPO_URL')
        self.git_username = os.environ.get('GIT_USERNAME')
        self.git_email = os.environ.get('GIT_EMAIL')
        self.git_token = os.environ.get('GIT_TOKEN')
        
        # 确保文章目录存在
        if not os.path.exists(articles_dir):
            os.makedirs(articles_dir)
    
    def _run_command(self, command):
        """
        执行shell命令并返回结果
        """
        try:
            result = subprocess.run(command, shell=True, check=True, 
                                   capture_output=True, text=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"命令执行失败: {command}\n错误: {e.stderr}")
            return None
    
    def setup_git(self):
        """
        配置Git环境
        """
        if not self.repo_url:
            print("未设置Git仓库URL，无法进行持久化存储")
            return False
            
        # 配置Git用户信息
        if self.git_username and self.git_email:
            self._run_command(f'git config --global user.name "{self.git_username}"')
            self._run_command(f'git config --global user.email "{self.git_email}"')
        
        # 配置Git合并策略，避免分支冲突
        self._run_command('git config --global pull.rebase false')  # 使用merge而非rebase
        self._run_command('git config --global pull.ff only')  # 只允许fast-forward合并
        self._run_command('git config --global core.autocrlf input')  # 统一行尾处理
        self._run_command('git config --global core.safecrlf false')  # 不检查行尾转换
        
        # 检查是否已经是Git仓库
        if os.path.exists('.git'):
            print("Git仓库已存在，尝试拉取最新更改")
            # 尝试拉取最新更改，添加合并策略参数
            try:
                if self.git_token:
                    repo_with_token = self.repo_url.replace('https://', f'https://{self.git_username}:{self.git_token}@')
                    # 确保远程仓库配置正确
                    self._run_command(f'git remote set-url origin {repo_with_token} || git remote add origin {repo_with_token}')
                    # 先尝试重置本地仓库到远程仓库状态
                    self._run_command('git fetch origin')
                    # 检查main分支是否存在
                    branch_check = self._run_command('git branch -a')
                    target_branch = 'main'
                    if branch_check and 'main' not in branch_check and 'master' in branch_check:
                        target_branch = 'master'
                    
                    # 确保在正确的分支上，而不是detached HEAD状态
                    self._run_command(f'git checkout {target_branch} || git checkout -b {target_branch} origin/{target_branch}')
                    self._run_command(f'git reset --hard origin/{target_branch}')
                    self._run_command(f'git checkout {target_branch}')
                    print("成功同步远程仓库状态")
                    return True
                else:
                    # 确保远程仓库配置正确
                    self._run_command(f'git remote set-url origin {self.repo_url} || git remote add origin {self.repo_url}')
                    pull_result = self._run_command('git pull --ff-only')
                    if pull_result is not None:
                        print("成功拉取最新更改")
                        return True
            except Exception as e:
                print(f"Git拉取操作异常: {str(e)}")
            
            print("拉取更改失败，尝试重新克隆仓库")
            # 如果拉取失败，删除当前.git目录并重新克隆
            self._run_command('rm -rf .git')
        
        # 克隆仓库
        print("正在克隆Git仓库...")
        
        if self.git_token:
            repo_with_token = self.repo_url.replace('https://', f'https://{self.git_username}:{self.git_token}@')
            clone_result = self._run_command(f'git clone {repo_with_token} .')
            if clone_result is not None:
                # 确保远程仓库配置正确
                self._run_command('git remote remove origin')
                self._run_command(f'git remote add origin {repo_with_token}')
                print("Git仓库克隆成功")
                return True
        else:
            clone_result = self._run_command(f'git clone {self.repo_url} .')
            if clone_result is not None:
                # 确保远程仓库配置正确
                self._run_command('git remote remove origin')
                self._run_command(f'git remote add origin {self.repo_url}')
                print("Git仓库克隆成功")
                return True
        
        print("Git仓库克隆失败，尝试备份现有文件并重新克隆")
        # 备份现有文件
        import shutil
        import tempfile
            
            # 创建临时目录用于备份
            temp_dir = tempfile.mkdtemp()
            print(f"创建临时备份目录: {temp_dir}")
            
            try:
                # 备份文章和feed文件
                if os.path.exists(self.articles_dir):
                    shutil.copytree(self.articles_dir, os.path.join(temp_dir, os.path.basename(self.articles_dir)))
                if os.path.exists(self.feed_file):
                    shutil.copy2(self.feed_file, temp_dir)
                
                # 删除.git目录
                if os.path.exists('.git'):
                    shutil.rmtree('.git')
                
                # 重新尝试克隆
                if self.git_token:
                    clone_result = self._run_command(f'git clone {repo_with_token} .')
                else:
                    clone_result = self._run_command(f'git clone {self.repo_url} .')
                
                if clone_result is not None:
                    print("Git仓库克隆成功，正在恢复备份文件")
                    # 恢复备份的文件
                    backup_articles_dir = os.path.join(temp_dir, os.path.basename(self.articles_dir))
                    if os.path.exists(backup_articles_dir):
                        # 确保目标目录存在
                        if not os.path.exists(self.articles_dir):
                            os.makedirs(self.articles_dir)
                        # 复制所有文件
                        for item in os.listdir(backup_articles_dir):
                            s = os.path.join(backup_articles_dir, item)
                            d = os.path.join(self.articles_dir, item)
                            if os.path.isfile(s):
                                shutil.copy2(s, d)
                    
                    backup_feed = os.path.join(temp_dir, os.path.basename(self.feed_file))
                    if os.path.exists(backup_feed):
                        shutil.copy2(backup_feed, self.feed_file)
                    
                    print("备份文件恢复完成")
                    return True
            except Exception as e:
                print(f"备份和恢复过程出错: {str(e)}")
            finally:
                # 清理临时目录
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
            
            print("Git仓库初始化失败")
            return False
    
    def save_changes(self, message=None):
        """
        将更改保存到Git仓库
        """
        if not message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"自动更新 - {timestamp}"
        
        # 添加所有更改
        self._run_command(f'git add {self.articles_dir} {self.feed_file}')
        
        # 提交更改
        commit_result = self._run_command(f'git commit -m "{message}"')
        if commit_result is None or "nothing to commit" in commit_result:
            print("没有需要提交的更改")
            return False
        
        # 检查当前分支状态
        branch_status = self._run_command('git status -b --porcelain')
        if branch_status and 'HEAD detached' in branch_status:
            print("检测到处于detached HEAD状态，尝试切换到主分支")
            # 检查可用分支
            branch_check = self._run_command('git branch -a')
            target_branch = 'main'
            if branch_check and 'main' not in branch_check and 'master' in branch_check:
                target_branch = 'master'
            
            # 尝试切换到主分支
            checkout_result = self._run_command(f'git checkout {target_branch}')
            if checkout_result is None:
                print(f"无法切换到{target_branch}分支，尝试创建并切换")
                self._run_command(f'git checkout -b {target_branch}')
        
        # 推送到远程仓库
        if self.git_token:
            repo_with_token = self.repo_url.replace('https://', f'https://{self.git_username}:{self.git_token}@')
            # 获取当前分支名
            current_branch = self._run_command('git rev-parse --abbrev-ref HEAD')
            if current_branch and current_branch != 'HEAD':
                push_result = self._run_command(f'git push {repo_with_token} {current_branch}')
            else:
                # 如果仍然是detached HEAD，则推送到默认分支
                push_result = self._run_command(f'git push {repo_with_token} HEAD:main')
        else:
            push_result = self._run_command('git push')
        
        if push_result is not None:
            print(f"更改已成功推送到Git仓库: {message}")
            return True
        else:
            print("推送更改失败")
            return False
    
    def get_latest_article_id(self):
        """
        获取最新文章ID
        """
        existing_articles = [f for f in os.listdir(self.articles_dir) 
                           if f.endswith('.md') and f.startswith('latepost_article_')]
        
        if not existing_articles:
            print("未找到现有文章，无法确定最新ID")
            return None
        
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
            return None
        
        last_id = max(article_ids)
        print(f"当前最新文章ID: {last_id}")
        return last_id

# 使用示例
def initialize_persistence():
    """
    初始化持久化存储，在应用启动时调用
    """
    persistence = GitPersistence()
    if persistence.setup_git():
        print("持久化存储初始化成功")
        return persistence
    else:
        print("持久化存储初始化失败，将使用本地存储")
        return None

def save_after_update(persistence, article_id=None):
    """
    更新后保存更改，在爬取新文章后调用
    """
    if persistence:
        message = f"更新文章 ID: {article_id}" if article_id else None
        return persistence.save_changes(message)
    return False