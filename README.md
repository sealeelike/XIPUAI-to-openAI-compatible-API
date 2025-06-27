# XIPUAI-to-openAI-compatible-API

## 概述

把xipuAI网页服务转化成API调用服务，支持知识库，上下文，联网搜索，temperature···

## 背景
之前看到有人把 Google AI Studio 逆向成 openAI格式 的API服务，用以免费使用时兴的 2.5pro(https://github.com/CJackHwang/AIstudioProxyAPI)
我看到洗脚利物浦xipuAI平台上的 o3，sonnet3.7等昂贵模型，不由冒出了同样的想法。


## 如何使用

### 依赖项概览

- 需要xjtlu师/生账号
- 可[点此](libraries)查看库
- win11开发
- auth模块需使用chrome浏览器
- 使用对话客户端，比如[cherry studio](https://github.com/CherryHQ/cherry-studio.git)，或者[deepchat](https://github.com/ThinkInAIXYZ/deepchat.git)

### 具体操作

#### 环境搭建
- 把[环境配置](environment.yml)下载到本地的某个空文件夹
- 在该文件夹打开cmd
- 使用conda复制环境
  `conda env create -f environment.yml`
- 激活环境
  `conda activate genai_project`


#### 初始配置
- 在刚刚的窗口运行[密码配置模块](config.py)
  `python config.py`

  输入你的西浦内部账号密码。脚本会生成一个.env文件，储存你的信息。这样以后就不需要重复输入密码了， _保护好个人信息哦！！_
- 运行[获取令牌脚本](auth.py)
  `python auth.py`
  全程无需任何操作，等待终端提示即可。
  （电脑需要安装chrome浏览器）
- 启动[adapter服务](xjtlu_adapter_final.py)
  `uvicorn adapter:app --reload`

  同时会在项目文件夹内生成log文件夹，里面有日志
- 桌面客户端对接
  新建服务商，类型openAI compatible，apiKEY随便写几个英文字母，baseurl`http://127.0.0.1:8000/v1/chat/completions`。

  拉取提供的模型。模型列表是程序内置的，无法实时获取。直接填写模型id会被传递到web服务。

#### 尝试使用
新建一个会话，选择模型并尝试会话

## 演示

此处可观看演示视频

https://drive.google.com/file/d/1zdsoDvZNL3ZOQWpaVhtDWx2kQRfcYgz8/view?usp=sharing

## 原理讲解

### config.py

这只是一个简单的密码存储脚本。

用户用它输入一次用户名和密码，它写入根目录env文件。这样以后就可以自动读取，不用重复输入。

### auth.py

- 获取env文件里的用户名密码
- 启动临时chrome窗口
- 模拟用户填写密码，点击“log in”
- 截获所需的令牌，存储到env文件。

每次获取新令牌都会覆盖老令牌

### adapter.py

## License

This project is licensed under the [NAME HERE] License - see the LICENSE.md file for details
