import type {
  APIErrorPayload,
  DatabaseHealthResponse,
  EvalModelProbeResponse,
  EvalModelRead,
  EvalModelUpdate,
  EvaluationBatchJobCreateRequest,
  EvaluationBatchJobResponse,
  EvaluationBatchJobSummaryResponse,
  EvaluationResultClearRequest,
  EvaluationResultListResponse,
  EvaluationResultOverrideRequest,
  EvaluationResultQueryParams,
  EvaluationResultRowResponse,
  EvaluationGenerateRequest,
  EvaluationGenerateSummaryResponse,
  EvaluationJudgeRequest,
  EvaluationJudgeSummaryResponse,
  EvaluationPayloadPreviewResponse,
  EvaluationPreviewResponse,
  EvaluationRunRequest,
  EvaluationRunSummaryResponse,
  EvaluationStatsResponse,
  HealthResponse,
  QuestionStatsResponse,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";

function encodePathSegments(path: string): string {
  return path
    .split("/")
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment))
    .join("/");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;

    try {
      const payload = (await response.json()) as APIErrorPayload;
      if (payload.detail) {
        message = payload.detail;
      }
    } catch {
      // Ignore JSON parsing errors and keep the HTTP status text.
    }

    throw new Error(message);
  }

  return (await response.json()) as T;
}

export const api = {
  getHealth() {
    return request<HealthResponse>("/health");
  },
  getDatabaseHealth() {
    return request<DatabaseHealthResponse>("/health/db");
  },
  getQuestionStats() {
    return request<QuestionStatsResponse>("/overview/questions");
  },
  getEvaluationStats() {
    return request<EvaluationStatsResponse>("/overview/evaluations");
  },
  listModels() {
    return request<EvalModelRead[]>("/models");
  },
  getModel(modelId: number) {
    return request<EvalModelRead>(`/models/${modelId}`);
  },
  updateModel(modelId: number, payload: EvalModelUpdate) {
    return request<EvalModelRead>(`/models/${modelId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },
  probeModel(modelId: number) {
    return request<EvalModelProbeResponse>(`/models/${modelId}/probe`, {
      method: "POST",
    });
  },
  previewEvaluation(payload: { question_id: number; model_id: number }) {
    return request<EvaluationPreviewResponse>("/evaluations/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  previewEvaluationPayload(payload: { question_id: number; model_id: number }) {
    return request<EvaluationPayloadPreviewResponse>("/evaluations/payload-preview", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  generateEvaluation(payload: EvaluationGenerateRequest) {
    return request<EvaluationGenerateSummaryResponse>("/evaluations/generate", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  judgeEvaluation(payload: EvaluationJudgeRequest) {
    return request<EvaluationJudgeSummaryResponse>("/evaluations/judge", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  runEvaluation(payload: EvaluationRunRequest) {
    return request<EvaluationRunSummaryResponse>("/evaluations/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  listBatchJobs() {
    return request<EvaluationBatchJobSummaryResponse[]>("/evaluations/batch-jobs");
  },
  createBatchJob(payload: EvaluationBatchJobCreateRequest) {
    return request<EvaluationBatchJobResponse>("/evaluations/batch-jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getBatchJob(jobId: string) {
    return request<EvaluationBatchJobResponse>(`/evaluations/batch-jobs/${jobId}`);
  },
  cancelBatchJob(jobId: string) {
    return request<EvaluationBatchJobResponse>(`/evaluations/batch-jobs/${jobId}/cancel`, {
      method: "POST",
    });
  },
  listEvaluationResults(params: EvaluationResultQueryParams) {
    const searchParams = new URLSearchParams();
    if (params.model_id !== undefined) {
      searchParams.set("model_id", String(params.model_id));
    }
    if (params.question_id !== undefined) {
      searchParams.set("question_id", String(params.question_id));
    }
    if (params.question_id_start !== undefined) {
      searchParams.set("question_id_start", String(params.question_id_start));
    }
    if (params.question_id_end !== undefined) {
      searchParams.set("question_id_end", String(params.question_id_end));
    }
    if (params.attempt !== undefined) {
      searchParams.set("attempt", String(params.attempt));
    }
    if (params.attempt_statuses?.length) {
      searchParams.set("attempt_statuses", params.attempt_statuses.join(","));
    }
    if (params.only_with_data !== undefined) {
      searchParams.set("only_with_data", String(params.only_with_data));
    }
    if (params.limit !== undefined) {
      searchParams.set("limit", String(params.limit));
    }
    if (params.offset !== undefined) {
      searchParams.set("offset", String(params.offset));
    }
    const query = searchParams.toString();
    return request<EvaluationResultListResponse>(`/evaluations/results${query ? `?${query}` : ""}`);
  },
  clearEvaluationResultAttempt(evalResultId: number, payload: EvaluationResultClearRequest) {
    return request<EvaluationResultRowResponse>(`/evaluations/results/${evalResultId}/clear`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  overrideEvaluationResultAttempt(evalResultId: number, payload: EvaluationResultOverrideRequest) {
    return request<EvaluationResultRowResponse>(`/evaluations/results/${evalResultId}/override`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getImageUrl(path: string) {
    const normalizedPath = path.replace(/\\/g, "/");
    if (/^(https?:|data:)/.test(normalizedPath) || normalizedPath.startsWith("/")) {
      return normalizedPath;
    }
    const imageRelativePath = normalizedPath.startsWith("images/")
      ? normalizedPath.slice("images/".length)
      : normalizedPath;
    return `${API_BASE_URL}/assets/images/${encodePathSegments(imageRelativePath)}`;
  },
};
