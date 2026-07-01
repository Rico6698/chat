# 医知 - AI智能问诊科普助手

基于 RAG 架构的医学科普智能问答系统。

## 功能特色

- 智能问答：RAG检索 + MiMo大模型生成
- 语音交互：Web Speech API 语音输入/输出
- 历史记录：本地保存，无需登录
- 医学专属：只回答医学健康相关问题
- 移动适配：手机/平板/电脑自适应

## 部署到 Vercel

1. Fork 本仓库
2. 在 Vercel 中导入项目
3. 配置环境变量：
   - `API_KEY`: MiMo API密钥
   - `API_BASE`: API地址
   - `MODEL`: 模型名称
4. 部署完成

## 技术栈

- 前端：HTML5 + CSS3 + JavaScript
- 后端：Vercel Serverless Functions (Python)
- AI：MiMo v2.5 + RAG
- TTS：Web Speech API (浏览器端)
