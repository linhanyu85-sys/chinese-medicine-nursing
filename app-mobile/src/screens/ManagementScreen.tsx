import React, { useEffect, useState } from "react";
import { ActivityIndicator, Alert, StyleSheet, Text, TextInput, View } from "react-native";

import { ActionButton, InfoRow, ScreenShell, SurfaceCard } from "../components/ui";
import { fetchHealthStatus, fetchManagementOverview, reloadKnowledgeBase } from "../services/api";
import { useAppStore } from "../store/appStore";
import type { ManagementOverview } from "../types";
import { colors, radius, spacing, typography } from "../theme";

export function ManagementScreen() {
  const backendUrl = useAppStore((state) => state.backendUrl);
  const health = useAppStore((state) => state.health);
  const setBackendUrl = useAppStore((state) => state.setBackendUrl);
  const setHealth = useAppStore((state) => state.setHealth);

  const [draftUrl, setDraftUrl] = useState(backendUrl);
  const [loading, setLoading] = useState(true);
  const [reloading, setReloading] = useState(false);
  const [overview, setOverview] = useState<ManagementOverview | null>(null);
  const [error, setError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [nextOverview, nextHealth] = await Promise.all([fetchManagementOverview(), fetchHealthStatus()]);
      setOverview(nextOverview);
      setHealth(nextHealth);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "读取失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setDraftUrl(backendUrl);
    load();
  }, [backendUrl]);

  return (
    <ScreenShell title="管理" subtitle="后端地址、模型状态与知识库刷新">
      <SurfaceCard>
        <Text style={styles.sectionTitle}>接口设置</Text>
        <TextInput
          value={draftUrl}
          onChangeText={setDraftUrl}
          placeholder="请输入后端地址"
          placeholderTextColor={colors.subText}
          autoCapitalize="none"
          autoCorrect={false}
          style={styles.input}
        />
        <View style={styles.row}>
          <ActionButton
            label="保存地址"
            onPress={() => {
              setBackendUrl(draftUrl);
              Alert.alert("已更新", "新的后端地址已保存。");
            }}
          />
          <ActionButton label="重新检测" variant="secondary" onPress={load} />
        </View>
      </SurfaceCard>

      <SurfaceCard>
        <Text style={styles.sectionTitle}>运行状态</Text>
        {loading ? (
          <View style={styles.loadingWrap}>
            <ActivityIndicator color={colors.accent} />
            <Text style={styles.loadingText}>正在读取状态...</Text>
          </View>
        ) : (
          <>
            <InfoRow label="接口状态" value={health?.status || "未知"} />
            <InfoRow label="知识条目" value={`${overview?.articleCount || 0}`} />
            <InfoRow label="目录主篇" value={`${overview?.partCount || 0}`} />
            <InfoRow label="最近更新时间" value={overview?.lastExport || "暂无"} />
          </>
        )}
      </SurfaceCard>

      <SurfaceCard>
        <Text style={styles.sectionTitle}>知识库刷新</Text>
        <ActionButton
          label={reloading ? "正在刷新" : "刷新知识库"}
          onPress={async () => {
            if (reloading) {
              return;
            }
            setReloading(true);
            try {
              const payload = await reloadKnowledgeBase();
              await load();
              Alert.alert("刷新完成", `${payload.result}，当前共 ${payload.articleCount} 条。`);
            } catch (err) {
              Alert.alert("刷新失败", err instanceof Error ? err.message : "刷新失败");
            } finally {
              setReloading(false);
            }
          }}
          disabled={reloading}
        />
      </SurfaceCard>

      {error ? (
        <SurfaceCard>
          <Text style={styles.errorText}>当前读取失败：{error}</Text>
        </SurfaceCard>
      ) : null}
    </ScreenShell>
  );
}

const styles = StyleSheet.create({
  sectionTitle: {
    ...typography.section,
    color: colors.text,
  },
  input: {
    minHeight: 48,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: "#fffaf5",
    paddingHorizontal: spacing.md,
    color: colors.text,
  },
  row: {
    flexDirection: "row",
    gap: spacing.sm,
  },
  loadingWrap: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
  },
  loadingText: {
    color: colors.subText,
  },
  errorText: {
    color: colors.danger,
    lineHeight: 20,
  },
});
