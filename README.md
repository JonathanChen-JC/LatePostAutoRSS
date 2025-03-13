# 晚点LatePost RSS 生成器

## 项目简介

这是一个自动抓取[晚点LatePost](https://www.latepost.com)文章并生成RSS订阅源的工具。该项目可以定期检查晚点LatePost网站的最新文章，将其转换为Markdown格式保存，并生成一个美观的RSS Feed，方便用户通过RSS阅读器订阅晚点LatePost的最新内容。

## 功能特点

- 🔄 **自动更新**：每小时自动检查并抓取晚点LatePost的最新文章
- 📝 **Markdown存储**：将抓取的文章以Markdown格式保存，便于管理和查看
- 🌐 **RSS生成**：自动生成标准的RSS Feed，支持大多数RSS阅读器
- 🎨 **美观样式**：RSS条目包含精心设计的HTML样式，提供良好的阅读体验
- 🔌 **Web服务**：内置Flask Web服务，可通过浏览器直接访问RSS Feed
- 🔄 **双重爬虫实现**：提供基于Selenium的完整爬虫和基于Requests的简易爬虫两种实现
- 💾 **Git持久化存储**：使用Git仓库作为持久化存储，解决云服务重启导致的数据丢失问题
- 🔄 **健康检查与自动恢复**：内置健康检查机制，通过自我ping保持服务活跃，解决Render免费服务的503问题

## 技术实现

项目主要使用以下技术：

- **Python**：核心编程语言
- **Flask**：提供Web服务，用于RSS Feed的访问
- **Selenium/Requests**：网页抓取和内容提取
- **BeautifulSoup4**：HTML解析
- **Feedgen**：生成标准的RSS Feed
- **Schedule**：定时任务调度
- **Git**：用于数据持久化存储
- **健康检查**：自动保活机制，防止Render免费服务休眠

## 项目结构

```
.
├── main.py                # 主程序入口，包含Flask应用和RSS生成器
├── latepost_scraper.py    # 基于Selenium的爬虫实现
├── simple_scraper.py      # 基于Requests的简易爬虫实现
├── update_rss.py          # 使用简易爬虫更新RSS的独立脚本
├── persistence.py         # Git持久化存储实现
├── health_check.py        # 健康检查和自动恢复机制
├── regenerate_feed.py     # 重新生成RSS Feed的辅助脚本
├── requirements.txt       # 项目依赖
├── render.yaml            # Render平台部署配置
├── feed.xml               # 生成的RSS Feed文件
└── latepost_articles/     # 存储抓取的文章
    └── latepost_article_*.md  # Markdown格式的文章文件
```

## 核心组件说明

### LatePostRSSGenerator (main.py)

这是项目的核心类，负责：
- 初始化RSS生成器和爬虫
- 从Markdown文件生成RSS Feed
- 检查并抓取新文章
- 将Markdown内容转换为美观的HTML

### LatePostScraper (latepost_scraper.py)

基于Selenium的爬虫实现，功能包括：
- 使用无头浏览器访问晚点LatePost网站
- 模拟人类行为，避免被反爬机制检测
- 提取文章内容、标题、作者等信息
- 将文章内容转换为Markdown格式并保存

### SimpleLatePostScraper (simple_scraper.py)

基于Requests的简易爬虫实现，相比Selenium版本更轻量：
- 直接使用HTTP请求获取网页内容
- 使用BeautifulSoup解析HTML
- 提取文章内容并转换为Markdown
- 支持批量抓取指定范围的文章

### GitPersistence (persistence.py)

基于Git的持久化存储实现，解决云服务重启数据丢失问题：
- 使用Git仓库作为持久化存储
- 服务启动时自动从Git仓库拉取最新数据
- 爬取新文章后自动提交并推送到Git仓库
- 支持通过环境变量配置Git仓库信息

### HealthCheck (health_check.py)

健康检查和自动恢复机制，解决Render免费服务的503问题：
- 提供健康检查端点(/health和/ping)
- 自动定期ping服务，保持服务活跃
- 智能检测外部访问，避免不必要的自我ping
- 提供服务运行时间和状态信息

## 部署指南

### 本地部署

1. 克隆项目到本地

```bash
git clone <repository-url>
cd LatePostRSS
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 运行项目

```bash
python main.py
```

服务将在 http://localhost:5000 启动，RSS Feed 可通过 http://localhost:5000/feed.xml 访问。

### Render平台部署

项目已配置好用于Render平台的部署文件(render.yaml)，可以直接在Render上部署：

1. 在Render上创建一个新的Web Service
2. 连接到包含此项目的GitHub仓库
3. 在Render的环境变量中配置以下变量：
   - `SERVICE_URL`: 服务的完整URL（例如：https://your-app.onrender.com），用于健康检查
   - `GIT_REPO_URL`: 用于存储数据的Git仓库URL（例如：https://github.com/username/repo.git）
   - `GIT_USERNAME`: Git用户名
   - `GIT_EMAIL`: Git邮箱
   - `GIT_TOKEN`: Git个人访问令牌（需要有仓库写入权限）
4. Render将自动检测render.yaml配置并部署服务

部署后，可以通过分配的URL访问服务，RSS Feed将位于`/feed.xml`路径。

### 解决Render服务重启和休眠问题

本项目采用了两种机制来解决Render免费服务的常见问题：

#### 1. Git持久化存储（解决数据丢失）

- 服务启动时，会从配置的Git仓库拉取最新数据
- 每次爬取新文章后，会自动将文章内容和RSS文件提交并推送到Git仓库
- 当服务重启时，会自动从Git仓库恢复数据，确保RSS Feed和文章内容不会丢失

##### 环境变量配置

为了启用Git持久化存储，需要在Render平台配置以下环境变量：

- `GIT_REPO_URL`：用于存储数据的Git仓库URL（必需）
  - 格式：`https://github.com/username/repo.git`
  - 确保这是一个空仓库或专门用于数据存储的仓库

- `GIT_USERNAME`：Git用户名（必需）
  - 用于配置Git提交信息
  - 通常是您的GitHub用户名

- `GIT_EMAIL`：Git邮箱（必需）
  - 用于配置Git提交信息
  - 通常是您的GitHub注册邮箱

- `GIT_TOKEN`：Git个人访问令牌（必需）
  - 用于授权访问Git仓库
  - 需要具有仓库的读写权限
  - 在GitHub中生成：Settings -> Developer settings -> Personal access tokens

配置完成后，服务将自动执行以下操作：

1. 首次启动时：
   - 克隆配置的Git仓库
   - 如果本地已有数据，会自动备份并恢复

2. 运行过程中：
   - 每次抓取新文章后自动提交更改
   - 定期推送更改到远程仓库

3. 服务重启时：
   - 自动从Git仓库拉取最新数据
   - 确保本地数据与远程仓库同步

#### 2. 健康检查与自动恢复（解决503错误）

- 服务内置健康检查端点(/health和/ping)，可用于外部监控
- 自动定期ping自身，保持服务活跃，防止Render将服务置为休眠状态
- 智能检测外部访问，减少不必要的自我ping，节约资源

这两种机制结合使用，确保即使Render服务重启或尝试进入休眠状态，服务也能保持活跃并正确恢复数据，大大提高了服务的可靠性。

#### 外部监控（可选但推荐）

进一步提高可靠性，建议设置外部监控服务定期访问您的应用：

- 使用 [UptimeRobot](https://uptimerobot.com/)（免费）设置HTTP监控，每5分钟ping一次您的服务
- 或使用 [cron-job.org](https://cron-job.org)（免费）设置定时任务访问您的健康检查端点
- 监控URL设置为：`https://<your-render-app>.onrender.com/ping`

## 使用方法

### 订阅RSS Feed

1. 在任何支持RSS的阅读器中，添加新的订阅源
2. 输入RSS Feed的URL：
   - 本地部署：`http://localhost:5000/feed.xml`
   - Render部署：`https://<your-render-app>.onrender.com/feed.xml`

### 手动更新RSS

如果需要手动更新RSS，可以运行：

```bash
python update_rss.py
```

这将检查最新文章并更新RSS Feed。

### 重新生成RSS Feed

如果需要重新生成RSS Feed（例如修改了RSS样式），可以运行：

```bash
python regenerate_feed.py
```

## 注意事项

- 本项目仅用于个人学习和研究，请勿用于商业用途
- 请合理设置抓取频率，避免对目标网站造成过大压力
- 如遇到反爬机制，可能需要调整爬虫参数或切换爬虫实现
- 在Render等免费云服务上部署时，请配置Git持久化存储，避免服务重启导致数据丢失

## 许可证

[MIT License](LICENSE)