# LatePost自动RSS更新服务

## 项目介绍

这是一个自动化服务，用于定期爬取[晚点LatePost](https://www.latepost.com)网站的最新文章，并生成标准的RSS feed，方便用户通过RSS阅读器订阅晚点的内容。

项目特点：
- 自动爬取晚点网站最新文章
- 将文章内容转换为Markdown格式保存
- 生成符合标准的RSS feed.xml文件
- 支持Git仓库同步，确保多实例间的feed.xml一致性
- 内置健康检查机制，解决免费托管服务的稳定性问题
- 提供Web服务，可直接访问获取RSS feed

## 技术架构

项目采用Python开发，主要组件包括：

- **爬虫模块**：使用requests和BeautifulSoup爬取晚点网站文章
- **RSS生成模块**：使用feedgen库生成标准RSS feed
- **持久化模块**：支持Git仓库同步，确保数据一致性
- **Web服务**：基于Flask提供Web访问接口
- **健康检查**：内置自我ping机制，保持服务活跃

## 安装部署

### 环境要求

- Python 3.8+
- Git

### 依赖安装

```bash
pip install -r requirements.txt
```

### 环境变量配置

项目需要配置以下环境变量：

- `GIT_REPO_URL`: Git仓库URL，用于同步feed.xml
- `GIT_USERNAME`: Git用户名
- `GIT_EMAIL`: Git邮箱
- `GIT_TOKEN`: Git访问令牌
- `SERVICE_URL`: 服务URL，用于健康检查（可选，默认为http://localhost:5000）

### 本地运行

```bash
python main.py
```

### 部署到Render

项目已包含`render.yaml`配置文件，可直接部署到[Render](https://render.com/)平台：

1. 在Render上创建新的Web Service
2. 选择从GitHub仓库部署
3. 配置必要的环境变量
4. 部署服务

## 使用说明

### 访问RSS feed

部署成功后，可通过以下URL访问RSS feed：

```
https://[your-service-url]/feed.xml
```

### 手动更新RSS

服务会自动定期（默认每小时）检查并更新RSS feed，无需手动干预。

### 文件结构

- `main.py`: 主程序入口
- `simple_scraper.py`: 晚点网站爬虫模块
- `update_rss.py`: RSS更新模块
- `persistence.py`: Git仓库操作模块
- `feed_initializer.py`: feed.xml初始化模块
- `health_check.py`: 健康检查模块
- `latepost_articles/`: 存储爬取的文章（Markdown格式）
- `feed.xml`: 生成的RSS feed文件

## 工作流程

1. 服务启动时，初始化feed.xml（如果不存在，尝试从Git仓库获取）
2. 定期检查晚点网站是否有新文章发布
3. 爬取新文章并保存为Markdown格式
4. 更新feed.xml，添加新文章条目
5. 将更新后的feed.xml推送到Git仓库
6. 提供Web访问接口，供用户获取RSS feed

## 注意事项

- 本项目仅用于个人学习和研究，请勿用于商业用途
- 请遵守网站的robots.txt规则和使用条款
- 爬虫设置了随机延迟和真实的User-Agent，减少对目标网站的影响

## 许可证

MIT License