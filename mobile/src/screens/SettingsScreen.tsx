import { useState } from "react";
import {
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import * as Clipboard from "expo-clipboard";
import Constants from "expo-constants";

import { Modal } from "../components/Modal";
import { Segmented } from "../components/Segmented";
import { CONTACT, PRIVACY_URL, TERMS_URL } from "../config";
import { useAuth } from "../hooks/useAuth";
import { clearLocal, useBookmarks } from "../hooks/useBookmarks";
import { useSettings, type SortOrder } from "../hooks/useSettings";
import { colors, fonts } from "../theme";
import * as authApi from "../utils/auth";
import * as favoritesApi from "../utils/favorites";

const SORT_OPTIONS = [
  { value: "release" as SortOrder, label: "최신 발매순" },
  { value: "no" as SortOrder, label: "곡번호순" },
];

const APP_VERSION = Constants.expoConfig?.version ?? "-";

/** 안내가 붙는 자리. 누른 버튼 바로 아래에만 뜬다. */
type NoticeSpot = "export" | "clear" | "withdraw";

export function SettingsScreen() {
  const { settings, update } = useSettings();
  const { session, logout } = useAuth();
  const { items, reload } = useBookmarks(Boolean(session));
  const [confirming, setConfirming] = useState<"clear" | "withdraw" | null>(
    null,
  );
  // 어느 버튼의 결과인지까지 들고 있는다. 누른 곳에서 시선이 멀어지지 않게.
  const [notice, setNotice] = useState<{
    where: NoticeSpot;
    text: string;
  } | null>(null);

  function Notice({ where }: { where: NoticeSpot }) {
    if (notice?.where !== where) return null;
    return (
      <Text style={styles.notice} accessibilityLiveRegion="polite">
        {notice.text}
      </Text>
    );
  }

  async function exportFavorites() {
    if (items.length === 0) {
      setNotice({ where: "export", text: "내보낼 즐겨찾기가 없어요." });
      return;
    }

    const text = items
      .map((song) => {
        const numbers = Object.entries(song.brands)
          .map(
            ([brand, list]) =>
              `${brand === "tj" ? "태진" : "금영"} ${list?.join(", ")}`,
          )
          .join(" / ");
        return `${song.title} - ${song.singer}\n  ${numbers}`;
      })
      .join("\n");

    try {
      await Clipboard.setStringAsync(text);
      setNotice({ where: "export", text: `${items.length}곡을 복사했어요.` });
    } catch {
      setNotice({ where: "export", text: "복사하지 못했어요." });
    }
  }

  async function clearFavorites() {
    if (session) await favoritesApi.clear().catch(() => undefined);
    else await clearLocal();
    await reload();
    setConfirming(null);
    setNotice({ where: "clear", text: "즐겨찾기를 모두 지웠어요." });
  }

  async function withdraw() {
    await authApi.remove().catch(() => undefined);
    await logout();
    setConfirming(null);
    setNotice({ where: "withdraw", text: "탈퇴가 완료됐어요." });
  }

  return (
    <ScrollView contentContainerStyle={styles.content}>
      <View style={styles.group}>
        <Text style={styles.title}>검색</Text>

        <View style={styles.row}>
          <View style={styles.labelCol}>
            <Text style={styles.label}>한국어 노래 표시</Text>
            <Text style={styles.desc}>
              일본곡 전용이지만 필요하다면 한국어 노래도 표시할 수 있습니다.
            </Text>
          </View>
          <Pressable
            style={[styles.switch, settings.showKorean && styles.switchOn]}
            onPress={() => update({ showKorean: !settings.showKorean })}
            hitSlop={8}
            accessibilityRole="switch"
            accessibilityState={{ checked: settings.showKorean }}
            accessibilityLabel="한국어 노래 표시"
          >
            <View style={[styles.knob, settings.showKorean && styles.knobOn]} />
          </Pressable>
        </View>

        <View style={[styles.row, styles.stack]}>
          <View>
            <Text style={styles.label}>정렬 기준</Text>
          </View>
          <View>
            <Segmented
              label="정렬 기준"
              options={SORT_OPTIONS}
              value={settings.sort}
              onChange={(sort) => update({ sort })}
            />
          </View>
        </View>
      </View>

      <View style={styles.group}>
        <Text style={styles.title}>데이터</Text>

        <Pressable
          style={styles.action}
          onPress={exportFavorites}
          accessibilityRole="button"
        >
          <Text style={styles.label}>즐겨찾기 내보내기</Text>
        </Pressable>
        <Notice where="export" />

        <Pressable
          style={styles.action}
          onPress={() => setConfirming("clear")}
          accessibilityRole="button"
        >
          <Text style={styles.label}>즐겨찾기 전체 삭제</Text>
        </Pressable>
        <Notice where="clear" />
      </View>

      <View style={styles.group}>
        <Text style={styles.title}>정보</Text>

        <Info label="앱 버전" value={APP_VERSION} />
        <Info label="노래 정보" value="태진 · 금영 · manana" />
        <Info label="글꼴" value="여기어때 잘난체" />
        <Info
          label="문의"
          value={CONTACT}
          onPress={() => Linking.openURL(`mailto:${CONTACT}`)}
        />
        {/* 로그인 여부와 관계없이 보여야 하고, 첫 화면에서 3단계 이내여야 한다 */}
        <Info
          label="이용약관"
          value="보기"
          onPress={() => Linking.openURL(TERMS_URL)}
        />
        <Info
          label="개인정보 처리방침"
          value="보기"
          onPress={() => Linking.openURL(PRIVACY_URL)}
        />

        <Text style={styles.legal}>
          이 앱에는 ㈜여기어때컴퍼니가 제공한 여기어때 잘난체가 적용되어
          있습니다. 곡 정보는 태진미디어·금영엔터테인먼트 및 manana API에서
          가져옵니다.
        </Text>
      </View>

      {/* App Store 심사 기준 5.1.1(v): 가입이 되는 앱은 앱 안에서 탈퇴할 수 있어야 한다 */}
      {session && (
        <View style={styles.group}>
          <Pressable
            onPress={() => setConfirming("withdraw")}
            accessibilityRole="button"
          >
            <Text style={styles.withdraw}>회원탈퇴</Text>
          </Pressable>
          <Notice where="withdraw" />
        </View>
      )}

      {confirming && (
        <Modal
          title={confirming === "clear" ? "즐겨찾기 전체 삭제" : "회원탈퇴"}
          onClose={() => setConfirming(null)}
        >
          <Text style={styles.confirm}>
            {confirming === "clear"
              ? "담아둔 곡이 모두 사라져요. 되돌릴 수 없어요."
              : "계정과 담아둔 곡이 모두 사라져요. 되돌릴 수 없어요."}
          </Text>
          <View style={styles.confirmButtons}>
            <Pressable
              style={styles.cancel}
              onPress={() => setConfirming(null)}
              accessibilityRole="button"
            >
              <Text style={styles.cancelText}>취소</Text>
            </Pressable>
            <Pressable
              style={styles.danger}
              onPress={confirming === "clear" ? clearFavorites : withdraw}
              accessibilityRole="button"
            >
              <Text style={styles.dangerText}>
                {confirming === "clear" ? "삭제" : "탈퇴"}
              </Text>
            </Pressable>
          </View>
        </Modal>
      )}
    </ScrollView>
  );
}

function Info({
  label,
  value,
  onPress,
}: {
  label: string;
  value: string;
  onPress?: () => void;
}) {
  const body = (
    <>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={[styles.infoValue, onPress && styles.infoLink]}>
        {value}
      </Text>
    </>
  );
  return onPress ? (
    <Pressable style={styles.info} onPress={onPress} accessibilityRole="link">
      {body}
    </Pressable>
  ) : (
    <View style={styles.info}>{body}</View>
  );
}

const styles = StyleSheet.create({
  content: {
    gap: 22,
    paddingTop: 18,
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  group: { gap: 2 },
  title: {
    marginBottom: 8,
    color: colors.ink,
    fontFamily: fonts.handBold,
    fontSize: 19,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 14,
    paddingVertical: 12,
    paddingHorizontal: 2,
    borderBottomWidth: 1,
    borderBottomColor: colors.lineThin,
  },
  stack: { flexDirection: "column", alignItems: "stretch", gap: 10 },
  labelCol: { flex: 1 },
  label: { color: colors.ink, fontFamily: fonts.body, fontSize: 14 },
  desc: {
    marginTop: 3,
    color: colors.inkFaint,
    fontFamily: fonts.body,
    fontSize: 11.5,
    lineHeight: 17,
  },
  action: {
    paddingVertical: 12,
    paddingHorizontal: 2,
    borderBottomWidth: 1,
    borderBottomColor: colors.lineThin,
  },
  switch: {
    width: 44,
    height: 26,
    justifyContent: "center",
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
    backgroundColor: colors.ivoryDeep,
  },
  switchOn: { borderColor: colors.accent, backgroundColor: colors.accent },
  knob: {
    width: 18,
    height: 18,
    marginLeft: 3,
    borderRadius: 9,
    backgroundColor: colors.paper,
  },
  knobOn: { marginLeft: 20 },
  notice: {
    marginTop: 6,
    marginHorizontal: 2,
    marginBottom: 2,
    color: colors.inkSoft,
    fontFamily: fonts.body,
    fontSize: 12.5,
  },
  info: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    paddingVertical: 10,
    paddingHorizontal: 2,
    borderBottomWidth: 1,
    borderBottomColor: colors.lineThin,
  },
  infoLabel: { color: colors.inkSoft, fontFamily: fonts.body, fontSize: 13 },
  infoValue: { color: colors.ink, fontFamily: fonts.body, fontSize: 13 },
  infoLink: {},
  legal: {
    marginTop: 12,
    marginHorizontal: 2,
    color: colors.inkFaint,
    fontFamily: fonts.body,
    fontSize: 11,
    lineHeight: 17.6,
  },
  withdraw: {
    alignSelf: "flex-start",
    paddingVertical: 8,
    paddingHorizontal: 2,
    color: colors.inkFaint,
    fontFamily: fonts.body,
    fontSize: 12.5,
    textDecorationLine: "underline",
  },
  confirm: {
    marginBottom: 16,
    color: colors.inkSoft,
    fontFamily: fonts.body,
    fontSize: 13.5,
    lineHeight: 21.6,
  },
  confirmButtons: { flexDirection: "row", gap: 8 },
  cancel: {
    flex: 1,
    padding: 11,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
  },
  cancelText: {
    color: colors.inkSoft,
    fontFamily: fonts.bodyBold,
    fontSize: 13.5,
  },
  danger: {
    flex: 1,
    padding: 11,
    alignItems: "center",
    borderRadius: 999,
    backgroundColor: colors.kumyoung,
  },
  dangerText: {
    color: colors.paper,
    fontFamily: fonts.bodyBold,
    fontSize: 13.5,
  },
});
