import { useMemo, useState } from 'react'
import { FlatList, Image, Pressable, StyleSheet, Text, View } from 'react-native'

import { AuthForm, type AuthMode } from '../components/AuthForm'
import { Modal } from '../components/Modal'
import { ProfileForm } from '../components/ProfileForm'
import { SongCard } from '../components/SongCard'
import { StateMessage } from '../components/StateMessage'
import { useAuth } from '../hooks/useAuth'
import { useBookmarks, type Bookmark } from '../hooks/useBookmarks'
import { Sketch } from '../components/Sketch'
import { colors, fonts } from '../theme'
import type { SongGroup } from '../types/karaoke'

type Sort = 'recent' | 'oldest' | 'title'

const SORTS: { value: Sort; label: string }[] = [
  { value: 'recent', label: '최신순' },
  { value: 'oldest', label: '오래된순' },
  { value: 'title', label: '글자순' },
]

function toGroup(bookmark: Bookmark): SongGroup {
  return {
    title: bookmark.title,
    singer: bookmark.singer,
    match_key: bookmark.match_key,
    brands: bookmark.brands,
    both: Object.keys(bookmark.brands).length > 1,
  }
}

export function MyScreen() {
  const { session, login, signup, logout, updateProfile } = useAuth()
  const { items, toggle, has } = useBookmarks(Boolean(session))
  const [sort, setSort] = useState<Sort>('recent')
  const [auth, setAuth] = useState<AuthMode | null>(null)
  const [editing, setEditing] = useState(false)

  const sorted = useMemo(() => {
    const copy = [...items]
    if (sort === 'title') {
      return copy.sort((a, b) => a.title.localeCompare(b.title, 'ko'))
    }
    copy.sort((a, b) => a.saved_at.localeCompare(b.saved_at))
    return sort === 'recent' ? copy.reverse() : copy
  }, [items, sort])

  const header = (
    <View style={styles.header}>
      <Sketch style={styles.profile}>
        <View style={styles.avatar}>
          {session?.avatar ? (
            <Image source={{ uri: session.avatar }} style={StyleSheet.absoluteFill} />
          ) : null}
        </View>
        <View style={styles.profileBody}>
          {session ? (
            <>
              <Text style={styles.name}>{session.username}</Text>
              <View style={styles.links}>
                <Pressable onPress={() => setEditing(true)} accessibilityRole="button">
                  <Text style={styles.link}>내 정보 수정</Text>
                </Pressable>
                <Text style={styles.divider}>|</Text>
                <Pressable onPress={logout} accessibilityRole="button">
                  <Text style={styles.link}>로그아웃</Text>
                </Pressable>
              </View>
            </>
          ) : (
            <>
              <Text style={styles.name}>로그인 전이에요</Text>
              <Text style={styles.note}>지금은 이 기기에만 저장돼요.</Text>
              <View style={styles.buttons}>
                <Pressable style={styles.action} onPress={() => setAuth('login')} accessibilityRole="button">
                  <Text style={styles.actionText}>로그인</Text>
                </Pressable>
                <Pressable style={styles.action} onPress={() => setAuth('signup')} accessibilityRole="button">
                  <Text style={styles.actionText}>회원가입</Text>
                </Pressable>
              </View>
            </>
          )}
        </View>
      </Sketch>

      <View style={styles.head}>
        <Text style={styles.heading}>
          내가 좋아하는 노래 <Text style={styles.count}>{items.length}</Text>
        </Text>
        {items.length > 0 && (
          <View style={styles.sorts}>
            {SORTS.map((option) => {
              const on = sort === option.value
              return (
                <Pressable
                  key={option.value}
                  onPress={() => setSort(option.value)}
                  accessibilityRole="button"
                  accessibilityState={{ selected: on }}
                >
                  <Text style={[styles.sort, on && styles.sortOn]}>{option.label}</Text>
                </Pressable>
              )
            })}
          </View>
        )}
      </View>
    </View>
  )

  return (
    <>
      <FlatList
        data={sorted}
        keyExtractor={(item) => item.match_key}
        renderItem={({ item, index }) => {
          const group = toGroup(item)
          return (
            <View style={index > 0 && styles.gap}>
              <SongCard
                group={group}
                index={index}
                bookmarked={has(group.match_key)}
                onToggleBookmark={toggle}
              />
            </View>
          )
        }}
        ListHeaderComponent={header}
        ListEmptyComponent={
          <StateMessage
            title="저장한 노래가 없어요"
            description="검색 결과에서 북마크를 눌러 담아보세요"
          />
        }
        contentContainerStyle={styles.content}
      />

      {auth && (
        <Modal title={auth === 'login' ? '로그인' : '회원가입'} onClose={() => setAuth(null)}>
          <AuthForm
            mode={auth}
            onSubmit={async (id, password) => {
              await (auth === 'login' ? login(id, password) : signup(id, password))
              setAuth(null)
            }}
          />
        </Modal>
      )}

      {editing && session && (
        <Modal title="내 정보 수정" onClose={() => setEditing(false)}>
          <ProfileForm
            session={session}
            onSave={async (patch) => {
              await updateProfile(patch)
              setEditing(false)
            }}
          />
        </Modal>
      )}
    </>
  )
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: 16, paddingBottom: 20 },
  header: {},
  profile: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    marginTop: 14,
    marginHorizontal: 4,
    paddingVertical: 18,
    paddingLeft: 20,
    paddingRight: 18,
  },
  avatar: {
    width: 54,
    height: 54,
    overflow: 'hidden',
    borderRadius: 27,
    backgroundColor: colors.ivoryDeep,
  },
  profileBody: { flex: 1, minWidth: 0 },
  name: { color: colors.ink, fontFamily: fonts.handBold, fontSize: 19 },
  note: { marginTop: 2, color: colors.inkSoft, fontFamily: fonts.body, fontSize: 12, lineHeight: 17 },
  links: { flexDirection: 'row', alignItems: 'center', gap: 7, marginTop: 5 },
  link: { color: colors.inkFaint, fontFamily: fonts.body, fontSize: 11.5 },
  divider: { color: colors.lineThin, fontSize: 10 },
  buttons: { flexDirection: 'row', gap: 8, marginTop: 9 },
  action: {
    paddingVertical: 7,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
  },
  actionText: { color: colors.inkSoft, fontFamily: fonts.bodySemi, fontSize: 12 },
  head: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'baseline',
    columnGap: 10,
    rowGap: 4,
    marginTop: 20,
    marginHorizontal: 4,
    marginBottom: 12,
    paddingTop: 16,
    borderTopWidth: 1,
    borderTopColor: colors.lineThin,
  },
  heading: { color: colors.ink, fontFamily: fonts.handBold, fontSize: 21 },
  count: { color: colors.accent },
  sorts: { flexDirection: 'row', gap: 8 },
  sort: { color: colors.inkFaint, fontFamily: fonts.body, fontSize: 12 },
  sortOn: { color: colors.ink, fontFamily: fonts.bodyBold, textDecorationLine: 'underline' },
  gap: { marginTop: 11 },
})
