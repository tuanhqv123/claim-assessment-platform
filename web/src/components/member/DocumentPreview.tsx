"use client";

import { useState } from "react";
import { Space, Switch, Tabs, Tag, Tooltip, Typography } from "antd";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import type { OcrLayoutElement } from "@/lib/memberApi";

const { Text } = Typography;

/** Category -> AntD palette color, neutral grey fallback. */
const CATEGORY_COLOR: Record<string, string> = {
  title: "#1677ff",
  text: "#52c41a",
  table: "#722ed1",
  figure: "#fa8c16",
  list: "#13c2c2",
  header: "#eb2f96",
  footer: "#a0d911",
  caption: "#fa541c",
  key_value: "#2f54eb",
  signature: "#faad14",
};
const FALLBACK_COLOR = "#8c8c8c";

function colorFor(category: string): string {
  return CATEGORY_COLOR[category.toLowerCase()] ?? FALLBACK_COLOR;
}

interface Props {
  fileUrl: string;
  layout: OcrLayoutElement[];
  /** `[width, height]`. May be `[0, 0]` until the image loads. */
  imageSize: [number, number];
}

export default function DocumentPreview({ fileUrl, layout, imageSize }: Props) {
  const [showBoxes, setShowBoxes] = useState(true);
  const [naturalSize, setNaturalSize] = useState<[number, number] | null>(null);

  const [width, height] =
    imageSize && imageSize[0] > 0 && imageSize[1] > 0 ? imageSize : (naturalSize ?? [0, 0]);

  const categories = Array.from(new Set((layout ?? []).map((el) => el.category)));
  const haveSize = width > 0 && height > 0;

  // Reading-order markdown reconstructed from the layout elements.
  const markdown = (layout ?? [])
    .map((el) => (el.text ?? "").trim())
    .filter(Boolean)
    .join("\n\n");

  const previewPane = (
    <Space direction="vertical" size={8} style={{ width: "100%" }}>
      <Space style={{ width: "100%", justifyContent: "space-between" }} align="center">
        <Space size={4} wrap>
          {categories.length === 0 ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              No regions detected
            </Text>
          ) : (
            categories.map((cat) => (
              <Tag key={cat} color={colorFor(cat)} style={{ marginInlineEnd: 0 }}>
                {cat}
              </Tag>
            ))
          )}
        </Space>
        <Space size={6} align="center">
          <Text type="secondary" style={{ fontSize: 12 }}>
            Boxes
          </Text>
          <Switch
            size="small"
            checked={showBoxes}
            onChange={setShowBoxes}
            disabled={(layout ?? []).length === 0}
          />
        </Space>
      </Space>

      <div
        style={{
          position: "relative",
          display: "inline-block",
          maxWidth: "100%",
          lineHeight: 0,
          border: "1px solid #f0f0f0",
          borderRadius: 8,
          overflow: "hidden",
          background: "#fafafa",
        }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={fileUrl}
          alt="Uploaded document preview"
          style={{ display: "block", maxWidth: "100%", height: "auto" }}
          onLoad={(e) => {
            const img = e.currentTarget;
            if (img.naturalWidth && img.naturalHeight) {
              setNaturalSize([img.naturalWidth, img.naturalHeight]);
            }
          }}
        />
        {showBoxes && haveSize && (layout ?? []).length > 0 && (
          <svg
            viewBox={`0 0 ${width} ${height}`}
            style={{ position: "absolute", inset: 0, width: "100%", height: "100%", pointerEvents: "none" }}
          >
            {layout.map((el, i) => {
              const [x1, y1, x2, y2] = el.bbox;
              const w = Math.max(0, x2 - x1);
              const h = Math.max(0, y2 - y1);
              const color = colorFor(el.category);
              return (
                <Tooltip key={i} title={el.category}>
                  <rect
                    x={x1}
                    y={y1}
                    width={w}
                    height={h}
                    fill={color}
                    fillOpacity={0.1}
                    stroke={color}
                    strokeWidth={Math.max(1, width / 400)}
                    style={{ pointerEvents: "all", cursor: "pointer" }}
                  />
                </Tooltip>
              );
            })}
          </svg>
        )}
      </div>
    </Space>
  );

  const markdownPane = (
    <div
      className="md-content"
      style={{
        maxHeight: 520,
        overflow: "auto",
        padding: "8px 12px",
        fontSize: 13,
        lineHeight: 1.6,
        border: "1px solid #f0f0f0",
        borderRadius: 8,
        background: "#fff",
      }}
    >
      {markdown ? (
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
          {markdown}
        </ReactMarkdown>
      ) : (
        <Text type="secondary">No text content extracted.</Text>
      )}
    </div>
  );

  return (
    <Tabs
      size="small"
      items={[
        { key: "preview", label: "Preview", children: previewPane },
        { key: "markdown", label: "Markdown", children: markdownPane },
      ]}
    />
  );
}
