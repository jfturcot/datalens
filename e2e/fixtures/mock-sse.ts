import type { Page } from "@playwright/test";

/**
 * Build a single SSE event string.
 */
function sse(event: string, data: object): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

interface MockResponse {
  content: string;
  sql?: string;
  display?: object;
  tools?: string[];
}

function buildBody(r: MockResponse): string {
  let body = "";
  for (const tool of r.tools ?? []) {
    body += sse("tool_start", { tool });
    body += sse("tool_end", { summary: `Returned results` });
  }
  const complete: Record<string, unknown> = { content: r.content };
  if (r.sql) complete.sql = r.sql;
  if (r.display) complete.display = r.display;
  body += sse("message_complete", complete);
  return body;
}

const GREETING: MockResponse = {
  content:
    "This dataset contains **20 rows** and **7 columns** covering startup companies. " +
    "Key columns include `company_name`, `industry_vertical`, `arr_thousands`, " +
    "`employee_count`, `churn_rate_percent`, and `yoy_growth_rate_percent`.\n\n" +
    "Here are some questions you could ask:\n" +
    "- What is the average ARR by industry?\n" +
    "- Which company has the highest growth rate?\n" +
    "- Show me a bar chart of ARR by company",
};

const AVG_ARR: MockResponse = {
  content:
    "The average ARR for fintech companies is approximately **1,330** thousand dollars " +
    "(based on 6 fintech companies in the dataset).",
  sql: "SELECT AVG(arr_thousands) as avg_arr FROM data WHERE industry_vertical = 'Fintech'",
  tools: ["execute_query"],
};

const HIGHEST_GROWTH: MockResponse = {
  content:
    "**PivotAI** has the highest year-over-year growth rate at **85.2%**. " +
    "PivotAI is an AI/ML company founded in 2021 with an ARR of $420K.",
  sql: "SELECT company_name, yoy_growth_rate_percent FROM data ORDER BY yoy_growth_rate_percent DESC LIMIT 1",
  tools: ["execute_query"],
};

const BAR_CHART: MockResponse = {
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
};

const FALLBACK: MockResponse = {
  content:
    "I can't execute that directly. Could you rephrase your question? " +
    "I can help you explore the dataset, run queries, and create visualizations.",
};

function matchResponse(content: string): MockResponse {
  const lower = content.toLowerCase();
  if (lower.includes("describe this dataset")) return GREETING;
  if (lower.includes("average arr")) return AVG_ARR;
  if (lower.includes("highest growth")) return HIGHEST_GROWTH;
  if (lower.includes("bar chart")) return BAR_CHART;
  return FALLBACK;
}

/**
 * Register a Playwright route handler that intercepts LLM chat requests
 * and returns canned SSE responses. All other API calls pass through.
 */
export async function mockLLMResponses(page: Page): Promise<void> {
  await page.route("**/api/conversations/*/messages", async (route) => {
    const request = route.request();
    if (request.method() !== "POST") {
      return route.continue();
    }

    const body = request.postDataJSON() as { content: string };
    const response = matchResponse(body.content);

    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      headers: {
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      },
      body: buildBody(response),
    });
  });
}
