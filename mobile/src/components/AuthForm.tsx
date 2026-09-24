import { useState } from 'react'
import { Linking, Pressable, StyleSheet, Text, TextInput, View } from 'react-native'

import { PRIVACY_URL, TERMS_URL } from '../config'
import { colors, fonts } from '../theme'
import { AuthRequestError } from '../utils/auth'
import { form } from './formStyles'

export type AuthMode = 'login' | 'signup'

const ID_MIN = 5
const ID_MAX = 20
// 비밀번호는 최소 길이만 본다. 상한을 두면 긴 암호구절을 쓰는 사람이 막힌다.
const PW_MIN = 8

interface Props {
  mode: AuthMode
  onSubmit: (id: string, password: string) => Promise<void>
}

function Check({
  checked,
  onToggle,
  label,
  url,
}: {
  checked: boolean
  onToggle: () => void
  label: string
  url: string
}) {
  return (
    <View style={styles.check}>
      <Pressable
        style={[styles.box, checked && styles.boxOn]}
        onPress={onToggle}
        hitSlop={8}
        accessibilityRole="checkbox"
        accessibilityState={{ checked }}
        accessibilityLabel={`${label} 동의 (필수)`}
      >
        {checked && <Text style={styles.tick}>✓</Text>}
      </Pressable>
      <Text style={styles.checkText}>
        <Text style={styles.link} onPress={() => Linking.openURL(url)}>
          {label}
        </Text>
        에 동의합니다 <Text style={styles.required}>(필수)</Text>
      </Text>
    </View>
  )
}

export function AuthForm({ mode, onSubmit }: Props) {
  const [id, setId] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  // 약관과 개인정보 수집·이용은 성격이 달라 따로 받는다.
  const [agreed, setAgreed] = useState({ terms: false, privacy: false })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)

  const isSignup = mode === 'signup'

  function validate(): Record<string, string> {
    const found: Record<string, string> = {}

    if (id.length < ID_MIN || id.length > ID_MAX) {
      found.username = `아이디는 ${ID_MIN}~${ID_MAX}자로 입력해 주세요.`
    } else if (!/^[a-zA-Z0-9_]+$/.test(id)) {
      found.username = '아이디는 영문, 숫자, 밑줄만 쓸 수 있어요.'
    }
    if (password.length < PW_MIN) {
      found.password = `비밀번호는 ${PW_MIN}자 이상으로 입력해 주세요.`
    }
    if (isSignup && password !== confirm) {
      found.confirm = '비밀번호가 서로 달라요.'
    }
    if (isSignup && !(agreed.terms && agreed.privacy)) {
      found.agree = '필수 항목에 동의해야 가입할 수 있어요.'
    }
    return found
  }

  async function handleSubmit() {
    const problems = validate()
    if (Object.keys(problems).length > 0) {
      setErrors(problems)
      return
    }

    setErrors({})
    setBusy(true)
    try {
      await onSubmit(id, password)
    } catch (err) {
      // 서버가 알려준 필드에 붙인다. 모르면 폼 전체 오류로 둔다.
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
      <View style={form.field}>
        <Text style={form.label}>아이디</Text>
        <TextInput
          style={[form.input, errors.username && form.inputInvalid]}
          value={id}
          onChangeText={(value) => setId(value.trim())}
          autoComplete="username"
          textContentType="username"
          autoCapitalize="none"
          autoCorrect={false}
          maxLength={ID_MAX}
          placeholder={`${ID_MIN}~${ID_MAX}자 영문·숫자`}
          placeholderTextColor={colors.inkFaint}
        />
        {errors.username && <Text style={form.hint}>{errors.username}</Text>}
      </View>

      <View style={form.field}>
        <Text style={form.label}>비밀번호</Text>
        <TextInput
          style={[form.input, errors.password && form.inputInvalid]}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          autoComplete={isSignup ? 'new-password' : 'current-password'}
          textContentType={isSignup ? 'newPassword' : 'password'}
          placeholder={`${PW_MIN}자 이상`}
          placeholderTextColor={colors.inkFaint}
        />
        {errors.password && <Text style={form.hint}>{errors.password}</Text>}
      </View>

      {isSignup && (
        <View style={form.field}>
          <Text style={form.label}>비밀번호 확인</Text>
          <TextInput
            style={[form.input, errors.confirm && form.inputInvalid]}
            value={confirm}
            onChangeText={setConfirm}
            secureTextEntry
            autoComplete="new-password"
            textContentType="newPassword"
            placeholder="한 번 더 입력해 주세요"
            placeholderTextColor={colors.inkFaint}
          />
          {errors.confirm && <Text style={form.hint}>{errors.confirm}</Text>}
        </View>
      )}

      {isSignup && (
        <View style={styles.agree}>
          <Text style={styles.agreeTitle}>약관 동의</Text>
          <Check
            checked={agreed.terms}
            onToggle={() => setAgreed((prev) => ({ ...prev, terms: !prev.terms }))}
            label="이용약관"
            url={TERMS_URL}
          />
          <Check
            checked={agreed.privacy}
            onToggle={() => setAgreed((prev) => ({ ...prev, privacy: !prev.privacy }))}
            label="개인정보 수집·이용"
            url={PRIVACY_URL}
          />
          <Text style={styles.note}>아이디와 비밀번호만 저장하며, 탈퇴하면 즉시 지워져요.</Text>
          {errors.agree && <Text style={form.hint}>{errors.agree}</Text>}
        </View>
      )}

      {errors.form && <Text style={form.error}>{errors.form}</Text>}

      <Pressable
        style={[form.submit, busy && form.submitDisabled]}
        onPress={handleSubmit}
        disabled={busy}
        accessibilityRole="button"
      >
        <Text style={form.submitText}>
          {busy ? '잠시만요…' : isSignup ? '가입하기' : '로그인'}
        </Text>
      </Pressable>
    </View>
  )
}

const styles = StyleSheet.create({
  agree: {
    gap: 2,
    marginTop: 4,
    paddingVertical: 12,
    paddingHorizontal: 14,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 12,
  },
  agreeTitle: { color: colors.inkSoft, fontFamily: fonts.bodyBold, fontSize: 12, marginBottom: 2 },
  check: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, paddingVertical: 4 },
  box: {
    width: 17,
    height: 17,
    marginTop: 2,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: colors.inkSoft,
    borderRadius: 4,
    backgroundColor: colors.paper,
  },
  boxOn: { borderColor: colors.accent, backgroundColor: colors.accent },
  tick: { color: colors.paper, fontSize: 12, fontWeight: '700', lineHeight: 14 },
  checkText: { flex: 1, color: colors.ink, fontFamily: fonts.body, fontSize: 13, lineHeight: 19.5 },
  link: { color: colors.ink, textDecorationLine: 'underline' },
  required: { color: colors.kumyoung, fontFamily: fonts.bodyBold },
  note: { marginTop: 6, color: colors.inkFaint, fontFamily: fonts.body, fontSize: 11.5 },
})
