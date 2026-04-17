export type APIStyle = "chat_completions" | "responses";

export interface HealthResponse {
  status: string;
}

export interface DatabaseHealthResponse extends HealthResponse {
  database: string;
}

export interface QuestionStatsResponse {
  total_questions: number;
  questions_with_content_images: number;
  questions_with_answer_images: number;
  questions_with_analysis_images: number;
}

export interface EvaluationStatsResponse {
  total_eval_rows: number;
  attempt_1_completed: number;
  attempt_2_completed: number;
  attempt_3_completed: number;
}

export interface EvalModelRead {
  model_id: number;
  model_name: string;
  release_date: string | null;
  api_url: string;
  api_style: APIStyle;
  api_model: string;
  has_api_key: boolean;
  is_configured: boolean;
  is_active: boolean;
  sort_order: number;
}

export interface EvalModelUpdate {
  model_name?: string;
  release_date?: string | null;
  api_url?: string;
  api_style?: APIStyle;
  api_model?: string;
  api_key?: string;
  is_active?: boolean;
  sort_order?: number;
}

export interface EvalModelProbeResponse {
  model_id: number;
  model_name: string;
  api_style: APIStyle;
  api_model: string;
  ok: boolean;
  latency_ms: number;
  provider_error: string | null;
  response_text_preview: string | null;
}

export interface EvaluationPreviewResponse {
  question_id: number;
  model_id: number;
  model_name: string;
  model_is_active: boolean;
  model_is_configured: boolean;
  prompt_text: string;
  content_image_paths: string[];
}

export interface EvaluationPayloadPreviewResponse {
  question_id: number;
  model_id: number;
  model_name: string;
  api_style: APIStyle;
  api_model: string;
  request_url: string;
  payload: Record<string, unknown>;
}

export interface EvaluationRunRequest {
  question_id: number;
  model_id: number;
  attempt: number;
  persist_result: boolean;
  request_timeout_seconds?: number | null;
}

export type EvaluationExecutionMode = "generate_only" | "judge_only" | "generate_and_judge";
export type EvaluationRunStatus = "correct" | "incorrect" | "error" | "unknown";
export type EvaluationGenerateStatus = "generated" | "error";

export interface EvaluationGenerateRequest {
  question_id: number;
  model_id: number;
  attempt: number;
  persist_result: boolean;
  request_timeout_seconds?: number | null;
}

export interface EvaluationJudgeRequest {
  question_id: number;
  model_id: number;
  attempt: number;
  persist_result: boolean;
}

export interface EvaluationGenerateSummaryResponse {
  eval_result_id: number;
  question_id: number;
  model_id: number;
  model_name: string;
  attempt: number;
  status: EvaluationGenerateStatus;
  error: string | null;
  finished_at: string;
}

export interface EvaluationJudgeSummaryResponse {
  eval_result_id: number;
  question_id: number;
  model_id: number;
  model_name: string;
  attempt: number;
  status: EvaluationRunStatus;
  error: string | null;
  finished_at: string;
}

export interface EvaluationRunSummaryResponse {
  eval_result_id: number;
  question_id: number;
  model_id: number;
  model_name: string;
  attempt: number;
  status: EvaluationRunStatus;
  error: string | null;
  finished_at: string;
}

export type BatchSelectionMode = "pending_all" | "pending_limit" | "range" | "manual";
export type BatchJobStatus = "queued" | "running" | "completed" | "cancelled" | "failed";
export type BatchItemStatus =
  | "pending"
  | "running"
  | "correct"
  | "incorrect"
  | "error"
  | "unknown"
  | "cancelled";

export interface EvaluationBatchJobCreateRequest {
  model_id: number;
  attempt: number;
  persist_result: boolean;
  request_timeout_seconds?: number | null;
  execution_mode: EvaluationExecutionMode;
  selection_mode: BatchSelectionMode;
  limit?: number | null;
  question_id_start?: number | null;
  question_id_end?: number | null;
  question_ids?: number[] | null;
  force: boolean;
}

export interface EvaluationBatchJobItemResponse {
  question_id: number;
  eval_result_id: number | null;
  status: BatchItemStatus;
  error: string | null;
  finished_at: string | null;
}

export interface EvaluationBatchJobSummaryResponse {
  job_id: string;
  model_id: number;
  model_name: string;
  attempt: number;
  execution_mode: EvaluationExecutionMode;
  selection_mode: BatchSelectionMode;
  persist_result: boolean;
  request_timeout_seconds: number | null;
  force: boolean;
  status: BatchJobStatus;
  total_questions: number;
  completed_questions: number;
  current_question_id: number | null;
  generated_count: number;
  correct_count: number;
  incorrect_count: number;
  error_count: number;
  unknown_count: number;
  cancelled_count: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  job_error: string | null;
}

export interface EvaluationBatchJobResponse extends EvaluationBatchJobSummaryResponse {
  items: EvaluationBatchJobItemResponse[];
}

export type EvaluationResultAttemptStatus = "pending" | "generated" | "correct" | "incorrect" | "error";
export type EvaluationResultClearScope = "generation_data" | "judge_data";

export interface EvaluationResultAttemptRead {
  attempt: number;
  status: EvaluationResultAttemptStatus;
  result: number | null;
  judge_result: number | null;
  result_override: number | null;
  is_result_overridden: boolean;
  result_overridden_at: string | null;
  response_text: string | null;
  judge_feedback: string | null;
  error: string | null;
  finished_at: string | null;
  has_response_text: boolean;
  has_judge_feedback: boolean;
}

export interface EvaluationResultQuestionRead {
  question_id: number;
  parent_id: string;
  subject: string;
  stage: string;
  grade: string;
  textbook_chapter: string;
  knowledge_level_1: string;
  knowledge_level_2: string;
  knowledge_level_3: string;
  question_type: string;
  difficulty: string;
  content_text: string;
  content_image_paths: string[];
  answer_text: string;
  answer_image_paths: string[];
  analysis_text: string;
  analysis_image_paths: string[];
}

export interface EvaluationResultModelRead {
  model_id: number;
  model_name: string;
  api_style: APIStyle;
  api_model: string;
  release_date: string | null;
  is_active: boolean;
}

export interface EvaluationResultRowResponse {
  eval_result_id: number;
  question: EvaluationResultQuestionRead;
  model: EvaluationResultModelRead;
  attempt_1: EvaluationResultAttemptRead;
  attempt_2: EvaluationResultAttemptRead;
  attempt_3: EvaluationResultAttemptRead;
  latest_finished_at: string | null;
  has_any_data: boolean;
}

export interface EvaluationResultListResponse {
  total: number;
  limit: number;
  offset: number;
  items: EvaluationResultRowResponse[];
}

export interface EvaluationResultQueryParams {
  model_id?: number;
  question_id?: number;
  question_id_start?: number;
  question_id_end?: number;
  attempt?: number;
  attempt_statuses?: EvaluationResultAttemptStatus[];
  only_with_data?: boolean;
  limit?: number;
  offset?: number;
}

export interface EvaluationResultClearRequest {
  attempt: number;
  scope: EvaluationResultClearScope;
}

export interface EvaluationResultOverrideRequest {
  attempt: number;
  result: 0 | 1 | null;
}

export interface APIErrorPayload {
  detail?: string;
}
