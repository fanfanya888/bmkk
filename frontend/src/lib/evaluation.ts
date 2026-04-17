export interface ParsedQuestionSpec {
  ids: number[];
  warnings: string[];
}

function parsePositiveInteger(raw: string): number | null {
  if (!/^\d+$/.test(raw)) {
    return null;
  }

  const value = Number(raw);
  if (!Number.isSafeInteger(value) || value <= 0) {
    return null;
  }

  return value;
}

export function parseQuestionSpec(input: string): ParsedQuestionSpec {
  const tokens = input
    .split(/[\s,，、;；]+/)
    .map((token) => token.trim())
    .filter(Boolean);
  const ids = new Set<number>();
  const warnings: string[] = [];

  tokens.forEach((token) => {
    const rangeMatch = token.match(/^(\d+)-(\d+)$/);
    if (rangeMatch) {
      const start = parsePositiveInteger(rangeMatch[1]);
      const end = parsePositiveInteger(rangeMatch[2]);
      if (!start || !end) {
        warnings.push(`无法解析区间: ${token}`);
        return;
      }

      if (start > end) {
        warnings.push(`区间起点大于终点: ${token}`);
        return;
      }

      for (let value = start; value <= end; value += 1) {
        ids.add(value);
      }
      return;
    }

    const value = parsePositiveInteger(token);
    if (!value) {
      warnings.push(`无法解析 question_id: ${token}`);
      return;
    }

    ids.add(value);
  });

  return {
    ids: Array.from(ids).sort((left, right) => left - right),
    warnings,
  };
}

export function formatPercent(value: number, total: number): string {
  if (total <= 0) {
    return "0%";
  }

  return `${((value / total) * 100).toFixed(1)}%`;
}

export function countByResult(results: Array<{ status: "correct" | "incorrect" | "error" | "unknown" }>) {
  return results.reduce(
    (accumulator, item) => {
      if (item.status === "error") {
        accumulator.error += 1;
      } else if (item.status === "correct") {
        accumulator.correct += 1;
      } else if (item.status === "incorrect") {
        accumulator.incorrect += 1;
      } else {
        accumulator.unknown += 1;
      }

      return accumulator;
    },
    {
      correct: 0,
      incorrect: 0,
      error: 0,
      unknown: 0,
    },
  );
}

export function countBatchItems(
  items: Array<{ status: "pending" | "running" | "generated" | "correct" | "incorrect" | "error" | "unknown" | "cancelled" }>,
) {
  return items.reduce(
    (accumulator, item) => {
      accumulator[item.status] += 1;
      return accumulator;
    },
    {
      pending: 0,
      running: 0,
      generated: 0,
      correct: 0,
      incorrect: 0,
      error: 0,
      unknown: 0,
      cancelled: 0,
    },
  );
}
