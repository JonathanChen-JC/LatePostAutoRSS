import os
import subprocess
import time
from datetime import datetime
import shutil
import tempfile

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
                    
                    # 同步文件
                    self._sync_files()
                    
                    # 确保feed.xml不为空
                    self._ensure_feed_not_empty()
                    return True
                else:
                    # 确保远程仓库配置正确
                    self._run_command(f'git remote set-url origin {self.repo_url} || git remote add origin {self.repo_url}')
                    pull_result = self._run_command('git pull --ff-only')
                    if pull_result is not None:
                        print("成功拉取最新更改")
                        
                        # 同步文件
                        self._sync_files()
                        
                        # 确保feed.xml不为空
                        self._ensure_feed_not_empty()
                        return True
            except Exception as e:
                print(f"Git拉取操作异常: {str(e)}")
            
            print("拉取更改失败，尝试重新克隆仓库")
            # 如果拉取失败，删除当前.git目录并重新克隆
            self._run_command('rm -rf .git')
        
        # 克隆仓库
        print("正在克隆Git仓库...")
        
        # 备份当前项目文件
        self._backup_project_files()
        
        if self.git_token:
            repo_with_token = self.repo_url.replace('https://', f'https://{self.git_username}:{self.git_token}@')
            clone_result = self._run_command(f'git clone {repo_with_token} .')
            if clone_result is not None:
                # 确保远程仓库配置正确
                self._run_command('git remote remove origin')
                self._run_command(f'git remote add origin {repo_with_token}')
                
                # 同步文件
                self._sync_files()
                
                # 确保feed.xml不为空
                self._ensure_feed_not_empty()
                print("Git仓库克隆成功")
                return True
        else:
            clone_result = self._run_command(f'git clone {self.repo_url} .')
            if clone_result is not None:
                # 确保远程仓库配置正确
                self._run_command('git remote remove origin')
                self._run_command(f'git remote add origin {self.repo_url}')
                
                # 同步文件
                self._sync_files()
                
                # 确保feed.xml不为空
                self._ensure_feed_not_empty()
                print("Git仓库克隆成功")
                return True
        
        print("Git仓库克隆失败，尝试备份现有文件并重新克隆")
        # 备份现有文件
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
                
                # 恢复feed.xml
                backup_feed = os.path.join(temp_dir, os.path.basename(self.feed_file))
                if os.path.exists(backup_feed):
                    shutil.copy2(backup_feed, self.feed_file)
                
                # 同步文件
                self._sync_files()
                
                # 确保feed.xml不为空
                self._ensure_feed_not_empty()
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
    
    def _backup_project_files(self):
        """
        备份项目自带的feed.xml和latepost_articles文件夹
        """
        try:
            # 确保文章目录存在
            if not os.path.exists(self.articles_dir):
                os.makedirs(self.articles_dir)
                print(f"创建文章目录: {self.articles_dir}")
            
            # 备份feed.xml
            if os.path.exists(self.feed_file):
                shutil.copy2(self.feed_file, f"{self.feed_file}.bak")
                print(f"已备份{self.feed_file}到{self.feed_file}.bak")
            
            # 备份latepost_articles文件夹
            if os.path.exists(self.articles_dir):
                backup_dir = f"{self.articles_dir}.bak"
                if os.path.exists(backup_dir):
                    shutil.rmtree(backup_dir)
                shutil.copytree(self.articles_dir, backup_dir)
                print(f"已备份{self.articles_dir}到{backup_dir}")
        except Exception as e:
            print(f"备份项目文件时出错: {str(e)}")
            # 确保备份目录存在
            backup_dir = f"{self.articles_dir}.bak"
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
                print(f"创建备份目录: {backup_dir}")
    
    def _sync_files(self):
        """
        同步Git仓库和项目文件
        """
        try:
            # 确保文章目录存在
            if not os.path.exists(self.articles_dir):
                os.makedirs(self.articles_dir)
                print(f"创建文章目录: {self.articles_dir}")
            
            # 检查Git仓库中是否存在feed.xml和latepost_articles文件夹
            repo_has_feed = os.path.exists(self.feed_file)
            repo_has_articles = os.path.exists(self.articles_dir) and len(os.listdir(self.articles_dir)) > 0
            
            # 检查是否有项目备份文件
            has_feed_backup = os.path.exists(f"{self.feed_file}.bak")
            has_articles_backup = os.path.exists(f"{self.articles_dir}.bak")
            
            # 检查feed.xml内容是否为空
            feed_is_empty = False
            if repo_has_feed:
                # 检查feed.xml文件内容
                try:
                    with open(self.feed_file, 'r', encoding='utf-8') as f:
                        feed_content = f.read().strip()
                    # 检查是否为空或只有基本XML结构
                    feed_is_empty = not feed_content or feed_content == '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"></rss>'
                    if feed_is_empty:
                        print(f"检测到{self.feed_file}内容为空或只有基本结构")
                except Exception as e:
                    print(f"读取{self.feed_file}时出错: {str(e)}")
                    feed_is_empty = True
            
            # 如果Git仓库中的feed.xml为空但备份不为空，使用备份
            if repo_has_feed and feed_is_empty and has_feed_backup:
                try:
                    with open(f"{self.feed_file}.bak", 'r', encoding='utf-8') as f:
                        backup_content = f.read().strip()
                    if backup_content and backup_content != '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"></rss>':
                        shutil.copy2(f"{self.feed_file}.bak", self.feed_file)
                        print(f"检测到{self.feed_file}为空，已使用非空的备份文件替换")
                        feed_is_empty = False
                except Exception as e:
                    print(f"读取备份feed文件时出错: {str(e)}")
            
            if not repo_has_feed or not repo_has_articles or feed_is_empty:
                # Git仓库中不存在feed.xml或latepost_articles文件夹，或feed.xml为空
                # 使用项目自带的文件同步到Git仓库
                print("Git仓库中缺少必要文件或feed.xml为空，将同步项目自带文件")
                
                # 同步feed.xml
                if (not repo_has_feed or feed_is_empty) and has_feed_backup:
                    # 检查备份文件内容
                    try:
                        with open(f"{self.feed_file}.bak", 'r', encoding='utf-8') as f:
                            backup_content = f.read().strip()
                        if backup_content and backup_content != '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"></rss>':
                            shutil.copy2(f"{self.feed_file}.bak", self.feed_file)
                            print(f"已将项目自带的非空{self.feed_file}同步到Git仓库")
                        else:
                            # 如果备份也是空的，创建一个基本的RSS结构
                            self._create_basic_feed()
                    except Exception as e:
                        print(f"读取备份feed文件时出错: {str(e)}")
                        # 创建一个基本的RSS结构
                        self._create_basic_feed()
                elif not repo_has_feed:
                    # 如果没有备份但需要feed.xml，创建一个基本的RSS结构
                    self._create_basic_feed()
                
                # 同步latepost_articles文件夹
                if not repo_has_articles and has_articles_backup:
                    # 确保文章目录存在
                    if not os.path.exists(self.articles_dir):
                        os.makedirs(self.articles_dir)
                    
                    # 复制所有文章文件
                    backup_dir = f"{self.articles_dir}.bak"
                    for item in os.listdir(backup_dir):
                        if item.endswith('.md'):
                            s = os.path.join(backup_dir, item)
                            d = os.path.join(self.articles_dir, item)
                            if os.path.isfile(s):
                                shutil.copy2(s, d)
                    print(f"已将项目自带的{self.articles_dir}文件夹同步到Git仓库")
                
                # 提交更改到Git仓库
                self.save_changes("初始化同步项目文件到Git仓库")
            else:
                # Git仓库中存在feed.xml和latepost_articles文件夹
                # 比较并同步到最新状态
                print("Git仓库中已存在必要文件，正在比较并同步到最新状态")
                
                # 同步feed.xml
                if has_feed_backup:
                    repo_feed_time = os.path.getmtime(self.feed_file)
                    backup_feed_time = os.path.getmtime(f"{self.feed_file}.bak")
                    
                    # 检查备份文件内容
                    backup_is_empty = True
                    try:
                        with open(f"{self.feed_file}.bak", 'r', encoding='utf-8') as f:
                            backup_content = f.read().strip()
                        backup_is_empty = not backup_content or backup_content == '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"></rss>'
                    except Exception as e:
                        print(f"读取备份feed文件时出错: {str(e)}")
                    
                    # 如果备份文件更新且非空，或者当前feed.xml为空但备份非空，则使用备份
                    if (backup_feed_time > repo_feed_time and not backup_is_empty) or (feed_is_empty and not backup_is_empty):
                        # 项目自带的feed.xml更新且非空，同步到Git仓库
                        shutil.copy2(f"{self.feed_file}.bak", self.feed_file)
                        print(f"已将更新的项目自带{self.feed_file}同步到Git仓库")
                    elif not feed_is_empty:
                        # Git仓库的feed.xml更新且非空，使用Git仓库的版本
                        print(f"使用Git仓库中的{self.feed_file}")
                    else:
                        # 两个版本都为空，创建一个基本的RSS结构
                        self._create_basic_feed()
                
                # 同步latepost_articles文件夹
                if has_articles_backup:
                    backup_dir = f"{self.articles_dir}.bak"
                    
                    # 获取Git仓库和项目备份中的所有文章文件
                    repo_articles = {f: os.path.getmtime(os.path.join(self.articles_dir, f)) 
                                    for f in os.listdir(self.articles_dir) if f.endswith('.md')}
                    backup_articles = {f: os.path.getmtime(os.path.join(backup_dir, f)) 
                                      for f in os.listdir(backup_dir) if f.endswith('.md')}
                    
                    # 同步更新的文件
                    for article, mtime in backup_articles.items():
                        if article in repo_articles:
                            # 文件在两边都存在，比较修改时间
                            if mtime > repo_articles[article]:
                                # 项目备份的文件更新，同步到Git仓库
                                shutil.copy2(os.path.join(backup_dir, article), os.path.join(self.articles_dir, article))
                                print(f"已将更新的项目自带文章 {article} 同步到Git仓库")
                        else:
                            # 文件只在项目备份中存在，添加到Git仓库
                            shutil.copy2(os.path.join(backup_dir, article), os.path.join(self.articles_dir, article))
                            print(f"已将项目自带文章 {article} 添加到Git仓库")
                    
                    # 检查Git仓库中的新文件
                    for article in repo_articles:
                        if article not in backup_articles:
                            print(f"Git仓库中存在新文章: {article}")
                    
                    # 如果有更改，提交到Git仓库
                    self.save_changes("同步项目文件和Git仓库")
                    
                # 最后检查feed.xml是否为空，如果为空则创建基本结构
                self._ensure_feed_not_empty()
        except Exception as e:
            print(f"同步文件时出错: {str(e)}")
            # 尝试创建基本文件结构
            if not os.path.exists(self.articles_dir):
                os.makedirs(self.articles_dir)
            if not os.path.exists(self.feed_file) or self._is_feed_empty():
                self._create_basic_feed()
                print("已创建基本文件结构")
                self.save_changes("初始化基本文件结构")
            
    def _create_basic_feed(self):
        """
        创建一个基本的非空RSS feed结构
        """
        try:
            from datetime import datetime
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
            with open(self.feed_file, 'w', encoding='utf-8') as f:
                f.write(basic_feed)
            print(f"创建了基本的非空RSS feed结构: {self.feed_file}")
            return True
        except Exception as e:
            print(f"创建基本feed结构时出错: {str(e)}")
            return False
            
    def _is_feed_empty(self):
        """
        检查feed.xml是否为空或只有基本结构
        """
        try:
            if not os.path.exists(self.feed_file):
                return True
                
            with open(self.feed_file, 'r', encoding='utf-8') as f:
                feed_content = f.read().strip()
            # 检查是否为空或只有基本XML结构
            return not feed_content or feed_content == '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"></rss>'
        except Exception as e:
            print(f"检查feed是否为空时出错: {str(e)}")
            return True
            
    def _ensure_feed_not_empty(self):
        """
        确保feed.xml不为空，如果为空则创建基本结构
        优先使用项目自带的feed.xml和Git仓库中的feed.xml中较新的非空文件
        """
        # 检查当前feed.xml是否为空
        current_feed_empty = self._is_feed_empty()
        
        # 检查备份feed.xml是否存在且非空
        backup_feed_path = f"{self.feed_file}.bak"
        backup_feed_exists = os.path.exists(backup_feed_path)
        backup_feed_empty = True
        backup_feed_time = 0
        
        if backup_feed_exists:
            try:
                backup_feed_time = os.path.getmtime(backup_feed_path)
                with open(backup_feed_path, 'r', encoding='utf-8') as f:
                    backup_content = f.read().strip()
                backup_feed_empty = not backup_content or backup_content == '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"></rss>'
            except Exception as e:
                print(f"读取备份feed文件时出错: {str(e)}")
        
        # 检查当前feed.xml的修改时间
        current_feed_time = 0
        if os.path.exists(self.feed_file):
            current_feed_time = os.path.getmtime(self.feed_file)
        
        # 决定使用哪个feed文件
        if current_feed_empty:
            if backup_feed_exists and not backup_feed_empty:
                # 当前feed为空但备份非空，使用备份
                print(f"当前feed.xml为空，使用非空的备份feed.xml")
                shutil.copy2(backup_feed_path, self.feed_file)
                return True
            else:
                # 当前feed为空且备份也为空或不存在，创建基本结构
                print("当前feed.xml为空且没有可用的备份，创建基本的非空RSS feed")
                self._create_basic_feed()
                return True
        elif backup_feed_exists and not backup_feed_empty and backup_feed_time > current_feed_time:
            # 两个feed都非空，但备份更新，使用备份
            print(f"备份feed.xml更新，使用备份feed.xml")
            shutil.copy2(backup_feed_path, self.feed_file)
            return True
        
        return False
    
    def save_changes(self, message=None):
        """
        将更改保存到Git仓库
        """
        if not message:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"自动更新 - {timestamp}"
        
        # 确保文件夹存在
        if not os.path.exists(self.articles_dir):
            os.makedirs(self.articles_dir)
            print(f"创建文章目录: {self.articles_dir}")
        
        # 确保feed.xml文件存在且不为空
        if not os.path.exists(self.feed_file) or self._is_feed_empty():
            # 检查是否有备份文件
            if os.path.exists(f"{self.feed_file}.bak"):
                try:
                    with open(f"{self.feed_file}.bak", 'r', encoding='utf-8') as f:
                        backup_content = f.read().strip()
                    if backup_content and backup_content != '<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"></rss>':
                        shutil.copy2(f"{self.feed_file}.bak", self.feed_file)
                        print(f"在保存更改前，已将非空备份feed文件同步到Git仓库")
                    else:
                        self._create_basic_feed()
                except Exception as e:
                    print(f"读取备份feed文件时出错: {str(e)}")
                    self._create_basic_feed()
            else:
                self._create_basic_feed()
        
        # 使用绝对路径添加所有更改
        articles_abs_path = os.path.abspath(self.articles_dir)
        feed_abs_path = os.path.abspath(self.feed_file)
        
        # 添加所有更改
        self._run_command(f'git add "{articles_abs_path}" "{feed_abs_path}"')
        
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
        # 确保文章目录存在
        if not os.path.exists(self.articles_dir):
            print(f"文章目录不存在，正在创建: {self.articles_dir}")
            os.makedirs(self.articles_dir)
            return None
            
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