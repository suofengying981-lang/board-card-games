'use strict';

const vscode = require('vscode');
const { translateText } = require('./translate');

/** @type {vscode.OutputChannel | undefined} */
let outputChannel;

function getOutput() {
  if (!outputChannel) {
    outputChannel = vscode.window.createOutputChannel('选中文本翻译');
  }
  return outputChannel;
}

/**
 * @returns {string | undefined}
 */
function getSelectionText() {
  const editor = vscode.window.activeTextEditor;
  if (editor && !editor.selection.isEmpty) {
    return editor.document.getText(editor.selection);
  }

  const terminal = vscode.window.activeTerminal;
  if (terminal && typeof terminal.selection === 'string' && terminal.selection.length > 0) {
    return terminal.selection;
  }

  return undefined;
}

/**
 * @param {'zh-CN' | 'en'} targetLang
 */
async function runTranslate(targetLang) {
  const selection = getSelectionText();
  if (!selection) {
    vscode.window.showWarningMessage('请先在编辑器或终端中选中要翻译的文本。');
    return;
  }

  const config = vscode.workspace.getConfiguration('cursorTranslate');
  const label = targetLang.startsWith('zh') ? '中文' : '英文';

  await vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: `正在翻译为${label}…`,
      cancellable: false,
    },
    async () => {
      try {
        const result = await translateText(config, selection, targetLang);
        const header = `[${result.provider}${result.detectedSource ? `，检测语言: ${result.detectedSource}` : ''}]`;
        const body = result.translated;

        getOutput().appendLine('---');
        getOutput().appendLine(`${header} → ${label}`);
        getOutput().appendLine(body);
        getOutput().show(true);

        const preview = body.length > 120 ? `${body.slice(0, 120)}…` : body;
        const action = await vscode.window.showInformationMessage(
          `翻译为${label}：${preview}`,
          '复制译文',
          '查看输出'
        );

        if (action === '复制译文') {
          await vscode.env.clipboard.writeText(body);
          vscode.window.showInformationMessage('译文已复制到剪贴板。');
        } else if (action === '查看输出') {
          getOutput().show(true);
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        vscode.window.showErrorMessage(`翻译失败：${message}`);
      }
    }
  );
}

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('cursorTranslate.translateToChinese', () => runTranslate('zh-CN')),
    vscode.commands.registerCommand('cursorTranslate.translateToEnglish', () => runTranslate('en'))
  );
}

function deactivate() {
  outputChannel?.dispose();
  outputChannel = undefined;
}

module.exports = { activate, deactivate };