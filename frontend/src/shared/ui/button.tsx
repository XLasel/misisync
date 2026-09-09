import Link from 'next/link'
import type { ComponentProps } from 'react'

import { classNames } from '@/shared/lib/class-names'

import s from './button.module.css'

type Variant = 'primary' | 'secondary'

function buttonClassName(variant: Variant, className?: string) {
  return classNames(s.root, variant === 'secondary' && s.secondary, className)
}

export function Button({
  className,
  variant = 'primary',
  ...props
}: ComponentProps<'button'> & { variant?: Variant }) {
  return <button className={buttonClassName(variant, className)} {...props} />
}

export function ButtonLink({
  className,
  variant = 'primary',
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant }) {
  return <Link className={buttonClassName(variant, className)} {...props} />
}
