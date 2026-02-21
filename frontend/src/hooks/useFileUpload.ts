import { useCallback, useState } from "react";
import { uploadFile } from "../lib/api";
import type { UploadResponse } from "../lib/types";

interface UseFileUploadReturn {
  uploading: boolean;
  progress: number;
  error: string | null;
  upload: (file: File) => Promise<UploadResponse>;
}

export function useFileUpload(): UseFileUploadReturn {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const upload = useCallback(async (file: File): Promise<UploadResponse> => {
    setUploading(true);
    setProgress(0);
    setError(null);

    try {
      // Simulate progress since fetch doesn't support upload progress natively
      const progressTimer = setInterval(() => {
        setProgress((p) => Math.min(p + 10, 90));
      }, 200);

      const result = await uploadFile(file);

      clearInterval(progressTimer);
      setProgress(100);
      setUploading(false);
      return result;
    } catch (err) {
      setUploading(false);
      setProgress(0);
      const msg = err instanceof Error ? err.message : "Upload failed";
      setError(msg);
      throw err;
    }
  }, []);

  return { uploading, progress, error, upload };
}
