import React, { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { ActionButton, CollapsibleCard, ScreenShell, StatusPill, SurfaceCard, TagChip } from "../components/ui";
import {
  createSession,
  fetchAssistantSessionDetail,
  fetchAssistantSessions,
  submitQuestion,
} from "../services/api";
import { useAppStore } from "../store/appStore";
import type {
  AssistantResult,
  AssistantSessionDetail,
  AssistantSessionSummary,
  AssistantTurn,
  CasePatternCandidate,
  RetrievalHit,
} from "../types";
import { colors, radius, spacing, typography } from "../theme";

const sampleQueries = [
  "小儿发热可以用哪些中医护理适宜技术？",
  "头痛患者耳穴贴压的观察要点有哪些？",
  "患者：女，32岁，内科住院第2天，反复头痛2天并伴恶心畏光，舌偏红苔薄黄脉弦，怎么护理？",
];

const answerSectionTitles = ["病情摘要", "护理判断", "护理建议", "观察与上报", "护理记录", "依据条目"];

function cleanLine(text: string) {
  return text.replace(/^[-*•]\s*/, "").replace(/^\d+[.、]\s*/, "").trim();
}

function parseAnswerSections(answer: string) {
  const sections: Array<{ title: string; lines: string[] }> = [];
  const lines = String(answer || "")
    .replace(/\r/g, "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  let current: { title: string; lines: string[] } | null = null;

  for (const line of lines) {
    const title = answerSectionTitles.find(
      (item) => line === item || line.startsWith(`${item}:`) || line.startsWith(`${item}：`),
    );
    if (title) {
      if (current) {
        sections.push(current);
      }
      const rest = line.replace(new RegExp(`^${title}[：:]?`), "").trim();
      current = {
        title,
        lines: rest ? [cleanLine(rest)] : [],
      };
      continue;
    }

    if (!current) {
      current = {
        title: "专业建议",
        lines: [],
      };
    }
    current.lines.push(cleanLine(line));
  }

  if (current) {
    sections.push(current);
  }

  return sections;
}

function sessionDetailFallback(sessionId: string) {
  return {
    sessionId,
    title: "新对话",
    createdAt: "",
    updatedAt: "",
    recentFocus: "",
    memoryTags: [],
    recentHits: [],
    turnCount: 0,
    latestTurn: null,
    turns: [],
  } satisfies AssistantSessionDetail;
}

function getDisplayTurn(result: AssistantResult | null, sessionDetail: AssistantSessionDetail | null) {
  return result?.session?.latestTurn || sessionDetail?.latestTurn || null;
}

function getDisplayHits(result: AssistantResult | null) {
  return result?.retrieval?.hits || [];
}

function formatSessionMeta(item: AssistantSessionSummary) {
  const timeText = item.updatedAt || item.createdAt || "暂无时间";
  return `${item.turnCount}轮对话 · ${timeText}`;
}

function formatPatternList(items: CasePatternCandidate[] | undefined) {
  return (items || []).map((item) => item.name).filter(Boolean);
}

export function AssistantScreen() {
  const backendUrl = useAppStore((state) => state.backendUrl);
  const currentSessionId = useAppStore((state) => state.currentSessionId);
  const pendingQuestion = useAppStore((state) => state.pendingQuestion);
  const setCurrentSessionId = useAppStore((state) => state.setCurrentSessionId);
  const setPendingQuestion = useAppStore((state) => state.setPendingQuestion);

  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionLoading, setSessionLoading] = useState(false);
  const [result, setResult] = useState<AssistantResult | null>(null);
  const [sessionList, setSessionList] = useState<AssistantSessionSummary[]>([]);
  const [sessionDetail, setSessionDetail] = useState<AssistantSessionDetail | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (pendingQuestion) {
      setQuestion(pendingQuestion);
      setPendingQuestion("");
    }
  }, [pendingQuestion, setPendingQuestion]);

  useEffect(() => {
    let active = true;

    async function bootstrap() {
      setSessionsLoading(true);
      try {
        const items = await fetchAssistantSessions();
        if (!active) {
          return;
        }
        setSessionList(items);

        const nextId = currentSessionId || items[0]?.sessionId || "";
        if (nextId) {
          setSessionLoading(true);
          try {
            const detail = await fetchAssistantSessionDetail(nextId);
            if (!active) {
              return;
            }
            setCurrentSessionId(nextId);
            setSessionDetail(detail);
          } finally {
            if (active) {
              setSessionLoading(false);
            }
          }
        } else {
          setSessionDetail(null);
        }
        setError("");
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : "读取会话失败");
        }
      } finally {
        if (active) {
          setSessionsLoading(false);
        }
      }
    }

    bootstrap();
    return () => {
      active = false;
    };
  }, [backendUrl, setCurrentSessionId]);

  const reloadSessionList = async (preferredId?: string) => {
    const items = await fetchAssistantSessions();
    setSessionList(items);
    const nextId = preferredId || currentSessionId || items[0]?.sessionId || "";
    if (nextId) {
      const detail = await fetchAssistantSessionDetail(nextId);
      setCurrentSessionId(nextId);
      setSessionDetail(detail);
      return detail;
    }
    return null;
  };

  const handleSelectSession = async (sessionId: string) => {
    if (!sessionId || sessionId === currentSessionId) {
      return;
    }
    setSessionLoading(true);
    setError("");
    setResult(null);
    try {
      const detail = await fetchAssistantSessionDetail(sessionId);
      setCurrentSessionId(sessionId);
      setSessionDetail(detail);
    } catch (err) {
      setError(err instanceof Error ? err.message : "读取会话失败");
    } finally {
      setSessionLoading(false);
    }
  };

  const handleNewSession = async () => {
    if (loading) {
      return;
    }
    setSessionLoading(true);
    setError("");
    try {
      const created = await createSession();
      setCurrentSessionId(created.sessionId);
      setSessionDetail(sessionDetailFallback(created.sessionId));
      setResult(null);
      setQuestion("");
      await reloadSessionList(created.sessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "新建会话失败");
    } finally {
      setSessionLoading(false);
    }
  };

  const handleSubmit = async (text?: string) => {
    const finalQuestion = (text ?? question).trim();
    if (!finalQuestion || loading) {
      return;
    }

    setLoading(true);
    setError("");
    setQuestion(finalQuestion);
    try {
      let sessionId = currentSessionId;
      if (!sessionId) {
        const created = await createSession();
        sessionId = created.sessionId;
        setCurrentSessionId(sessionId);
      }

      const response = await submitQuestion(finalQuestion, sessionId);
      setCurrentSessionId(response.sessionId);
      setResult(response);
      setSessionDetail(response.session);
      const items = await fetchAssistantSessions();
      setSessionList(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "问答失败");
    } finally {
      setLoading(false);
    }
  };

  const displayTurn = getDisplayTurn(result, sessionDetail);
  const displayAnswer = result?.answer || displayTurn?.answer || "";
  const displaySections = parseAnswerSections(displayAnswer);
  const displayHits = getDisplayHits(result);
  const displayAnalysis = result?.analysis || (
    displayTurn
      ? {
          question: displayTurn.question,
          normalized: displayTurn.question,
          intent: displayTurn.analysis?.intent || "历史会话",
          focus: displayTurn.analysis?.focus || displayTurn.focus || "",
          matchedTags: displayTurn.analysis?.matchedTags || displayTurn.tags || [],
          keywords: [],
          fragments: [],
          memoryTags: [],
          useMemory: false,
        }
      : null
  );
  const activeSessionTitle = sessionDetail?.title || result?.session?.title || "未建立会话";
  const activeSessionMeta = sessionDetail
    ? `${sessionDetail.turnCount}轮对话 · ${sessionDetail.updatedAt || sessionDetail.createdAt || "暂无时间"}`
    : "新建对话后即可隔离上下文";
  const caseProfile = displayAnalysis?.caseProfile;
  const historyTurns = (sessionDetail?.turns || []).slice().reverse();
  const patternTags = formatPatternList(caseProfile?.patternCandidates);

  return (
    <ScreenShell title="智能问答" subtitle="病例问答、会话隔离与历史回看">
      <SurfaceCard>
        <View style={styles.sessionHead}>
          <View style={styles.sessionInfo}>
            <Text style={styles.sectionTitle}>当前会话</Text>
            <Text style={styles.sessionTitle}>{activeSessionTitle}</Text>
            <Text style={styles.sessionMeta}>{activeSessionMeta}</Text>
          </View>
          <StatusPill text={caseProfile?.isCase ? "病例模式" : "普通问答"} tone={caseProfile?.isCase ? "warning" : "info"} />
        </View>
        <View style={styles.actions}>
          <ActionButton label="新建对话" onPress={handleNewSession} />
          <ActionButton
            label={sessionsLoading || sessionLoading ? "正在刷新..." : "刷新历史"}
            variant="secondary"
            onPress={async () => {
              setSessionsLoading(true);
              try {
                await reloadSessionList();
                setError("");
              } catch (err) {
                setError(err instanceof Error ? err.message : "刷新失败");
              } finally {
                setSessionsLoading(false);
              }
            }}
            disabled={sessionsLoading || sessionLoading}
          />
        </View>
      </SurfaceCard>

      <SurfaceCard>
        <Text style={styles.inputLabel}>护士问题输入</Text>
        <TextInput
          multiline
          value={question}
          onChangeText={setQuestion}
          placeholder="请输入病例或护理问题，例如：头痛住院患者伴恶心畏光，舌偏红苔薄黄脉弦，怎么护理？"
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

      {displayAnalysis ? (
        <SurfaceCard>
          <Text style={styles.sectionTitle}>病例识别</Text>
          <Text style={styles.bodyText}>检索意图：{displayAnalysis.intent}</Text>
          <Text style={styles.bodyText}>护理焦点：{displayAnalysis.focus || "未识别"}</Text>
          {caseProfile?.summary ? <Text style={styles.bodyText}>识别摘要：{caseProfile.summary}</Text> : null}
          {patternTags.length ? (
            <View style={styles.tagWrap}>
              {patternTags.map((tag) => (
                <TagChip key={`pattern-${tag}`} text={tag} />
              ))}
            </View>
          ) : null}
          {(displayAnalysis.matchedTags || []).length ? (
            <View style={styles.tagWrap}>
              {displayAnalysis.matchedTags.map((tag) => (
                <TagChip key={`tag-${tag}`} text={tag} />
              ))}
            </View>
          ) : null}
        </SurfaceCard>
      ) : null}

      <SurfaceCard>
        <Text style={styles.sectionTitle}>专业建议</Text>
        {loading ? (
          <View style={styles.loadingWrap}>
            <ActivityIndicator color={colors.accent} />
            <Text style={styles.loadingText}>正在检索相关章节并整理病例建议...</Text>
          </View>
        ) : displaySections.length ? (
          <View style={styles.answerWrap}>
            {displaySections.map((section) => (
              <View key={section.title} style={styles.answerSection}>
                <Text style={styles.answerSectionTitle}>{section.title}</Text>
                {section.lines.map((line, index) => (
                  <Text key={`${section.title}-${index}`} style={styles.answerLine}>
                    {index + 1}. {line}
                  </Text>
                ))}
              </View>
            ))}
          </View>
        ) : (
          <Text style={styles.bodyText}>请先输入问题开始问答。</Text>
        )}
      </SurfaceCard>

      <SurfaceCard>
        <Text style={styles.sectionTitle}>证据条目</Text>
        {displayHits.length ? (
          displayHits.map((item: RetrievalHit) => (
            <View key={`${item.fileLabel}-${item.title}`} style={styles.hitCard}>
              <View style={styles.hitHead}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.hitTitle}>{item.title}</Text>
                  <Text style={styles.hitMeta}>
                    {item.fileLabel}
                    {item.kind ? ` · ${item.kind}` : ""}
                  </Text>
                </View>
                <Text style={styles.hitScore}>{Math.round(item.score)}</Text>
              </View>
              <View style={styles.tagWrap}>
                {(item.basis || []).map((reason) => (
                  <TagChip key={`${item.fileLabel}-${reason}`} text={reason} />
                ))}
              </View>
              <Text style={styles.bodyText}>{item.snippet}</Text>
            </View>
          ))
        ) : displayTurn?.references?.length ? (
          displayTurn.references.map((item, index) => (
            <View key={`${item.fileLabel}-${index}`} style={styles.referenceRow}>
              <Text style={styles.referenceTitle}>
                [{item.fileLabel}] {item.title}
              </Text>
            </View>
          ))
        ) : (
          <Text style={styles.bodyText}>暂无条目明细，系统可能使用了章节回溯。</Text>
        )}
      </SurfaceCard>

      <CollapsibleCard title="历史会话" subtitle={`共 ${sessionList.length} 个会话`} defaultExpanded={false}>
        {sessionList.length ? (
          sessionList.map((item) => {
            const active = item.sessionId === currentSessionId;
            return (
              <Pressable
                key={item.sessionId}
                style={[styles.sessionItem, active && styles.sessionItemActive]}
                onPress={() => handleSelectSession(item.sessionId)}
              >
                <View style={styles.sessionItemHead}>
                  <Text style={styles.sessionItemTitle}>{item.title || "未命名会话"}</Text>
                  {active ? <StatusPill text="当前" tone="success" /> : null}
                </View>
                <Text style={styles.sessionItemMeta}>{formatSessionMeta(item)}</Text>
                <Text style={styles.sessionItemPreview}>{item.preview || "暂无内容"}</Text>
              </Pressable>
            );
          })
        ) : (
          <Text style={styles.bodyText}>暂无历史会话，点击“新建对话”即可开始隔离上下文。</Text>
        )}
      </CollapsibleCard>

      <CollapsibleCard title="本会话记录" subtitle={`共 ${historyTurns.length} 轮`} defaultExpanded={false}>
        {historyTurns.length ? (
          historyTurns.map((turn: AssistantTurn, index) => (
            <View key={`${turn.time}-${index}`} style={styles.turnCard}>
              <Text style={styles.turnTime}>{turn.time}</Text>
              <Text style={styles.turnLabel}>护士提问</Text>
              <Text style={styles.turnQuestion}>{turn.question}</Text>
              {turn.analysis?.focus ? <Text style={styles.turnMeta}>焦点：{turn.analysis.focus}</Text> : null}
              {(turn.analysis?.matchedTags || []).length ? (
                <View style={styles.tagWrap}>
                  {(turn.analysis?.matchedTags || []).map((tag) => (
                    <TagChip key={`${turn.time}-${tag}`} text={tag} />
                  ))}
                </View>
              ) : null}
              <Text style={styles.turnLabel}>回答摘要</Text>
              <Text style={styles.turnAnswer}>{turn.answerSummary || "暂无摘要"}</Text>
            </View>
          ))
        ) : (
          <Text style={styles.bodyText}>当前会话还没有历史记录。</Text>
        )}
      </CollapsibleCard>

      {error ? (
        <SurfaceCard>
          <Text style={styles.errorText}>当前问答失败：{error}</Text>
        </SurfaceCard>
      ) : null}
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  sessionHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: spacing.md,
  },
  sessionInfo: {
    flex: 1,
    gap: 4,
  },
  sectionTitle: {
    ...typography.section,
    color: colors.text,
  },
  sessionTitle: {
    color: colors.primary,
    fontSize: 20,
    lineHeight: 28,
    fontWeight: "800",
  },
  sessionMeta: {
    color: colors.subText,
    lineHeight: 20,
  },
  inputLabel: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: "700",
  },
  textarea: {
    minHeight: 132,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fffaf5",
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.md,
    color: colors.text,
    fontSize: 15,
    textAlignVertical: "top",
    lineHeight: 22,
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
    lineHeight: 22,
  },
  bodyText: {
    color: colors.text,
    lineHeight: 22,
  },
  loadingWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  loadingText: {
    color: colors.subText,
  },
  answerWrap: {
    gap: spacing.md,
  },
  answerSection: {
    borderRadius: radius.md,
    padding: spacing.md,
    backgroundColor: "#fffaf5",
    borderWidth: 1,
    borderColor: colors.border,
    gap: 6,
  },
  answerSectionTitle: {
    color: colors.primary,
    fontSize: 15,
    fontWeight: "800",
  },
  answerLine: {
    color: colors.text,
    lineHeight: 22,
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
    alignItems: "flex-start",
    gap: spacing.md,
  },
  hitTitle: {
    color: colors.text,
    fontWeight: "800",
    lineHeight: 22,
  },
  hitMeta: {
    color: colors.subText,
    fontSize: 12,
    marginTop: 4,
  },
  hitScore: {
    color: colors.accent,
    fontWeight: "800",
    fontSize: 18,
  },
  referenceRow: {
    borderRadius: radius.md,
    padding: spacing.md,
    backgroundColor: "#faf5ed",
    borderWidth: 1,
    borderColor: colors.border,
  },
  referenceTitle: {
    color: colors.text,
    lineHeight: 22,
    fontWeight: "600",
  },
  sessionItem: {
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fffaf5",
    padding: spacing.md,
    gap: spacing.xs,
  },
  sessionItemActive: {
    borderColor: colors.accent,
    backgroundColor: "#fff3e8",
  },
  sessionItemHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    gap: spacing.md,
  },
  sessionItemTitle: {
    flex: 1,
    color: colors.text,
    fontWeight: "800",
    lineHeight: 22,
  },
  sessionItemMeta: {
    color: colors.subText,
    fontSize: 12,
  },
  sessionItemPreview: {
    color: colors.text,
    lineHeight: 21,
  },
  turnCard: {
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fffaf5",
    padding: spacing.md,
    gap: spacing.sm,
  },
  turnTime: {
    color: colors.subText,
    fontSize: 12,
  },
  turnLabel: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: "700",
  },
  turnQuestion: {
    color: colors.text,
    lineHeight: 22,
    fontWeight: "600",
  },
  turnMeta: {
    color: colors.subText,
    lineHeight: 20,
  },
  turnAnswer: {
    color: colors.text,
    lineHeight: 22,
  },
  errorText: {
    color: colors.danger,
    lineHeight: 20,
  },
});
