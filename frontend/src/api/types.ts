export interface User {
  id: number;
  email: string;
  role: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Photo {
  id: number;
  url: string;
  det_score: number | null;
  face_px: number | null;
}

export interface Student {
  id: number;
  roll_no: string;
  full_name: string;
  email: string | null;
  is_active: boolean;
  consent_recorded: boolean;
  consent_date: string | null;
  embedding_count: number;
  ready: boolean;
}

export interface StudentDetail extends Student {
  photos: Photo[];
}

export interface PhotoUploadResult {
  filename: string;
  accepted: boolean;
  reason: string | null;
  embedding_id: number | null;
}

export interface PhotoUploadResponse {
  results: PhotoUploadResult[];
  embedding_count: number;
  ready: boolean;
  warnings: string[];
}

export interface Course {
  id: number;
  code: string;
  name: string;
  student_count: number;
}

export interface CourseDetail extends Course {
  students: Student[];
}

export interface AttendanceRecord {
  student_id: number;
  roll_no: string;
  full_name: string;
  status: 'present' | 'absent' | 'needs_review';
  similarity: number | null;
  margin: number | null;
  bbox: [number, number, number, number] | null;
  marked_by: 'auto' | 'teacher';
}

export interface UnmatchedFace {
  bbox: [number, number, number, number];
  label: 'unknown' | 'unrecognizable';
  det_score: number;
}

export interface Counts {
  enrolled: number;
  faces_detected: number;
  present: number;
  needs_review: number;
  absent: number;
  unknown_faces: number;
  unrecognizable_faces: number;
}

export interface SessionData {
  id: number;
  course: Course;
  session_date: string;
  period: number;
  status: 'done' | 'needs_review' | 'failed';
  detector_version: string | null;
  embedder_version: string | null;
  counts: Counts;
  banner: string | null;
  original_url: string | null;
  annotated_url: string | null;
  records: AttendanceRecord[];
  unmatched_faces: UnmatchedFace[];
  processing_ms: number | null;
}

export interface SessionSummary {
  id: number;
  course_id: number;
  course_code: string;
  session_date: string;
  period: number;
  status: string;
  faces_detected: number;
  present: number;
  absent: number;
  needs_review: number;
}

export interface AttendanceHistoryRow {
  session_id: number;
  session_date: string;
  period: number;
  course_code: string;
  roll_no: string;
  full_name: string;
  status: string;
  marked_by: string;
}

export interface AttendanceSummary {
  roll_no: string;
  full_name: string;
  sessions: number;
  present: number;
  absent: number;
  percent: number;
}

export interface HealthInfo {
  status: string;
  detector: string;
  embedder: string;
  models_loaded: boolean;
  students: number;
  embeddings: number;
}
