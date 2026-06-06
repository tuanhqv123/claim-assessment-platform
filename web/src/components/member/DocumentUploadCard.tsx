"use client";

import { useEffect, useRef, useState } from "react";
import { Upload, Typography, Flex, App, Spin, Tag, Button, Divider } from "antd";
import {
  InboxOutlined,
  LoadingOutlined,
  FileTextOutlined,
  UploadOutlined,
  WarningOutlined,
  DeleteOutlined,
  CloseOutlined,
  CheckCircleFilled,
} from "@ant-design/icons";
import type { UploadProps, UploadFile } from "antd/es/upload/interface";
import {
  ocrExtractStream,
  type OcrExtractResult,
  type OcrStepEvent,
} from "@/lib/memberApi";
import ExtractionResult from "./ExtractionResult";

const { Text } = Typography;

/** Merge a streamed step event into the accumulated list (keyed by step). */
function applyStep(steps: OcrStepEvent[], ev: OcrStepEvent): OcrStepEvent[] {
  const idx = steps.findIndex((s) => s.step === ev.step);
  if (idx >= 0) {
    const next = [...steps];
    next[idx] = { ...next[idx], ...ev };
    return next;
  }
  return [...steps, ev];
}

function stepSummary(s: OcrStepEvent): string {
  const d = s.data ?? {};
  if (s.step === "ocr") {
    const cats = Array.isArray(d.categories) ? (d.categories as string[]) : [];
    return `${d.regions ?? "?"} regions${cats.length ? " · " + cats.join(", ") : ""}`;
  }
  if (s.step === "structure") {
    const conf =
      typeof d.confidence === "number" ? ` · ${Math.round((d.confidence as number) * 100)}%` : "";
    return `${d.document_type ?? "?"} · ${d.fields ?? 0} fields${conf}`;
  }
  if (s.step === "validate") {
    const n = (d.issues as number) ?? 0;
    return n ? `${n} issue${n > 1 ? "s" : ""}` : "valid";
  }
  return "";
}

function OcrStepList({ steps }: { steps: OcrStepEvent[] }) {
  if (!steps.length) return null;
  return (
    <Flex vertical gap={6} style={{ paddingInlineStart: 28 }}>
      {steps.map((s) => (
        <Flex key={s.step} align="center" gap={8}>
          {s.status === "done" ? (
            <CheckCircleFilled style={{ color: "#52c41a", fontSize: 13 }} />
          ) : (
            <LoadingOutlined spin style={{ color: "#0d9488", fontSize: 13 }} />
          )}
          <Text style={{ fontSize: 12.5 }}>{s.label ?? s.step}</Text>
          {s.status === "done" && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {stepSummary(s)}
            </Text>
          )}
        </Flex>
      ))}
    </Flex>
  );
}

const { Dragger } = Upload;

const ACCEPT = "image/*,application/pdf,.png,.jpg,.jpeg,.webp,.gif,.bmp,.tif,.tiff,.pdf";

export interface UploadedDoc {
  uid: string;
  file: File;
  fileName: string;
  result: OcrExtractResult;
  fileUrl?: string;
}

function isImageFile(file: File): boolean {
  return file.type.startsWith("image/") || /\.(png|jpe?g|gif|webp|bmp)$/i.test(file.name);
}

interface Props {
  onDocsChange: (docs: UploadedDoc[]) => void;
}

