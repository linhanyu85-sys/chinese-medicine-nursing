import React from "react";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { View } from "react-native";

import { AssistantScreen } from "../screens/AssistantScreen";
import { HomeScreen } from "../screens/HomeScreen";
import { KnowledgeDetailScreen } from "../screens/KnowledgeDetailScreen";
import { KnowledgeScreen } from "../screens/KnowledgeScreen";
import { ManagementScreen } from "../screens/ManagementScreen";
import { colors, radius, shadows } from "../theme";

export type RootStackParams = {
  主导航: undefined;
  条目详情: { articleId: string };
};

export type TabParams = {
  首页: undefined;
  知识库: undefined;
  智能问答: undefined;
  管理: undefined;
};

const Stack = createNativeStackNavigator<RootStackParams>();
const Tab = createBottomTabNavigator<TabParams>();

const tabMeta: Record<keyof TabParams, { label: string; icon: keyof typeof MaterialCommunityIcons.glyphMap }> = {
  首页: { label: "首页", icon: "home-variant-outline" },
  知识库: { label: "知识库", icon: "bookshelf" },
  智能问答: { label: "智能问答", icon: "head-question-outline" },
  管理: { label: "管理", icon: "tune-variant" },
};

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => {
        const meta = tabMeta[route.name as keyof TabParams];
        return {
          headerShown: false,
          tabBarActiveTintColor: colors.accent,
          tabBarInactiveTintColor: colors.subText,
          tabBarLabelStyle: { fontSize: 12, fontWeight: "700", marginBottom: 4 },
          tabBarStyle: {
            position: "absolute",
            left: 14,
            right: 14,
            bottom: 12,
            height: 76,
            borderTopWidth: 0,
            borderRadius: radius.xl,
            paddingTop: 8,
            backgroundColor: "#fffaf3f6",
            ...shadows.tabBar,
          },
          tabBarLabel: meta.label,
          tabBarIcon: ({ focused, color }) => (
            <View
              style={{
                width: 34,
                height: 34,
                borderRadius: 17,
                alignItems: "center",
                justifyContent: "center",
                backgroundColor: focused ? "#f2e8d8" : "transparent",
              }}
            >
              <MaterialCommunityIcons name={meta.icon} size={20} color={color} />
            </View>
          ),
        };
      }}
    >
      <Tab.Screen name="首页" component={HomeScreen} />
      <Tab.Screen name="知识库" component={KnowledgeScreen} />
      <Tab.Screen name="智能问答" component={AssistantScreen} />
      <Tab.Screen name="管理" component={ManagementScreen} />
    </Tab.Navigator>
  );
}

export function RootNavigator() {
  return (
    <Stack.Navigator
      screenOptions={{
        contentStyle: { backgroundColor: colors.bg },
        headerShadowVisible: false,
        headerStyle: { backgroundColor: colors.bgSoft },
        headerTitleStyle: { color: colors.text, fontWeight: "700" },
      }}
    >
      <Stack.Screen name="主导航" component={MainTabs} options={{ headerShown: false }} />
      <Stack.Screen name="条目详情" component={KnowledgeDetailScreen} options={{ title: "条目详情" }} />
    </Stack.Navigator>
  );
}
