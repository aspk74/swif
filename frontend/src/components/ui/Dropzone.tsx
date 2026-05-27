import { useState, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { UploadCloud, Loader2 } from "lucide-react";
import { uploadPolicyPdf } from "../../lib/api";

interface DropzoneProps {
  onUploadComplete: () => void;
  onToast: (message: string, type: "success" | "error") => void;
}

export function Dropzone({ onUploadComplete, onToast }: DropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progressMsg, setProgressMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragActive(false);

      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        await processFile(files[0]);
      }
    },
    [] // eslint-disable-line react-hooks/exhaustive-deps
  );

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await processFile(files[0]);
    }
  };

  const processFile = async (file: File) => {
    if (file.type !== "application/pdf") {
      onToast("Only PDF files are supported.", "error");
      return;
    }

    setIsUploading(true);
    setProgressMsg("Initializing upload...");

    try {
      const result = await uploadPolicyPdf(file, (msg) => {
        setProgressMsg(msg);
      });

      onToast(
        `Success! Extracted ${result.extracted} rules (${result.inserted} new, ${result.updated} updated).`,
        "success"
      );
      onUploadComplete();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Upload failed.";
      onToast(msg, "error");
    } finally {
      setIsUploading(false);
      setProgressMsg("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <div style={{ marginBottom: 24 }}>
      <input
        type="file"
        accept="application/pdf"
        style={{ display: "none" }}
        ref={fileInputRef}
        onChange={handleFileSelect}
      />

      <motion.div
        className="glass-card"
        style={{
          border: isDragActive
            ? "2px dashed rgba(59, 130, 246, 0.5)"
            : "1px dashed var(--border-subtle)",
          background: isDragActive
            ? "rgba(59, 130, 246, 0.05)"
            : "var(--bg-card)",
          padding: "32px",
          textAlign: "center",
          cursor: isUploading ? "default" : "pointer",
          position: "relative",
          overflow: "hidden",
        }}
        animate={{
          boxShadow: isDragActive
            ? "0 0 40px rgba(59, 130, 246, 0.15)"
            : "0 0 0px rgba(0,0,0,0)",
        }}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => {
          if (!isUploading) fileInputRef.current?.click();
        }}
      >
        <AnimatePresence mode="wait">
          {isUploading ? (
            <motion.div
              key="uploading"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 16,
              }}
            >
              <div style={{ position: "relative" }}>
                <Loader2
                  size={32}
                  style={{ color: "var(--cyan)" }}
                  className="animate-spin"
                />
                <motion.div
                  style={{
                    position: "absolute",
                    inset: -8,
                    borderRadius: "50%",
                    border: "2px solid rgba(34, 211, 238, 0.2)",
                    borderTopColor: "transparent",
                  }}
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>
                  Processing Policy Document
                </div>
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    marginTop: 4,
                  }}
                >
                  {progressMsg}
                </div>
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 12,
              }}
            >
              <div
                style={{
                  width: 48,
                  height: 48,
                  borderRadius: "50%",
                  background: isDragActive
                    ? "linear-gradient(135deg, rgba(59,130,246,0.2), rgba(99,102,241,0.2))"
                    : "rgba(255, 255, 255, 0.05)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  transition: "background 0.3s ease",
                }}
              >
                <UploadCloud
                  size={24}
                  style={{
                    color: isDragActive ? "#93c5fd" : "var(--text-muted)",
                    transition: "color 0.3s ease",
                  }}
                />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: "0.95rem" }}>
                  <span style={{ color: "var(--text-primary)" }}>
                    Click to upload
                  </span>{" "}
                  or drag and drop
                </div>
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "var(--text-muted)",
                    marginTop: 4,
                  }}
                >
                  PDF files only (max 20MB)
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
