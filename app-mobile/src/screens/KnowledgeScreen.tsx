import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { useNavigation } from "@react-navigation/native";

import { AnimatedBlock, ScreenShell, SurfaceCard, TagChip } from "../components/ui";
import { fetchArticleList, fetchTree } from "../services/api";
import type { ArticleCard, TreeNode } from "../types";
import { colors, radius, spacing, typography } from "../theme";

export function KnowledgeScreen() {
  const navigation = useNavigation<any>();
  const [query, setQuery] = useState("");
  const [activeTag, setActiveTag] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [articles, setArticles] = useState<ArticleCard[]>([]);
  const [tree, setTree] = useState<TreeNode[]>([]);
  const [error, setError] = useState("");

  const tagOptions = useMemo(
    () => tree.map((item) => item.shortTitle || item.title).filter(Boolean).slice(0, 8),
    [tree]
  );

  const load = async (silent = false) => {
    if (!silent) {
      setLoading(true);
    }
    try {
      const [nextTree, nextArticles] = await Promise.all([fetchTree(), fetchArticleList(query, activeTag)]);
      setTree(nextTree);
      setArticles(nextArticles);
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
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      load(true);
    }, 260);
    return () => clearTimeout(timer);
  }, [query, activeTag]);

  return (
    <ScreenShell title="知识库" subtitle="目录按篇章顺序编排，支持关键词与标签检索">
      <AnimatedBlock delay={40}>
        <SurfaceCard>
          <Text style={styles.searchLabel}>知识检索</Text>
          <TextInput
            placeholder="输入病证、技术名称、护理任务或健康教育问题"
            placeholderTextColor={colors.subText}
            style={styles.input}
            value={query}
            onChangeText={setQuery}
          />
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.tagRow}>
            <Pressable
              style={[styles.filterChip, !activeTag && styles.filterChipActive]}
              onPress={() => setActiveTag("")}
            >
              <Text style={[styles.filterText, !activeTag && styles.filterTextActive]}>全部</Text>
            </Pressable>
            {tagOptions.map((item) => (
              <Pressable
                key={item}
                style={[styles.filterChip, activeTag === item && styles.filterChipActive]}
                onPress={() => setActiveTag(activeTag === item ? "" : item)}
              >
                <Text style={[styles.filterText, activeTag === item && styles.filterTextActive]}>{item}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </SurfaceCard>
      </AnimatedBlock>

      {loading ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={colors.accent} />
          <Text style={styles.loadingText}>正在加载知识库...</Text>
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
          <AnimatedBlock delay={100}>
            <SurfaceCard>
              <Text style={styles.sectionTitle}>目录导航</Text>
              {tree.map((part) => (
                <View key={part.id} style={styles.treeBlock}>
                  <Text style={styles.treeTitle}>{part.title}</Text>
                  <Text style={styles.treeMeta}>
                    {(part.children || [])
                      .filter((item) => (item.title || "").trim() !== "总论")
                      .map((item) => item.shortTitle || item.title)
                      .join("、")}
                  </Text>
                </View>
              ))}
            </SurfaceCard>
          </AnimatedBlock>

          <AnimatedBlock delay={160}>
            <View style={styles.listWrap}>
              {articles.map((article) => (
                <Pressable
                  key={article.articleId}
                  style={styles.articleCard}
                  onPress={() => navigation.navigate("条目详情", { articleId: article.articleId })}
                >
                  <View style={styles.articleHead}>
                    <Text style={styles.articleTitle}>{article.title}</Text>
                    {article.score ? <Text style={styles.scoreText}>{Math.round(article.score)}</Text> : null}
                  </View>
                  <Text style={styles.articleSummary}>{article.summary}</Text>
                  <View style={styles.tagWrap}>
                    {(article.tags || []).slice(0, 4).map((tag) => (
                      <TagChip key={`${article.articleId}-${tag}`} text={tag} />
                    ))}
                  </View>
                  <Text style={styles.articleMeta}>
                    {article.fileLabel} · {article.chapterTitle || article.partTitle || "知识条目"}
                  </Text>
                </Pressable>
              ))}
            </View>
          </AnimatedBlock>
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
  searchLabel: {
    color: colors.accent,
    fontSize: 13,
    fontWeight: "700",
  },
  input: {
    minHeight: 50,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fffaf5",
    paddingHorizontal: spacing.md,
    color: colors.text,
    fontSize: 15,
  },
  tagRow: {
    gap: spacing.sm,
  },
  filterChip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fffaf5",
  },
  filterChipActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  filterText: {
    color: colors.text,
    fontSize: 13,
    fontWeight: "600",
  },
  filterTextActive: {
    color: "#fffaf4",
  },
  loadingWrap: {
    alignItems: "center",
    paddingVertical: spacing.xl,
    gap: spacing.sm,
  },
  loadingText: {
    color: colors.subText,
  },
  sectionTitle: {
    ...typography.section,
    color: colors.text,
  },
  treeBlock: {
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  treeTitle: {
    color: colors.text,
    fontSize: 15,
    fontWeight: "700",
  },
  treeMeta: {
    marginTop: 4,
    color: colors.subText,
    lineHeight: 20,
  },
  listWrap: {
    gap: spacing.md,
    marginTop: spacing.md,
    marginBottom: 120,
  },
  articleCard: {
    borderRadius: radius.xl,
    padding: spacing.lg,
    backgroundColor: "#fffaf4",
    borderWidth: 1,
    borderColor: colors.border,
    gap: spacing.sm,
  },
  articleHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: spacing.md,
    alignItems: "flex-start",
  },
  articleTitle: {
    flex: 1,
    color: colors.text,
    fontSize: 17,
    lineHeight: 24,
    fontWeight: "800",
  },
  scoreText: {
    color: colors.accent,
    fontWeight: "800",
  },
  articleSummary: {
    color: colors.subText,
    lineHeight: 22,
  },
  tagWrap: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: spacing.sm,
  },
  articleMeta: {
    color: colors.subText,
    fontSize: 12,
  },
  errorText: {
    color: colors.danger,
    lineHeight: 20,
  },
});
