import { useState } from 'react'
import { Image, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'

import type { Session } from '../hooks/useAuth'
import { colors, fonts } from '../theme'
import { AuthRequestError } from '../utils/auth'
import { ImageError, pickAvatarDataUrl } from '../utils/image'
import { form } from './formStyles'

const ID_MIN = 5
const ID_MAX = 20

interface Props {
  session: Session
  onSave: (patch: { username?: string; avatar?: string }) => Promise<void>
}

export function ProfileForm({ session, onSave }: Props) {
  const [username, setUsername] = useState(session.username)
  const [avatar, setAvatar] = useState(session.avatar ?? '')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  async function pickImage() {
    try {
      const picked = await pickAvatarDataUrl()
      if (picked) {
        setAvatar(picked)
        setErrors({})
      }
    } catch (err) {
      setErrors({
        avatar: err instanceof ImageError ? err.message : '이미지를 처리하지 못했어요.',
      })
    }
  }

  async function handleSubmit() {
    if (username.length < ID_MIN || username.length > ID_MAX) {
      setErrors({ username: `아이디는 ${ID_MIN}~${ID_MAX}자로 입력해 주세요.` })
      return
    }
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      setErrors({ username: '아이디는 영문, 숫자, 밑줄만 쓸 수 있어요.' })
      return
    }

    setErrors({})
    setBusy(true)
    try {
      await onSave({ username, avatar })
    } catch (err) {
      if (err instanceof AuthRequestError && err.field) {
        setErrors({ [err.field]: err.message })
      } else {
        setErrors({
          form: err instanceof Error ? err.message : '잠시 후 다시 시도해 주세요.',
        })
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <View style={form.wrap}>
      <View style={styles.avatarRow}>
        <View style={styles.avatar}>
          {avatar ? <Image source={{ uri: avatar }} style={StyleSheet.absoluteFill} /> : null}
        </View>
        <View style={styles.actions}>
          <View style={styles.buttons}>
            <Pressable style={styles.pick} onPress={pickImage} accessibilityRole="button">
              <Text style={styles.pickText}>사진 바꾸기</Text>
            </Pressable>
            {avatar ? (
              <Pressable style={styles.pick} onPress={() => setAvatar('')} accessibilityRole="button">
                <Text style={styles.pickText}>지우기</Text>
              </Pressable>
            ) : null}
          </View>
          <Text style={styles.hint}>사진첩에서 골라 정사각형으로 잘라요</Text>
        </View>
      </View>

      <View style={form.field}>
        <Text style={form.label}>아이디</Text>
        <TextInput
          style={[form.input, errors.username && form.inputInvalid]}
          value={username}
          onChangeText={(value) => setUsername(value.trim())}
          autoCapitalize="none"
          autoCorrect={false}
          maxLength={ID_MAX}
        />
        {errors.username && <Text style={form.hint}>{errors.username}</Text>}
      </View>

      {(errors.avatar || errors.form) && (
        <Text style={form.error}>{errors.avatar || errors.form}</Text>
      )}

      <Pressable
        style={[form.submit, busy && form.submitDisabled]}
        onPress={handleSubmit}
        disabled={busy}
        accessibilityRole="button"
      >
        <Text style={form.submitText}>{busy ? '저장 중…' : '저장'}</Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  avatarRow: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 4 },
  avatar: {
    width: 64,
    height: 64,
    overflow: 'hidden',
    borderRadius: 32,
    backgroundColor: colors.ivoryDeep,
  },
  actions: { flex: 1, gap: 6 },
  buttons: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  pick: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 999,
  },
  pickText: { color: colors.inkSoft, fontFamily: fonts.bodySemi, fontSize: 12 },
  hint: { color: colors.inkFaint, fontFamily: fonts.body, fontSize: 11 },
})
