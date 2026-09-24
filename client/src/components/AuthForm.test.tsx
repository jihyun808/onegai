import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { AuthForm } from './AuthForm'

const ID = 'jihyeon'
const PW = 'password123'

async function fillSignup(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText('아이디'), ID)
  await user.type(screen.getByLabelText('비밀번호'), PW)
  await user.type(screen.getByLabelText('비밀번호 확인'), PW)
}

describe('AuthForm — 가입 동의', () => {
  it('동의하지 않으면 가입 요청을 보내지 않는다', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<AuthForm mode="signup" onSubmit={onSubmit} />)

    await fillSignup(user)
    await user.click(screen.getByRole('button', { name: '가입하기' }))

    expect(onSubmit).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('필수 항목에 동의해야')
  })

  it('둘 중 하나만 체크해도 막는다', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<AuthForm mode="signup" onSubmit={onSubmit} />)

    await fillSignup(user)
    await user.click(screen.getByRole('checkbox', { name: /이용약관/ }))
    await user.click(screen.getByRole('button', { name: '가입하기' }))

    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('둘 다 체크하면 가입된다', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn().mockResolvedValue(undefined)
    render(<AuthForm mode="signup" onSubmit={onSubmit} />)

    await fillSignup(user)
    await user.click(screen.getByRole('checkbox', { name: /이용약관/ }))
    await user.click(screen.getByRole('checkbox', { name: /개인정보 수집·이용/ }))
    await user.click(screen.getByRole('button', { name: '가입하기' }))

    expect(onSubmit).toHaveBeenCalledWith(ID, PW)
  })

  it('약관 링크는 새 탭으로 안전하게 연다', () => {
    render(<AuthForm mode="signup" onSubmit={vi.fn()} />)

    for (const name of ['이용약관', '개인정보 수집·이용']) {
      const link = screen.getByRole('link', { name })
      expect(link).toHaveAttribute('target', '_blank')
      expect(link).toHaveAttribute('rel', 'noopener noreferrer')
    }
  })

  it('로그인 화면에는 동의 절차가 없다', () => {
    render(<AuthForm mode="login" onSubmit={vi.fn()} />)
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument()
  })
})
