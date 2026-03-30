import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import type { RouteProp } from "@react-navigation/native";
import { useRoute } from "@react-navigation/native";

import { InfoRow, ScreenShell, SurfaceCard, TagChip } from "../components/ui";
import type { RootStackParams } from "../navigation/RootNavigator";
import { fetchArticleDetail } from "../services/api";
import type { ArticleDetail } from "../types";
import { colors, radius, spacing, typography } from "../theme";

type RenderBlock =
  | { type: "paragraph"; text: string }
  | { type: "table"; headers: string[]; rows: string[][] };

function splitTableRow(line: string) {
  const trimmed = line.trim();
  const stripStart = trimmed.startsWith("|") ? trimmed.slice(1) : trimmed;
  const stripBoth = stripStart.endsWith("|") ? stripStart.slice(0, -1) : stripStart;
  return stripBoth.split("|").map((cell) => cell.trim());
}

function isSeparatorRow(line: string) {
  const cells = splitTableRow(line).map((cell) => cell.replace(/:/g, "").trim());
  return cells.length > 0 && cells.every((cell) => /^-+$/.test(cell) || cell === "");
}

function parseMarkdownBlocks(markdown: string): RenderBlock[] {
  const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
  const blocks: RenderBlock[] = [];
  let buffer: string[] = [];
  let i = 0;

  const flushParagraph = () => {
    const text = buffer.join("\n").trim();
    if (text) {
      blocks.push({ type: "paragraph", text });
    }
    buffer = [];
  };

  while (i < lines.length) {
    const line = lines[i];
    const next = lines[i + 1] ?? "";
    const hasPipe = line.includes("|");
    const maybeTable = hasPipe && next.includes("|") && isSeparatorRow(next);

    if (maybeTable) {
      flushParagraph();
      const header = splitTableRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|")) {
        rows.push(splitTableRow(lines[i]));
        i += 1;
      }
      if (header.length) {
        blocks.push({ type: "table", headers: header, rows });
      }
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      i += 1;
      continue;
    }

    buffer.push(line);
    i += 1;
  }

  flushParagraph();
  return blocks;
}

export function KnowledgeDetailScreen() {
  const route = useRoute<RouteProp<RootStackParams, "条目详情">>();
  const [data, setData] = useState<ArticleDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = async (silent = false) => {
    if (!silent) {
      setLoading(true);
    }
    try {
      const detail = await fetchArticleDetail(route.params.articleId);
      setData(detail);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "读取失败");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    load();
  }, [route.params.articleId]);

  const blocks = useMemo(() => parseMarkdownBlocks(data?.body || ""), [data?.body]);

  return (
    <ScreenShell title={data?.shortTitle || "条目详情"} subtitle={data?.fileLabel || "知识库条目"}>
      {loading ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={colors.accent} />
          <Text style={styles.loadingText}>正在加载正文内容</Text>
        </View>
      ) : (
        <ScrollView
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => {
                setRefreshing(true);
                load(true);
              }}
              tintColor={colors.accent}
            />
          }
        >
          <SurfaceCard>
            <Text style={styles.title}>{data?.title}</Text>
            <View style={styles.tagWrap}>
              {(data?.tags || []).slice(0, 10).map((tag) => (
                <TagChip key={tag} text={tag} />
              ))}
            </View>
            <Text style={styles.summary}>{data?.summary}</Text>
            <InfoRow label="所属篇" value={data?.partTitle || "暂无"} />
            <InfoRow label="所属章" value={data?.chapterTitle || "暂无"} />
            <InfoRow label="更新时间" value={data?.updatedAt || "暂无"} />
          </SurfaceCard>

          <SurfaceCard style={styles.blockSpace}>
            <Text style={styles.sectionTitle}>正文</Text>
            {blocks.length ? (
              blocks.map((block, index) => {
                if (block.type === "paragraph") {
                  return (
                    <Text key={`p-${index}`} style={styles.bodyText}>
                      {block.text}
                    </Text>
                  );
                }

                return (
                  <ScrollView key={`t-${index}`} horizontal style={styles.tableWrap}>
                    <View style={styles.table}>
                      <View style={[styles.row, styles.headerRow]}>
                        {block.headers.map((cell, cellIndex) => (
                          <Text key={`h-${cellIndex}`} style={[styles.cell, styles.headerCell]}>
                            {cell || " "}
                          </Text>
                        ))}
                      </View>
                      {block.rows.map((row, rowIndex) => (
                        <View key={`r-${rowIndex}`} style={styles.row}>
                          {row.map((cell, cellIndex) => (
                            <Text key={`c-${rowIndex}-${cellIndex}`} style={styles.cell}>
                              {cell || " "}
                            </Text>
                          ))}
                        </View>
                      ))}
                    </View>
                  </ScrollView>
                );
              })
            ) : (
              <Text style={styles.bodyText}>暂无正文内容</Text>
            )}
          </SurfaceCard>
        </ScrollView>
      )}

      {error ? (
        <SurfaceCard>
          <Text style={styles.errorText}>当前读取失败：{error}</Text>
        </SurfaceCard>
      ) : null}
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  loadingWrap: {
    alignItems: "center",
    paddingVertical: spacing.xl,
    gap: spacing.sm,
  },
  loadingText: {
    color: colors.subText,
  },
  title: {
    ...typography.section,
    color: colors.text,
  },
  summary: {
    color: colors.text,
    lineHeight: 22,
  },
  tagWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  blockSpace: {
    marginTop: spacing.md,
    gap: spacing.md,
  },
  sectionTitle: {
    ...typography.section,
    color: colors.text,
  },
  bodyText: {
    color: colors.text,
    lineHeight: 26,
    fontSize: 15,
  },
  tableWrap: {
    marginVertical: spacing.sm,
  },
  table: {
    borderWidth: 1,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    overflow: "hidden",
    minWidth: 520,
    backgroundColor: "#fffdf9",
  },
  row: {
    flexDirection: "row",
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  headerRow: {
    backgroundColor: "#f3eadb",
  },
  cell: {
    minWidth: 130,
    paddingHorizontal: spacing.sm,
    paddingVertical: 10,
    color: colors.text,
    borderRightWidth: 1,
    borderRightColor: colors.border,
    lineHeight: 22,
    fontSize: 14,
  },
  headerCell: {
    fontWeight: "700",
  },
  errorText: {
    color: colors.danger,
    lineHeight: 20,
  },
});
