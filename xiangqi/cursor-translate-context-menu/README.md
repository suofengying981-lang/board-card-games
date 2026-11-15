# 选中文本翻译（Cursor / VS Code 扩展）

在编辑器或集成终端中**选中文字并右键**，可将内容翻译为**简体中文**或**英文**。默认使用 LibreTranslate 公共实例（无需 API Key，有速率限制），失败时可回退 MyMemory 免费接口。

## 功能

- 右键菜单：**翻译为中文 (Translate to Chinese)** — 自动检测源语言，译为 zh-CN
- 右键菜单：**翻译为英文 (Translate to English)**
- 命令面板中也可搜索上述命令名执行
- 结果：通知栏预览 + **输出** 面板「选中文本翻译」（可复制全文）

## 安装

打包后在 Cursor **IDE 窗口**（File → Open IDE）用 **Cmd+Shift+X** → **⋯** → **Install from VSIX…** 安装生成的 `.vsix`。

### 方式 A：VSIX 安装（推荐，Mac / 无 cursor CLI）

```bash
cd xiangqi/cursor-translate-context-menu
npx --yes @vscode/vsce package
```

### 方式 B：本地文件夹安装（需 cursor 命令在 PATH）

1. 确认本目录包含 `package.json` 与 `extension.js`
2. 在终端执行（Cursor 使用 `cursor`，VS Code 使用 `code`）：

```bash
cursor --install-extension /path/to/cursor-translate-context-menu
```

或先打包再安装：

```bash
cd /path/to/cursor-translate-context-menu
npm install -g @vscode/vsce   # 可选，仅打包时需要
vsce package
cursor --install-extension cursor-translate-context-menu-0.1.0.vsix
```

3. 重载窗口：`Developer: Reload Window`

### 方式 C：扩展开发宿主（F5 调试）

1. 用 Cursor/VS Code 打开本文件夹
2. 按 **F5** 启动「Extension Development Host」
3. 在新窗口中选中文本 → 右键测试

## 适用与不适用场景

| 场景 | 是否支持 |
|------|----------|
| 文本编辑器中选中文本 | ✅ |
| 集成终端中选中文本（需较新版本 VS Code/Cursor 的终端选区 API） | ✅（视客户端版本而定） |
| **Cursor 设置页、自定义 Webview UI** | ❌ 无标准编辑器上下文菜单 |

Cursor 的设置界面是自定义前端，**不会**出现本扩展注入的编辑器右键菜单。请在代码编辑器、Markdown、终端等标准工作区中使用。

## 翻译服务与 API Key（可选）

1. **默认**：`cursorTranslate.libreTranslateUrl` = `https://libretranslate.de`  
   - 无需 Key，但有**速率限制**；请勿高频批量翻译。
2. **可选 Key**：若改用 [libretranslate.com](https://libretranslate.com) 等需 Key 的实例，在设置中填写 `cursorTranslate.apiKey`，或在本机环境变量设置 `LIBRETRANSLATE_API_KEY`（勿写入仓库）。
3. **回退**：`cursorTranslate.fallbackToMyMemory`（默认开启）在 LibreTranslate 失败时使用 [MyMemory](https://mymemory.translated.net/)（约每日 1000 词免费限额，无 Key）。

设置路径：**Cursor Settings → 搜索 `cursorTranslate`**

## 隐私说明

选中文本会通过网络发送至上述翻译服务进行处理，请勿翻译机密内容。

## 许可

MIT