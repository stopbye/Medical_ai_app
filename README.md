# 医疗AI应用 (Medical AI Application)

## 项目概述

这是一个医疗AI应用项目，旨在通过结合后端API服务和前端用户界面，提供智能化的医疗辅助功能。项目涵盖了AI助手、医院信息查询、症状分析和用户管理等核心模块，旨在提升医疗服务的效率和用户体验。

## 项目结构

```text
medical_ai_app/
├── 01001.ipynb
├── README.md
├── backend/                  # 后端服务目录
│   ├── requirements.txt      # Python依赖文件
│   └── src/                  # 后端源代码
│       ├── __init__.py
│       ├── main.py             # 后端主入口文件
│       ├── database/           # 数据库相关模块
│       ├── models/             # 数据模型定义
│       ├── routes/             # API路由定义
│       └── static/             # 静态文件目录
└── frontend/                 # 前端应用目录
    ├── package.json          # npm包配置文件
    ├── vite.config.js        # Vite构建工具配置文件
    ├── tailwind.config.js    # Tailwind CSS配置文件
    ├── postcss.config.cjs    # PostCSS配置文件
    ├── index.html            # 前端入口HTML文件
    └── src/                  # 前端源代码
        ├── main.jsx          # 前端主入口文件
        ├── App.jsx           # 主应用组件
        ├── index.css         # 全局CSS样式
        ├── App.css           # 应用CSS样式
        ├── assets/           # 静态资源（图片、字体等）
        ├── components/       # 可复用UI组件
        ├── hooks/            # React自定义Hooks
        ├── lib/              # 工具函数或库
        └── tw-animate-css/   # Tailwind CSS动画相关文件
```

## 技术栈

### 后端

*   **Python**: 主要编程语言。
*   **FastAPI**: 用于构建高性能API服务。
*   **SQLAlchemy**: ORM（对象关系映射）工具，用于数据库交互。
*   **Pydantic**: 用于数据验证和设置管理。
*   **Uvicorn**: ASGI服务器，用于运行FastAPI应用。

### 前端

*   **React**: 用于构建用户界面的JavaScript库。
*   **Vite**: 快速的前端构建工具。
*   **Tailwind CSS**: 实用至上的CSS框架，用于快速构建响应式UI。
*   **JavaScript/JSX**: 前端编程语言。

## 功能概述

*   **AI助手**: 提供智能问答和医疗建议。
*   **医院信息**: 查询医院列表、详细信息和科室信息。
*   **症状分析**: 根据用户输入的症状进行初步分析和建议。
*   **用户管理**: 用户注册、登录、个人信息管理等。

## 环境搭建与运行

### 前提条件

*   Python 3.8+
*   Node.js 14+
*   npm 或 yarn

### 后端设置

1.  **进入后端目录**：
    ```bash
    cd backend
    ```

2.  **安装Python依赖**：
    ```bash
    pip install -r requirements.txt
    ```

3.  **运行后端服务**：
    ```bash
    uvicorn src.main:app --reload
    ```
    后端服务通常会在 `http://127.0.0.1:8000` 运行。

### 前端设置

1.  **进入前端目录**：
    ```bash
    cd frontend
    ```

2.  **安装Node.js依赖**：
    ```bash
    npm install
    ```

3.  **运行前端应用**：
    ```bash
    npm run dev
    ```
    前端应用通常会在 `http://localhost:5173` 运行（具体端口可能因Vite配置而异）。

## API文档

后端服务启动后，可以通过访问 `http://127.0.0.1:8000/docs` 查看自动生成的Swagger UI API文档。
