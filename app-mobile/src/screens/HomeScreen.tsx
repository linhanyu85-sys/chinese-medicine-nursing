import React, { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useNavigation } from "@react-navigation/native";

import { AnimatedBlock, ScreenShell, SurfaceCard, TagChip } from "../components/ui";
import { fetchHealthStatus, fetchHomePayload } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { HomePayload } from "../types";
import { colors, radius, spacing, typography } from "../theme";

export function HomeScreen() {
  const navigation = useNavigation<any>();
  const setHealth = useAppStore((state) => state.setHealth);
  const setPendingQuestion = useAppStore((state) => state.setPendingQuestion);
  const [data, setData] = useState<HomePayload | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([fetchHomePayload(), fetchHealthStatus()])
      .then(([home, health]) => {
        if (!active) {
          return;
        }
        setData(home);
        setHealth(health);
        setError("");
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message || "读取失败");
        }
      });
    return () => {
      active = false;
    };
  }, [setHealth]);

  return (
    <ScreenShell title="中医适宜技术助手" subtitle="面向临床护士的知识库与智能咨询">
      <AnimatedBlock delay={60}>
        <View style={styles.entryWrap}>
          <Pressable style={[styles.entry, styles.entryPrimary]} onPress={() => navigation.navigate("知识库")}>
            <Text style={styles.entryEyebrow}>知识库端</Text>
            <Text style={styles.entryTitle}>按篇章顺序阅读教材与护理要点</Text>
            <Text style={styles.entryDesc}>支持目录定位、关键词检索与正文表格阅读。</Text>
          </Pressable>
          <Pressable style={styles.entry} onPress={() => navigation.navigate("智能问答")}>
            <Text style={styles.entryEyebrowMuted}>智能问答端</Text>
            <Text style={styles.entryTitleDark}>先检索相关章节，再结合上下文给出专业建议</Text>
            <Text style={styles.entryDescDark}>支持新建对话隔离上下文，并可回看历史会话。</Text>
          </Pressable>
        </View>
      </AnimatedBlock>

      <AnimatedBlock delay={120}>
        <SurfaceCard>
          <Text style={styles.sectionTitle}>快捷条目</Text>
          <View style={styles.quickWrap}>
            {(data?.quickEntries || []).map((item) => (
              <Pressable
                key={item.articleId}
                style={styles.quickItem}
                onPress={() => navigation.navigate("条目详情", { articleId: item.articleId })}
              >
                <Text style={styles.quickTitle}>{item.shortTitle || item.title}</Text>
                <Text style={styles.quickMeta}>{item.fileLabel}</Text>
              </Pressable>
            ))}
          </View>
        </SurfaceCard>
      </AnimatedBlock>

      <AnimatedBlock delay={180}>
        <SurfaceCard>
          <Text style={styles.sectionTitle}>{data?.dailyTip?.title || "临床要点"}</Text>
          <Text style={styles.tipBody}>{data?.dailyTip?.content || "加载中..."}</Text>
          <View style={styles.tipTags}>
            <TagChip text="中医特色" />
            <TagChip text="临床可用" />
            <TagChip text="证据可追溯" />
          </View>
        </SurfaceCard>
      </AnimatedBlock>

      <AnimatedBlock delay={240}>
        <SurfaceCard>
          <Text style={styles.sectionTitle}>示例提问</Text>
          <View style={styles.questionList}>
            {(data?.sampleQueries || []).slice(0, 4).map((item) => (
              <Pressable
                key={item}
                style={styles.questionItem}
                onPress={() => {
                  setPendingQuestion(item);
                  navigation.navigate("智能问答");
                }}
              >
                <Text style={styles.questionText}>{item}</Text>
              </Pressable>
            ))}
          </View>
        </SurfaceCard>
      </AnimatedBlock>

      <AnimatedBlock delay={300}>
        <SurfaceCard>
          <Text style={styles.sectionTitle}>运行概览</Text>
          <View style={styles.statGrid}>
            <View style={styles.statItem}>
              <Text style={styles.statNumber}>{data?.stats?.articleCount || "--"}</Text>
              <Text style={styles.statLabel}>知识条目</Text>
            </View>
            <View style={styles.statItem}>
              <Text style={styles.statNumber}>{data?.stats?.partCount || "--"}</Text>
              <Text style={styles.statLabel}>篇章目录</Text>
            </View>
            <View style={styles.statItemWide}>
              <Text style={styles.statLabel}>最近更新时间</Text>
              <Text style={styles.exportText}>{data?.stats?.lastExport || "暂无"}</Text>
            </View>
          </View>
          {error ? <Text style={styles.errorText}>当前读取失败：{error}</Text> : null}
        </SurfaceCard>
      </AnimatedBlock>
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  entryWrap: {
    gap: spacing.md,
  },
  entry: {
    borderRadius: radius.xl,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    backgroundColor: "#fffaf4",
  },
  entryPrimary: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  entryEyebrow: {
    color: "#f7ebdf",
    fontSize: 12,
    fontWeight: "700",
    marginBottom: 8,
  },
  entryEyebrowMuted: {
    color: colors.accent,
    fontSize: 12,
    fontWeight: "700",
    marginBottom: 8,
  },
  entryTitle: {
    color: "#fffaf4",
    fontSize: 22,
    lineHeight: 28,
    fontWeight: "800",
  },
  entryTitleDark: {
    ...typography.section,
    color: colors.text,
  },
  entryDesc: {
    marginTop: spacing.sm,
    color: "rgba(255,250,244,0.9)",
    lineHeight: 20,
  },
  entryDescDark: {
    marginTop: spacing.sm,
    color: colors.subText,
    lineHeight: 20,
  },
  sectionTitle: {
    ...typography.section,
    color: colors.text,
  },
  quickWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  quickItem: {
    width: "48%",
    minHeight: 96,
    padding: spacing.md,
    borderRadius: radius.lg,
    backgroundColor: "#f7f0e4",
    borderWidth: 1,
    borderColor: colors.border,
    justifyContent: "space-between",
  },
  quickTitle: {
    color: colors.text,
    fontSize: 15,
    lineHeight: 22,
    fontWeight: "700",
  },
  quickMeta: {
    color: colors.subText,
    fontSize: 12,
  },
  tipBody: {
    color: colors.text,
    lineHeight: 22,
  },
  tipTags: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  questionList: {
    gap: spacing.sm,
  },
  questionItem: {
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: "#faf5ed",
    borderWidth: 1,
    borderColor: colors.border,
  },
  questionText: {
    color: colors.text,
    lineHeight: 22,
  },
  statGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  statItem: {
    flex: 1,
    minWidth: 120,
    padding: spacing.md,
    borderRadius: radius.lg,
    backgroundColor: "#f7f0e4",
  },
  statItemWide: {
    width: "100%",
    padding: spacing.md,
    borderRadius: radius.lg,
    backgroundColor: "#f7f0e4",
  },
  statNumber: {
    color: colors.primary,
    fontSize: 26,
    fontWeight: "800",
  },
  statLabel: {
    color: colors.subText,
    fontSize: 13,
  },
  exportText: {
    color: colors.text,
    marginTop: 6,
  },
  errorText: {
    color: colors.danger,
    lineHeight: 20,
  },
});
