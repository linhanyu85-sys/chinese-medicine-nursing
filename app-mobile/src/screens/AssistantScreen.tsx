import React, { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { ActionButton, ScreenShell, SurfaceCard, TagChip } from "../components/ui";
import { createSession, submitQuestion } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { AssistantResult } from "../types";
import { colors, radius, spacing, typography } from "../theme";

const sampleQueries = [
  "小儿发热可以用哪些中医护理适宜技术？",
  "热敏灸技术有哪些适应证和禁忌证？",
  "感冒患者如何进行护理观察与健康教育？",
];

export function AssistantScreen() {
  const currentSessionId = useAppStore((state) => state.currentSessionId);
  const pendingQuestion = useAppStore((state) => state.pendingQuestion);
  const setCurrentSessionId = useAppStore((state) => state.setCurrentSessionId);
  const setPendingQuestion = useAppStore((state) => state.setPendingQuestion);

  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AssistantResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (pendingQuestion) {
      setQuestion(pendingQuestion);
      setPendingQuestion("");
    }
  }, [pendingQuestion, setPendingQuestion]);

  const handleSubmit = async (text?: string) => {
    const finalQuestion = (text ?? question).trim();
    if (!finalQuestion || loading) {
      return;
    }
    setQuestion(finalQuestion);
    setLoading(true);
    setError("");
    try {
      let sessionId = currentSessionId;
      if (!sessionId) {
        const session = await createSession();
        sessionId = session.sessionId;
        setCurrentSessionId(sessionId);
      }

      const response = await submitQuestion(finalQuestion, sessionId);
      setCurrentSessionId(response.sessionId);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "问答失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenShell title="智能问答" subtitle="检索相关章节后，基于上下文给出护理建议">
      <SurfaceCard>
        <Text style={styles.inputLabel}>护士问题输入</Text>
        <TextInput
          multiline
          value={question}
          onChangeText={setQuestion}
          placeholder="请输入临床护理问题，例如：现在有点发热头痛，适合哪些中医护理技术？"
          placeholderTextColor={colors.subText}
          style={styles.textarea}
        />
        <View style={styles.actions}>
          <ActionButton
            label={loading ? "正在分析..." : "开始问答"}
            onPress={() => handleSubmit()}
            disabled={loading}
          />
          <ActionButton
            label="清空"
            variant="secondary"
            onPress={() => {
              setQuestion("");
              setResult(null);
              setError("");
            }}
          />
        </View>
        <View style={styles.sampleWrap}>
          {sampleQueries.map((item) => (
            <Pressable key={item} style={styles.sampleItem} onPress={() => handleSubmit(item)}>
              <Text style={styles.sampleText}>{item}</Text>
            </Pressable>
          ))}
        </View>
      </SurfaceCard>

      {loading ? (
        <SurfaceCard>
          <View style={styles.loadingWrap}>
            <ActivityIndicator color={colors.accent} />
            <Text style={styles.loadingText}>正在检索相关章节，请稍候...</Text>
          </View>
        </SurfaceCard>
      ) : null}

      {result?.analysis ? (
        <SurfaceCard>
          <Text style={styles.sectionTitle}>问题归纳</Text>
          <Text style={styles.bodyText}>检索意图：{result.analysis.intent}</Text>
          <Text style={styles.bodyText}>护理焦点：{result.analysis.focus}</Text>
          <View style={styles.tagWrap}>
            {(result.analysis.matchedTags || []).map((tag) => (
              <TagChip key={`tag-${tag}`} text={tag} />
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      <SurfaceCard>
        <Text style={styles.sectionTitle}>专业建议</Text>
        <Text style={styles.answerText}>{result?.answer || "请先输入问题开始问答。"}</Text>
      </SurfaceCard>

      <SurfaceCard>
        <Text style={styles.sectionTitle}>依据条目</Text>
        {result?.retrieval?.hits?.length ? (
          result.retrieval.hits.map((item) => (
            <View key={item.fileLabel} style={styles.hitCard}>
              <View style={styles.hitHead}>
                <Text style={styles.hitTitle}>{item.title}</Text>
                <Text style={styles.hitScore}>{Math.round(item.score)}</Text>
              </View>
              <Text style={styles.hitMeta}>{item.fileLabel}</Text>
              <View style={styles.tagWrap}>
                {(item.basis || []).map((reason) => (
                  <TagChip key={`${item.fileLabel}-${reason}`} text={reason} />
                ))}
              </View>
              <Text style={styles.bodyText}>{item.snippet}</Text>
            </View>
          ))
        ) : (
          <Text style={styles.bodyText}>暂无命中条目，系统已按相关章节进行回溯。</Text>
        )}
        {result?.retrieval?.chapterContext?.title ? (
          <View style={styles.chapterContext}>
            <Text style={styles.chapterTitle}>相关章节：{result.retrieval.chapterContext.title}</Text>
            <Text style={styles.bodyText}>{result.retrieval.chapterContext.summary}</Text>
          </View>
        ) : null}
      </SurfaceCard>

      {result?.memory ? (
        <SurfaceCard>
          <Text style={styles.sectionTitle}>会话重点</Text>
          <Text style={styles.bodyText}>最近焦点：{result.memory.recentFocus || "暂无"}</Text>
          <View style={styles.tagWrap}>
            {(result.memory.memoryTags || []).map((tag) => (
              <TagChip key={`memory-${tag}`} text={tag} />
            ))}
          </View>
        </SurfaceCard>
      ) : null}

      {error ? (
        <SurfaceCard>
          <Text style={styles.errorText}>当前问答失败：{error}</Text>
        </SurfaceCard>
      ) : null}
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  inputLabel: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: "700",
  },
  textarea: {
    minHeight: 120,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fffaf5",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    color: colors.text,
    fontSize: 15,
    textAlignVertical: "top",
  },
  actions: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  sampleWrap: {
    gap: spacing.sm,
  },
  sampleItem: {
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: "#faf5ed",
    borderWidth: 1,
    borderColor: colors.border,
  },
  sampleText: {
    color: colors.text,
    lineHeight: 21,
  },
  loadingWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  loadingText: {
    color: colors.subText,
  },
  sectionTitle: {
    ...typography.section,
    color: colors.text,
  },
  bodyText: {
    color: colors.text,
    lineHeight: 22,
  },
  answerText: {
    color: colors.text,
    lineHeight: 25,
    fontSize: 15,
  },
  tagWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  hitCard: {
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fffaf4",
    padding: spacing.md,
    gap: spacing.sm,
  },
  hitHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: spacing.md,
  },
  hitTitle: {
    flex: 1,
    color: colors.text,
    fontWeight: "800",
    lineHeight: 22,
  },
  hitScore: {
    color: colors.accent,
    fontWeight: "800",
  },
  hitMeta: {
    color: colors.subText,
    fontSize: 12,
  },
  chapterContext: {
    marginTop: spacing.sm,
    borderRadius: radius.md,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#f8f3ea",
    gap: spacing.sm,
  },
  chapterTitle: {
    color: colors.text,
    fontWeight: "700",
  },
  errorText: {
    color: colors.danger,
    lineHeight: 20,
  },
});
