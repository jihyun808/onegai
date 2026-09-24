import {
  KeyboardAvoidingView,
  Modal as RNModal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native'

import { colors, fonts } from '../theme'
import { CloseIcon } from './icons'
import { Sketch } from './Sketch'

interface Props {
  title: string
  onClose: () => void
  children: React.ReactNode
}

/** 가운데 뜨는 대화상자. 바깥을 누르거나 뒤로가기로 닫힌다. */
export function Modal({ title, onClose, children }: Props) {
  return (
    <RNModal visible transparent animationType="fade" onRequestClose={onClose}>
      <KeyboardAvoidingView
        style={styles.backdrop}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="닫기" />
        <Sketch variant={1} style={styles.panel}>
          <View style={styles.head}>
            <Text style={styles.title} numberOfLines={2}>
              {title}
            </Text>
            <Pressable
              style={styles.close}
              onPress={onClose}
              hitSlop={8}
              accessibilityRole="button"
              accessibilityLabel="닫기"
            >
              <CloseIcon size={13} color={colors.inkSoft} />
            </Pressable>
          </View>
          <ScrollView keyboardShouldPersistTaps="handled" bounces={false}>
            {children}
          </ScrollView>
        </Sketch>
      </KeyboardAvoidingView>
    </RNModal>
  )
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 20,
    backgroundColor: 'rgba(47,42,36,0.38)',
  },
  panel: {
    width: '100%',
    maxWidth: 340,
    maxHeight: '85%',
    paddingTop: 20,
    paddingHorizontal: 22,
    paddingBottom: 22,
  },
  head: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
    marginBottom: 16,
  },
  title: { flex: 1, color: colors.ink, fontFamily: fonts.handBold, fontSize: 21 },
  close: {
    width: 26,
    height: 26,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 13,
    backgroundColor: colors.ivoryDeep,
  },
})
