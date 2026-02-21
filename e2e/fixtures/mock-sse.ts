import type { Page } from "@playwright/test";

interface MockResponse {
  content: string;
  sql?: string;
  display?: object;
  tools?: string[];
}

const RESPONSES: Record<string, MockResponse> = {
  greeting: {
    content:
      "This dataset contains **20 rows** and **7 columns** covering startup companies. " +
      "Key columns include `company_name`, `industry_vertical`, `arr_thousands`, " +
      "`employee_count`, `churn_rate_percent`, and `yoy_growth_rate_percent`.\n\n" +
      "Here are some questions you could ask:\n" +
      "- What is the average ARR by industry?\n" +
      "- Which company has the highest growth rate?\n" +
      "- Show me a bar chart of ARR by company",
  },
  avg_arr: {
    content:
      "The average ARR for fintech companies is approximately **1,330** thousand dollars " +
      "(based on 6 fintech companies in the dataset).",
    sql: "SELECT AVG(arr_thousands) as avg_arr FROM data WHERE industry_vertical = 'Fintech'",
    tools: ["execute_query"],
  },
  highest_growth: {
    content:
      "**PivotAI** has the highest year-over-year growth rate at **85.2%**. " +
      "PivotAI is an AI/ML company founded in 2021 with an ARR of $420K.",
    sql: "SELECT company_name, yoy_growth_rate_percent FROM data ORDER BY yoy_growth_rate_percent DESC LIMIT 1",
    tools: ["execute_query"],
  },
  bar_chart: {
    content: "Here's the average ARR by industry vertical:",
    sql: "SELECT industry_vertical, AVG(arr_thousands) as avg_arr FROM data GROUP BY industry_vertical ORDER BY avg_arr DESC",
    tools: ["execute_query"],
    display: {
      type: "bar_chart",
      title: "Average ARR by Industry Vertical",
      data: [
        { industry_vertical: "SaaS", avg_arr: 3667 },
        { industry_vertical: "Security", avg_arr: 3800 },
        { industry_vertical: "HealthTech", avg_arr: 1347 },
        { industry_vertical: "Fintech", avg_arr: 1330 },
        { industry_vertical: "CleanTech", avg_arr: 1683 },
        { industry_vertical: "AI/ML", avg_arr: 550 },
        { industry_vertical: "DevOps", avg_arr: 950 },
      ],
      x_axis: "industry_vertical",
      y_axis: "avg_arr",
    },
  },
  fallback: {
    content:
      "I can't execute that directly. Could you rephrase your question? " +
      "I can help you explore the dataset, run queries, and create visualizations.",
  },
};

/**
 * Monkey-patch window.fetch inside the page to intercept LLM chat POST
 * requests and return canned SSE responses via a proper ReadableStream.
 */
export async function mockLLMResponses(page: Page): Promise<void> {
  await page.addInitScript((responsesJson: string) => {
    const responses = JSON.parse(responsesJson);

    function matchKey(content: string): string {
      const lower = content.toLowerCase();
      if (lower.includes("describe this dataset")) return "greeting";
      if (lower.includes("bar chart")) return "bar_chart";
      if (lower.includes("average arr")) return "avg_arr";
      if (lower.includes("highest growth")) return "highest_growth";
      return "fallback";
    }

    function buildSSE(r: {
      content: string;
      sql?: string;
      display?: object;
      tools?: string[];
    }): string {
      let body = "";
      for (const tool of r.tools ?? []) {
        body += `event: tool_start\ndata: ${JSON.stringify({ tool })}\n\n`;
        body += `event: tool_end\ndata: ${JSON.stringify({ summary: "Returned results" })}\n\n`;
      }
      const complete: Record<string, unknown> = { content: r.content };
      if (r.sql) complete.sql = r.sql;
      if (r.display) complete.display = r.display;
      body += `event: message_complete\ndata: ${JSON.stringify(complete)}\n\n`;
      return body;
    }

    const originalFetch = window.fetch.bind(window);

    window.fetch = async function (
      input: RequestInfo | URL,
      init?: RequestInit,
    ): Promise<Response> {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.href
            : input.url;

      const isMessagePost =
        /\/api\/conversations\/[^/]+\/messages/.test(url) &&
        init?.method === "POST";

      if (!isMessagePost) {
        return originalFetch(input, init);
      }

      const reqBody = JSON.parse(init!.body as string) as { content: string };
      const key = matchKey(reqBody.content);
      const mockResp = responses[key];
      const sseText = buildSSE(mockResp);
      const encoded = new TextEncoder().encode(sseText);

      const stream = new ReadableStream({
        start(controller) {
          // Emit all events, then close the stream
          controller.enqueue(encoded);
          controller.close();
        },
      });

      return new Response(stream, {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      });
    } as typeof window.fetch;
  }, JSON.stringify(RESPONSES));
}