export default function DocumentUploadCard({ onDocsChange }: Props) {
  const { message } = App.useApp();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [docs, setDocs] = useState<UploadedDoc[]>([]);
  const [stepsByUid, setStepsByUid] = useState<Record<string, OcrStepEvent[]>>({});

  const clearSteps = (uid: string) =>
    setStepsByUid((prev) => {
      const next = { ...prev };
      delete next[uid];
      return next;
    });
  const objectUrls = useRef<Map<string, string>>(new Map());
  // Files the user cancelled mid-extraction; their late results are ignored.
  const cancelledUids = useRef<Set<string>>(new Set());

  const updateDocs = (next: UploadedDoc[]) => {
    setDocs(next);
    onDocsChange(next);
  };

  const revokeUrl = (uid: string) => {
    const url = objectUrls.current.get(uid);
    if (url) {
      URL.revokeObjectURL(url);
      objectUrls.current.delete(uid);
    }
  };

  useEffect(() => {
    const urls = objectUrls.current;
    return () => {
      urls.forEach((url) => URL.revokeObjectURL(url));
      urls.clear();
    };
  }, []);

  const beforeUpload = (file: File) => {
    const ok =
      file.type.startsWith("image/") ||
      file.type === "application/pdf" ||
      /\.(png|jpe?g|webp|gif|bmp|tiff?|pdf)$/i.test(file.name);
    if (!ok) {
      message.error(`${file.name} is not an image or PDF.`);
      return Upload.LIST_IGNORE;
    }
    if (file.size > 5 * 1024 * 1024) {
      message.error(`${file.name} exceeds the 5 MB limit.`);
      return Upload.LIST_IGNORE;
    }
    return true;
  };

  const customRequest: UploadProps["customRequest"] = async (options) => {
    const { file, onSuccess, onError } = options;
    const uid = (file as UploadFile).uid;
    try {
      const result = await ocrExtractStream(file as File, (ev) => {
        setStepsByUid((prev) => ({ ...prev, [uid]: applyStep(prev[uid] ?? [], ev) }));
      });
      onSuccess?.(result);
    } catch (err) {
      onError?.(err as Error);
    }
  };

  const handleChange: UploadProps["onChange"] = (info) => {
    // Drop any cancelled files from the displayed list and ignore their results.
    setFileList(info.fileList.filter((f) => !cancelledUids.current.has(f.uid)));
    if (cancelledUids.current.has(info.file.uid)) {
      if (info.file.status === "done" || info.file.status === "error") {
        cancelledUids.current.delete(info.file.uid);
      }
      return;
    }
    if (info.file.status === "done" && info.file.response) {
      const result = info.file.response as OcrExtractResult;
      const realFile = info.file.originFileObj as File;
      revokeUrl(info.file.uid);
      let fileUrl: string | undefined;
      if (realFile && isImageFile(realFile)) {
        fileUrl = URL.createObjectURL(realFile);
        objectUrls.current.set(info.file.uid, fileUrl);
      }
      const entry: UploadedDoc = {
        uid: info.file.uid,
        file: realFile,
        fileName: info.file.name,
        result,
        fileUrl,
      };
      updateDocs([...docs.filter((d) => d.uid !== entry.uid), entry]);
      clearSteps(info.file.uid);
      message.success(`Extracted ${info.file.name}`);
    } else if (info.file.status === "error") {
      message.error(`OCR failed for ${info.file.name}`);
    }
  };

  const removeFile = (uid: string) => {
    revokeUrl(uid);
    setFileList((prev) => prev.filter((f) => f.uid !== uid));
    updateDocs(docs.filter((d) => d.uid !== uid));
    clearSteps(uid);
  };

  const cancelUpload = (uid: string) => {
    cancelledUids.current.add(uid);
    removeFile(uid);
  };

  const uploadProps: UploadProps = {
    accept: ACCEPT,
    multiple: true,
    fileList,
    beforeUpload,
    customRequest,
    onChange: handleChange,
    showUploadList: false,
  };

  // Only hide the dropzone once a document has FINISHED extracting. Hiding it
  // while an upload is still in flight would unmount the <Dragger> that owns the
  // request, so AntD's "done" callback never fires (the upload appears stuck).
  const hasDocs = docs.length > 0;
  const uploadingActive = fileList.some((f) => f.status === "uploading");

  return (
    <>
      <Flex align="center" justify="space-between" gap={8} style={{ marginBottom: 16 }}>
        <Flex align="center" gap={8}>
          <FileTextOutlined style={{ color: "#0d9488", fontSize: 15 }} />
          <Text strong style={{ fontSize: 14 }}>
            Documents &amp; OCR
          </Text>
        </Flex>
        {hasDocs && (
          <Upload {...uploadProps}>
            <Button size="small" icon={<UploadOutlined />}>
              Upload another
            </Button>
          </Upload>
        )}
      </Flex>

      {!hasDocs && (
        <div style={{ display: uploadingActive ? "none" : "block" }}>
          <Dragger {...uploadProps}>
            <Flex vertical align="center" gap={2} style={{ padding: "6px 0" }}>
              <InboxOutlined style={{ fontSize: 30, color: "#0d9488" }} />
              <Text style={{ fontSize: 13.5, fontWeight: 500 }}>
                Click or drag a document to upload
              </Text>
              <Text type="secondary" style={{ fontSize: 12 }}>
                Receipt · discharge summary · lab report · prescription
              </Text>
            </Flex>
          </Dragger>
        </div>
      )}

      {fileList.length > 0 && (
        <Flex vertical>
          {fileList.map((f, i) => {
            const doc = docs.find((d) => d.uid === f.uid);
            return (
              <div key={f.uid}>
                {i > 0 && <Divider style={{ margin: "16px 0" }} />}
                {f.status === "uploading" && (
                  <Flex vertical gap={8}>
                    <Flex align="center" gap={10}>
                      <Spin indicator={<LoadingOutlined spin />} size="small" />
                      <Text style={{ fontSize: 13 }}>{f.name}</Text>
                      <Tag color="processing" style={{ marginInlineStart: "auto", marginInlineEnd: 0 }}>
                        Extracting
                      </Tag>
                      <Button
                        size="small"
                        type="text"
                        icon={<CloseOutlined />}
                        onClick={() => cancelUpload(f.uid)}
                      />
                    </Flex>
                    <OcrStepList steps={stepsByUid[f.uid] ?? []} />
                  </Flex>
                )}
                {f.status === "error" && (
                  <Flex align="center" gap={10}>
                    <WarningOutlined style={{ color: "#ff4d4f" }} />
                    <Text style={{ fontSize: 13 }}>{f.name}</Text>
                    <Tag color="error" style={{ marginInlineStart: "auto" }}>
                      Failed
                    </Tag>
                    <Button
                      size="small"
                      type="text"
                      icon={<DeleteOutlined />}
                      onClick={() => removeFile(f.uid)}
                    />
                  </Flex>
                )}
                {f.status === "done" && doc && (
                  <ExtractionResult
                    fileName={doc.fileName}
                    result={doc.result}
                    fileUrl={doc.fileUrl}
                    onRemove={() => removeFile(f.uid)}
                  />
                )}
              </div>
            );
          })}
        </Flex>
      )}
    </>
  );
}
