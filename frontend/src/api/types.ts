export type Role = 'admin' | 'student';

export interface LoginResponse {
  access_token: string;
  role: Role;
  name: string;
}

export interface Student {
  id: number;
  roll_no: string;
  full_name: string;
  photo_count: number;
}

export interface Photo {
  id: number;
  url: string;
}

export interface StudentDetail extends Student {
  photos: Photo[];
}

export interface PhotoUploadResponse {
  results: { filename: string; accepted: boolean; reason: string | null }[];
}

export interface AttendanceRecord {
  student_id: number;
  roll_no: string;
  full_name: string;
  status: 'present' | 'absent';
  similarity: number | null;
}

export interface Session {
  id: number;
  created_at: string;
  total: number;
  present: number;
  absent: number;
  avg_match: number | null;
  image_urls: string[];
  records: AttendanceRecord[];
}

export interface MyAttendance {
  name: string;
  roll_no: string;
  total: number;
  present: number;
  absent: number;
  percentage: number;
  records: { session_id: number; date: string; status: 'present' | 'absent' }[];
}
