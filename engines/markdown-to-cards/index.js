#!/usr/bin/env node
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import http from "http";
import { CARD_STYLE_IDS, COLOR_SCHEME_IDS, DEFAULT_COLOR_SCHEME_ID, renderMarkdownToCards } from "./lib/render.js";

// ============================================================
// MCP Server
// ============================================================
const server = new Server(
  { name: "mcp-md2card", version: "2.1.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    {
      name: "markdown_to_cards",
      description: "将 Markdown 文章转换为小红书风格卡片图片（PNG）。自动生成封面 + 正文多页卡片；正文支持标题、引用、代码块、表格和 Markdown 图片；默认 legacy 样式使用 claude-orange-light 配色，也可选择 coral/lavender/editorial/sage/prologue/classic/monograph，以及与公众号发布对齐的 claude/medium/minimal/openai/cards-claude/monograph_all_both 等模板风格；小红书官方风格启发的封面模板使用 xhs-* style。color_scheme 仅适用于 legacy 默认模板；其他风格可用 accent_color/background_color/text_color/font_size 手动微调。返回所有生成图片的路径。",
      inputSchema: {
        type: "object",
        properties: {
          markdown: { type: "string", description: "要转换的 Markdown 文章内容（支持 H1 标题作为封面标题）" },
          account: { type: "string", description: "小红书账号 slot；提供后会从 ~/.xhs/accounts.json 读取该账号的 card_config 作为默认卡片配置（可选）" },
          output_dir: { type: "string", description: "图片输出目录（可选，默认为临时目录）" },
          base_dir: { type: "string", description: "解析 Markdown 相对图片路径的基准目录（可选，默认当前工作目录）" },
          cover_bg_path: { type: "string", description: "封面底图路径（可选，默认使用内置底图）" },
          cover_image_path: { type: "string", description: "图片封面样式使用的封面图片路径或 URL（可选）" },
          cover_style: { type: "string", enum: ["template", "image", "both"], description: "封面样式：template 为纯文字封面，image 为文字+图片封面，both 同时生成两种（可选；提供 cover_image_path 时默认 image）" },
          cover_template: { type: "string", enum: ["style", "default"], description: "封面模板来源：style 使用当前主题封面，default 使用默认 legacy 封面但正文仍用当前主题（可选，默认 style）" },
          style: { type: "string", enum: CARD_STYLE_IDS, description: "卡片模板风格（可选，默认 legacy）" },
          color_scheme: { type: "string", enum: COLOR_SCHEME_IDS, description: `legacy 默认模板专用预设配色（可选，默认 ${DEFAULT_COLOR_SCHEME_ID}；style 非 legacy 时不要传）` },
          chapter_label: { type: "string", description: "新主题封面/页眉显示的章节或栏目标签（可选，默认 精选长图文）" },
          cover_variant: { type: "string", enum: ["primary", "alt", "all"], description: "新主题封面版式（可选，默认 primary；all 同时生成 primary 和 alt）" },
          accent_color: { type: "string", description: "强调色手动覆盖，用于标题、链接、装饰线等（可选）" },
          background_color: { type: "string", description: "正文/模板背景色手动覆盖（可选）" },
          text_color: { type: "string", description: "正文文字颜色手动覆盖（可选）" },
          font_size: { type: "number", description: "正文基础字号 px（可选，默认 25）" },
        },
        required: ["markdown"],
      },
    },
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  if (name === "markdown_to_cards") {
    if (!args?.markdown) {
      return { content: [{ type: "text", text: "Error: markdown is required" }], isError: true };
    }
    try {
      const result = await renderMarkdownToCards(args.markdown, {
        account: args.account,
        output_dir: args.output_dir,
        base_dir: args.base_dir,
        cover_bg_path: args.cover_bg_path,
        cover_image_path: args.cover_image_path,
        cover_style: args.cover_style,
        cover_template: args.cover_template,
        style: args.style,
        color_scheme: args.color_scheme,
        chapter_label: args.chapter_label,
        cover_variant: args.cover_variant,
        accent_color: args.accent_color,
        background_color: args.background_color,
        text_color: args.text_color,
        font_size: args.font_size,
      });

      const lines = [
        `生成 ${result.total_pages} 张卡片（含封面）`,
        `输出目录: ${result.output_dir}`,
        "文件列表:",
        ...result.files.map((f, i) => `  ${i + 1}. ${f}`),
      ];
      if (result.warnings?.length) {
        lines.push("警告:", ...result.warnings.map((w) => `  - ${w}`));
      }

      return {
        content: [{ type: "text", text: lines.join("\n") }],
      };
    } catch (err) {
      return { content: [{ type: "text", text: `Error: ${err.message}` }], isError: true };
    }
  }

  return { content: [{ type: "text", text: `Unknown tool: ${name}` }], isError: true };
});

const httpFlag = process.argv.indexOf("--http");
if (httpFlag !== -1) {
  const port = parseInt(process.argv[httpFlag + 1]) || 18070;
  const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
  const httpServer = http.createServer(async (req, res) => {
    if (req.method === "POST" && req.url === "/mcp") {
      await transport.handleRequest(req, res);
    } else if (req.method === "GET" && req.url === "/mcp") {
      await transport.handleRequest(req, res);
    } else if (req.method === "DELETE" && req.url === "/mcp") {
      await transport.handleRequest(req, res);
    } else {
      res.writeHead(404); res.end();
    }
  });
  await server.connect(transport);
  httpServer.listen(port, () => {
    process.stderr.write(`markdown-to-cards MCP HTTP server running on port ${port}\n`);
  });
} else {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}
