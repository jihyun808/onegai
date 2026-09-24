import { StyleSheet } from 'react-native'

import { colors, fonts } from '../theme'

/** 로그인·가입·내 정보 수정이 함께 쓰는 입력 모양 (웹 AuthForm.css). */
export const form = StyleSheet.create({
  wrap: { gap: 13 },
  field: { gap: 5 },
  label: { color: colors.inkSoft, fontFamily: fonts.bodySemi, fontSize: 12 },
  input: {
    paddingVertical: 11,
    paddingHorizontal: 13,
    borderWidth: 1,
    borderColor: colors.lineThin,
    borderRadius: 12,
    backgroundColor: colors.paper,
    color: colors.ink,
    fontFamily: fonts.body,
    fontSize: 16,
  },
  inputFocus: { borderColor: colors.line },
  inputInvalid: { borderColor: colors.kumyoung },
  hint: { color: colors.kumyoung, fontFamily: fonts.body, fontSize: 11.5, lineHeight: 16 },
  error: { color: colors.kumyoung, fontFamily: fonts.body, fontSize: 12, lineHeight: 17 },
  submit: {
    marginTop: 4,
    padding: 12,
    alignItems: 'center',
    borderRadius: 999,
    backgroundColor: colors.accent,
  },
  submitDisabled: { opacity: 0.55 },
  submitText: { color: colors.paper, fontFamily: fonts.bodyBold, fontSize: 14 },
})
